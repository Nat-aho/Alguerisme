"""Utility functions for environment variable management."""

import os
from pathlib import Path

from dotenv import load_dotenv


def get_env_or_die(key: str) -> str:
    """Get an environment variable or raise an error if not set.

    Parameters
    ----------
    key : str
        Environment variable key

    Returns
    -------
    str
        Environment variable value

    """
    value = os.getenv(key)
    if value is None:
        raise EnvironmentError(f"Environment variable '{key}' is not set.")
    return value


def load_environment(env_file: Path) -> None:
    """Load environment variables from a .env file.

    Parameters
    ----------
    env_file : Path
        Path to the .env file

    """
    if env_file.exists():
        load_dotenv(env_file, override=True)
    else:
        raise FileNotFoundError(f".env file not found: {env_file}")
