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

    except FileNotFoundError:
        logger.error(f"Secret '{secret_name}' is missing from the secret store.")
        raise KeyError(f"Secret '{secret_name}' not found.") from None

    except OSError as e:
        logger.error(f"IO error accessing secret '{secret_name}': {type(e).__name__}")
        raise RuntimeError(
            f"Secret '{secret_name}' exists but is inaccessible."
        ) from None

    except Exception:
        logger.error(f"Unexpected error retrieving secret '{secret_name}'")
        raise RuntimeError(f"Internal error fetching secret '{secret_name}'") from None
