"""Configuration model for the HTML collector."""

from pydantic import BaseModel, Field


class CollectorConfig(BaseModel):
    """Collector configuration settings."""

    max_workers: int = Field(
        default=5, description="Maximum concurrent workers for collection"
    )
    request_delay: float = Field(
        default=1.0, description="Delay between requests per worker (s)"
    )
