"""Async job logic for running the web crawler."""


import logging
from typing import Optional

from sqlmodel import Session

from alguerisme.configs import AppConfig
from alguerisme.core.crawler.crawler import Crawler
from alguerisme.core.database import create_database_engine
from alguerisme.core.crawler.crawler_service import CrawlerService
from alguerisme.core.crawler.models import CrawlServiceStats

logger = logging.getLogger(__name__)


async def run_crawl_job(
    letters: Optional[list[str]] = None, config: Optional[AppConfig] = None
) -> CrawlServiceStats:
    """Run the crawl job for the specified letters."""
    if config is None:
        config = AppConfig.load_or_default()

    engine = create_database_engine(config.db_config)

    try:
        with Session(engine) as session:
            crawler = Crawler.from_config(
                web_dictionary_config=config.web_dictionary,
                http_client_config=config.http_client,
                crawler_config=config.crawler,
            )
            service = CrawlerService(crawler, session)

            async with service.crawler.http_client:
                stats = await service.run(letters=letters)
                return stats

    except Exception as e:
        logger.error(f"Job failed: {e}")
        raise e

    finally:
        engine.dispose()
