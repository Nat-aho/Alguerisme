"""Core image collector for downloading images from URLs."""

import asyncio
import logging
from typing import Optional

from alguerisme.configs.http_client import HttpClientConfig
from alguerisme.core.http_client import HttpClientSession

logger = logging.getLogger(__name__)


class ImageDownloadResult:
    """Result of a single image download attempt."""

    def __init__(
        self,
        url: str,
        success: bool,
        image_data: Optional[bytes] = None,
        content_type: Optional[str] = None,
        error: Optional[str] = None,
    ):
        """Initialize download result.

        Parameters
        ----------
        url : str
            Source URL of the image
        success : bool
            Whether download succeeded
        image_data : Optional[bytes]
            Raw image binary data if successful
        content_type : Optional[str]
            MIME type from response headers
        error : Optional[str]
            Error message if failed

        """
        self.url = url
        self.success = success
        self.image_data = image_data
        self.content_type = content_type
        self.error = error


class ImageCollector:
    """Core component for downloading images from URLs.

    Pure async logic - no database dependencies.
    Service layer handles MinIO uploads and DB transactions.
    Uses HttpClientSession for consistent retry logic and error handling.
    """

    def __init__(self, http_config: HttpClientConfig):
        """Initialize the image collector.

        Parameters
        ----------
        http_config : HttpClientConfig
            HTTP client configuration

        """
        self.http_config = http_config
        self.session: Optional[HttpClientSession] = None

    async def __aenter__(self) -> "ImageCollector":
        """Async context manager entry."""
        self.session = HttpClientSession.from_config(self.http_config)
        await self.session.get_client()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        if self.session:
            await self.session.close()

    async def download_image(
        self, url: str, max_size_mb: int = 10
    ) -> ImageDownloadResult:
        """Download a single image from URL.

        Parameters
        ----------
        url : str
            Image URL to download
        max_size_mb : int
            Maximum allowed image size in MB (overrides http_config.max_response_size)

        Returns
        -------
        ImageDownloadResult
            Result containing image data or error

        """
        if not self.session:
            raise RuntimeError("ImageCollector must be used as async context manager")

        try:
            # Temporarily override max_response_size for images
            original_max_size = self.session.max_response_size
            self.session.max_response_size = max_size_mb * 1024 * 1024

            response = await self.session.get(url)

            # Restore original max size
            self.session.max_response_size = original_max_size

            if response.status_code != 200:
                return ImageDownloadResult(
                    url=url,
                    success=False,
                    error=f"HTTP {response.status_code}",
                )

            content_type = response.headers.get("Content-Type", "image/jpeg")
            image_data = response.content

            logger.debug(f"Downloaded image from {url}: {len(image_data)} bytes")
            return ImageDownloadResult(
                url=url,
                success=True,
                image_data=image_data,
                content_type=content_type,
            )

        except asyncio.TimeoutError:
            logger.warning(f"Timeout downloading image: {url}")
            return ImageDownloadResult(url=url, success=False, error="Timeout")

        except Exception as e:
            logger.error(f"Failed to download image from {url}: {e}")
            return ImageDownloadResult(url=url, success=False, error=str(e))

    async def download_images(
        self, urls: list[str], max_size_mb: int = 10
    ) -> list[ImageDownloadResult]:
        """Download multiple images concurrently.

        Parameters
        ----------
        urls : list[str]
            List of image URLs to download
        max_size_mb : int
            Maximum allowed image size in MB per image

        Returns
        -------
        list[ImageDownloadResult]
            List of results for each URL

        """
        tasks = [self.download_image(url, max_size_mb) for url in urls]
        results = await asyncio.gather(*tasks, return_exceptions=False)
        return list(results)

    @classmethod
    async def download_single_image(
        cls, url: str, http_config: HttpClientConfig, max_size_mb: int = 10
    ) -> ImageDownloadResult:
        """Download a single image.

        Parameters
        ----------
        url : str
            Image URL to download
        http_config : HttpClientConfig
            HTTP client configuration
        max_size_mb : int
            Maximum allowed image size in MB

        Returns
        -------
        ImageDownloadResult
            Result containing image data or error

        """
        async with cls(http_config) as collector:
            return await collector.download_image(url, max_size_mb)
