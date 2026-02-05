"""Crawler service for URL discovery and persistence."""

import asyncio
import logging

from sqlmodel import Session

from alguerisme.core.crawler.crawler import Crawler
from alguerisme.core.crawler.models import CrawlServiceStats
from alguerisme.core.database.crud import get_or_create_entry_url
from alguerisme.utils.alphabet import Letter

logger = logging.getLogger(__name__)


class CrawlerService:
    """Service for crawling dictionary and persisting URLs."""

    def __init__(self, crawler: Crawler, session: Session):
        """Initialize the crawler service."""
        self.crawler = crawler
        self.session = session

    async def run(self, letters: list[Letter]) -> CrawlServiceStats:
        """Crawl the dictionary for the given letters and save URLs to the DB.

        Parameters
        ----------
            letters: list[Letter]
                List of validated Letter objects to crawl

        Returns
        -------
            CrawlServiceStats
                Statistics from the crawl operation

        """
        logger.info(f"Starting async crawl and save for letters: {letters}")

        stats = CrawlServiceStats.empty()

        # Iterate over the async generator
        async for page_result in self.crawler.stream(letters):
            stats.crawled_pages += 1

            if not page_result.success or not page_result.urls:
                continue

            saved, skipped, failed = await asyncio.to_thread(
                self._save_batch_sync, page_result.urls, page_result.letter
            )

            stats.urls_saved += saved
            stats.urls_skipped += skipped
            stats.urls_failed += failed

            logger.debug(
                f"Processed page {page_result.page_number} for {page_result.letter}: "
                f"+{saved} new URLs"
            )

        logger.info("Crawl complete")
        logger.info(stats.summary())

        return stats

    def _save_batch_sync(self, urls: set[str], letter: Letter) -> tuple[int, int, int]:
        """Save a batch of URLs synchronously.

        Parameters
        ----------
            urls: set[str]
                Set of URL strings to save
            letter: Letter
                Letter object associated with these URLs

        Returns
        -------
            tuple[int, int, int]
                Tuple of (saved_count, skipped_count, failed_count)

        """
        saved_count = 0
        skipped_count = 0
        failed_count = 0

        try:
            for url in urls:
                try:
                    # Convert Letter to str at DB boundary
                    _, created = get_or_create_entry_url(self.session, url, str(letter))
                    if created:
                        saved_count += 1
                    else:
                        skipped_count += 1
                except Exception as e:
                    failed_count += 1
                    logger.error(f"Failed to save URL {url}: {e}")

            # Commit the batch
            self.session.commit()

        except Exception as e:
            logger.error(f"Critical DB error saving batch for {letter}: {e}")
            self.session.rollback()
            # If the commit failed, everything in this batch failed
            failed_count += saved_count + skipped_count
            saved_count = 0
            skipped_count = 0

        return saved_count, skipped_count, failed_count
