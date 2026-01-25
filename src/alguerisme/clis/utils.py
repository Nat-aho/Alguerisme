"""Utilities for command-line interfaces."""

import logging

from rich.console import Console
from rich.logging import RichHandler


console = Console()


def setup_logging(verbose: bool = False) -> None:
    """Set up logging with Rich handler.

    Parameters
    ----------
    verbose : bool
        Enable verbose logging

    """
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(message)s",
        handlers=[RichHandler(console=console, rich_tracebacks=True)],
    )
