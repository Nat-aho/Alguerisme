"""Database configuration and connection management."""

from pydantic import BaseModel, Field, PrivateAttr, SecretStr
from sqlalchemy.engine import URL

from alguerisme.utils.env import get_env_or_die
from alguerisme.utils.secrets import get_secret


class DatabaseConfig(BaseModel):
    """PostgreSQL database configuration settings.

    All settings are loaded from environment variables.

    Environment Variables:
        DATABASE_HOST: PostgreSQL host (default: localhost)
        DATABASE_PORT: PostgreSQL port (default: 5432)
        DATABASE_USER: PostgreSQL username (default: alguerisme)
        DATABASE_NAME: PostgreSQL database name (default: alguerisme)
        DATABASE_ECHO: Echo SQL queries for debugging (default: false)

    """

    model_config = {"arbitrary_types_allowed": True}

    host: str = Field(
        default="localhost",
        description="PostgreSQL host",
    )
    port: int = Field(
        default=5432,
        description="PostgreSQL port",
    )
    user: str = Field(
        default="alguerisme",
        description="PostgreSQL username",
    )
    database: str = Field(
        default="alguerisme",
        description="PostgreSQL database name",
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

    @classmethod
    def from_env(cls) -> "DatabaseConfig":
        """Create DatabaseConfig from environment variables.

        Returns
        -------
        DatabaseConfig
            Configuration from environment variables

        """
        return cls(
            host=get_env_or_die("DATABASE_HOST"),
            port=int(get_env_or_die("DATABASE_PORT")),
            user=get_env_or_die("DATABASE_USER"),
            database=get_env_or_die("DATABASE_NAME"),
            echo=get_env_or_die("DATABASE_ECHO").lower() in ("true", "1", "yes"),
        )
