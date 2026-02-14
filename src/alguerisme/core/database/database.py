"""Database utility functions for initializing and managing the database."""

from sqlalchemy.engine import URL
from sqlmodel import Session, SQLModel, create_engine

from alguerisme.configs import DatabaseConfig


def init_database(config: DatabaseConfig):
    """Initialize database tables.

    Creates all tables defined in SQLModel metadata if they don't exist.

    Parameters
    ----------
    config : DatabaseConfig
        Database configuration

    """
    engine = create_database_engine(config)
    SQLModel.metadata.create_all(engine)


def get_session(config: DatabaseConfig) -> Session:
    """Get a database session.

    Parameters
    ----------
    config : DatabaseConfig
        Database configuration

    Returns
    -------
    Session
        SQLModel database session

    """
    engine = create_database_engine(config)
    return Session(engine)


def create_database_engine(config: DatabaseConfig):
    """Create SQLAlchemy engine from configuration.

    Parameters
    ----------
    config : DatabaseConfig
        Database configuration

    Returns
    -------
    Engine
        SQLAlchemy engine instance

    """
    database_url = get_database_url(config)
    return create_engine(database_url, echo=config.echo)


def get_database_url(config: DatabaseConfig) -> URL:
    """Build PostgreSQL database URL from configuration.

    Parameters
    ----------
    config : DatabaseConfig
        Database configuration

    Returns
    -------
    sqlalchemy.engine.URL
        SQLAlchemy database URL

    """
    return config.url
