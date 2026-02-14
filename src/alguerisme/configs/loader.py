"""Configuration loader with caching (Thread-safe Singleton pattern)."""

import logging
import threading
from pathlib import Path
from typing import Optional

from alguerisme.configs import AppConfig
from alguerisme.utils.env import get_env_or_die

logger = logging.getLogger(__name__)

# Private global cache and thread lock
_APP_CONFIG: Optional[AppConfig] = None
_CONFIG_LOCK = threading.Lock()


def load_app_config() -> AppConfig:
    """Load and cache the application configuration in a thread-safe manner.

    Uses the Double-Checked Locking pattern.
    """
    global _APP_CONFIG

    if _APP_CONFIG is not None:
        return _APP_CONFIG

    # Acquire lock to ensure only one thread loads the config
    with _CONFIG_LOCK:
        # Ensure it wasn't initialized while we waited for the lock
        if _APP_CONFIG is not None:
            return _APP_CONFIG

        config_path = get_env_or_die("CONFIG_PATH")
        logger.info(f"Loading configuration from: {config_path}")

        loaded_config = AppConfig.from_yaml(Path(config_path))
        _APP_CONFIG = loaded_config

        return _APP_CONFIG


def reset_app_config() -> None:
    """Invalidate the configuration cache.

    Use this primarily in testing `pytest` fixtures to ensure
    tests run in isolation with fresh configurations.
    """
    global _APP_CONFIG

    with _CONFIG_LOCK:
        _APP_CONFIG = None
        logger.debug("Application configuration cache has been reset.")
