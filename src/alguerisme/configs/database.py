"""Database configuration and connection management."""

from pydantic import BaseModel, Field, PrivateAttr, SecretStr
from sqlalchemy.engine import URL

from alguerisme.utils.env import get_env_or_die
from alguerisme.utils.secrets import get_secret


class DatabaseConfig(BaseModel):
    """PostgreSQL database configuration settings.

    Connection settings (host, port, user, database) are loaded from
    environment variables. Pool settings are configured via YAML config file.

    Environment Variables:
        DATABASE_HOST: PostgreSQL host
        DATABASE_PORT: PostgreSQL port
        DATABASE_USER: PostgreSQL username
        DATABASE_NAME: PostgreSQL database name

    """

    model_config = {"arbitrary_types_allowed": True}

    # Connection settings - loaded from environment
    host: str = Field(
        default_factory=lambda: get_env_or_die("DATABASE_HOST"),
        description="PostgreSQL host",
    )
    port: int = Field(
        default_factory=lambda: int(get_env_or_die("DATABASE_PORT")),
        description="PostgreSQL port",
    )
    user: str = Field(
        default_factory=lambda: get_env_or_die("DATABASE_USER"),
        description="PostgreSQL username",
    )
    database: str = Field(
        default_factory=lambda: get_env_or_die("DATABASE_NAME"),
        description="PostgreSQL database name",
    )

    # Pool settings - configured in YAML
    pool_size: int = Field(
        default=5,
        description="Connection pool size",
    )
    max_overflow: int = Field(
        default=10,
        description="Maximum overflow connections beyond pool_size",
    )
    pool_pre_ping: bool = Field(
        default=True,
        description="Validate connections before using them",
    )
    pool_recycle: int = Field(
        default=3600,
        description="Recycle connections after N seconds (default: 1 hour)",
    )
    echo: bool = Field(
        default=False,
        description="Echo SQL queries (for debugging)",
    )

    _password: SecretStr | None = PrivateAttr(default=None)
    _url: URL | None = PrivateAttr(default=None)

    @property
    def password(self) -> str:
        """Read and cache the database password."""
        if self._password is None:
            self._password = SecretStr(get_secret("db_password"))
        return self._password.get_secret_value()

    @property
    def url(self) -> URL:
        """Build and cache the database URL."""
        if self._url is None:
            self._url = URL.create(
                drivername="postgresql",
                username=self.user,
                password=self.password,
                host=self.host,
                port=self.port,
                database=self.database,
            )
        return self._url
