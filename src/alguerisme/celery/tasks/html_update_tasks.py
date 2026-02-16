"""Celery tasks for applying HTML changes."""

import asyncio
import logging

from celery import chord
from celery.exceptions import SoftTimeLimitExceeded
from sqlmodel import Session, select

from alguerisme.celery.app import app
from alguerisme.configs.loader import load_app_config
from alguerisme.core.collector.models import (
    ApplyChangesResult,
    CollectionStats,
    LetterCollectionResult,
)
from alguerisme.core.database import create_database_engine
from alguerisme.core.database.models import EntryURLs
from alguerisme.jobs import (
    run_html_update_apply_job,
    run_html_update_check_job,
)
from alguerisme.notifications.manager import NotificationManager
from alguerisme.reports import CollectionReport
from alguerisme.utils.alphabet import Alphabet, Letter

logger = logging.getLogger(__name__)


@app.task(
    bind=True, autoretry_for=(Exception,), retry_backoff=True, max_retries=5
)
def check_vocabols_updates(
    self, letters: list[str] | None = None, limit: int | None = None
) -> str:
    """Orchestrator: Check existing vocabols URLs for content updates by letter.

    Creates parallel worker tasks for each letter and aggregates results.
    Follows the same pattern as crawler and collector.

    Parameters
    ----------
    letters : list[str], optional
        List of letters to check (None = all standard letters)
    limit : int, optional
        Maximum URLs per letter (None = check all for each letter)

    Returns
    -------
    str
        Chord task ID for tracking progress

    """
    if letters is None:
        letters = [str(letter) for letter in Alphabet.standard()]

    logger.info(
        f"Orchestrating update check for {len(letters)} letters: {letters}"
    )

    header = [check_vocabols_updates_for_letter.s(letter, limit) for letter in letters]
    callback = send_update_check_notification.s(collection_type="update_check")

    try:
        # Chord runs header tasks in parallel, then triggers callback
        result = chord(header)(callback)

        logger.info(f"Successfully enqueued update check chord. Task ID: {result.id}")
        return result.id

    except Exception as exc:
        logger.error(f"Failed to enqueue update check chord: {exc}", exc_info=True)
        raise self.retry(exc=exc)


@app.task(
    bind=True,
    soft_time_limit=3600,  # 1 hour per letter
    time_limit=3900,  # 1h 5min - hard kill
    retry_backoff=60,  # Wait 1m, 2m, 4m... on failure
    max_retries=3,
)
def check_vocabols_updates_for_letter(
    self, letter_str: str, limit: int | None = None
) -> dict:
    """Worker: Check all vocabols URLs for a specific letter for content updates.

    Parameters
    ----------
    letter_str : str
        Letter to check vocabols for (e.g., "a", "b", "ny")
    limit : int, optional
        Maximum URLs to check for this letter

    Returns
    -------
    dict
        LetterCollectionResult dict with statistics

    """
    try:
        letter = Letter(letter_str)
    except ValueError as e:
        logger.error(f"Invalid letter received: {letter_str} - {e}")
        return LetterCollectionResult.failed(
            letter_str, f"Invalid letter: {e}"
        ).to_dict()

    logger.info(
        f"Worker checking updates for letter: {letter} "
        f"(attempt {self.request.retries + 1}/{self.max_retries + 1})"
    )

    config = load_app_config()

    try:
        # Get all URLs for this letter
        engine = create_database_engine(config.db_config)
        with Session(engine) as session:
            # Query all URLs filtered by letter
            statement = select(EntryURLs).where(EntryURLs.letter == str(letter))
            if limit:
                statement = statement.limit(limit)

            urls = list(session.exec(statement).all())
        engine.dispose()

        if not urls:
            logger.info(f"No URLs for letter {letter}")
            return LetterCollectionResult.success(
                letter=str(letter), stats=CollectionStats.empty()
            ).to_dict()

        logger.info(f"Found {len(urls)} URLs for letter {letter}")

        # Run update check job for this letter
        stats = asyncio.run(run_html_update_check_job(urls, config))

        logger.info(f"Update check complete for {letter}: {stats.summary()}")

        return LetterCollectionResult.success(
            letter=str(letter), stats=stats
        ).to_dict()

    except SoftTimeLimitExceeded:
        logger.error(f"Update check task exceeded time limit for {letter}")
        return LetterCollectionResult.failed(
            letter=str(letter), error="Task exceeded time limit"
        ).to_dict()

    except Exception as exc:
        if self.request.retries < self.max_retries:
            logger.warning(
                f"Update check task failed for {letter}, retrying "
                f"(attempt {self.request.retries + 1}/{self.max_retries}): {exc}"
            )
            raise self.retry(exc=exc)
        else:
            logger.error(
                f"Update check task failed for {letter} after "
                f"{self.max_retries} retries: {exc}",
                exc_info=True,
            )
            return LetterCollectionResult.failed(
                letter=str(letter),
                error=f"Failed after {self.max_retries} retries: {str(exc)}",
            ).to_dict()


