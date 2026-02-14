"""Celery app and tasks for Alguerisme."""

import asyncio
import logging

from celery import Celery, chord
from celery.exceptions import SoftTimeLimitExceeded
from celery.schedules import crontab

from alguerisme.configs.loader import load_app_config
from alguerisme.core.crawler.models import LetterCrawlResult
from alguerisme.jobs import run_crawl_job
from alguerisme.notifications.manager import NotificationManager
from alguerisme.reports import CrawlReport
from alguerisme.utils.alphabet import Alphabet, Letter

logger = logging.getLogger(__name__)


def build_celery_app() -> Celery:
    """Build and configure the Celery application."""
    config = load_app_config()

    app = Celery(
        "alguerisme",
        broker=config.celery_config.broker_url,
        backend=config.celery_config.result_backend,
    )

    app.conf.update(
        timezone=config.celery_config.timezone,
        enable_utc=config.celery_config.enable_utc,
        task_serializer=config.celery_config.task_serializer,
        accept_content=config.celery_config.accept_content,
        result_serializer=config.celery_config.result_serializer,
        result_expires=config.celery_config.result_expires,
    )

    app.conf.beat_schedule = {
        "daily-crawl-midnight": {
            "task": "alguerisme.celery.app.trigger_daily_crawl",
            "schedule": crontab(hour=0, minute=0),
        },
    }

    return app


app = build_celery_app()


@app.task(bind=True, autoretry_for=(Exception,), retry_backoff=True, max_retries=5)
def trigger_daily_crawl(self, letters: list[str] | None = None) -> str:
    """Run orchestrator: Trigger crawl for specified letters."""
    if letters is None:
        letters = [str(letter) for letter in Alphabet.standard()]

    logger.info(f"Orchestrating crawl for {len(letters)} letters: {letters}")

    header = [crawl_letter_task.s(letter) for letter in letters]
    callback = send_crawl_notification.s()
    try:
        # Chord runs header tasks in parallel, then triggers callback with all results
        result = chord(header)(callback)

        logger.info(f"Successfully enqueued crawl chord. Task ID: {result.id}")
        return result.id

    except Exception as exc:
        logger.error(f"Failed to enqueue daily crawl chord: {exc}", exc_info=True)
        raise self.retry(exc=exc)


@app.task(bind=True)
def send_crawl_notification(self, results: list[dict]) -> dict:
    """Send notification after crawl completion."""
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


@app.task(
    bind=True,
    soft_time_limit=900,  # 15 minutes - raises exception
    time_limit=960,  # 16 minutes - hard kill
    retry_backoff=60,  # Wait 1m, 2m, 4m... on failure
    max_retries=3,
)
def crawl_letter_task(self, letter_str: str) -> dict:
    """Crawl a single letter."""
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
