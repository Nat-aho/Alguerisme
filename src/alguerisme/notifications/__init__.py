"""Notification services."""

from alguerisme.core.crawler.models import CrawlMetrics
from alguerisme.notifications.manager import NotificationChannel, NotificationManager
from alguerisme.notifications.protocols import Reportable
from alguerisme.notifications.telegram import TelegramNotifier
from alguerisme.reports import CrawlReport

__all__ = [
    "CrawlMetrics",
    "CrawlReport",
    "NotificationChannel",
    "NotificationManager",
    "Reportable",
    "TelegramNotifier",
]
