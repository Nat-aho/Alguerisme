"""Service layer for business logic and orchestration."""

from alguerisme.services.crawler.crawler import CrawlerService
from alguerisme.services.crawler.models import CrawlServiceResult

__all__ = ["CrawlerService", "CrawlServiceResult"]
