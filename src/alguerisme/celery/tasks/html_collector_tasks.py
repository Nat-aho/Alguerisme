"""Celery tasks for collecting vocabols HTML."""

import asyncio
import logging

from celery import chord
from celery.exceptions import SoftTimeLimitExceeded
from sqlmodel import Session, select

from alguerisme.celery.app import app
from alguerisme.configs.loader import load_app_config
from alguerisme.core.collector.models import (
    CollectionStats,
    LetterCollectionResult,
    LetterCollectionResults,
)
from alguerisme.core.database import create_database_engine
from alguerisme.core.database.crud import (
    list_pending_vocabols_urls,  # noqa: F401 - Keep for future use
)
from alguerisme.core.database.models import EntryURLs, VocabolsRawHTML
from alguerisme.jobs import (
    run_html_collection_job,
)
from alguerisme.notifications.manager import NotificationManager
from alguerisme.reports import CollectionReport
from alguerisme.utils.alphabet import Alphabet, Letter

logger = logging.getLogger(__name__)


@app.task(bind=True, autoretry_for=(Exception,), retry_backoff=True, max_retries=5)
def collect_new_vocabols(
    self, letters: list[str] | None = None, limit: int | None = None
) -> str:
    """Orchestrator: Collect HTML for NEW vocabols by letter.

    Creates parallel worker tasks for each letter and aggregates results.
    Follows the same pattern as the crawler.

    Parameters
    ----------
    letters : list[str], optional
        List of letters to collect (None = all standard letters)
    limit : int, optional
        Maximum URLs per letter (None = all pending)

    Returns
    -------
    str
        Chord task ID for tracking progress

    """
    if letters is None:
        letters = [str(letter) for letter in Alphabet.standard()]

    logger.info(
        f"Orchestrating new vocabols collection for {len(letters)} letters: {letters}"
    )

    header = [collect_vocabols_for_letter.s(letter, limit) for letter in letters]
    callback = send_collection_notification.s(collection_type="new")

    try:
        # Chord runs header tasks in parallel, then triggers callback
        result = chord(header)(callback)

        logger.info(f"Successfully enqueued collection chord. Task ID: {result.id}")
        return result.id

    except Exception as exc:
        logger.error(f"Failed to enqueue collection chord: {exc}", exc_info=True)
        raise self.retry(exc=exc)


@app.task(
    bind=True,
    soft_time_limit=3600,  # 1 hour per letter
    time_limit=3900,  # 1h 5min - hard kill
    retry_backoff=60,  # Wait 1m, 2m, 4m... on failure
    max_retries=3,
)
def collect_vocabols_for_letter(
    self, letter_str: str, limit: int | None = None
) -> dict:
    """Worker: Collect HTML for all vocabols of a specific letter.

    Parameters
    ----------
    letter_str : str
        Letter to collect vocabols for (e.g., "a", "b", "ny")
    limit : int, optional
        Maximum URLs to collect for this letter

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
        f"Worker collecting vocabols for letter: {letter} "
        f"(attempt {self.request.retries + 1}/{self.max_retries + 1})"
    )

    config = load_app_config()

    try:
        # Get pending URLs for this letter
        engine = create_database_engine(config.db_config)
        with Session(engine) as session:
            # Query pending URLs filtered by letter
            # Pending = EntryURLs not yet in VocabolsRawHTML
            subquery = select(VocabolsRawHTML.entry_url_id)
            statement = (
                select(EntryURLs)
                .where(EntryURLs.letter == str(letter))
                .where(EntryURLs.id.notin_(subquery))  # type: ignore[attr-defined]
            )
            if limit:
                statement = statement.limit(limit)

            urls = list(session.exec(statement).all())
        engine.dispose()

        if not urls:
            logger.info(f"No pending URLs for letter {letter}")
            return LetterCollectionResult.success(
                letter=str(letter), stats=CollectionStats.empty()
            ).to_dict()

        logger.info(f"Found {len(urls)} pending URLs for letter {letter}")

        # Run collection job for this letter
        stats = asyncio.run(run_html_collection_job(urls, config))

        logger.info(f"Collection complete for {letter}: {stats.summary()}")

        return LetterCollectionResult.success(
            letter=str(letter), stats=stats
        ).to_dict()

    except SoftTimeLimitExceeded:
        logger.error(f"Collection task exceeded time limit for {letter}")
        return LetterCollectionResult.failed(
            letter=str(letter), error="Task exceeded time limit"
        ).to_dict()

    except Exception as exc:
        if self.request.retries < self.max_retries:
            logger.warning(
                f"Collection task failed for {letter}, retrying "
                f"(attempt {self.request.retries + 1}/{self.max_retries}): {exc}"
            )
            raise self.retry(exc=exc)
        else:
            logger.error(
                f"Collection task failed for {letter} after "
                f"{self.max_retries} retries: {exc}",
                exc_info=True,
            )
            return LetterCollectionResult.failed(
                letter=str(letter),
                error=f"Failed after {self.max_retries} retries: {str(exc)}",
            ).to_dict()


@app.task(bind=True)
def send_collection_notification(
    self, results: list[dict], collection_type: str
) -> dict:
    """Aggregate collection results and send notification.

    Parameters
    ----------
    results : list[dict]
        List of LetterCollectionResult dicts from worker tasks
    collection_type : str
        Type of collection: "new" or "update_check"

    Returns
    -------
    dict
        Notification delivery result

    """
    letter_results = [LetterCollectionResult.from_dict(r) for r in results]

    successful = [r for r in letter_results if not r.is_failed]
    failed = [r for r in letter_results if r.is_failed]

    logger.info(
        f"Collection complete: {len(successful)} successful letters, "
        f"{len(failed)} failed letters"
    )

    if failed:
        failed_letters = [r.letter for r in failed]
        logger.warning(f"Failed letters: {failed_letters}")
        for result in failed:
            logger.warning(f"  - Letter {result.letter}: {result.error}")

    # Send notification with detailed letter results
    collection_results = LetterCollectionResults.from_results(letter_results)
    report = CollectionReport(collection_results, collection_type=collection_type)
    config = load_app_config()
    manager = NotificationManager(config)

    return asyncio.run(manager.send(report))
