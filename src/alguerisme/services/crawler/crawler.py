"""Crawler service for URL discovery and persistence."""

import logging
from typing import Optional

from sqlmodel import Session

from alguerisme.core.crawler import Crawler, CrawlResult
from alguerisme.crud import get_or_create_entry_url
from alguerisme.services.crawler.models import CrawlServiceResult

logger = logging.getLogger(__name__)


class CrawlerService:
    """Service for crawling dictionary and persisting URLs.

    Orchestrates the crawler with database persistence, handling
    URL discovery, deduplication, and storage.

    Parameters
    ----------
    crawler : Crawler
        Configured crawler instance
    session : Session
        Database session for persistence

    """

    def __init__(self, crawler: Crawler, session: Session):
        """Initialize crawler service.

        Parameters
        ----------
        crawler : Crawler
            Configured crawler instance
        session : Session
            Database session for persistence

        """
        self.crawler = crawler
        self.session = session
        logger.info("CrawlerService initialized")

    def crawl_and_save(self, letters: Optional[list[str]] = None) -> CrawlServiceResult:
        """Crawl dictionary and save discovered URLs.

        Runs the crawler to discover URLs, then saves them to the database
        with proper letter associations. Handles deduplication automatically.

        Parameters
        ----------
        letters : Optional[list[str]]
            Letters to crawl, None for all letters

        Returns
        -------
        CrawlServiceResult
            Result containing crawl data and persistence statistics

        """
        logger.info(f"Starting crawl and save for letters: {letters}")

        # Run crawler (pure operation, no side effects)
        crawl_result = self.crawler.run(letters)

        logger.info(
            f"Crawl complete: {crawl_result.url_count} URLs discovered "
            f"across {crawl_result.total_pages} pages"
        )

        # Save URLs to database
        saved, skipped, failed = self._save_urls(crawl_result)

        logger.info(
            f"Persistence complete: {saved} new URLs saved, "
            f"{skipped} already existed, {failed} failed"
        )

        return CrawlServiceResult(
            crawl_result=crawl_result,
            urls_saved=saved,
            urls_skipped=skipped,
            urls_failed=failed,
        )

    def _save_urls(self, crawl_result: CrawlResult) -> tuple[int, int, int]:
        """Save URLs from crawl result to database.

        Parameters
        ----------
        crawl_result : CrawlResult
            Crawl result containing discovered URLs with letter info

        Returns
        -------
        tuple[int, int, int]
            Tuple of (saved_count, skipped_count, failed_count)

        """
        saved_count = 0
        skipped_count = 0
        failed_count = 0

        for letter, urls in crawl_result.urls_by_letter.items():
            for url in urls:
                try:
                    _, created = get_or_create_entry_url(self.session, url, letter)

                    if created:
                        saved_count += 1
                        logger.debug(f"Saved new URL: {url}")
                    else:
                        skipped_count += 1
                        logger.debug(f"URL already exists: {url}")

                except Exception as e:
                    failed_count += 1
                    logger.error(f"Failed to save URL {url}: {e}", exc_info=True)
                    # Continue with other URLs

        return saved_count, skipped_count, failed_count
