"""Configuration model for HTTP client settings."""

from typing import Dict, Tuple

from pydantic import BaseModel, Field


class HttpClientConfig(BaseModel):
    """Configuration model for HTTP client settings."""

    timeout: float = Field(default=10.0, description="Request timeout in seconds")
    user_agent: str = Field(
        default="Mozilla/5.0 (X11; Linux x86_64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36",
        description="User-Agent header",
    )
    headers: Dict[str, str] = Field(
        default_factory=dict, description="Additional HTTP headers"
    )

    max_retries: int = Field(default=3, description="Maximum retries per request")
    retry_start_timeout: float = Field(
        default=1.0, description="Initial wait time in seconds before the first retry"
    )
    retry_status_codes: Tuple[int, ...] = Field(
        default=(429, 500, 502, 503, 504),
        description="HTTP status codes that trigger retries",
    )
