"""Service for collecting HTML from NEW vocabol dictionary entries."""

import asyncio
import logging
from uuid import UUID

from sqlmodel import Session

from alguerisme.core.collector.enums import CollectionStatus
from alguerisme.core.collector.html_collector import HTMLCollector
from alguerisme.core.collector.models import CollectionResult, CollectionStats
from alguerisme.core.collector.utils import calculate_content_hash
from alguerisme.core.database.crud import create_vocabols_raw_html
from alguerisme.core.database.models import EntryURLs, VocabolsRawHTMLCreate

logger = logging.getLogger(__name__)


class HTMLCollectorService:
    """Collects HTML for NEW vocabol dictionary entries.

    This service handles first-time HTML collection for vocabol URLs
    that haven't been collected yet.

    """

    def __init__(self, collector: HTMLCollector, session: Session):
        """Initialize the collector service.

        Parameters
        ----------
        collector : Collector
            Collector instance for fetching HTML
        session : Session
            Database session for persistence

        """
        self.collector = collector
        self.session = session

    async def run(
        self,
        entry_urls: list[EntryURLs],
        request_delay: float = 1.0,
        max_workers: int = 5,
    ) -> CollectionStats:
        """Collect HTML for new vocabol URLs.

        Parameters
        ----------
        entry_urls : list[EntryURLs]
            URLs to collect (should be pending/new URLs)
        request_delay : float
            Delay between requests in seconds
        max_workers : int
            Max concurrent requests

        Returns
        -------
        CollectionStats
            Statistics: collected, unchanged, changed, failed

        """
        logger.info(f"Starting new collection for {len(entry_urls)} URLs")

        stats = CollectionStats.empty()
        semaphore = asyncio.Semaphore(max_workers)

        async def _collect_with_limit(entry_url: EntryURLs) -> None:
            """Collect a single URL with rate limiting."""
            async with semaphore:
                result, status = await self._collect_url(entry_url.url, entry_url.id)

                # Update stats based on status
                if status == CollectionStatus.COLLECTED:
                    stats.urls_collected += 1
                    logger.debug(f"Collected: {entry_url.url}")
                elif status == CollectionStatus.FAILED:
                    stats.urls_failed += 1
                    logger.warning(f"Failed: {entry_url.url} - {result.error}")

                # Rate limit: wait before releasing semaphore slot
                await asyncio.sleep(request_delay)

        # Create tasks for all URLs
        tasks = [_collect_with_limit(url) for url in entry_urls]

        # Run all tasks concurrently
        await asyncio.gather(*tasks, return_exceptions=True)

        logger.info(stats.summary())

        return stats

    async def _collect_url(
        self, url: str, entry_url_id: UUID
    ) -> tuple[CollectionResult, CollectionStatus]:
        """Collect a single URL and save to database.

        Parameters
        ----------
        url : str
            URL to collect
        entry_url_id : UUID
            ID of the entry_urls record

        Returns
        -------
        tuple[CollectionResult, CollectionStatus]
            Collection result and status

        """
        logger.debug(f"Collecting NEW URL: {url}")

        # Collect the HTML
        result = await self.collector.collect(url, entry_url_id)

        # Save to database
        if result.success:
            status = self._save_new_collection(result)
        else:
            self._log_failure(result)
            status = CollectionStatus.FAILED

        return result, status

    def _save_new_collection(self, result: CollectionResult) -> CollectionStatus:
        """Save a new collection to database.

        Parameters
        ----------
        result : CollectionResult
            Successful collection result

        Returns
        -------
        CollectionStatus
            COLLECTED on success, FAILED on error

        """
        if not result.entry_url_id:
            logger.warning(f"Cannot save result for {result.url}: missing entry_url_id")
            return CollectionStatus.FAILED

        if not result.raw_html:
            logger.warning(f"Cannot save result for {result.url}: missing raw_html")
            return CollectionStatus.FAILED

        try:
            # Calculate content hash
            content_hash = calculate_content_hash(result.raw_html)

            # Create new record in production table
            html_create = VocabolsRawHTMLCreate(
                entry_url_id=result.entry_url_id,
                url=result.url,
                raw_html=result.raw_html,
                content_hash=content_hash,
                http_status_code=result.http_status_code,
                error_message=None,
            )
            create_vocabols_raw_html(self.session, html_create)

            logger.info(f"New collection saved for {result.url}")
            return CollectionStatus.COLLECTED

        except Exception as e:
            logger.exception(f"Failed to save new collection for {result.url}: {e}")
            self.session.rollback()
            raise

    def _log_failure(self, result: CollectionResult) -> None:
        """Log a failed collection result.

        Parameters
        ----------
        result : CollectionResult
            Failed collection result

        """
        logger.warning(
            f"Collection failed for {result.url}: "
            f"HTTP {result.http_status_code}, Error: {result.error}"
        )
