"""Job for collecting HTML from NEW vocabol URLs."""

import logging

from sqlmodel import Session

from alguerisme.configs import AppConfig
from alguerisme.core.collector.html_collector import HTMLCollector
from alguerisme.core.collector.models import CollectionStats
from alguerisme.core.collector.html_collector_service import HTMLCollectorService
from alguerisme.core.database import create_database_engine
from alguerisme.core.database.models import EntryURLs

logger = logging.getLogger(__name__)


async def run_html_collection_job(
    entry_urls: list[EntryURLs],
    config: AppConfig,
) -> CollectionStats:
    """Run the HTML collection job for specified URLs.

    Collects HTML for NEW vocabol URLs that haven't been collected yet.
    Saves directly to vocabols_raw_html without change detection.

    Parameters
    ----------
    entry_urls : list[EntryURLs]
        List of EntryURLs to collect HTML from (should be pending/new URLs)
    config : AppConfig
        Application configuration

    Returns
    -------
    CollectionStats
        Statistics from the collection operation

    """
    engine = create_database_engine(config.db_config)

    try:
        # Use async context manager for collector to ensure HTTP client cleanup
        async with HTMLCollector.from_config(
            web_dictionary_config=config.web_dictionary,
            http_client_config=config.http_client,
        ) as collector:
            # Create session within async context
            with Session(engine) as session:
                service = HTMLCollectorService(collector, session)
                stats = await service.run(
                    entry_urls=entry_urls,
                    request_delay=config.collector.request_delay,
                    max_workers=config.collector.max_workers,
                )
                return stats

    except Exception:
        logger.exception("New collection job failed")
        raise

    finally:
        engine.dispose()
