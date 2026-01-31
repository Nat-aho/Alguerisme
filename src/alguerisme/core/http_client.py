"""Async HTTP client session with retry logic."""

import asyncio
import logging
from typing import Awaitable, Callable, Container, Dict, Optional

import httpx

from alguerisme.configs.http_client import HttpClientConfig

logger = logging.getLogger(__name__)


class HttpClientSession:
    """Async HTTP client session with retry logic."""

    def __init__(
        self,
        timeout: float = 10.0,
        user_agent: str = "AlguerismeBot/1.0",
        headers: Optional[Dict[str, str]] = None,
        max_retries: int = 3,
        retry_start_timeout: float = 1.0,
        retry_status_codes: Container[int] = (429, 500, 502, 503, 504),
    ):
        """Initialize the HTTP client session."""
        self.timeout = timeout
        self.user_agent = user_agent
        self.headers = headers or {}
        self.max_retries = max_retries
        self.retry_start_timeout = retry_start_timeout
        self.retry_status_codes = retry_status_codes

        self._client: Optional[httpx.AsyncClient] = None

    async def get_client(self) -> httpx.AsyncClient:
        """Get or create the async client."""
        if self._client is None or self._client.is_closed:
            headers = {"User-Agent": self.user_agent}
            if self.headers:
                headers.update(self.headers)

            self._client = httpx.AsyncClient(
                headers=headers, timeout=self.timeout, follow_redirects=True
            )
        return self._client

    async def get(self, url: str) -> httpx.Response:
        """Perform GET request with manual retry logic."""
        client = await self.get_client()
        return await self._request_with_retry(client.get, url)

    async def _request_with_retry(
        self,
        request_method: Callable[..., Awaitable[httpx.Response]],
        url: str,
        **kwargs,
    ) -> httpx.Response:
        """Perform an HTTP request with retry logic."""
        attempt = 0
        backoff = self.retry_start_timeout

        while True:
            try:
                response = await request_method(url, **kwargs)

                if response.status_code in self.retry_status_codes:
                    raise httpx.HTTPStatusError(
                        f"Retryable status code {response.status_code}",
                        request=response.request,
                        response=response,
                    )

                return response

            except (httpx.RequestError, httpx.HTTPStatusError) as e:
                attempt += 1
                if attempt > self.max_retries:
                    logger.warning(f"Max retries reached for {url}: {e}")
                    raise e

                logger.debug(f"Request failed ({e}), retrying in {backoff}s...")
                await asyncio.sleep(backoff)
                backoff *= 2.0  # Exponential backoff

    async def close(self):
        """Close the async client session."""
        if self._client:
            await self._client.aclose()
            self._client = None

    async def __aenter__(self):
        """Enter the async context manager."""
        await self.get_client()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Exit the async context manager."""
        await self.close()

    @classmethod
    def from_config(cls, config: HttpClientConfig) -> "HttpClientSession":
        """Create an HttpClientSession instance from a configuration object."""
        return cls(
            timeout=config.timeout,
            user_agent=config.user_agent,
            headers=config.headers,
            max_retries=config.max_retries,
            retry_start_timeout=config.retry_start_timeout,
            retry_status_codes=config.retry_status_codes,
        )
