"""Utility functions for managing secrets."""

import logging
from pathlib import Path

logger = logging.getLogger(__name__)

_DEFAULT_SECRET_PATH = Path("/run/secrets/")


def get_secret(secret_name: str) -> str:
    """Retrieve a secret value from Docker secrets.

    Parameters
    ----------
    secret_name : str
        Name of the secret to retrieve

    Returns
    -------
    str
        Secret value

    """
    docker_secret_path = _DEFAULT_SECRET_PATH / secret_name
    try:
        return docker_secret_path.read_text().strip()
    except FileNotFoundError as e:
        logger.error(f"Docker secret file not found for '{secret_name}': {e}")
    except OSError as e:
        logger.error(
            f"Found Docker secret '{secret_name}' but could not read it: {e}"
        )
    except Exception as e:
        logger.error(
            f"Unexpected error while reading Docker secret '{secret_name}': {e}"
        )
    raise EnvironmentError(f"Secret '{secret_name}' not found.")
