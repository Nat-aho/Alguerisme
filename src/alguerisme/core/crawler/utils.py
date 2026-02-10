"""Utility functions for crawling vocabulary entry URLs from a web dictionary."""

import asyncio
import logging
from typing import AsyncGenerator, Sequence, Set

from alguerisme.configs.crawler import CrawlerConfig
from alguerisme.core.crawler.models import PageCrawlResult
from alguerisme.core.http_client import HttpClientSession
from alguerisme.core.web_dictionary import WebDictionary
from alguerisme.utils.alphabet import Letter

logger = logging.getLogger(__name__)


async def stream_pages_async(
    letters: Sequence[Letter],
    web_dictionary: WebDictionary,
    http_client: HttpClientSession,
    crawler_config: CrawlerConfig,
) -> AsyncGenerator[PageCrawlResult, None]:
    """Stream crawl results page by page asynchronously.

    Parameters
    ----------
        letters: Sequence[Letter]
            List of validated Letter objects to crawl
        web_dictionary: WebDictionary
            WebDictionary instance for building URLs and parsing pages
        http_client: HttpClientSession
            HTTP client session for making requests to the web dictionary
        crawler_config: CrawlerConfig
            Configuration for the crawler behavior

    Yields
    ------
        PageCrawlResult
            Results for each crawled page

    """
    queue: asyncio.Queue[PageCrawlResult | None] = asyncio.Queue()

    producer = asyncio.create_task(
        _producer_task(queue, letters, web_dictionary, http_client, crawler_config)
    )

    while True:
        item = await queue.get()
        if item is None:
            break
        yield item

    await producer


async def _producer_task(
    queue: asyncio.Queue,
    letters: Sequence[Letter],
    web_dictionary: WebDictionary,
    http_client: HttpClientSession,
    crawler_config: CrawlerConfig,
):
    """Manage workers and push results to the queue.

    Uses TaskGroup for proper async task management. Individual letter failures
    are logged but don't stop other letters from being crawled. The sentinel
    value is guaranteed to be sent via the finally block.
    """
    semaphore = asyncio.Semaphore(crawler_config.max_workers)

    async def _worker_bridge(letter: Letter):
        """Bridge: Iterates the generator and pushes to queue.

        Catches and logs exceptions to allow other letters to continue processing.
        Critical errors in one letter won't stop the entire crawl.
        """
        try:
            async with semaphore:
                async for result in _crawl_letter_generator(
                    letter, web_dictionary, http_client, crawler_config
                ):
                    await queue.put(result)
        except Exception as e:
            logger.exception(f"[{letter}] Worker failed with unexpected error: {e}")
            # Don't re-raise - let other letters continue crawling

    try:
        # TaskGroup ensures proper cleanup and cancellation semantics
        async with asyncio.TaskGroup() as tg:
            for letter in letters:
                tg.create_task(_worker_bridge(letter))
    except* Exception as eg:
        # This should rarely happen since _worker_bridge catches exceptions
        # Only critical/unexpected errors (like asyncio bugs) would reach here
        logger.error(f"Critical error in task group: {eg}")
        raise
    finally:
        # CRITICAL: Always send sentinel to prevent consumer from hanging
        await queue.put(None)


async def _crawl_letter_generator(
    letter: Letter,
    web_dictionary: WebDictionary,
    http_client: HttpClientSession,
    crawler_config: CrawlerConfig,
) -> AsyncGenerator[PageCrawlResult, None]:
    """Crawl a single letter, yielding results page by page."""
    page = 1
    known_urls: Set[str] = set()
    logger.info(f"[{letter}] Starting crawl")

    while True:
        result = await _fetch_single_page(letter, page, web_dictionary, http_client)

        new_urls = [u for u in result.urls if u not in known_urls]
        known_urls.update(new_urls)

        if result.success:
            result = PageCrawlResult(
                letter=result.letter,
                page_number=result.page_number,
                urls=set(new_urls),
                status_code=result.status_code,
                error=result.error,
            )

        yield result

        if not result.success:
            logger.warning(f"[{letter}] Failed on page {page}. Stopping.")
            break

        if not new_urls:
            logger.info(f"[{letter}] No new URLs on page {page}. Stopping.")
            break

        page += 1
        await asyncio.sleep(crawler_config.request_delay)


async def _fetch_single_page(
    letter: Letter,
    page: int,
    web_dictionary: WebDictionary,
    http_client: HttpClientSession,
) -> PageCrawlResult:
    """Fetch and parse a single page for a given letter."""
    # Convert Letter to str at the boundary where we build URLs
    url = web_dictionary.build_index_url(str(letter), page)

    try:
        response = await http_client.get(url)

        page_urls = await asyncio.to_thread(
            web_dictionary.parse_page_urls, response.text
        )

        return PageCrawlResult(
            letter=letter,
            page_number=page,
            urls=set(page_urls),
            status_code=response.status_code,
        )

    except Exception as e:
        logger.error(f"[{letter}] Error on page {page}: {e}")
        status_code = 0
        response = getattr(e, "response", None)
        if response is not None and hasattr(response, "status_code"):
            status_code = getattr(response, "status_code", 0)
        return PageCrawlResult.from_error(
            letter=letter,
            page_number=page,
            error=str(e),
            status_code=status_code,
        )
