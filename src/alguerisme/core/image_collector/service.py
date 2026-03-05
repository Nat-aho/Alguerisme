"""Image collector service."""

import asyncio
import logging
from datetime import datetime
from typing import Optional
from uuid import UUID

from sqlmodel import Session

from alguerisme.configs.http_client import HttpClientConfig
from alguerisme.configs.minio import MinioConfig
from alguerisme.core.database.crud import (
    add_vocabols_image_to_session,
    find_parsed_vocabols_without_images,
    get_entry_urls_by_letter,
    get_vocabols_image_by_parsed_id,
)
from alguerisme.core.database.models import ParsedVocabols, VocabolsImagesCreate
from alguerisme.core.image_collector.collector import ImageCollector
from alguerisme.core.image_collector.models import ImageCollectionStats
from alguerisme.core.minio_client import MinioClient
from alguerisme.utils.alphabet import normalize_letter

logger = logging.getLogger(__name__)


class ImageCollectorService:
    """Service layer for coordinating image collection.

    Handles:
    - Finding parsed vocabols needing images
    - Downloading images via ImageCollector
    - Uploading to MinIO
    - Recording metadata in database
    - Transaction management
    """

    def __init__(
        self,
        session: Session,
        http_config: HttpClientConfig,
        minio_config: MinioConfig,
    ):
        """Initialize the service.

        Parameters
        ----------
        session : Session
            Database session for transactions
        http_config : HttpClientConfig
            HTTP client configuration
        minio_config : MinioConfig
            MinIO configuration

        """
        self.session = session
        self.http_config = http_config
        self.minio_client = MinioClient.from_config(minio_config)
        self.minio_config = minio_config

    def collect_images_for_letter_sync(
        self, letter: str, max_vocabols: Optional[int] = None
    ) -> ImageCollectionStats:
        """Collect images for all parsed vocabols of a letter (sync wrapper).

        Parameters
        ----------
        letter : str
            Letter to collect images for
        max_vocabols : Optional[int]
            Maximum number of vocabols to process (for testing)

        Returns
        -------
        ImageCollectionStats
            Statistics for the collection operation

        """
        return asyncio.run(self.collect_images_for_letter(letter, max_vocabols))

    async def collect_images_for_letter(
        self, letter: str, max_vocabols: Optional[int] = None
    ) -> ImageCollectionStats:
        """Collect images for all parsed vocabols of a letter.

        Parameters
        ----------
        letter : str
            Letter to collect images for
        max_vocabols : Optional[int]
            Maximum number of vocabols to process (for testing)

        Returns
        -------
        ImageCollectionStats
            Statistics for the collection operation

        """
        normalized_letter = normalize_letter(letter)
        logger.info(f"Starting image collection for letter: {normalized_letter}")

        stats = ImageCollectionStats.empty()

        # Find all parsed vocabols without images for this letter
        vocabols_needing_images = self._find_vocabols_needing_images(normalized_letter)

        if max_vocabols:
            vocabols_needing_images = vocabols_needing_images[:max_vocabols]

        stats.total_vocabols_with_images = len(vocabols_needing_images)

        if not vocabols_needing_images:
            logger.info(
                f"No vocabols needing image collection for letter {normalized_letter}"
            )
            return stats

        logger.info(
            f"Found {len(vocabols_needing_images)} vocabols with images for "
            f"letter {normalized_letter}"
        )

        # Process each vocabol
        async with ImageCollector(self.http_config) as collector:
            for vocabol in vocabols_needing_images:
                try:
                    await self._collect_images_for_vocabol(vocabol, collector, stats)
                except Exception as e:
                    logger.error(
                        f"Failed to collect images for vocabol {vocabol.id}: {e}"
                    )
                    stats.images_failed += 1

        logger.info(
            f"Image collection for letter {normalized_letter}: {stats.summary()}"
        )
        return stats

    def _find_vocabols_needing_images(self, letter: str) -> list[ParsedVocabols]:
        """Find parsed vocabols that need image collection for a specific letter.

        Uses the letter from entry_urls table, not the first character of the word,
        to handle accented characters correctly (é, à, etc.).

        Parameters
        ----------
        letter : str
            Letter to filter by

        Returns
        -------
        list[ParsedVocabols]
            List of vocabols needing images

        """
        all_needing_images = find_parsed_vocabols_without_images(self.session)

        # Get entry_url_ids for this letter
        entry_urls = get_entry_urls_by_letter(self.session, letter)
        entry_url_ids_for_letter = {eu.id for eu in entry_urls}

        # Filter vocabols by entry_url_id matching the letter
        filtered = [
            v for v in all_needing_images if v.entry_url_id in entry_url_ids_for_letter
        ]

        return filtered

    async def _collect_images_for_vocabol(
        self,
        vocabol: ParsedVocabols,
        collector: ImageCollector,
        stats: ImageCollectionStats,
    ) -> None:
        """Collect all images for a single vocabol.

        Parameters
        ----------
        vocabol : ParsedVocabols
            Parsed vocabol to collect images for
        collector : ImageCollector
            Image collector instance
        stats : ImageCollectionStats
            Stats object to update

        """
        # Check if already collected
        existing = get_vocabols_image_by_parsed_id(self.session, vocabol.id)
        if existing:
            logger.debug(f"Images already collected for vocabol {vocabol.id}")
            stats.images_skipped_exists += 1
            return

        if not vocabol.image_urls:
            logger.debug(f"No image URLs for vocabol {vocabol.id}")
            return

        # Collect all images for this vocabol
        for image_url in vocabol.image_urls:
            # Download image
            result = await collector.download_image(image_url)

            if not result.success:
                logger.warning(
                    f"Failed to download image for vocabol {vocabol.id}: {result.error}"
                )
                # Record failure in DB
                self._record_image_failure(
                    vocabol.id, image_url, result.error or "Unknown", vocabol.parsed_at
                )
                stats.images_failed += 1
                continue

            # Generate S3 key
            s3_key = self._generate_s3_key(vocabol, image_url)

            # Upload to MinIO
            try:
                content_hash = self.minio_client.upload_image(
                    image_data=result.image_data,  # type: ignore
                    s3_key=s3_key,
                    content_type=result.content_type or "image/jpeg",
                )

                # Record success in DB
                self._record_image_success(
                    vocabol.id,
                    image_url,
                    s3_key,
                    result.content_type or "image/jpeg",
                    len(result.image_data),  # type: ignore
                    content_hash,
                    vocabol.parsed_at,
                )
                stats.images_collected += 1
                logger.info(
                    f"Collected image for vocabol {vocabol.algueres_word}: {s3_key}"
                )

            except Exception as e:
                logger.error(
                    f"Failed to upload image to MinIO for vocabol {vocabol.id}: {e}"
                )
                self._record_image_failure(
                    vocabol.id, image_url, str(e), vocabol.parsed_at
                )
                stats.images_failed += 1

    def _generate_s3_key(self, vocabol: ParsedVocabols, image_url: str) -> str:
        """Generate S3 key for image storage.

        Format: images/{letter}/{vocabol_id}/{filename}

        Parameters
        ----------
        vocabol : ParsedVocabols
            Parsed vocabol
        image_url : str
            Source image URL

        Returns
        -------
        str
            S3 object key

        """
        # Extract filename from URL
        filename = image_url.split("/")[-1].split("?")[0]
        if not filename:
            filename = "image.jpg"

        # Get first letter of algueres word
        letter = vocabol.algueres_word[0].upper() if vocabol.algueres_word else "Z"

        return f"images/{letter}/{vocabol.id}/{filename}"

    def _record_image_success(
        self,
        parsed_vocabol_id: UUID,
        source_url: str,
        s3_key: str,
        content_type: str,
        size_bytes: int,
        content_hash: str,
        source_parsed_at: datetime,
    ) -> None:
        """Record successful image collection in database.

        Parameters
        ----------
        parsed_vocabol_id : UUID
            ID of the parsed vocabol
        source_url : str
            Original image URL
        s3_key : str
            MinIO object key
        content_type : str
            MIME type
        size_bytes : int
            Image size in bytes
        content_hash : str
            SHA256 hash
        source_parsed_at : datetime
            Timestamp from parsed_vocabols.parsed_at when images were collected

        """
        image_create = VocabolsImagesCreate(
            parsed_vocabol_id=parsed_vocabol_id,
            source_url=source_url,
            s3_key=s3_key,
            s3_bucket=self.minio_config.bucket_name,
            content_type=content_type,
            size_bytes=size_bytes,
            content_hash=content_hash,
            collection_status="success",
            source_parsed_at=source_parsed_at,
        )

        add_vocabols_image_to_session(self.session, image_create)
        self.session.commit()

    def _record_image_failure(
        self,
        parsed_vocabol_id: UUID,
        source_url: str,
        error_message: str,
        source_parsed_at: datetime,
    ) -> None:
        """Record failed image collection in database.

        Parameters
        ----------
        parsed_vocabol_id : UUID
            ID of the parsed vocabol
        source_url : str
            Original image URL
        error_message : str
            Error message
        source_parsed_at : datetime
            Timestamp from parsed_vocabols.parsed_at when collection was attempted

        """
        image_create = VocabolsImagesCreate(
            parsed_vocabol_id=parsed_vocabol_id,
            source_url=source_url,
            s3_key="",  # Empty since upload failed
            s3_bucket=self.minio_config.bucket_name,
            collection_status="failed",
            error_message=error_message,
            source_parsed_at=source_parsed_at,
        )

        add_vocabols_image_to_session(self.session, image_create)
        self.session.commit()
