"""Collector module for fetching raw HTML from dictionary entry pages."""

import logging
from typing import Optional
from uuid import UUID

from alguerisme.configs.http_client import HttpClientConfig
from alguerisme.configs.web_dictionary import WebDictionaryConfig
from alguerisme.core.collector.models import CollectionResult
from alguerisme.core.http_client import HttpClientSession
from alguerisme.core.web_dictionary import WebDictionary

logger = logging.getLogger(__name__)


class HTMLCollector:
    """Collector for fetching and extracting raw HTML from dictionary entries."""

    def __init__(
        self,
        web_dictionary: WebDictionary,
        http_client: HttpClientSession,
    ):
        """Initialize the collector.

        Parameters
        ----------
        web_dictionary : WebDictionary
            WebDictionary instance for HTML extraction (uses content_selector)
        http_client : HttpClientSession
            HTTP client session for making requests

        """
        self.web_dictionary = web_dictionary
        self.http_client = http_client

        logger.info(
            f"Collector initialized for {self.web_dictionary.base_url} "
            f"with selector '{self.web_dictionary.content_selector}'"
        )

    async def collect(
        self,
        url: str,
        entry_url_id: Optional[UUID] = None,
        letter: Optional[str] = None,
    ) -> CollectionResult:
        """Collect raw HTML content from a single URL.

        Parameters
        ----------
        url : str
            The URL to collect HTML from
        entry_url_id : Optional[UUID]
            Optional ID of the entry_urls record
        letter : Optional[str]
            Optional letter that this entry belongs to

        Returns
        -------
        CollectionResult
            Result containing the raw HTML or error information

        """
        logger.debug(f"Collecting HTML from: {url}")

        try:
            # Fetch the page
            response = await self.http_client.get(url)

            if response.status_code != 200:
                error_msg = f"HTTP {response.status_code}"
                logger.warning(f"Failed to fetch {url}: {error_msg}")
                return CollectionResult.from_error(
                    url=url,
                    entry_url_id=entry_url_id,
                    letter=letter,
                    error=error_msg,
                    status_code=response.status_code,
                )

            # Extract content using WebDictionary
            raw_html = self.web_dictionary.extract_content_html(response.text)

            if not raw_html:
                error_msg = (
                    f"Selector '{self.web_dictionary.content_selector}' not found"
                )
                logger.warning(f"Content extraction failed for {url}: {error_msg}")
                return CollectionResult.from_error(
                    url=url,
                    entry_url_id=entry_url_id,
                    letter=letter,
                    error=error_msg,
                    status_code=200,
                )

            logger.debug(f"Successfully collected {len(raw_html)} bytes from {url}")

            return CollectionResult.from_success(
                url=url,
                entry_url_id=entry_url_id,
                letter=letter,
                raw_html=raw_html,
                status_code=200,
            )

        except Exception as e:
            error_msg = f"{type(e).__name__}: {str(e)}"
            logger.exception(f"Exception while collecting {url}: {error_msg}")
            return CollectionResult.from_error(
                url=url,
                entry_url_id=entry_url_id,
                letter=letter,
                error=error_msg,
                status_code=0,
            )

    async def __aenter__(self):
        """Enter the async context manager."""
        return self

    async def __aexit__(self, exc_type, exc_value, traceback):
        """Exit the async context manager and close the HTTP client."""
        await self.close()

    async def close(self):
        """Close the underlying HTTP client and release resources."""
        await self.http_client.close()

    @classmethod
    def from_config(
        cls,
        web_dictionary_config: WebDictionaryConfig,
        http_client_config: HttpClientConfig,
    ) -> "HTMLCollector":
        """Create a Collector instance from configuration objects.

        Parameters
        ----------
        web_dictionary_config : WebDictionaryConfig
            Configuration for the web dictionary
        http_client_config : HttpClientConfig
            Configuration for the HTTP client

        Returns
        -------
        Collector
            Configured Collector instance

        """
        web_dictionary = WebDictionary.from_config(web_dictionary_config)
        http_client = HttpClientSession.from_config(http_client_config)

        return cls(
            web_dictionary=web_dictionary,
            http_client=http_client,
        )
