"""Celery tasks for orchestrating the web crawling process."""

import asyncio
import logging

from celery import group

from alguerisme.celery.app import app
from alguerisme.jobs import run_crawl_job

logger = logging.getLogger(__name__)


@app.task(bind=True)
def trigger_daily_crawl(self):
    """Trigger the daily crawl by creating tasks for each letter."""
    letters = list("ABCDEFGHIJKLMNOPQRSTUVWXYZ")

    logger.info(f"Orchestrating daily crawl for {len(letters)} letters")

    # Create a group of tasks to execute in parallel
    job_group = group(crawl_letter_task.s(letter) for letter in letters)

    # Send the group to the broker
    job_group.apply_async()


@app.task(
    bind=True,
    autoretry_for=(Exception,),
    retry_backoff=60,  # Wait 1m, 2m, 4m...
    max_retries=3,
    time_limit=300,  # Hard kill after 5 minutes
)
def crawl_letter_task(self, letter: str):
    """Crawl a single letter and save URLs to DB."""
    logger.info(f"Worker processing letter: {letter}")

    try:
        stats = asyncio.run(run_crawl_job(letters=[letter]))

        logger.info(f"Task complete for {letter}")
        logger.info(stats.summary())
        return stats

    except Exception as exc:
        logger.error(f"Task failed for {letter}: {exc}")
        raise exc
