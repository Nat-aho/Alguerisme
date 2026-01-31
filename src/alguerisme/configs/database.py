"""Database configuration and connection management."""

from pydantic import BaseModel, Field

from alguerisme.utils.env import get_env_or_die


class DatabaseConfig(BaseModel):
    """PostgreSQL database configuration settings.

    All settings are loaded from environment variables.

    Environment Variables:
        DATABASE_HOST: PostgreSQL host (default: localhost)
        DATABASE_PORT: PostgreSQL port (default: 5432)
        DATABASE_USER: PostgreSQL username (default: alguerisme)
        DATABASE_PASSWORD: PostgreSQL password (default: "")
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
    password: str = Field(
        default="",
        description="PostgreSQL password",
    )
    database: str = Field(
        default="alguerisme",
        description="PostgreSQL database name",
    )
    echo: bool = Field(
        default=False,
        description="Echo SQL queries (for debugging)",
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
            password=get_env_or_die("DATABASE_PASSWORD"),
            database=get_env_or_die("DATABASE_NAME"),
            echo=get_env_or_die("DATABASE_ECHO").lower() in ("true", "1", "yes"),
        )
