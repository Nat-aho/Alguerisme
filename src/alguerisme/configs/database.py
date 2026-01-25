"""Database configuration and connection management."""

import os
from enum import Enum
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv
from pydantic import BaseModel, Field


class DatabaseBackend(str, Enum):
    """Supported database backends."""

    SQLITE = "sqlite"
    POSTGRES = "postgres"


class DatabaseConfig(BaseModel):
    """Database configuration settings.

    Can be overridden with environment variables:
    - DATABASE_BACKEND
    - DATABASE_SQLITE_PATH
    - DATABASE_POSTGRES_HOST
    - DATABASE_POSTGRES_PORT
    - DATABASE_POSTGRES_USER
    - DATABASE_POSTGRES_PASSWORD
    - DATABASE_POSTGRES_DATABASE
    - DATABASE_ECHO

    Load from .env files using:
    - DatabaseConfig.from_env_file(".env.dev")
    - DatabaseConfig.from_env_file(".env.prod")
    """

    backend: DatabaseBackend = Field(
        default=DatabaseBackend.SQLITE,
        description="Database backend to use",
    )
    sqlite_path: str = Field(
        default="alguerisme.db",
        description="Path to SQLite database file",
    )
    postgres_host: str = Field(
        default="localhost",
        description="PostgreSQL host",
    )
    postgres_port: int = Field(
        default=5432,
        description="PostgreSQL port",
    )
    postgres_user: str = Field(
        default="alguerisme",
        description="PostgreSQL username",
    )
    postgres_password: str = Field(
        default="",
        description="PostgreSQL password",
    )
    postgres_database: str = Field(
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

        Environment variables override default values.
        Use DATABASE_ prefix for all settings.

        Returns
        -------
        DatabaseConfig
            Configuration from environment variables

        """
        backend = os.getenv("DATABASE_BACKEND", "sqlite")

        return cls(
            backend=DatabaseBackend(backend),
            sqlite_path=os.getenv("DATABASE_SQLITE_PATH", "alguerisme.db"),
            postgres_host=os.getenv("DATABASE_POSTGRES_HOST", "localhost"),
            postgres_port=int(os.getenv("DATABASE_POSTGRES_PORT", "5432")),
            postgres_user=os.getenv("DATABASE_POSTGRES_USER", "alguerisme"),
            postgres_password=os.getenv("DATABASE_POSTGRES_PASSWORD", ""),
            postgres_database=os.getenv("DATABASE_POSTGRES_DATABASE", "alguerisme"),
            echo=os.getenv("DATABASE_ECHO", "false").lower() in ("true", "1", "yes"),
        )

    @classmethod
    def from_env_file(cls, env_file: Optional[Path | str] = None) -> "DatabaseConfig":
        """Create DatabaseConfig from .env file.

        Parameters
        ----------
        env_file : Optional[Path | str]
            Path to .env file. If None, looks for .env in current directory.
            Common values: ".env.dev", ".env.prod"

        Returns
        -------
        DatabaseConfig
            Configuration loaded from .env file

        """
        if env_file:
            load_dotenv(env_file, override=True)
        else:
            load_dotenv(override=True)

        return cls.from_env()

    def with_env_overrides(self) -> "DatabaseConfig":
        """Apply environment variable overrides to this config.

        Returns
        -------
        DatabaseConfig
            New config with environment variables applied

        """
        backend = os.getenv("DATABASE_BACKEND")

        return DatabaseConfig(
            backend=DatabaseBackend(backend) if backend else self.backend,
            sqlite_path=os.getenv("DATABASE_SQLITE_PATH", self.sqlite_path),
            postgres_host=os.getenv("DATABASE_POSTGRES_HOST", self.postgres_host),
            postgres_port=int(
                os.getenv("DATABASE_POSTGRES_PORT", str(self.postgres_port))
            ),
            postgres_user=os.getenv("DATABASE_POSTGRES_USER", self.postgres_user),
            postgres_password=os.getenv(
                "DATABASE_POSTGRES_PASSWORD", self.postgres_password
            ),
            postgres_database=os.getenv(
                "DATABASE_POSTGRES_DATABASE", self.postgres_database
            ),
            echo=os.getenv("DATABASE_ECHO", str(self.echo)).lower()
            in ("true", "1", "yes"),
        )
