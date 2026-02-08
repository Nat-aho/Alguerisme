"""Celery and Redis configuration."""

import os

from pydantic import BaseModel, Field

from alguerisme.utils.secrets import get_secret


class CeleryConfig(BaseModel):
    """Configuration for Celery and Redis."""

    redis_host: str = Field(default="redis")
    redis_port: int = Field(default=6379)
    redis_db: int = Field(default=0)

    timezone: str = Field(default="Europe/Rome")
    enable_utc: bool = Field(default=True)
    task_serializer: str = Field(default="json")
    result_serializer: str = Field(default="json")
    accept_content: list[str] = Field(default_factory=lambda: ["json"])
    result_expires: int = Field(default=3600)

    @property
    def password(self) -> str:
        """Retrieve Redis password from secrets."""
        return get_secret("redis_password")

    @property
    def broker_url(self) -> str:
        """Construct the Redis Broker URL."""
        auth = f":{self.password}@" if self.password else ""
        return f"redis://{auth}{self.redis_host}:{self.redis_port}/{self.redis_db}"

    @property
    def result_backend(self) -> str:
        """Construct the Redis Backend URL."""
        auth = f":{self.password}@" if self.password else ""
        return f"redis://{auth}{self.redis_host}:{self.redis_port}/{self.redis_db}"

    @classmethod
    def from_env(cls) -> "CeleryConfig":
        """Load configuration structure from environment."""
        return cls(
            redis_host=os.getenv("REDIS_HOST", "redis"),
            redis_port=int(os.getenv("REDIS_PORT", 6379)),
            redis_db=int(os.getenv("REDIS_DB", 0)),
            timezone=os.getenv("CELERY_TIMEZONE", "Europe/Rome"),
        )
