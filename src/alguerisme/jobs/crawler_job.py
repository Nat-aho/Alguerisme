"""Async job logic for running the web crawler."""


import logging

from sqlmodel import Session

from alguerisme.configs import AppConfig
from alguerisme.core.crawler.crawler import Crawler
from alguerisme.core.database import create_database_engine
from alguerisme.core.crawler.crawler_service import CrawlerService
from alguerisme.core.crawler.models import CrawlServiceStats
from alguerisme.utils.alphabet import Letter

logger = logging.getLogger(__name__)


async def run_crawl_job(
    letters: list[Letter], config: AppConfig
) -> CrawlServiceStats:
    """Run the crawl job for the specified letters.

    Parameters
    ----------
    letters: list[Letter]
        List of validated Letter objects
    config: AppConfig
        Application configuration

    Returns
    -------
    CrawlServiceStats
        Statistics from the crawl operation

    """
    engine = create_database_engine(config.db_config)

    try:
        # Use async context manager for crawler to ensure HTTP client cleanup
        async with Crawler.from_config(
            web_dictionary_config=config.web_dictionary,
            http_client_config=config.http_client,
            crawler_config=config.crawler,
        ) as crawler:
            # Create session within async context
            with Session(engine) as session:
                service = CrawlerService(crawler, session)
                stats = await service.run(letters=letters)
                return stats

    except Exception:
        logger.exception("Job failed")
        raise

    finally:
        engine.dispose()
