"""Configuration model for the web crawler."""

from pydantic import BaseModel, Field


class CrawlerConfig(BaseModel):
    """Crawler configuration settings."""

    max_workers: int = Field(
        default=5, description="Maximum concurrent workers for crawling"
    )
    request_delay: float = Field(
        default=1.0, description="Delay between requests per worker (s)"
    )
