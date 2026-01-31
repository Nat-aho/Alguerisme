"""Utility functions for crawling vocabulary entry URLs from a web dictionary."""

import logging
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Dict, Sequence, Set

import requests

from alguerisme.configs.crawler import CrawlerConfig
from alguerisme.core.crawler.models import (
    CrawlResult,
    CrawlStatus,
    LetterCrawlResult,
    PageCrawlResult,
)
from alguerisme.core.http_client import HttpClientSession
from alguerisme.core.web_dictionary import WebDictionary

logger = logging.getLogger(__name__)


def fetch_urls_for_letters(
    letters: Sequence[str],
    web_dictionary: WebDictionary,
    http_client: HttpClientSession,
    crawler_config: CrawlerConfig,
) -> CrawlResult:
    """Fetch vocabulary entry URLs for multiple letters."""
    logger.info(f"Starting URL discovery for letters: {letters}")
    logger.info(f"Using {crawler_config.max_workers} parallel workers")

    urls_by_letter: Dict[str, Set[str]] = {}
    letters_successful = 0
    letters_failed = 0
    total_pages = 0
    letter_results = {}
    letters_completed = []

    with ThreadPoolExecutor(max_workers=crawler_config.max_workers) as executor:
        future_to_letter = {
            executor.submit(
                _fetch_letter_urls,
                letter,
                web_dictionary,
                http_client,
                crawler_config,
            ): letter
            for letter in letters
        }

        for future in as_completed(future_to_letter):
            letter = future_to_letter[future]
            try:
                result = future.result()
                letter_results[letter] = result
                letters_completed.append(letter)

                urls_by_letter[letter] = result.urls
                total_pages += result.pages_crawled

                if result.success:
                    letters_successful += 1
                    logger.info(
                        f"Letter '{letter}': {result.url_count} URLs discovered "
                        f"({result.pages_crawled} pages)"
                    )
                else:
                    letters_failed += 1
                    logger.warning(f"Letter '{letter}' failed: {result.stopped_reason}")

            except Exception as e:
                letters_failed += 1
                logger.exception(f"Unexpected error crawling letter '{letter}': {e}")
                letter_results[letter] = LetterCrawlResult.from_error(letter)

    logger.info("URL discovery complete")

    crawl_result = CrawlResult(
        urls_by_letter=urls_by_letter,
        letters_crawled=letters_completed,
        letters_successful=letters_successful,
        letters_failed=letters_failed,
        total_pages=total_pages,
        letter_results=letter_results,
    )

    logger.info(crawl_result.summary())

    return crawl_result


def _fetch_letter_urls(
    letter: str,
    web_dictionary: WebDictionary,
    http_client: HttpClientSession,
    crawler_config: CrawlerConfig,
) -> LetterCrawlResult:
    """Fetch vocabulary entry URLs for a single letter."""
    urls: Set[str] = set()
    page = 0
    pages_successful = 0

    logger.info(f"Fetching URLs for letter '{letter}'")

    try:
        keep_crawling = True
        while keep_crawling:
            page += 1
            page_result = _fetch_page_urls(letter, page, web_dictionary, http_client)

            if page_result.success:
                pages_successful += 1

            page_urls = page_result.urls
            new_urls = [url for url in page_urls if url not in urls]

            if not new_urls:
                logger.info(
                    f"No new URLs on page {page} for letter '{letter}'. "
                    "Stopping pagination."
                )
                keep_crawling = False

            urls.update(new_urls)
            logger.info(f"Page {page}: found {len(new_urls)} new URLs")

            delay = crawler_config.request_delay
            logger.debug(f"Sleeping {delay:.2f}s")

            time.sleep(delay)

        logger.info(f"Total {len(urls)} URLs found for letter '{letter}'")
        return LetterCrawlResult(
            letter=letter,
            urls=urls,
            pages_crawled=page,
            pages_successful=pages_successful,
            stopped_reason=CrawlStatus.COMPLETED,
        )

    except Exception as e:
        logger.exception(f"Error crawling letter '{letter}': {e}")
        return LetterCrawlResult.from_error(letter)


def _fetch_page_urls(
    letter: str,
    page: int,
    web_dictionary: WebDictionary,
    http_client: HttpClientSession,
) -> PageCrawlResult:
    """Fetch vocabulary URLs from a single index page."""
    index_url = web_dictionary.build_index_url(letter, page)

    try:
        logger.debug(f"Fetching URLs for letter '{letter}', page {page}: {index_url}")
        response = http_client.get(index_url)

        response.raise_for_status()

        page_urls = web_dictionary.parse_page_urls(response.text)
        unique_page_urls = set(page_urls)

        logger.debug(f"Found {len(unique_page_urls)} vocabulary URLs")
        if unique_page_urls:
            logger.debug(f"Sample URLs: {list(unique_page_urls)[:3]}")

        return PageCrawlResult(
            urls=unique_page_urls,
            status_code=response.status_code,
            page_number=page,
        )

    except requests.RequestException as e:
        status_code = getattr(
            getattr(e, "response", None),
            "status_code",
            500,
        )
        logger.warning(
            "Failed to fetch %s (status=%s): %s",
            index_url,
            status_code,
            e,
        )
        return PageCrawlResult.from_error(
            page_number=page,
            error=str(e),
            status_code=status_code,
        )

    except Exception as e:
        logger.exception(f"Unexpected error fetching {index_url}: {e}")
        return PageCrawlResult.from_error(
            page_number=page,
            error=str(e),
            status_code=500,
        )
