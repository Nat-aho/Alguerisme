"""HTTP client utilities for creating and configuring HTTP sessions."""

from typing import Dict, Optional, Tuple

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from alguerisme.configs.http_client import HttpClientConfig


class HttpClientSession:
    """HTTP client session with retry logic and configurable settings."""

    def __init__(
        self,
        timeout: float = 10.0,
        user_agent: str = "Mozilla/5.0 (X11; Linux x86_64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36",
        headers: Optional[Dict[str, str]] = None,
        max_retries: int = 3,
        retry_status_codes: Tuple[int, ...] = (429, 500, 502, 503, 504),
        retry_backoff_factor: float = 1.0,
        max_retry_delay: float = 30.0,
    ):
        """Initialize HTTP client session."""
        self.timeout = timeout
        self.user_agent = user_agent
        self.headers = headers or {}
        self.max_retries = max_retries
        self.retry_status_codes = retry_status_codes
        self.retry_backoff_factor = retry_backoff_factor
        self.max_retry_delay = max_retry_delay

        self._session: Optional[requests.Session] = None

    @property
    def session(self) -> requests.Session:
        """Get or create the requests session with retry logic."""
        if self._session is None:
            self._session = self._create_session()
        return self._session

    def _create_session(self) -> requests.Session:
        """Create and configure a requests.Session with retry logic."""
        session = requests.Session()

        # Set headers
        session.headers.update({"User-Agent": self.user_agent})
        if self.headers:
            session.headers.update(self.headers)

        # Configure retry strategy
        retry_strategy = Retry(
            total=self.max_retries,
            status_forcelist=list(self.retry_status_codes),
            backoff_factor=self.retry_backoff_factor,
            raise_on_status=False,
        )

        adapter = HTTPAdapter(max_retries=retry_strategy)
        session.mount("http://", adapter)
        session.mount("https://", adapter)

        return session

    def get(self, url: str, **kwargs) -> requests.Response:
        """Perform GET request with configured timeout."""
        if "timeout" not in kwargs:
            kwargs["timeout"] = self.timeout
        return self.session.get(url, **kwargs)

    def close(self):
        """Close the session."""
        if self._session is not None:
            self._session.close()
            self._session = None

    def __enter__(self):
        """Context manager entry."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.close()

    @classmethod
    def from_config(cls, config: "HttpClientConfig") -> "HttpClientSession":
        """Create HttpClientSession from HttpClientConfig."""
        return cls(
            timeout=config.timeout,
            user_agent=config.user_agent,
            headers=config.headers,
            max_retries=config.max_retries,
            retry_status_codes=config.retry_status_codes,
            retry_backoff_factor=config.retry_backoff_factor,
            max_retry_delay=config.max_retry_delay,
        )
