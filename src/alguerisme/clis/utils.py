"""Utilities for command-line interfaces."""

import logging
from typing import Literal

from rich.console import Console
from rich.logging import RichHandler

console = Console()


def setup_logging(
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR"] = "INFO",
) -> None:
    """Set up logging with Rich handler.

    Parameters
    ----------
    log_level : Literal["DEBUG", "INFO", "WARNING", "ERROR"]
        Logging level to set

    """
    level = getattr(logging, log_level)
    logging.basicConfig(
        level=level,
        format="%(message)s",
        handlers=[RichHandler(console=console, rich_tracebacks=True)],
    )
