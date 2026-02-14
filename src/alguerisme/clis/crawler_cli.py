"""CLI for running the web crawler with Typer and YAML configuration."""

import asyncio
from typing import Literal

import typer
from rich.console import Console

from alguerisme.clis.utils import setup_logging
from alguerisme.configs.loader import load_app_config
from alguerisme.jobs import run_crawl_job
from alguerisme.utils.alphabet import Letter, Alphabet

app = typer.Typer(
    name="alguerisme-crawler",
    help="Crawl Alguerés dictionary and save URLs to database",
    no_args_is_help=True,
    add_completion=False,
)

console = Console()


@app.command()
def run(
    letters: list[str] = typer.Option(
        [str(letter) for letter in Alphabet.standard()],
        "--letters",
        "-l",
        help="Specific letters to crawl (e.g. -l A -l B -l C)",
    ),
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR"] = typer.Option(
        "INFO",
        "--log-level",
        "-L",
        help="Logging level (DEBUG, INFO, WARNING, ERROR)",
    ),
) -> None:
    """Crawl the Alguerés dictionary and save URLs to database."""
    setup_logging(log_level)

    try:
        validated_letters = [Letter(letter) for letter in letters]

        config = load_app_config()
        console.print("[green]✓[/green] Configuration loaded")

        console.print("[blue]Starting crawl job...[/blue]")
        stats = asyncio.run(run_crawl_job(letters=validated_letters, config=config))
        console.print(f"[green]✓[/green] Crawl job completed:\n{stats.summary()}")

    except ValueError as e:
        console.print(f"[red]Invalid letter:[/red] {e}")
        raise typer.Exit(code=1)
    except Exception as e:
        console.print(f"[red]Failed:[/red] {e}")
        raise typer.Exit(code=1)
