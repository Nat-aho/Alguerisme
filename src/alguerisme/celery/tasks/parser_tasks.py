"""Celery tasks for parsing vocabols HTML."""

import asyncio
import logging

from celery import chord
from celery.exceptions import SoftTimeLimitExceeded

from alguerisme.celery.app import app
from alguerisme.configs.loader import load_app_config
from alguerisme.core.parser.models import (
    LetterParseResult,
    LetterParseResults,
)
from alguerisme.jobs import run_parse_job
from alguerisme.notifications.manager import NotificationManager
from alguerisme.reports import ParseReport
from alguerisme.utils.alphabet import Alphabet, Letter

logger = logging.getLogger(__name__)


@app.task(bind=True, autoretry_for=(Exception,), retry_backoff=True, max_retries=5)
def parse_vocabols(self, letters: list[str] | None = None) -> str:
    """Orchestrator: Parse raw HTML vocabols by letter.

    Creates parallel worker tasks for each letter and aggregates results.
    Follows the same pattern as the crawler and collector.

    Parameters
    ----------
    letters : list[str], optional
        List of letters to parse (None = all standard letters)

    Returns
    -------
    str
        Chord task ID for tracking progress

    """
    if letters is None:
        letters = [str(letter) for letter in Alphabet.standard()]

    logger.info(f"Orchestrating parsing for {len(letters)} letters: {letters}")

    header = [parse_vocabols_for_letter.s(letter) for letter in letters]
    callback = send_parse_notification.s()

    try:
        # Chord runs header tasks in parallel, then triggers callback
        result = chord(header)(callback)

        logger.info(f"Successfully enqueued parse chord. Task ID: {result.id}")
        return result.id

    except Exception as exc:
        logger.error(f"Failed to enqueue parse chord: {exc}", exc_info=True)
        raise self.retry(exc=exc)


@app.task(
    bind=True,
    soft_time_limit=1800,  # 30 minutes per letter
    time_limit=2100,  # 35 minutes - hard kill
    retry_backoff=60,  # Wait 1m, 2m, 4m... on failure
    max_retries=3,
)
def parse_vocabols_for_letter(self, letter_str: str) -> dict:
    """Worker: Parse raw HTML for all vocabols of a specific letter.

    Parameters
    ----------
    letter_str : str
        Letter to parse vocabols for (e.g., "a", "b", "ny")

    Returns
    -------
    dict
        LetterParseResult as dict (for JSON serialization)

    """
    try:
        letter = Letter(letter_str)
    except ValueError as e:
        logger.error(f"Invalid letter received: {letter_str} - {e}")
        return LetterParseResult.failed(
            letter=letter_str, error=f"Invalid letter: {e}"
        ).to_dict()

    logger.info(
        f"Worker parsing vocabols for letter: {letter} "
        f"(attempt {self.request.retries + 1}/{self.max_retries + 1})"
    )

    config = load_app_config()

    try:
        # Run parse job for this letter
        stats = asyncio.run(run_parse_job([letter], config))

        if stats.total_entries == 0:
            logger.info(f"No unparsed entries for letter {letter}")
        else:
            logger.info(f"Parsing complete for {letter}: {stats.summary()}")

        return LetterParseResult.successful(letter=str(letter), stats=stats).to_dict()

    except SoftTimeLimitExceeded:
        logger.error(f"Parser soft time limit exceeded for letter {letter}")
        return LetterParseResult.failed(
            letter=str(letter), error="Soft time limit exceeded"
        ).to_dict()
    except Exception as e:
        logger.exception(f"Parser failed for letter {letter}")
        return LetterParseResult.failed(letter=str(letter), error=str(e)).to_dict()


@app.task(bind=True)
def send_parse_notification(self, results: list[dict]) -> dict:
    """Send notification after parsing completion.

    Aggregates results from all letter parse tasks and sends
    a summary notification via configured channels.

    Parameters
    ----------
    results : list[dict]
        List of LetterParseResult dicts from worker tasks

    Returns
    -------
    dict
        Notification delivery result

    """
    letter_results = [LetterParseResult.from_dict(r) for r in results]
    parse_result = LetterParseResults.from_results(letter_results)

    successful_letters = parse_result.success_letters
    failed_letters = parse_result.failed_letters

    logger.info(
        f"Parse complete: {len(successful_letters)} successful, "
        f"{len(failed_letters)} failed"
    )
    if failed_letters:
        logger.warning(f"Failed letters: {failed_letters}")

    report = ParseReport(parse_result)

    config = load_app_config()
    manager = NotificationManager(config)

    return asyncio.run(manager.send(report))