@app.task(bind=True)
def send_update_check_notification(
    self, results: list[dict], collection_type: str
) -> dict:
    """Aggregate update check results and send notification.

    Parameters
    ----------
    results : list[dict]
        List of LetterCollectionResult dicts from worker tasks
    collection_type : str
        Type of collection: "update_check"

    Returns
    -------
    dict
        Notification delivery result

    """
    letter_results = [LetterCollectionResult.from_dict(r) for r in results]

    successful = [r for r in letter_results if not r.is_failed]
    failed = [r for r in letter_results if r.is_failed]

    logger.info(
        f"Update check complete: {len(successful)} successful letters, "
        f"{len(failed)} failed letters"
    )

    if failed:
        failed_letters = [r.letter for r in failed]
        logger.warning(f"Failed letters: {failed_letters}")
        for result in failed:
            logger.warning(f"  - Letter {result.letter}: {result.error}")

    # Send notification with detailed letter results
    report = CollectionReport(letter_results, collection_type=collection_type)
    config = load_app_config()
    manager = NotificationManager(config)

    return asyncio.run(manager.send(report))


@app.task(
    bind=True,
    soft_time_limit=600,  # 10 minutes
    time_limit=660,  # 11 minutes (hard kill)
    retry_backoff=60,  # Wait 1m, 2m, 4m... on failure
    max_retries=2,
)
def apply_approved_changes_task(self) -> dict:
    """Apply all approved HTML changes to production.

    This task should be manually triggered after reviewing and approving changes.
    It reads all APPROVED changes from vocabols_html_changes and applies them
    to the vocabols_raw_html table.

    Returns
    -------
    dict
        Application statistics:
        - applied: number of changes applied
        - skipped: number of changes skipped
        - errors: number of errors encountered

    Examples
    --------
    # Trigger manually after approving changes
    apply_approved_changes_task.delay()

    """
    logger.info("Starting apply approved changes task")

    config = load_app_config()

    try:
        # Run the job
        result = run_html_update_apply_job(config)

        if result.status == "success":
            logger.info(
                f"Apply changes complete: {result.applied} applied, "
                f"{result.skipped} skipped, {result.errors} errors"
            )
        else:
            logger.error(f"Apply changes failed: {result.message}")

        return result.to_dict()

    except SoftTimeLimitExceeded:
        logger.error("Apply changes task exceeded soft time limit")
        return ApplyChangesResult.error(message="Task exceeded time limit").to_dict()

    except Exception as exc:
        if self.request.retries < self.max_retries:
            logger.warning(
                f"Apply changes task failed, retrying "
                f"(attempt {self.request.retries + 1}/{self.max_retries}): {exc}"
            )
            raise self.retry(exc=exc)
        else:
            logger.error(
                f"Apply changes task failed after {self.max_retries} retries: {exc}",
                exc_info=True,
            )
            return ApplyChangesResult.error(
                message=f"Failed after {self.max_retries} retries: {str(exc)}"
            ).to_dict()
