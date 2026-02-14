"""Utilities for command-line interfaces."""

import logging
from typing import Literal, Optional

import typer
from rich.console import Console
from rich.logging import RichHandler

from alguerisme.utils.alphabet import Alphabet, normalize_letters

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


def get_letters_or_default(letters: Optional[str], console: Console) -> list[str]:
    """Get validated letters list or default to full alphabet (A-Z).

    Parameters
    ----------
    letters : Optional[str]
        Letters string (e.g., 'ABC') or None for full alphabet
    console : Console
        Rich console for error output

    Returns
    -------
    list[str]
        List of normalized uppercase letters

    Raises
    ------
    typer.Exit
        If letters string is empty or contains invalid letters

    """
    if letters is not None:
        validated_letters = normalize_letters(list(letters), unique=True)
        if not validated_letters:
            console.print("[red]Error:[/red] Letters string cannot be empty")
            raise typer.Exit(code=1)
        return validated_letters
    else:
        # Use full alphabet A-Z
        alphabet = Alphabet.standard()
        return [str(letter) for letter in alphabet]
