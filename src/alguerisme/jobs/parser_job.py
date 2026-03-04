"""Job for parsing raw HTML vocabol entries."""

import logging

from sqlmodel import Session, select

from alguerisme.configs import AppConfig
from alguerisme.core.database import create_database_engine
from alguerisme.core.database.models import VocabolsRawHTML
from alguerisme.core.parser.models import ParseStats
from alguerisme.core.parser.parser import VocabolParser
from alguerisme.core.parser.parser_service import VocabolParserService
from alguerisme.utils.alphabet import Letter

logger = logging.getLogger(__name__)


async def run_parse_job(letters: list[Letter], config: AppConfig) -> ParseStats:
    """Run the parse job for the specified letters.

    Fetches raw HTML entries for the given letters and parses them
    into structured data.

    Parameters
    ----------
    letters : list[Letter]
        List of validated Letter objects
    config : AppConfig
        Application configuration

    Returns
    -------
    ParseStats
        Statistics from the parse operation

    """
    engine = create_database_engine(config.db_config)

    try:
        # Create parser from config
        parser = VocabolParser.from_config(
            web_config=config.web_dictionary,
            parser_config=config.parser,
            base_url=config.web_dictionary.base_url,
        )

        # Query raw HTML entries for the given letters
        with Session(engine) as session:
            # Get unparsed entries for these letters
            letter_strs = [str(letter) for letter in letters]
            statement = (
                select(VocabolsRawHTML)
                .where(VocabolsRawHTML.letter.in_(letter_strs))
                .where(VocabolsRawHTML.raw_html.isnot(None))
            )
            raw_html_entries = list(session.exec(statement).all())

            logger.info(
                f"Found {len(raw_html_entries)} raw HTML entries "
                f"for letters: {letter_strs}"
            )

            if not raw_html_entries:
                logger.warning("No raw HTML entries found to parse")
                return ParseStats.empty()

            # Parse and save
            service = VocabolParserService(parser, session)
            stats = service.parse_and_save(raw_html_entries)

            return stats

    except Exception:
        logger.exception("Parse job failed")
        raise

    finally:
        engine.dispose()
