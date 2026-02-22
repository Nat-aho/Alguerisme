"""Service for checking existing vocabols for HTML content changes."""

import asyncio
import logging
from uuid import UUID

from sqlmodel import Session

from alguerisme.core.collector.enums import ChangeStatus, CollectionStatus
from alguerisme.core.collector.html_collector import HTMLCollector
from alguerisme.core.collector.models import CollectionResult, CollectionStats
from alguerisme.core.collector.utils import (
    ChangeMetrics,
    calculate_change_metrics,
    calculate_content_hash,
)
from alguerisme.core.database.crud import (
    create_vocabols_html_change,
    create_vocabols_raw_html,
    find_approved_change_by_entry_url_id,
    find_pending_change_by_entry_url_id,
    find_rejected_change_by_entry_url_id,
    find_vocabols_raw_html_by_entry_url_id,
    update_pending_change,
)
from alguerisme.core.database.models import (
    EntryURLs,
    VocabolsHtmlChanges,
    VocabolsHtmlChangesCreate,
    VocabolsRawHTML,
    VocabolsRawHTMLCreate,
)

logger = logging.getLogger(__name__)


class HTMLUpdateCheckerService:
    """Checks existing vocabols for HTML content changes.

    This service re-checks ALL vocabol URLs to detect content updates.
    Performs hash comparison and creates change records for review when
    changes are detected. Handles approved/rejected/pending change logic.

    Used by: check_vocabols_updates_task (monthly)

    """

    def __init__(self, collector: HTMLCollector, session: Session):
        """Initialize the update checker service.

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
        """Check vocabol URLs for HTML changes.

        Parameters
        ----------
        entry_urls : list[EntryURLs]
            URLs to check (should be existing URLs)
        request_delay : float
            Delay between requests in seconds
        max_workers : int
            Max concurrent requests

        Returns
        -------
        CollectionStats
            Statistics: collected, unchanged, changed, failed

        """
        logger.info(f"Starting update check for {len(entry_urls)} URLs")

        stats = CollectionStats.empty()
        semaphore = asyncio.Semaphore(max_workers)

        async def _check_with_limit(entry_url: EntryURLs) -> None:
            """Check a single URL with rate limiting."""
            async with semaphore:
                result, status = await self._check_url(
                    entry_url.url, entry_url.id, entry_url.letter
                )

                # Update stats based on status
                if status == CollectionStatus.COLLECTED:
                    stats.urls_collected += 1
                    logger.debug(f"First collection: {entry_url.url}")
                elif status == CollectionStatus.UNCHANGED:
                    stats.urls_unchanged += 1
                    logger.debug(f"No change: {entry_url.url}")
                elif status == CollectionStatus.CHANGED:
                    stats.urls_changed += 1
                    logger.warning(f"Change detected: {entry_url.url}")
                elif status == CollectionStatus.FAILED:
                    stats.urls_failed += 1
                    logger.warning(f"Failed: {entry_url.url} - {result.error}")

                # Rate limit: wait before releasing semaphore slot
                await asyncio.sleep(request_delay)

        # Create tasks for all URLs
        tasks = [_check_with_limit(url) for url in entry_urls]

        # Run all tasks concurrently and capture results
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Check for any exceptions that were caught
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                entry_url = entry_urls[i]
                stats.urls_failed += 1
                logger.error(
                    f"Error checking {entry_url.url}: {result}",
                    exc_info=result,
                )

        logger.info(stats.summary())

        return stats

    async def _check_url(
        self, url: str, entry_url_id: UUID, letter: str
    ) -> tuple[CollectionResult, CollectionStatus]:
        """Check a single URL for changes.

        Parameters
        ----------
        url : str
            URL to check
        entry_url_id : UUID
            ID of the entry_urls record
        letter : str
            Letter that this entry belongs to

        Returns
        -------
        tuple[CollectionResult, CollectionStatus]
            Collection result and status

        """
        logger.debug(f"Checking URL for updates: {url}")

        # Collect the HTML
        result = await self.collector.collect(url, entry_url_id, letter)

        # Check for changes and save
        if result.success:
            status = self._check_and_save_changes(result)
        else:
            self._log_failure(result)
            status = CollectionStatus.FAILED

        return result, status

    def _check_and_save_changes(self, result: CollectionResult) -> CollectionStatus:
        """Check for changes and handle accordingly.

        Parameters
        ----------
        result : CollectionResult
            Successful collection result

        Returns
        -------
        CollectionStatus
            Status indicating what happened (COLLECTED/UNCHANGED/CHANGED/FAILED)

        """
        if not result.entry_url_id:
            logger.warning(f"Cannot save result for {result.url}: missing entry_url_id")
            return CollectionStatus.FAILED

        if not result.raw_html:
            logger.warning(f"Cannot save result for {result.url}: missing raw_html")
            return CollectionStatus.FAILED

        try:
            # Calculate content hash
            new_hash = calculate_content_hash(result.raw_html)

            # Check if already exists in production table
            current = find_vocabols_raw_html_by_entry_url_id(
                self.session, result.entry_url_id
            )

            if not current:
                # Defensive: URL should exist, but handle gracefully
                logger.warning(
                    f"URL {result.url} has no existing record, saving as new collection"
                )
                return self._save_new_collection(result, new_hash)

            # Compare hashes
            if current.content_hash == new_hash:
                # No change detected
                logger.debug(f"No change detected for {result.url}")
                return CollectionStatus.UNCHANGED

            # Content changed! Handle the change
            return self._handle_detected_change(result, current, new_hash)

        except Exception as e:
            logger.exception(f"Failed to check changes for {result.url}: {e}")
            self.session.rollback()
            raise

    def _save_new_collection(
        self, result: CollectionResult, content_hash: str
    ) -> CollectionStatus:
        """Save a new collection (defensive case - shouldn't happen often).

        Parameters
        ----------
        result : CollectionResult
            Collection result
        content_hash : str
            SHA256 hash of content

        Returns
        -------
        CollectionStatus
            COLLECTED

        """
        assert result.entry_url_id is not None
        assert result.raw_html is not None
        assert result.letter is not None

        html_create = VocabolsRawHTMLCreate(
            entry_url_id=result.entry_url_id,
            url=result.url,
            letter=result.letter,
            raw_html=result.raw_html,
            content_hash=content_hash,
            http_status_code=result.http_status_code,
            error_message=None,
        )
        create_vocabols_raw_html(self.session, html_create)
        logger.info(f"New collection saved for {result.url}")
        return CollectionStatus.COLLECTED

    def _handle_detected_change(
        self, result: CollectionResult, current, new_hash: str
    ) -> CollectionStatus:
        """Handle a detected content change.

        Parameters
        ----------
        result : CollectionResult
            Collection result with new content
        current : VocabolsRawHTML
            Current record from database
        new_hash : str
            SHA256 hash of new content

        Returns
        -------
        CollectionStatus
            CHANGED if change recorded, UNCHANGED if skipped

        """
        # Fields already validated in _check_and_save_changes
        assert result.entry_url_id is not None
        assert result.raw_html is not None

        # Calculate change metrics
        metrics = calculate_change_metrics(current.raw_html, result.raw_html)

        # Check for existing change records
        existing_approved = find_approved_change_by_entry_url_id(
            self.session, result.entry_url_id
        )
        if existing_approved:
            logger.info(
                f"Skipping {result.url}: approved change exists, waiting for apply"
            )
            return CollectionStatus.UNCHANGED

        existing_rejected = find_rejected_change_by_entry_url_id(
            self.session, result.entry_url_id
        )
        if existing_rejected:
            return self._handle_rejected_change(
                existing_rejected, result, new_hash, metrics
            )

        existing_pending = find_pending_change_by_entry_url_id(
            self.session, result.entry_url_id
        )
        if existing_pending:
            return self._update_pending_change(
                existing_pending, result, new_hash, metrics
            )

        # No existing change record - create new one
        return self._create_change_record(result, current, new_hash, metrics)

    def _handle_rejected_change(
        self,
        rejected: VocabolsHtmlChanges,
        result: CollectionResult,
        new_hash: str,
        metrics: ChangeMetrics,
    ) -> CollectionStatus:
        """Handle a previously rejected change.

        Parameters
        ----------
        rejected : VocabolsHtmlChanges
            Existing rejected change record
        result : CollectionResult
            New collection result
        new_hash : str
            SHA256 hash of new content
        metrics : ChangeMetrics
            Calculated change metrics

        Returns
        -------
        CollectionStatus
            CHANGED if different hash, UNCHANGED if same

        """
        if rejected.new_hash == new_hash:
            # Same change that was rejected before - skip it
            logger.debug(f"Skipping {result.url}: same rejected change (hash matches)")
            return CollectionStatus.UNCHANGED

        # Different change detected - reset to PENDING
        logger.info(f"Overwriting rejected change for {result.url}: new hash detected")
        # Assert validates that raw_html is not None
        # (already checked in _check_and_save_changes)
        assert result.raw_html is not None
        rejected.new_html = result.raw_html
        rejected.new_hash = new_hash
        rejected.size_change_bytes = metrics.size_change_bytes
        rejected.size_change_pct = metrics.size_change_pct
        rejected.change_type = metrics.change_type
        rejected.status = ChangeStatus.PENDING
        rejected.reviewed_at = None
        rejected.reviewed_by = None
        update_pending_change(self.session, rejected)

        logger.warning(
            f"New change detected after rejection for {result.url}: "
            f"{metrics.size_change_bytes:+d} bytes ({metrics.size_change_pct:+.1f}%)"
        )
        return CollectionStatus.CHANGED

    def _update_pending_change(
        self,
        pending: VocabolsHtmlChanges,
        result: CollectionResult,
        new_hash: str,
        metrics: ChangeMetrics,
    ) -> CollectionStatus:
        """Update an existing pending change with latest data.

        Parameters
        ----------
        pending : VocabolsHtmlChanges
            Existing pending change record
        result : CollectionResult
            New collection result
        new_hash : str
            SHA256 hash of new content
        metrics : ChangeMetrics
            Calculated change metrics

        Returns
        -------
        CollectionStatus
            CHANGED

        """
        # Assert validates that raw_html is not None
        # (already checked in _check_and_save_changes)
        assert result.raw_html is not None
        pending.new_html = result.raw_html
        pending.new_hash = new_hash
        pending.size_change_bytes = metrics.size_change_bytes
        pending.size_change_pct = metrics.size_change_pct
        pending.change_type = metrics.change_type
        update_pending_change(self.session, pending)

        logger.info(
            f"Updated pending change for {result.url}: "
            f"{metrics.size_change_bytes:+d} bytes ({metrics.size_change_pct:+.1f}%)"
        )
        return CollectionStatus.CHANGED

    def _create_change_record(
        self,
        result: CollectionResult,
        current: VocabolsRawHTML,
        new_hash: str,
        metrics: ChangeMetrics,
    ) -> CollectionStatus:
        """Create a new change record for review.

        Parameters
        ----------
        result : CollectionResult
            New collection result
        current : VocabolsRawHTML
            Current record from database
        new_hash : str
            SHA256 hash of new content
        metrics : ChangeMetrics
            Calculated change metrics

        Returns
        -------
        CollectionStatus
            CHANGED

        """
        # Fields already validated in _check_and_save_changes
        assert result.entry_url_id is not None
        assert result.raw_html is not None

        change_create = VocabolsHtmlChangesCreate(
            entry_url_id=result.entry_url_id,
            url=result.url,
            new_html=result.raw_html,
            new_hash=new_hash,
            old_html=current.raw_html,
            old_hash=current.content_hash,
            change_type=metrics.change_type,
            size_change_bytes=metrics.size_change_bytes,
            size_change_pct=metrics.size_change_pct,
            status=ChangeStatus.PENDING,
        )
        create_vocabols_html_change(self.session, change_create)

        logger.warning(
            f"Change detected for {result.url}: "
            f"{metrics.size_change_bytes:+d} bytes ({metrics.size_change_pct:+.1f}%). "
            f"Stored for review."
        )
        return CollectionStatus.CHANGED

    def _log_failure(self, result: CollectionResult) -> None:
        """Log a failed collection result.

        Parameters
        ----------
        result : CollectionResult
            Failed collection result

        """
        logger.warning(
            f"Update check failed for {result.url}: "
            f"HTTP {result.http_status_code}, Error: {result.error}"
        )
