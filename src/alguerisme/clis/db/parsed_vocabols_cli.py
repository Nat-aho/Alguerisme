"""CLI for inspecting parsed_vocabols table."""

from typing import Literal, Optional

import typer
from rich.console import Console
from rich.table import Table
from sqlalchemy import func
from sqlmodel import Session, select

from alguerisme.clis.utils import get_letters_or_default, setup_logging
from alguerisme.configs.loader import load_app_config
from alguerisme.core.database import crud
from alguerisme.core.database.database import get_session
from alguerisme.core.database.models import ParsedVocabols
from alguerisme.utils.alphabet import normalize_letter

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
            # Build query
            statement = select(ParsedVocabols)

            # Filter by letters if provided
            if letters:
                validated_letters = get_letters_or_default(letters, console)
                # Get entry_url_ids for these letters
                entry_urls = []
                for letter in validated_letters:
                    entry_urls.extend(crud.get_entry_urls_by_letter(session, letter))

                entry_url_ids = [eu.id for eu in entry_urls]
                statement = statement.where(
                    ParsedVocabols.entry_url_id.in_(entry_url_ids)  # type: ignore[attr-defined]
                )

            # Filter by images
            if with_images is not None:
                if with_images:
                    statement = statement.where(ParsedVocabols.image_url_count > 0)
                else:
                    statement = statement.where(ParsedVocabols.image_url_count == 0)

            # Filter by audio
            if with_audio is not None:
                if with_audio:
                    statement = statement.where(ParsedVocabols.audio_url_count > 0)
                else:
                    statement = statement.where(ParsedVocabols.audio_url_count == 0)

            statement = statement.limit(limit)
            entries = session.exec(statement).all()

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
    total = crud.count_parsed_vocabols(session)

    # Count entries with images
    with_images = session.exec(
        select(func.count())
        .select_from(ParsedVocabols)
        .where(ParsedVocabols.image_url_count > 0)
    ).one()

    # Count entries with audio
    with_audio = session.exec(
        select(func.count())
        .select_from(ParsedVocabols)
        .where(ParsedVocabols.audio_url_count > 0)
    ).one()

    # Sum of all images
    total_images = session.exec(
        select(func.sum(ParsedVocabols.image_url_count)).select_from(ParsedVocabols)
    ).one() or 0

    # Sum of all audio files
    total_audio = session.exec(
        select(func.sum(ParsedVocabols.audio_url_count)).select_from(ParsedVocabols)
    ).one() or 0

    # Count entries with errors
    with_errors = session.exec(
        select(func.count())
        .select_from(ParsedVocabols)
        .where(ParsedVocabols.parsing_errors.isnot(None))  # type: ignore[attr-defined]
    ).one()

    # Create stats table
    table = Table(title="Parsed Vocabols Statistics")
    table.add_column("Metric", style="cyan")
    table.add_column("Count", style="green", justify="right")
    table.add_column("Percentage", style="yellow", justify="right")

    table.add_row("Total Parsed", str(total), "100%")
    table.add_row(
        "With Images",
        str(with_images),
        f"{with_images/total*100:.1f}%" if total > 0 else "0%",
    )
    table.add_row(
        "With Audio",
        str(with_audio),
        f"{with_audio/total*100:.1f}%" if total > 0 else "0%",
    )
    table.add_row(
        "With Errors",
        str(with_errors),
        f"{with_errors/total*100:.1f}%" if total > 0 else "0%",
    )
    table.add_row("Total Images", str(total_images), "-")
    table.add_row("Total Audio", str(total_audio), "-")

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
        normalized = normalize_letter(letter)

        # Get entry_url_ids for this letter
        entry_urls = crud.get_entry_urls_by_letter(session, normalized)
        entry_url_ids = [eu.id for eu in entry_urls]

        if not entry_url_ids:
            table.add_row(normalized, "0", "0", "0", "0.0", "0.0")
            continue

        # Count total parsed for this letter
        total = session.exec(
            select(func.count())
            .select_from(ParsedVocabols)
            .where(ParsedVocabols.entry_url_id.in_(entry_url_ids))  # type: ignore[attr-defined]
        ).one()

        # Count with images
        with_images = session.exec(
            select(func.count())
            .select_from(ParsedVocabols)
            .where(ParsedVocabols.entry_url_id.in_(entry_url_ids))  # type: ignore[attr-defined]
            .where(ParsedVocabols.image_url_count > 0)
        ).one()

        # Count with audio
        with_audio = session.exec(
            select(func.count())
            .select_from(ParsedVocabols)
            .where(ParsedVocabols.entry_url_id.in_(entry_url_ids))  # type: ignore[attr-defined]
            .where(ParsedVocabols.audio_url_count > 0)
        ).one()

        # Average images per entry
        avg_images = session.exec(
            select(func.avg(ParsedVocabols.image_url_count))
            .select_from(ParsedVocabols)
            .where(ParsedVocabols.entry_url_id.in_(entry_url_ids))  # type: ignore[attr-defined]
        ).one() or 0.0

        # Average audio per entry
        avg_audio = session.exec(
            select(func.avg(ParsedVocabols.audio_url_count))
            .select_from(ParsedVocabols)
            .where(ParsedVocabols.entry_url_id.in_(entry_url_ids))  # type: ignore[attr-defined]
        ).one() or 0.0

        table.add_row(
            normalized,
            str(total),
            str(with_images),
            str(with_audio),
            f"{avg_images:.1f}",
            f"{avg_audio:.1f}",
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
