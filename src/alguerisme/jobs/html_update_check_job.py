"""Job for checking existing vocabols for HTML updates."""

import logging

from sqlmodel import Session

from alguerisme.configs import AppConfig
from alguerisme.core.collector.html_collector import HTMLCollector
from alguerisme.core.collector.models import CollectionStats
from alguerisme.core.collector.html_update_service import (
    HTMLUpdateCheckerService,
)
from alguerisme.core.database import create_database_engine
from alguerisme.core.database.models import EntryURLs

logger = logging.getLogger(__name__)


async def run_html_update_check_job(
    entry_urls: list[EntryURLs],
    config: AppConfig,
) -> CollectionStats:
    """Run the update check job for specified URLs.

    Re-checks existing vocabol URLs to detect HTML content changes.
    Performs hash comparison and creates change records for review.

    Parameters
    ----------
    entry_urls : list[EntryURLs]
        List of EntryURLs to check for updates (should be existing URLs)
    config : AppConfig
        Application configuration

    Returns
    -------
    CollectionStats
        Statistics from the update check operation

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
                service = HTMLUpdateCheckerService(collector, session)
                stats = await service.run(
                    entry_urls=entry_urls,
                    request_delay=config.collector.request_delay,
                    max_workers=config.collector.max_workers,
                )
                return stats

    except Exception:
        logger.exception("Update check job failed")
        raise

    finally:
        engine.dispose()
