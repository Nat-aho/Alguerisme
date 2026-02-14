"""Crawler service for URL discovery and persistence."""

import logging

from sqlmodel import Session

from alguerisme.core.crawler.crawler import Crawler
from alguerisme.core.crawler.models import CrawlStats
from alguerisme.core.database.crud import get_or_add_entry_url_to_session
from alguerisme.utils.alphabet import Letter

logger = logging.getLogger(__name__)


class CrawlerService:
    """Service for crawling dictionary and persisting URLs."""

    def __init__(self, crawler: Crawler, session: Session):
        """Initialize the crawler service."""
        self.crawler = crawler
        self.session = session

    async def run(self, letters: list[Letter]) -> CrawlStats:
        """Crawl the dictionary for the given letters and save URLs to the DB.

        Parameters
        ----------
            letters: list[Letter]
                List of validated Letter objects to crawl

        Returns
        -------
            CrawlStats
                Statistics from the crawl operation

        """
        logger.info(f"Starting async crawl and save for letters: {letters}")

        stats = CrawlStats.empty()

        # Iterate over the async generator
        async for page_result in self.crawler.stream(letters):
            stats.crawled_pages += 1

            if not page_result.success or not page_result.urls:
                continue

            saved, skipped, failed = self._save_batch_sync(
                page_result.urls, page_result.letter
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

        Uses a retry strategy: attempts batch commit first for performance,
        then falls back to individual commits on failure to identify specific issues.

        Note: get_or_add_entry_url_to_session does NOT auto-commit.
        This service controls all transaction boundaries to enable proper
        batch processing and rollbacks.

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

        def process_url(url: str) -> None:
            """Process a single URL and update counts."""
            nonlocal saved_count, skipped_count
            # Convert Letter to str at DB boundary
            _, created = get_or_add_entry_url_to_session(self.session, url, str(letter))
            if created:
                saved_count += 1
            else:
                skipped_count += 1

        try:
            # Fast path: Attempt batch processing with single commit
            # All URLs are added to session but nothing is persisted until commit()
            for url in urls:
                process_url(url)
            self.session.commit()  # Single transaction for all URLs

        except Exception as e:
            # Batch commit failed - rollback discards ALL pending changes
            self.session.rollback()
            logger.warning(
                f"Batch commit failed for {letter}, "
                f"retrying {len(urls)} URLs individually: {e}"
            )

            # Reset counts - the rollback discarded all changes from the batch attempt
            saved_count = 0
            skipped_count = 0

            # Slow path: Retry each URL individually with per-URL commits
            # This allows partial success - some URLs may commit while others fail
            for url in urls:
                try:
                    process_url(url)
                    self.session.commit()  # Individual transaction per URL
                except Exception as individual_e:
                    self.session.rollback()
                    failed_count += 1
                    logger.error(f"Failed to save URL {url}: {individual_e}")

        return saved_count, skipped_count, failed_count
