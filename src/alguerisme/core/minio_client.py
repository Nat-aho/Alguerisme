"""MinIO client wrapper for async operations."""

import hashlib
import logging
from io import BytesIO
from typing import Optional

from minio import Minio
from minio.error import S3Error

from alguerisme.configs.minio import MinioConfig

logger = logging.getLogger(__name__)


class MinioClient:
    """Wrapper for MinIO async operations.

    Provides high-level interface for uploading/downloading images
    with automatic bucket initialization and error handling.
    """

    def __init__(self, config: MinioConfig):
        """Initialize MinIO client with configuration.

        Parameters
        ----------
        config : MinioConfig
            MinIO configuration with credentials and bucket settings

        """
        self.config = config
        self.client = Minio(
            endpoint=config.endpoint,
            access_key=config.access_key,
            secret_key=config.secret_key,
            secure=config.secure,
            region=config.region,
        )
        logger.info(
            f"MinIO client initialized for bucket: {config.bucket_name} "
            f"at {config.endpoint}"
        )

    def ensure_bucket_exists(self) -> None:
        """Create bucket if it doesn't exist.

        Raises
        ------
        S3Error
            If bucket creation fails

        """
        try:
            if not self.client.bucket_exists(self.config.bucket_name):
                self.client.make_bucket(
                    self.config.bucket_name, location=self.config.region
                )
                logger.info(f"Created bucket: {self.config.bucket_name}")
            else:
                logger.debug(f"Bucket already exists: {self.config.bucket_name}")
        except S3Error as e:
            logger.error(f"Failed to ensure bucket exists: {e}")
            raise

    def upload_image(
        self,
        image_data: bytes,
        s3_key: str,
        content_type: str = "image/jpeg",
    ) -> str:
        """Upload image to MinIO.

        Parameters
        ----------
        image_data : bytes
            Raw image binary data
        s3_key : str
            S3 object key (path) for the image
        content_type : str
            MIME type of the image

        Returns
        -------
        str
            SHA256 hash of uploaded image data

        Raises
        ------
        S3Error
            If upload fails

        """
        try:
            # Calculate hash
            content_hash = hashlib.sha256(image_data).hexdigest()

            # Upload to MinIO
            data_stream = BytesIO(image_data)
            self.client.put_object(
                bucket_name=self.config.bucket_name,
                object_name=s3_key,
                data=data_stream,
                length=len(image_data),
                content_type=content_type,
            )

            logger.debug(
                f"Uploaded image to {self.config.bucket_name}/{s3_key} "
                f"({len(image_data)} bytes)"
            )
            return content_hash

        except S3Error as e:
            logger.error(f"Failed to upload image to {s3_key}: {e}")
            raise

    def download_image(self, s3_key: str) -> Optional[bytes]:
        """Download image from MinIO.

        Parameters
        ----------
        s3_key : str
            S3 object key (path) for the image

        Returns
        -------
        Optional[bytes]
            Image binary data if found, None if not found

        """
        try:
            response = self.client.get_object(
                bucket_name=self.config.bucket_name, object_name=s3_key
            )
            data = response.read()
            response.close()
            response.release_conn()

            logger.debug(
                f"Downloaded image from {self.config.bucket_name}/{s3_key} "
                f"({len(data)} bytes)"
            )
            return data

        except S3Error as e:
            if e.code == "NoSuchKey":
                logger.warning(f"Image not found: {s3_key}")
                return None
            logger.error(f"Failed to download image from {s3_key}: {e}")
            raise

    def delete_image(self, s3_key: str) -> bool:
        """Delete image from MinIO.

        Parameters
        ----------
        s3_key : str
            S3 object key (path) for the image

        Returns
        -------
        bool
            True if deleted successfully, False if not found

        """
        try:
            self.client.remove_object(
                bucket_name=self.config.bucket_name, object_name=s3_key
            )
            logger.info(f"Deleted image: {self.config.bucket_name}/{s3_key}")
            return True

        except S3Error as e:
            if e.code == "NoSuchKey":
                logger.warning(f"Image not found for deletion: {s3_key}")
                return False
            logger.error(f"Failed to delete image {s3_key}: {e}")
            raise

    def object_exists(self, s3_key: str) -> bool:
        """Check if object exists in MinIO.

        Parameters
        ----------
        s3_key : str
            S3 object key (path) to check

        Returns
        -------
        bool
            True if object exists, False otherwise

        """
        try:
            self.client.stat_object(
                bucket_name=self.config.bucket_name, object_name=s3_key
            )
            return True
        except S3Error as e:
            if e.code == "NoSuchKey":
                return False
            logger.error(f"Error checking object existence {s3_key}: {e}")
            raise

    @classmethod
    def from_config(cls, config: MinioConfig) -> "MinioClient":
        """Create MinioClient from configuration and ensure bucket exists.

        Parameters
        ----------
        config : MinioConfig
            MinIO configuration

        Returns
        -------
        MinioClient
            Initialized client with bucket ready

        """
        client = cls(config)
        client.ensure_bucket_exists()
        return client
