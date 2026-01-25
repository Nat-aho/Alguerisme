"""CLI for running the web crawler with Typer and YAML configuration."""

import logging
from pathlib import Path
from typing import Optional

import typer
from rich.console import Console
from rich.table import Table

from alguerisme.clis.utils import setup_logging
from alguerisme.configs import AppConfig, DatabaseBackend
from alguerisme.core.crawler import Crawler
from alguerisme.database import get_session, init_database
from alguerisme.services.crawler import CrawlerService

app = typer.Typer(
    name="alguerisme-crawler",
    help="Crawl Alguerés dictionary and save URLs to database",
    add_completion=False,
)

console = Console()


@app.command()
def run(
    config_file: Optional[Path] = typer.Option(
        None,
        "--config",
        "-c",
        help="Path to YAML configuration file (default: config.yaml)",
        exists=True,
        dir_okay=False,
    ),
    letters: Optional[list[str]] = typer.Option(
        None,
        "--letters",
        "-l",
        help="Specific letters to crawl (e.g., -l a -l b -l c)",
    ),
    init_db: bool = typer.Option(
        False,
        "--init-db",
        help="Initialize database tables before crawling",
    ),
    verbose: bool = typer.Option(
        False,
        "--verbose",
        "-v",
        help="Enable verbose logging",
    ),
) -> None:
    """Crawl the Alguerés dictionary and save URLs to database.

    Loads configuration from a YAML file (default: config.yaml in current directory).
    Command-line options override configuration file values.
    """
    setup_logging(verbose)
    logger = logging.getLogger(__name__)

    try:
        config = AppConfig.load_or_default(config_file)
        console.print(
            f"[green]✓[/green] Configuration loaded from: "
            f"{config_file or 'config.yaml (default)'}"
        )

        if init_db:
            console.print("[yellow]Initializing database tables...[/yellow]")
            init_database(config.database)
            console.print("[green]✓[/green] Database initialized")

        console.print("\n[bold]Configuration Summary:[/bold]")
        console.print(f"  Database: {config.database.backend}")
        if config.database.backend == DatabaseBackend.SQLITE:
            console.print(f"  SQLite path: {config.database.sqlite_path}")
        else:
            console.print(
                f"  PostgreSQL: {config.database.postgres_user}@"
                f"{config.database.postgres_host}:"
                f"{config.database.postgres_port}/"
                f"{config.database.postgres_database}"
            )
        console.print(f"  Letters: {letters if letters else 'all'}")
        console.print(f"  Max workers: {config.crawler.max_workers}")
        console.print(f"  Request delay: {config.crawler.request_delay}s\n")

        crawler = Crawler.from_config(
            web_dictionary_config=config.web_dictionary,
            http_client_config=config.http_client,
            crawler_config=config.crawler,
        )

        session = get_session(config.database)

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
