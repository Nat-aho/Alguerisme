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
        max_response_size: int = 10 * 1024 * 1024,  # 10 MB
    ):
        """Initialize the HTTP client session."""
        self.timeout = timeout
        self.user_agent = user_agent
        self.headers = headers or {}
        self.max_retries = max_retries
        self.retry_start_timeout = retry_start_timeout
        self.retry_status_codes = retry_status_codes
        self.max_response_size = max_response_size

        self._client: Optional[httpx.AsyncClient] = None
        self._client_lock = asyncio.Lock()

    async def get_client(self) -> httpx.AsyncClient:
        """Get or create the async client (thread-safe with lock)."""
        # Fast path: client already exists and is open
        if self._client is not None and not self._client.is_closed:
            return self._client

        # Slow path: need to create client (use lock to prevent race condition)
        async with self._client_lock:
            # Double-check: another coroutine might have fixed it while we waited
            if self._client is not None and not self._client.is_closed:
                return self._client

            # Clean up closed client if exists
            if self._client is not None and self._client.is_closed:
                await self._client.aclose()

            # Create new client
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
        """Perform an HTTP request with retry logic and size validation."""
        attempt = 0
        backoff = self.retry_start_timeout

        while True:
            response = None
            try:
                response = await request_method(url, **kwargs)

                # Validation block - any exception here will close response
                try:
                    if response.status_code in self.retry_status_codes:
                        raise httpx.HTTPStatusError(
                            f"Retryable status code {response.status_code}",
                            request=response.request,
                            response=response,
                        )

                    self._validate_response_size(response)

                    # Success path - return without closing
                    return response

                except (httpx.RequestError, httpx.HTTPStatusError):
                    # Close and retry
                    await response.aclose()
                    raise

            except (httpx.RequestError, httpx.HTTPStatusError) as e:
                attempt += 1
                if attempt > self.max_retries:
                    logger.warning(f"Max retries reached for {url}: {e}")
                    raise

                logger.debug(f"Request failed ({e}), retrying in {backoff}s...")
                await asyncio.sleep(backoff)
                backoff *= 2.0  # Exponential backoff

    def _validate_response_size(self, response: httpx.Response):
        """Validate response size against max_response_size."""
        content_length = response.headers.get("content-length")
        if content_length and int(content_length) > self.max_response_size:
            raise httpx.RequestError(
                f"Response size {content_length} bytes exceeds "
                f"maximum {self.max_response_size} bytes"
            )

        if len(response.content) > self.max_response_size:
            raise httpx.RequestError(
                f"Response content {len(response.content)} bytes exceeds "
                f"maximum {self.max_response_size} bytes"
            )

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
            max_response_size=config.max_response_size,
        )
