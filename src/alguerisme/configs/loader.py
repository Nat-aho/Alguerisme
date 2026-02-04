"""Configuration loader with caching (Singleton pattern)."""

import logging
from pathlib import Path
from typing import Optional

from alguerisme.configs import AppConfig
from alguerisme.utils.env import get_env_or_die

logger = logging.getLogger(__name__)

# Private global cache
_APP_CONFIG: Optional[AppConfig] = None


def load_app_config() -> AppConfig:
    """Load and cache the application configuration."""
    global _APP_CONFIG

    if _APP_CONFIG is not None:
        return _APP_CONFIG

    config_path = get_env_or_die("CONFIG_PATH")
    logger.info(f"Loading configuration from: {config_path}")

    loaded_config = AppConfig.from_yaml(Path(config_path))

    _APP_CONFIG = loaded_config

    return _APP_CONFIG
