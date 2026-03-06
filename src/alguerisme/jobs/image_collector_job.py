"""Image collector job orchestrating resources and calling the service."""

import logging

from sqlmodel import Session

from alguerisme.configs.loader import load_app_config
from alguerisme.core.database.database import create_database_engine
from alguerisme.core.image_collector.models import (
    LetterImageCollectionResult,
)
from alguerisme.core.image_collector.service import ImageCollectorService
from alguerisme.utils.alphabet import Alphabet, Letter

logger = logging.getLogger(__name__)


def run_image_collection_for_letter(
    letter: str | Letter,
) -> LetterImageCollectionResult:
    """Run image collection job for a single letter.

    Orchestrates database engine, session, and service instantiation.

    Parameters
    ----------
    letter : str | Letter
        Letter to collect images for

    Returns
    -------
    LetterImageCollectionResult
        Result containing stats or error

    """
    # Normalize letter
    if isinstance(letter, str):
        letter = Letter(letter)

    logger.info(f"Starting image collection job for letter: {letter.value}")

    # Load config
    config = load_app_config()

    # Create database engine
    engine = create_database_engine(config.db_config)

    try:
        # Execute in session
        with Session(engine) as session:
            service = ImageCollectorService(
                session=session,
                http_config=config.http_client_images,
                minio_config=config.minio_config,
            )

            stats = service.collect_images_for_letter_sync(letter.value)

            logger.info(f"Completed image collection for letter {letter.value}")
            return LetterImageCollectionResult.successful(letter.value, stats)

    except Exception as e:
        logger.error(
            f"Image collection failed for letter {letter.value}: {e}", exc_info=True
        )
        return LetterImageCollectionResult.failed(letter.value, str(e))

    finally:
        engine.dispose()


def run_image_collection_for_letters(
    letters: list[str],
) -> list[LetterImageCollectionResult]:
    """Run image collection job for multiple letters sequentially.

    Parameters
    ----------
    letters : list[str]
        Letters to collect images for

    Returns
    -------
    list[LetterImageCollectionResult]
        Results for each letter

    """
    # Validate letters
    alphabet = Alphabet()
    letter_objects = [
        Letter(letter) for letter in letters if letter.upper() in alphabet
    ]

    logger.info(f"Starting image collection job for letters: {', '.join(letters)}")

    results = []
    for letter in letter_objects:
        result = run_image_collection_for_letter(letter)
        results.append(result)

    # Log summary
    successful = [r for r in results if r.success]
    failed = [r for r in results if not r.success]

    logger.info(
        f"Image collection job complete: {len(successful)}/{len(results)} "
        f"letters succeeded"
    )
    if failed:
        logger.warning(f"Failed letters: {', '.join([r.letter for r in failed])}")

    return results
