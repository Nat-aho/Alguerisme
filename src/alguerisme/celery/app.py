"""Celery app configuration for Alguerisme."""

from celery import Celery
from celery.schedules import crontab

from alguerisme.configs.loader import load_app_config


def build_celery_app() -> Celery:
    """Build and configure the Celery application."""
    config = load_app_config()

    app = Celery(
        "alguerisme",
        broker=config.celery_config.broker_url,
        backend=config.celery_config.backend_url,
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
        "urls-vocabols-crawler": {
            "task": "alguerisme.celery.tasks.crawler_tasks.crawl_letters",
            "schedule": crontab(day_of_week=1, hour=2, minute=0),
        },
        "html-vocabols-collector": {
            "task": "alguerisme.celery.tasks.html_collector_tasks.collect_new_vocabols",
            "schedule": crontab(day_of_week=2, hour=2, minute=0),
        },
        "html-vocabols-updates-check": {
            "task": (
                "alguerisme.celery.tasks.html_update_tasks"
                ".check_vocabols_updates"
            ),
            "schedule": crontab(day_of_week=3, hour=2, minute=0),
        },
    }

    return app


app = build_celery_app()

# Import tasks to register them with Celery
# This must be done after app is created to avoid circular imports
# Tasks import app from this module, so we import them after app exists
from alguerisme.celery.tasks import crawler_tasks  # noqa: E402, F401
from alguerisme.celery.tasks import html_collector_tasks  # noqa: E402, F401
from alguerisme.celery.tasks import html_update_tasks  # noqa: E402, F401
