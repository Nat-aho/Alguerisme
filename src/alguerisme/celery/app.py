"""Celery Application Setup."""

from celery import Celery
from celery.schedules import crontab

from alguerisme.celery import tasks  # noqa: F401

app = Celery(
    "alguerisme",
    broker="redis://localhost:6379/0",
    backend="redis://localhost:6379/0",
    include=["alguerisme.celery.tasks"],
)

app.conf.update(
    timezone="Europe/Rome",
    enable_utc=True,
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
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
