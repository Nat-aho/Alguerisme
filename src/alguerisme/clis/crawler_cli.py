"""CLI for running the web crawler with Typer and YAML configuration."""

import logging
from pathlib import Path
from typing import Optional

import typer
from rich.console import Console
from rich.table import Table

from alguerisme.clis.utils import setup_logging
from alguerisme.configs import AppConfig, DatabaseConfig
from alguerisme.core.crawler import Crawler
from alguerisme.services.database import get_session
from alguerisme.services.crawler import CrawlerService

app = typer.Typer(
    name="alguerisme-crawler",
    help="Crawl Alguerés dictionary and save URLs to database",
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
    verbose: bool = typer.Option(
        False,
        "--verbose",
        "-v",
        help="Enable verbose logging",
    ),
) -> None:
    """Crawl the Alguerés dictionary and save URLs to database.

    Loads crawler configuration from YAML and database config from environment.
    """
    setup_logging(verbose)
    logger = logging.getLogger(__name__)

    try:
        if env_file:
            from alguerisme.utils.env import load_environment

            load_environment(env_file)
            console.print(f"[green]✓[/green] Environment loaded from: {env_file}")

        db_config = DatabaseConfig.from_env()

        config = AppConfig.load_or_default(config_file)
        console.print(
            f"[green]✓[/green] Crawler config loaded from: "
            f"{config_file or 'config.yaml (default)'}"
        )

        console.print("\n[bold]Configuration Summary:[/bold]")
        console.print(
            f"  PostgreSQL: {db_config.user}@"
            f"{db_config.host}:"
            f"{db_config.port}/"
            f"{db_config.database}"
        )
        console.print(f"  Letters: {letters if letters else 'all'}")
        console.print(f"  Max workers: {config.crawler.max_workers}")
        console.print(f"  Request delay: {config.crawler.request_delay}s\n")

        crawler = Crawler.from_config(
            web_dictionary_config=config.web_dictionary,
            http_client_config=config.http_client,
            crawler_config=config.crawler,
        )

        session = get_session(db_config)

        console.print("[bold green]Starting crawl...[/bold green]\n")

        crawler_service = CrawlerService(crawler, session)
        result = crawler_service.crawl_and_save(letters)

        console.print("\n[bold green]✓ Crawl Complete![/bold green]\n")

        table = Table(title="Crawl Results", show_header=True, header_style="bold cyan")
        table.add_column("Metric", style="cyan")
        table.add_column("Value", style="magenta", justify="right")

        table.add_row("Pages Crawled", str(result.crawl_result.total_pages))
        table.add_row("URLs Discovered", str(result.crawl_result.url_count))
        table.add_row("New URLs Saved", str(result.urls_saved))
        table.add_row("Existing URLs Skipped", str(result.urls_skipped))
        table.add_row("Failed Operations", str(result.urls_failed))

        console.print(table)

        if result.crawl_result.urls_by_letter:
            console.print("\n[bold]URLs per letter:[/bold]")
            letter_table = Table(show_header=True, header_style="bold cyan")
            letter_table.add_column("Letter", style="cyan")
            letter_table.add_column("Count", style="magenta", justify="right")

            for letter, urls in sorted(result.crawl_result.urls_by_letter.items()):
                letter_table.add_row(letter.upper(), str(len(urls)))

            console.print(letter_table)

        session.close()
        crawler.http_client.close()

        console.print("\n[green]✓ Done![/green]")

    except Exception as e:
        console.print(f"\n[bold red]Error:[/bold red] {e}")
        logger.error("Crawl failed", exc_info=True)
        raise typer.Exit(code=1)


def main() -> None:
    """Run the CLI application."""
    app()


if __name__ == "__main__":
    main()
