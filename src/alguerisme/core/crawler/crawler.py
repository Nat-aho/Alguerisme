"""Crawler module for fetching dictionary entry URLs."""

import logging

from alguerisme.configs.crawler import CrawlerConfig
from alguerisme.configs.http_client import HttpClientConfig
from alguerisme.configs.web_dictionary import WebDictionaryConfig
from alguerisme.core.crawler.utils import stream_pages_async
from alguerisme.core.http_client import HttpClientSession
from alguerisme.core.web_dictionary import WebDictionary
from alguerisme.utils.alphabet import Letter

logger = logging.getLogger(__name__)


class Crawler:
    """Web crawler for discovering dictionary entry URLs."""

    def __init__(
        self,
        web_dictionary: WebDictionary,
        http_client: HttpClientSession,
        crawler_config: CrawlerConfig,
    ):
        """Initialize the crawler."""
        self.web_dictionary = web_dictionary
        self.http_client = http_client
        self.crawler_config = crawler_config

        logger.info(f"Crawler initialized for {self.web_dictionary.base_url}")

    async def stream(self, letters: list[Letter]):
        """Asynchronously stream crawl results for the given letters.

        Parameters
        ----------
            letters: list[Letter]
                List of validated Letter objects to crawl

        Yields
        ------
            PageCrawlResult
                Results for each crawled page

        """
        async for result in stream_pages_async(
            letters=letters,
            web_dictionary=self.web_dictionary,
            http_client=self.http_client,
            crawler_config=self.crawler_config,
        ):
            yield result

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
        crawler_config: CrawlerConfig,
    ) -> "Crawler":
        """Create a Crawler instance from configuration objects."""
        web_dictionary = WebDictionary.from_config(web_dictionary_config)

        http_client = HttpClientSession.from_config(http_client_config)

        return cls(
            web_dictionary=web_dictionary,
            http_client=http_client,
            crawler_config=crawler_config,
        )
