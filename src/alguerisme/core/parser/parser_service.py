"""Service for parsing vocabol HTML and persisting results."""

import logging

from sqlmodel import Session

from alguerisme.core.database.crud import upsert_parsed_vocabol_to_session
from alguerisme.core.database.models import ParsedVocabolsCreate, VocabolsRawHTML
from alguerisme.core.parser.models import ParseStats
from alguerisme.core.parser.parser import VocabolParser

logger = logging.getLogger(__name__)


class VocabolParserService:
    """Service for parsing vocabol HTML entries and persisting to database.

    Follows the same pattern as CrawlerService with batch commit strategy.
    """

    def __init__(self, parser: VocabolParser, session: Session):
        """Initialize the parser service.

        Parameters
        ----------
        parser : VocabolParser
            Parser instance for parsing HTML
        session : Session
            Database session for persistence

        """
        self.parser = parser
        self.session = session

    def parse_and_save(self, raw_html_entries: list[VocabolsRawHTML]) -> ParseStats:
        """Parse raw HTML entries and save to database.

        Uses batch commit strategy: tries to commit all at once,
        falls back to individual commits on failure.

        Parameters
        ----------
        raw_html_entries : list[VocabolsRawHTML]
            List of raw HTML entries to parse

        Returns
        -------
        ParseStats
            Statistics about the parsing operation

        """
        logger.info(f"Starting parse operation for {len(raw_html_entries)} entries")

        stats = ParseStats(total_entries=len(raw_html_entries))

        # Parse all entries and add to session (no commits yet)
        for entry in raw_html_entries:
            self._parse_single_entry(entry, stats)

        # Batch commit strategy (service controls transaction boundary)
        try:
            self.session.commit()
            logger.info(
                f"Batch commit successful: {stats.parsed_successfully} entries saved"
            )
        except Exception as e:
            logger.warning(
                f"Batch commit failed: {e}. Falling back to individual commits"
            )
            self.session.rollback()
            stats = self._fallback_individual_commits(raw_html_entries)

        logger.info(stats.summary())
        return stats

    def _parse_single_entry(self, entry: VocabolsRawHTML, stats: ParseStats) -> None:
        """Parse a single entry and add to session without committing.

        Parameters
        ----------
        entry : VocabolsRawHTML
            Raw HTML entry to parse
        stats : ParseStats
            Stats object to update

        """
        # Skip if no HTML content
        if not entry.raw_html:
            logger.debug(f"Skipping {entry.url}: no HTML content")
            stats.skipped_no_html += 1
            return

        try:
            # Parse HTML (pure function, no I/O)
            parsed = self.parser.parse(entry.raw_html)

            # Skip if parsing resulted in completely empty entry
            if parsed.is_empty():
                logger.debug(f"Skipping {entry.url}: parsing resulted in empty entry")
                stats.skipped_empty_result += 1
                return

            # Convert to database model
            db_entry = ParsedVocabolsCreate(
                entry_url_id=entry.entry_url_id,
                raw_html_id=entry.id,
                url=entry.url,
                algueres_word=parsed.algueres_word,
                algueres_definition=parsed.algueres_definition,
                catalan_word=parsed.catalan_word,
                catalan_definition=parsed.catalan_definition,
                italian_word=parsed.italian_word,
                italian_definition=parsed.italian_definition,
                image_urls=parsed.image_urls,  # SQLModel handles JSONB serialization
                audio_urls=parsed.audio_urls,  # SQLModel handles JSONB serialization
                image_url_count=len(parsed.image_urls),
                audio_url_count=len(parsed.audio_urls),
                parsing_errors=None,
            )

            # Upsert to session without committing (service controls transaction)
            # This handles both new entries and re-parsing updated HTML
            parsed_entry, was_created = upsert_parsed_vocabol_to_session(
                self.session, db_entry
            )
            stats.parsed_successfully += 1
            if was_created:
                stats.entries_created += 1
            else:
                stats.entries_updated += 1

            action = "Created" if was_created else "Updated"
            logger.debug(f"{action}: {entry.url}")

        except Exception as e:
            logger.error(f"Failed to parse {entry.url}: {e}")
            stats.parsing_failed += 1

            # Optionally save failed entry with error message
            try:
                error_entry = ParsedVocabolsCreate(
                    entry_url_id=entry.entry_url_id,
                    raw_html_id=entry.id,
                    url=entry.url,
                    parsing_errors=str(e)[:500],  # Truncate long errors
                )
                upsert_parsed_vocabol_to_session(self.session, error_entry)
            except Exception as save_error:
                logger.error(
                    f"Failed to save error record for {entry.url}: {save_error}"
                )

    def _fallback_individual_commits(
        self, raw_html_entries: list[VocabolsRawHTML]
    ) -> ParseStats:
        """Fallback strategy: commit each entry individually.

        Parameters
        ----------
        raw_html_entries : list[VocabolsRawHTML]
            List of raw HTML entries to parse

        Returns
        -------
        ParseStats
            Statistics from individual commit attempts

        """
        stats = ParseStats(total_entries=len(raw_html_entries))

        for entry in raw_html_entries:
            # Skip if no HTML
            if not entry.raw_html:
                stats.skipped_no_html += 1
                continue

            try:
                # Parse
                parsed = self.parser.parse(entry.raw_html)

                if parsed.is_empty():
                    stats.skipped_empty_result += 1
                    continue

                # Create DB entry
                db_entry = ParsedVocabolsCreate(
                    entry_url_id=entry.entry_url_id,
                    raw_html_id=entry.id,
                    url=entry.url,
                    algueres_word=parsed.algueres_word,
                    algueres_definition=parsed.algueres_definition,
                    catalan_word=parsed.catalan_word,
                    catalan_definition=parsed.catalan_definition,
                    italian_word=parsed.italian_word,
                    italian_definition=parsed.italian_definition,
                    image_urls=parsed.image_urls,  # SQLModel handles JSONB
                    audio_urls=parsed.audio_urls,  # SQLModel handles JSONB
                    image_url_count=len(parsed.image_urls),
                    audio_url_count=len(parsed.audio_urls),
                    parsing_errors=None,
                )

                # Upsert and commit individually
                parsed_entry, was_created = upsert_parsed_vocabol_to_session(
                    self.session, db_entry
                )
                self.session.commit()
                stats.parsed_successfully += 1
                if was_created:
                    stats.entries_created += 1
                else:
                    stats.entries_updated += 1

                action = "Created" if was_created else "Updated"
                logger.debug(f"{action} (individual): {entry.url}")

            except Exception as e:
                logger.error(f"Individual commit failed for {entry.url}: {e}")
                self.session.rollback()
                stats.parsing_failed += 1

        return stats
