"""Celery and Redis configuration."""

import os

from pydantic import BaseModel, Field, PrivateAttr, SecretStr

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

    _password: SecretStr | None = PrivateAttr(default=None)
    _broker_url: str | None = PrivateAttr(default=None)
    _backend_url: str | None = PrivateAttr(default=None)

    @property
    def password(self) -> str:
        """Retrieve Redis password from secrets."""
        if self._password is None:
            self._password = SecretStr(get_secret("redis_password"))
        return self._password.get_secret_value()

    @property
    def broker_url(self) -> str:
        """Construct the Redis Broker URL."""
        if self._broker_url is None:
            auth = f":{self.password}@" if self.password else ""
            self._broker_url = (
                f"redis://{auth}{self.redis_host}:{self.redis_port}/{self.redis_db}"
            )
        return self._broker_url

    @property
    def backend_url(self) -> str:
        """Construct the Redis Backend URL."""
        if self._backend_url is None:
            auth = f":{self.password}@" if self.password else ""
            self._backend_url = (
                f"redis://{auth}{self.redis_host}:{self.redis_port}/{self.redis_db}"
            )
        return self._backend_url

    @classmethod
    def from_env(cls) -> "CeleryConfig":
        """Load configuration structure from environment."""
        return cls(
            redis_host=os.getenv("REDIS_HOST", "redis"),
            redis_port=int(os.getenv("REDIS_PORT", 6379)),
            redis_db=int(os.getenv("REDIS_DB", 0)),
            timezone=os.getenv("CELERY_TIMEZONE", "Europe/Rome"),
        )
