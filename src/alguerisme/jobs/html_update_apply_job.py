"""Job for applying approved HTML changes to production."""

import logging
from datetime import datetime, timezone

from sqlmodel import Session

from alguerisme.configs import AppConfig
from alguerisme.core.collector.enums import ChangeStatus
from alguerisme.core.collector.models import ApplyChangesResult
from alguerisme.core.database import create_database_engine
from alguerisme.core.database.crud import (
    delete_change_by_id,
    find_vocabols_raw_html_by_entry_url_id,
    list_changes_by_status,
)

logger = logging.getLogger(__name__)


def run_html_update_apply_job(config: AppConfig) -> ApplyChangesResult:
    """Apply all approved changes to the production table.

    This job:
    1. Gets all approved changes from vocabols_html_changes
    2. Updates vocabols_raw_html with new content
    3. Sets last_updated_at to track when content changed
    4. Deletes the approved change records

    Parameters
    ----------
    config : AppConfig
        Application configuration

    Returns
    -------
    ApplyChangesResult
        Result with statistics about the operation

    """
    engine = create_database_engine(config.db_config)
    applied_count = 0
    skipped_count = 0
    error_count = 0

    try:
        with Session(engine) as session:
            # Get all approved changes
            approved_changes = list_changes_by_status(
                session, status=ChangeStatus.APPROVED
            )

            if not approved_changes:
                logger.info("No approved changes to apply")
                return ApplyChangesResult.success(
                    applied=0,
                    skipped=0,
                    errors=0,
                    message="No approved changes found",
                )

            logger.info(f"Found {len(approved_changes)} approved changes to apply")
            now = datetime.now(timezone.utc)

            for change in approved_changes:
                try:
                    # Get current production record
                    current = find_vocabols_raw_html_by_entry_url_id(
                        session, change.entry_url_id
                    )

                    if not current:
                        logger.warning(
                            f"No current record found for {change.url}, skipping"
                        )
                        skipped_count += 1
                        # Still delete the change record
                        delete_change_by_id(session, change.id)
                        continue

                    # Apply the change
                    current.raw_html = change.new_html
                    current.content_hash = change.new_hash
                    current.last_updated_at = now
                    current.http_status_code = 200  # Assume success

                    session.add(current)
                    session.commit()

                    logger.info(f"Applied change for {change.url}")
                    applied_count += 1

                    # Delete the approved change record
                    delete_change_by_id(session, change.id)

                except Exception as e:
                    logger.error(
                        f"Error applying change for {change.url}: {e}",
                        exc_info=True
                    )
                    session.rollback()
                    error_count += 1
                    # Don't delete the change if there was an error

            logger.info(
                f"Apply changes complete: {applied_count} applied, "
                f"{skipped_count} skipped, {error_count} errors"
            )

            return ApplyChangesResult.success(
                applied=applied_count,
                skipped=skipped_count,
                errors=error_count,
            )

    except Exception as e:
        logger.exception("Apply changes job failed")
        return ApplyChangesResult.error(message=str(e))

    finally:
        engine.dispose()
