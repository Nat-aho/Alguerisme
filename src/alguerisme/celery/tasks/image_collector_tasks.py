"""Celery tasks for collecting vocabol images."""

import logging

from celery import chord
from celery.exceptions import SoftTimeLimitExceeded

from alguerisme.celery.app import app
from alguerisme.configs.loader import load_app_config
from alguerisme.core.image_collector.models import (
    LetterImageCollectionResult,
    LetterImageCollectionResults,
)
from alguerisme.jobs.image_collector_job import run_image_collection_for_letter
from alguerisme.notifications.manager import NotificationManager
from alguerisme.reports import ImageCollectionReport
from alguerisme.utils.alphabet import Alphabet, Letter

logger = logging.getLogger(__name__)


@app.task(bind=True, autoretry_for=(Exception,), retry_backoff=True, max_retries=5)
def collect_images_for_letters(self, letters: list[str] | None = None) -> str:
    """Collect images for parsed vocabols for specified letters.

    This task creates parallel worker tasks for each letter and
    aggregates results via a callback.

    Parameters
    ----------
    letters : list[str], optional
        List of letters to collect images for (None = all standard letters)

    Returns
    -------
    str
        Chord task ID for tracking progress

    """
    if letters is None:
        letters = [str(letter) for letter in Alphabet.standard()]

    logger.info(f"Orchestrating image collection for {len(letters)} letters: {letters}")

    header = [collect_images_for_letter.s(letter) for letter in letters]
    callback = send_image_collection_notification.s()
    try:
        # Chord runs header tasks in parallel, then triggers callback with all results
        result = chord(header)(callback)

        logger.info(
            f"Successfully enqueued image collection chord. Task ID: {result.id}"
        )
        return result.id

    except Exception as exc:
        logger.error(f"Failed to enqueue image collection chord: {exc}", exc_info=True)
        raise self.retry(exc=exc)


@app.task(
    bind=True,
    soft_time_limit=900,  # 15 minutes - raises exception
    time_limit=960,  # 16 minutes - hard kill
    retry_backoff=60,  # Wait 1m, 2m, 4m... on failure
    max_retries=3,
)
def collect_images_for_letter(self, letter_str: str) -> dict:
    """Collect images for a single letter's parsed vocabols.

    Worker task that downloads images for all parsed vocabols
    with image URLs for a specific letter.

    Parameters
    ----------
    letter_str : str
        Letter to collect images for (e.g., "A", "B", "C")

    Returns
    -------
    dict
        LetterImageCollectionResult dict with statistics

    """
    try:
        letter = Letter(letter_str)
    except ValueError as e:
        logger.error(f"Invalid letter received: {letter_str} - {e}")
        return LetterImageCollectionResult.failed(
            letter_str, f"Invalid letter: {e}"
        ).to_dict()

    logger.info(
        f"Worker processing image collection for letter: {letter} "
        f"(attempt {self.request.retries + 1}/{self.max_retries + 1})"
    )

    try:
        result = run_image_collection_for_letter(letter)
        logger.info(f"Image collection task complete for {letter}")
        return result.to_dict()

    except SoftTimeLimitExceeded:
        logger.error(f"Task exceeded soft time limit for {letter}")
        return LetterImageCollectionResult.failed(
            letter=str(letter), error="Task exceeded time limit"
        ).to_dict()

    except Exception as exc:
        if self.request.retries < self.max_retries:
            logger.warning(
                f"Image collection task failed for {letter}, retrying "
                f"(attempt {self.request.retries + 1}/{self.max_retries}): {exc}"
            )
            raise self.retry(exc=exc)

        else:
            logger.error(
                f"Image collection task failed for {letter} "
                f"after {self.max_retries} retries: {exc}",
                exc_info=True,
            )
            return LetterImageCollectionResult.failed(
                letter=str(letter),
                error=f"Failed after {self.max_retries} retries: {str(exc)}",
            ).to_dict()


@app.task(bind=True)
def send_image_collection_notification(self, results: list[dict]) -> dict:
    """Send notification after image collection completion.

    Aggregates results from all letter image collection tasks and sends
    a summary notification via configured channels.

    Parameters
    ----------
    results : list[dict]
        List of LetterImageCollectionResult dicts from worker tasks

    Returns
    -------
    dict
        Notification delivery result

    """
    letter_results = [LetterImageCollectionResult.from_dict(r) for r in results]
    collection_result = LetterImageCollectionResults.from_results(letter_results)

    successful_letters = collection_result.successful_letters
    failed_letters = collection_result.failed_letters

    logger.info(
        f"Image collection complete: {len(successful_letters)} successful, "
        f"{len(failed_letters)} failed"
    )
    if failed_letters:
        logger.warning(f"Failed letters: {failed_letters}")

    report = ImageCollectionReport(collection_result)

    config = load_app_config()
    manager = NotificationManager(config)

    import asyncio

    return asyncio.run(manager.send(report))
