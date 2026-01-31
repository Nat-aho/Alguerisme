"""Celery application entry point."""

from celery import Celery
from celery.schedules import crontab

from alguerisme.configs.celery import CeleryConfig

config = CeleryConfig.from_env()

app = Celery(
    "alguerisme",
    broker=config.broker_url,
    backend=config.result_backend,
    include=["alguerisme.celery.tasks"],
)

app.conf.update(
    timezone=config.timezone,
    enable_utc=config.enable_utc,
    task_serializer=config.task_serializer,
    accept_content=config.accept_content,
    result_serializer=config.result_serializer,
)

# Schedule: Daily crawl at midnight
app.conf.beat_schedule = {
    "daily-crawl-midnight": {
        "task": "alguerisme.celery.tasks.trigger_daily_crawl",
        "schedule": crontab(hour=0, minute=0),
    },
}

if __name__ == "__main__":
    app.start()
