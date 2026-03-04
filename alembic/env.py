"""Alembic environment configuration for database migrations.

This module configures Alembic to work with SQLModel and load database
configuration from environment variables.

Environment Variables:
    DATABASE_HOST: PostgreSQL host
    DATABASE_PORT: PostgreSQL port
    DATABASE_USER: PostgreSQL username
    DATABASE_PASSWORD: PostgreSQL password
    DATABASE_NAME: PostgreSQL database name

Usage:
    # Load from .env.dev
    dotenv run --dotenv .env.dev alembic upgrade head

    # Load from .env.prod
    dotenv run --dotenv .env.prod alembic upgrade head

    # Or set variables manually
    DATABASE_HOST=localhost DATABASE_USER=user alembic upgrade head

"""

from logging.config import fileConfig

from sqlalchemy import engine_from_config, pool

# Import your SQLModel models and database utilities
from sqlmodel import SQLModel
from sqlmodel.sql.sqltypes import AutoString

from alembic import context
from alguerisme.configs.database import DatabaseConfig
from alguerisme.core.database import get_database_url

# Import enums first to avoid circular dependency issues
from alguerisme.core.collector.enums import ChangeStatus, ChangeType  # noqa: F401

# Now import models (they depend on enums being available)
from alguerisme.core.database.models import (
    EntryURLs,
    ParsedVocabols,
    VocabolsHtmlChanges,
    VocabolsRawHTML,
)

_alembic_models = (
    EntryURLs,
    VocabolsRawHTML,
    VocabolsHtmlChanges,
    ParsedVocabols,
)  # Add SQLModel models here for autogeneration support

# this is the Alembic Config object, which provides
# access to the values within the .ini file in use.
config = context.config

# Load database configuration from environment variables
# Make sure to load .env file before running alembic
# Example: dotenv run --dotenv .env.dev alembic upgrade head
db_config = DatabaseConfig()
database_url = get_database_url(db_config)

# Override the sqlalchemy.url with our configured database URL
config.set_main_option(
    "sqlalchemy.url", database_url.render_as_string(hide_password=False)
)

# Interpret the config file for Python logging.
# This line sets up loggers basically.
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# add your model's MetaData object here
# for 'autogenerate' support
# Use SQLModel's metadata which includes all table=True models
target_metadata = SQLModel.metadata


# Custom type renderer to handle SQLModel's AutoString
def render_item(type_, obj, autogen_context):
    """Render SQLModel AutoString as sa.String for migrations."""
    if isinstance(obj, AutoString):
        # Convert AutoString to regular SQLAlchemy String
        if obj.length:
            return f"sa.String(length={obj.length})"
        return "sa.String()"
    # Return False to use default rendering
    return False


# other values from the config, defined by the needs of env.py,
# can be acquired:
# my_important_option = config.get_main_option("my_important_option")
# ... etc.


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode.

    This configures the context with just a URL
    and not an Engine, though an Engine is acceptable
    here as well.  By skipping the Engine creation
    we don't even need a DBAPI to be available.

    Calls to context.execute() here emit the given string to the
    script output.

    """
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        render_item=render_item,
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode.

    In this scenario we need to create an Engine
    and associate a connection with the context.

    """
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            render_item=render_item,
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
