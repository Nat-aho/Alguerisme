"""CLI for inspecting parsed_vocabols table."""

from typing import Literal, Optional

import typer
from rich.console import Console
from rich.table import Table
from sqlmodel import Session

from alguerisme.clis.utils import get_letters_or_default, setup_logging
from alguerisme.configs.loader import load_app_config
from alguerisme.core.database import crud
from alguerisme.core.database.database import get_session
from alguerisme.core.database.models import ParsedVocabols

app = typer.Typer(
    name="parsed-vocabols",
    help="Inspect parsed_vocabols table",
    no_args_is_help=True,
    add_completion=False,
)

console = Console()


@app.command()
def stats(
    letters: Optional[str] = typer.Option(
        None,
        "--letters",
        "-l",
        help="Letters to filter by (e.g., 'ABC'). Uses all if omitted.",
    ),
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR"] = typer.Option(
        "WARNING",
        "--log-level",
        "-L",
        help="Logging level",
    ),
) -> None:
    """Show statistics about parsed vocabols (total, with images, with audio)."""
    setup_logging(log_level)

    try:
        config = load_app_config()

        with get_session(config.db_config) as session:
            if letters:
                validated_letters = get_letters_or_default(letters, console)
                _show_stats_by_letters(session, validated_letters)
            else:
                _show_overall_stats(session)

    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        raise typer.Exit(1) from e


@app.command(name="list")
def list_entries(
    limit: int = typer.Option(
        50,
        "--limit",
        "-n",
        help="Maximum number of rows to display",
    ),
    letters: Optional[str] = typer.Option(
        None,
        "--letters",
        "-l",
        help="Letters to filter by (e.g., 'ABC'). Uses all if omitted.",
    ),
    with_images: Optional[bool] = typer.Option(
        None,
        "--with-images/--without-images",
        help="Filter by presence of images",
    ),
    with_audio: Optional[bool] = typer.Option(
        None,
        "--with-audio/--without-audio",
        help="Filter by presence of audio",
    ),
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR"] = typer.Option(
        "WARNING",
        "--log-level",
        "-L",
        help="Logging level",
    ),
) -> None:
    """List parsed vocabols with optional filters."""
    setup_logging(log_level)

    try:
        config = load_app_config()

        with get_session(config.db_config) as session:
            # Validate letters if provided
            validated_letters = None
            if letters:
                validated_letters = get_letters_or_default(letters, console)

            # Get entries using CRUD function
            entries = crud.get_parsed_vocabols_list(
                session,
                limit=limit,
                letters=validated_letters,
                with_images=with_images,
                with_audio=with_audio,
            )

            # Display results
            _display_entries_table(entries)

    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        raise typer.Exit(1) from e


@app.command()
def show(
    url: str = typer.Argument(..., help="URL of the parsed vocabol to show"),
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR"] = typer.Option(
        "WARNING",
        "--log-level",
        "-L",
        help="Logging level",
    ),
) -> None:
    """Show detailed information for a specific parsed vocabol by URL."""
    setup_logging(log_level)

    try:
        config = load_app_config()

        with get_session(config.db_config) as session:
            entry = crud.find_parsed_vocabol_by_url(session, url)

            if not entry:
                console.print(f"[red]No parsed vocabol found for URL: {url}[/red]")
                raise typer.Exit(1)

            _display_entry_details(entry)

    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        raise typer.Exit(1) from e


def _show_overall_stats(session: Session) -> None:
    """Show overall statistics for all parsed vocabols."""
    stats = crud.get_parsed_vocabols_overall_stats(session)

    # Create stats table
    table = Table(title="Parsed Vocabols Statistics")
    table.add_column("Metric", style="cyan")
    table.add_column("Count", style="green", justify="right")
    table.add_column("Percentage", style="yellow", justify="right")

    table.add_row("Total Parsed", str(stats.total), "100%")
    table.add_row(
        "With Images",
        str(stats.with_images),
        f"{stats.with_images / stats.total * 100:.1f}%" if stats.total > 0 else "0%",
    )
    table.add_row(
        "With Audio",
        str(stats.with_audio),
        f"{stats.with_audio / stats.total * 100:.1f}%" if stats.total > 0 else "0%",
    )
    table.add_row(
        "With Errors",
        str(stats.with_errors),
        f"{stats.with_errors / stats.total * 100:.1f}%" if stats.total > 0 else "0%",
    )
    table.add_row("Total Images", str(stats.total_images), "-")
    table.add_row("Total Audio", str(stats.total_audio), "-")

    console.print(table)


