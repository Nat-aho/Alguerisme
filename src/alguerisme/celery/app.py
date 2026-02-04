"""Celery app and tasks for Alguerisme."""

import asyncio
import logging

from celery import Celery, group
from celery.schedules import crontab

from alguerisme.configs.loader import load_app_config
from alguerisme.jobs import run_crawl_job

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
    )

    app.conf.beat_schedule = {
        "daily-crawl-midnight": {
            # Note: We point to THIS file now
            "task": "alguerisme.celery.app.trigger_daily_crawl",
            "schedule": crontab(hour=0, minute=0),
        },
    }

    return app


app = build_celery_app()


@app.task(bind=True)
def trigger_daily_crawl(self):
    """Orchestrator: Enqueues a sub-task for every letter."""
    letters = list("ABCDEFGHIJKLMNOPQRSTUVWXYZ")
    logger.info(f"Orchestrating daily crawl for {len(letters)} letters")

    # Creates a group of tasks that can run in parallel
    job_group = group(crawl_letter_task.s(letter) for letter in letters)
    job_group.apply_async()


@app.task(
    bind=True,
    autoretry_for=(Exception,),
    retry_backoff=60,  # Wait 1m, 2m, 4m... on failure
    max_retries=3,
    time_limit=300,  # Hard kill after 5 minutes
)
def crawl_letter_task(self, letter: str):
    """Worker: Crawls a single letter."""
    logger.info(f"Worker processing letter: {letter}")
    config = load_app_config()
    try:
        stats = asyncio.run(run_crawl_job(letters=[letter], config=config))

        logger.info(f"Task complete for {letter}")
        return stats

    except Exception as exc:
        logger.error(f"Task failed for {letter}: {exc}")
        raise self.retry(exc=exc)
