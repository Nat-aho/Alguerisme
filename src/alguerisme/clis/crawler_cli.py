"""CLI for running the web crawler with Typer and YAML configuration."""

import asyncio
from pathlib import Path
from typing import Literal, Optional

import typer
from rich.console import Console

from alguerisme.clis.utils import setup_logging
from alguerisme.configs import AppConfig
from alguerisme.jobs import run_crawl_job

app = typer.Typer(
    name="alguerisme-crawler",
    help="Crawl Alguerés dictionary and save URLs to database",
    no_args_is_help=True,
    add_completion=False,
)

console = Console()


@app.command()
def run(
    config_file: Path = typer.Option(
        "config.yaml",
        "--config",
        "-c",
        help="Path to YAML configuration file (default: config.yaml)",
        exists=True,
        dir_okay=False,
    ),
    env_file: Optional[Path] = typer.Option(
        None,
        "--env",
        "-e",
        help="Path to .env file to load environment variables from.",
        exists=True,
        dir_okay=False,
    ),
    letters: Optional[list[str]] = typer.Option(
        None,
        "--letters",
        "-l",
        help="Specific letters to crawl (e.g., -l a -l b -l c)",
    ),
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR"] = typer.Option(
        "INFO",
        "--log-level",
        "-L",
        help="Logging level (DEBUG, INFO, WARNING, ERROR)",
    ),
) -> None:
    """Crawl the Alguerés dictionary and save URLs to database.

    Loads crawler configuration from YAML and database config from environment.
    """
    setup_logging(log_level)

    try:
        if env_file:
            from alguerisme.utils.env import load_environment

            load_environment(env_file)
            console.print(f"[green]✓[/green] Environment loaded from: {env_file}")

        config = AppConfig.from_yaml(config_file)
        console.print(f"[green]✓[/green] Configuration loaded from: {config_file}")

        console.print("[blue]Starting crawl job...[/blue]")
        stats = asyncio.run(run_crawl_job(letters=letters, config=config))
        console.print(f"[green]✓[/green] Crawl job completed:\n{stats.summary()}")

    except Exception as e:
        console.print(f"[red]Failed:[/red] {e}")
        raise typer.Exit(code=1)


def main() -> None:
    """Run the CLI application."""
    app()


if __name__ == "__main__":
    main()