def _show_stats_by_letters(session: Session, letters: list[str]) -> None:
    """Show statistics broken down by letter."""
    table = Table(title=f"Parsed Vocabols Statistics for {', '.join(letters)}")
    table.add_column("Letter", style="cyan", justify="center")
    table.add_column("Total", style="green", justify="right")
    table.add_column("With Images", style="blue", justify="right")
    table.add_column("With Audio", style="magenta", justify="right")
    table.add_column("Avg Images", style="yellow", justify="right")
    table.add_column("Avg Audio", style="yellow", justify="right")

    for letter in letters:
        stats = crud.get_parsed_vocabols_stats_by_letter(session, letter)

        table.add_row(
            stats.letter,
            str(stats.total),
            str(stats.with_images),
            str(stats.with_audio),
            f"{stats.avg_images:.1f}",
            f"{stats.avg_audio:.1f}",
        )

    console.print(table)


def _display_entries_table(entries) -> None:
    """Display parsed vocabols in a table format."""
    table = Table(title=f"Parsed Vocabols ({len(entries)} entries)")
    table.add_column("Alguerés", style="cyan")
    table.add_column("Català", style="blue")
    table.add_column("Italiano", style="green")
    table.add_column("Images", style="magenta", justify="center")
    table.add_column("Audio", style="yellow", justify="center")
    table.add_column("URL", style="dim", overflow="fold")

    for entry in entries:
        table.add_row(
            entry.algueres_word or "-",
            entry.catalan_word or "-",
            entry.italian_word or "-",
            str(entry.image_url_count),
            str(entry.audio_url_count),
            entry.url,
        )

    console.print(table)


def _display_entry_details(entry: ParsedVocabols) -> None:
    """Display detailed information for a single parsed vocabol."""
    console.print("\n[bold cyan]Parsed Vocabol Details[/bold cyan]\n")

    # Basic info
    console.print(f"[bold]ID:[/bold] {entry.id}")
    console.print(f"[bold]URL:[/bold] {entry.url}")
    console.print(f"[bold]Parsed At:[/bold] {entry.parsed_at}")

    # Alguerés
    console.print("\n[bold cyan]Alguerés:[/bold cyan]")
    console.print(f"  Word: {entry.algueres_word or '-'}")
    console.print(f"  Definition: {entry.algueres_definition or '-'}")

    # Catalan
    console.print("\n[bold blue]Català:[/bold blue]")
    console.print(f"  Word: {entry.catalan_word or '-'}")
    console.print(f"  Definition: {entry.catalan_definition or '-'}")

    # Italian
    console.print("\n[bold green]Italiano:[/bold green]")
    console.print(f"  Word: {entry.italian_word or '-'}")
    console.print(f"  Definition: {entry.italian_definition or '-'}")

    # Media
    console.print("\n[bold magenta]Media:[/bold magenta]")
    console.print(f"  Images: {entry.image_url_count}")
    if entry.image_urls:
        for i, url in enumerate(entry.image_urls, 1):
            console.print(f"    {i}. {url}")

    console.print(f"  Audio: {entry.audio_url_count}")
    if entry.audio_urls:
        for i, url in enumerate(entry.audio_urls, 1):
            console.print(f"    {i}. {url}")

    # Errors
    if entry.parsing_errors:
        console.print("\n[bold red]Parsing Errors:[/bold red]")
        console.print(f"  {entry.parsing_errors}")

    console.print()
