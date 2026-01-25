"""Unified application configuration from YAML file."""

from pathlib import Path
from typing import Optional

import yaml
from pydantic import BaseModel, Field

from alguerisme.configs.crawler import CrawlerConfig
from alguerisme.configs.http_client import HttpClientConfig
from alguerisme.configs.web_dictionary import WebDictionaryConfig


class AppConfig(BaseModel):
    """Unified application configuration.

    This combines crawler, HTTP client, and web dictionary configurations
    that can be loaded from a YAML file.

    NOTE: Database configuration is handled separately via environment variables.
    """

    http_client: HttpClientConfig = Field(
        default_factory=lambda: HttpClientConfig(),
        description="HTTP client configuration",
    )
    web_dictionary: WebDictionaryConfig = Field(
        default_factory=lambda: WebDictionaryConfig(),
        description="Web dictionary configuration",
    )
    crawler: CrawlerConfig = Field(
        default_factory=lambda: CrawlerConfig(),
        description="Crawler configuration",
    )

    @classmethod
    def from_yaml(cls, yaml_path: Path) -> "AppConfig":
        """Load configuration from YAML file.

        Parameters
        ----------
        yaml_path : Path
            Path to YAML configuration file

        Returns
        -------
        AppConfig
            Loaded configuration instance

        """
        with open(yaml_path, "r") as f:
            config_dict = yaml.safe_load(f)

        return cls(**config_dict)

    def to_yaml(self, yaml_path: Path) -> None:
        """Save configuration to YAML file.

        Parameters
        ----------
        yaml_path : Path
            Path where to save YAML configuration

        """
        with open(yaml_path, "w") as f:
            yaml.dump(
                self.model_dump(mode="python"),
                f,
                default_flow_style=False,
                sort_keys=False,
            )

    @classmethod
    def get_default_config_path(cls) -> Path:
        """Get default configuration file path.

        Returns
        -------
        Path
            Default path to config.yaml in current directory

        """
        return Path.cwd() / "config.yaml"

    @classmethod
    def load_or_default(cls, config_path: Optional[Path] = None) -> "AppConfig":
        """Load config from file or return default if file doesn't exist.

        Parameters
        ----------
        config_path : Optional[Path]
            Path to config file, uses default if None

        Returns
        -------
        AppConfig
            Loaded or default configuration

        """
        if config_path is None:
            config_path = cls.get_default_config_path()

        if config_path.exists():
            return cls.from_yaml(config_path)
        else:
            return cls()
