"""CLI for parser operations."""

import asyncio
import logging

import typer
from rich.console import Console

from alguerisme.configs.loader import load_app_config
from alguerisme.jobs.parser_job import run_parse_job
from alguerisme.utils.alphabet import Alphabet

app = typer.Typer(
    name="parser",
    help="Parse raw HTML vocabol entries",
    no_args_is_help=True,
)

console = Console()
logger = logging.getLogger(__name__)


@app.command("run")
def run_parser(
    letters: list[str] = typer.Option(
        None,
        "--letters",
        "-l",
        help="Letters to parse (space-separated). If not provided, parses all.",
    ),
):
    """Parse raw HTML entries for specified letters.

    Examples
    --------
    alguerisme parser run --letters A B C
    alguerisme parser run  # Parse all letters

    """
    console.print("[bold cyan]Starting parser...[/bold cyan]")

    # Load config
    config = load_app_config()

    # Validate letters
    alphabet = Alphabet.standard()
    if letters:
        try:
            validated_letters = alphabet.validate_subset(letters)
        except ValueError as e:
            console.print(f"[red]Error: {e}[/red]")
            raise typer.Exit(1)
    else:
        # Parse all letters if none specified
        validated_letters = list(alphabet)

    console.print(
        f"Parsing letters: {', '.join(str(letter) for letter in validated_letters)}"
    )

    # Run the parse job
    try:
        stats = asyncio.run(run_parse_job(validated_letters, config))

        console.print("\n[bold green]✓ Parsing complete[/bold green]")
        console.print(f"  Parsed successfully: {stats.parsed_successfully}")
        console.print(f"  Failed: {stats.parsing_failed}")
        console.print(f"  Skipped (no HTML): {stats.skipped_no_html}")
        console.print(f"  Skipped (empty): {stats.skipped_empty_result}")

    except Exception as e:
        console.print(f"\n[red]✗ Parsing failed: {e}[/red]")
        logger.exception("Parser failed")
        raise typer.Exit(1)


if __name__ == "__main__":
    app()
