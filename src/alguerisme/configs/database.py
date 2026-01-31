"""Database configuration and connection management."""

from pydantic import BaseModel, Field

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

    @property
    def password(self) -> str:
        """Retrieve database password from secrets."""
        return get_secret("db_password")

    @property
    def url(self) -> str:
        """Construct the database connection URL."""
        return (
            f"postgresql://{self.user}:{self.password}"
            f"@{self.host}:{self.port}/{self.database}"
        )

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
