"""Celery tasks for crawling dictionary index pages."""

import asyncio
import logging

from celery import chord
from celery.exceptions import SoftTimeLimitExceeded

from alguerisme.celery.app import app
from alguerisme.configs.loader import load_app_config
from alguerisme.core.crawler.models import LetterCrawlResult
from alguerisme.jobs import run_crawl_job
from alguerisme.notifications.manager import NotificationManager
from alguerisme.reports import CrawlReport
from alguerisme.utils.alphabet import Alphabet, Letter

logger = logging.getLogger(__name__)


@app.task(bind=True, autoretry_for=(Exception,), retry_backoff=True, max_retries=5)
def crawl_letters(self, letters: list[str] | None = None) -> str:
    """Crawl dictionary index pages for specified letters.

    This task creates parallel worker tasks for each letter and
    aggregates results via a callback.

    Parameters
    ----------
    letters : list[str], optional
        List of letters to crawl (None = all standard letters)

    Returns
    -------
    str
        Chord task ID for tracking progress

    """
    if letters is None:
        letters = [str(letter) for letter in Alphabet.standard()]

    logger.info(f"Orchestrating crawl for {len(letters)} letters: {letters}")

    header = [crawl_letter.s(letter) for letter in letters]
    callback = send_crawl_notification.s()
    try:
        # Chord runs header tasks in parallel, then triggers callback with all results
        result = chord(header)(callback)

        logger.info(f"Successfully enqueued crawl chord. Task ID: {result.id}")
        return result.id

    except Exception as exc:
        logger.error(f"Failed to enqueue daily crawl chord: {exc}", exc_info=True)
        raise self.retry(exc=exc)


@app.task(
    bind=True,
    soft_time_limit=900,  # 15 minutes - raises exception
    time_limit=960,  # 16 minutes - hard kill
    retry_backoff=60,  # Wait 1m, 2m, 4m... on failure
    max_retries=3,
)
def crawl_letter(self, letter_str: str) -> dict:
    """Crawl a single letter's index pages.

    Worker task that fetches all index pages for a specific letter
    and saves discovered URLs to the database.

    Parameters
    ----------
    letter_str : str
        Letter to crawl (e.g., "a", "b", "ny")

    Returns
    -------
    dict
        LetterCrawlResult dict with statistics

    """
    try:
        letter = Letter(letter_str)
    except ValueError as e:
        logger.error(f"Invalid letter received: {letter_str} - {e}")
        return LetterCrawlResult.failed(letter_str, f"Invalid letter: {e}").to_dict()

    logger.info(
        f"Worker processing letter: {letter} "
        f"(attempt {self.request.retries + 1}/{self.max_retries + 1})"
    )

    config = load_app_config()

    try:
        stats = asyncio.run(run_crawl_job(letters=[letter], config=config))
        logger.info(f"Task complete for {letter}")

        return LetterCrawlResult.success(letter=str(letter), stats=stats).to_dict()

    except SoftTimeLimitExceeded:
        logger.error(f"Task exceeded soft time limit for {letter}")
        return LetterCrawlResult.failed(
            letter=str(letter), error="Task exceeded time limit"
        ).to_dict()

    except Exception as exc:
        if self.request.retries < self.max_retries:
            logger.warning(
                f"Task failed for {letter}, retrying "
                f"(attempt {self.request.retries + 1}/{self.max_retries}): {exc}"
            )
            raise self.retry(exc=exc)

        else:
            logger.error(
                f"Task failed for {letter} after {self.max_retries} retries: {exc}",
                exc_info=True,
            )
            return LetterCrawlResult.failed(
                letter=str(letter),
                error=f"Failed after {self.max_retries} retries: {str(exc)}",
            ).to_dict()


@app.task(bind=True)
def send_crawl_notification(self, results: list[dict]) -> dict:
    """Send notification after crawl completion.

    Aggregates results from all letter crawl tasks and sends
    a summary notification via configured channels.

    Parameters
    ----------
    results : list[dict]
        List of LetterCrawlResult dicts from worker tasks

    Returns
    -------
    dict
        Notification delivery result

    """
    letter_results = [LetterCrawlResult.from_dict(r) for r in results]

    successful = [r for r in letter_results if not r.is_failed]
    failed = [r for r in letter_results if r.is_failed]

    logger.info(f"Crawl complete: {len(successful)} successful, {len(failed)} failed")
    if failed:
        failed_letters = [r.letter for r in failed]
        logger.warning(f"Failed letters: {failed_letters}")

    report = CrawlReport(letter_results)

    config = load_app_config()
    manager = NotificationManager(config)

    return asyncio.run(manager.send(report))
