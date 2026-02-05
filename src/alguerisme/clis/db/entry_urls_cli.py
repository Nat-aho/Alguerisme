"""CLI for managing the entry_urls table."""

from typing import Literal, Optional

import typer
from rich.console import Console
from rich.table import Table

from alguerisme.clis.utils import setup_logging
from alguerisme.configs.loader import load_app_config
from alguerisme.core.database import crud
from alguerisme.core.database.database import get_session
from alguerisme.utils.alphabet import Alphabet, Letter

app = typer.Typer(
    name="entry-urls",
    help="Manage entry_urls table",
    no_args_is_help=True,
    add_completion=False,
)

console = Console()


@app.command()
def show(
    limit: int = typer.Option(
        50,
        "--limit",
        "-n",
        help="Maximum number of rows to display",
    ),
    letter: Optional[str] = typer.Option(
        None,
        "--letter",
        "-l",
        help="Filter by letter",
    ),
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR"] = typer.Option(
        "WARNING",
        "--log-level",
        "-L",
        help="Logging level",
    ),
) -> None:
    """Display contents of the entry_urls table."""
    setup_logging(log_level)

    try:
        # Validate letter if provided
        validated_letter = None
        if letter:
            try:
                validated_letter = Letter(letter)
            except ValueError as e:
                console.print(f"[red]Invalid letter:[/red] {e}")
                raise typer.Exit(code=1)

        config = load_app_config()
        session = get_session(config.db_config)

        # Get total count efficiently
        if validated_letter:
            total_count = crud.count_entry_urls_by_letter(
                session, str(validated_letter)
            )
        else:
            total_count = crud.count_entry_urls(session)

        # Get entries with pagination (efficient - only fetch what we need)
        entries = crud.get_entry_urls_paginated(
            session,
            limit=limit,
            offset=0,
            letter=str(validated_letter) if validated_letter else None,
        )

        # Create table
        title = f"Entry URLs (showing {len(entries)} of {total_count})"
        rich_table = Table(title=title)
        rich_table.add_column("ID", style="cyan", no_wrap=True)
        rich_table.add_column("URL", style="blue")
        rich_table.add_column("Letter", style="green")
        rich_table.add_column("Discovered At", style="yellow")

        for entry in entries:
            rich_table.add_row(
                str(entry.id)[:8] + "...",
                entry.url[:60] + "..." if len(entry.url) > 60 else entry.url,
                entry.letter or "N/A",
                entry.discovered_at.strftime("%Y-%m-%d %H:%M:%S"),
            )

        console.print(rich_table)

        if total_count > limit:
            note = (
                f"\n[yellow]Note:[/yellow] Showing {limit} of "
                f"{total_count} entries. Use --limit to show more."
            )
            console.print(note)

        session.close()

    except Exception as e:
        console.print(f"[red]Failed:[/red] {e}")
        raise typer.Exit(1)


@app.command()
def count(
    letter: Optional[str] = typer.Option(
        None,
        "--letter",
        "-l",
        help="Filter by letter",
    ),
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR"] = typer.Option(
        "WARNING",
        "--log-level",
        "-L",
        help="Logging level",
    ),
) -> None:
    """Count rows in the entry_urls table."""
    setup_logging(log_level)

    try:
        # Validate letter if provided
        validated_letter = None
        if letter:
            try:
                validated_letter = Letter(letter)
            except ValueError as e:
                console.print(f"[red]Invalid letter:[/red] {e}")
                raise typer.Exit(code=1)

        config = load_app_config()
        session = get_session(config.db_config)

        if validated_letter:
            count_val = crud.count_entry_urls_by_letter(
                session, str(validated_letter)
            )
            msg = (
                f"[green]✓[/green] Entry URLs for letter "
                f"'{validated_letter}': {count_val}"
            )
            console.print(msg)
        else:
            count_val = crud.count_entry_urls(session)
            console.print(f"[green]✓[/green] Total Entry URLs: {count_val}")

        session.close()

    except Exception as e:
        console.print(f"[red]Failed:[/red] {e}")
        raise typer.Exit(1)


@app.command()
def stats(
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR"] = typer.Option(
        "WARNING",
        "--log-level",
        "-L",
        help="Logging level",
    ),
) -> None:
    """Display statistics for the entry_urls table."""
    setup_logging(log_level)

    try:
        config = load_app_config()
        session = get_session(config.db_config)

        # Get overall stats
        total = crud.count_entry_urls(session)

        # Create stats table
        stats_table = Table(title="Entry URLs Statistics")
        stats_table.add_column("Metric", style="cyan")
        stats_table.add_column("Value", style="green", justify="right")

        stats_table.add_row("Total Entry URLs", str(total))

        # Get counts by letter
        alphabet = Alphabet.standard()
        letter_counts = {}
        for letter_obj in alphabet:
            count = crud.count_entry_urls_by_letter(session, str(letter_obj))
            if count > 0:
                letter_counts[str(letter_obj)] = count

        if letter_counts:
            stats_table.add_section()
            stats_table.add_row("[bold]By Letter[/bold]", "")
            for letter, count in sorted(letter_counts.items()):
                stats_table.add_row(f"  Letter {letter}", str(count))

        console.print(stats_table)
        session.close()

    except Exception as e:
        console.print(f"[red]Failed:[/red] {e}")
        raise typer.Exit(1)


@app.command()
def clean(
    letter: Optional[str] = typer.Option(
        None,
        "--letter",
        "-l",
        help="Only delete entries for this letter",
    ),
    force: bool = typer.Option(
        False,
        "--force",
        "-f",
        help="Skip confirmation prompt",
    ),
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR"] = typer.Option(
        "WARNING",
        "--log-level",
        "-L",
        help="Logging level",
    ),
) -> None:
    """Delete all rows from the entry_urls table."""
    setup_logging(log_level)

    try:
        # Validate letter if provided
        validated_letter = None
        if letter:
            try:
                validated_letter = Letter(letter)
            except ValueError as e:
                console.print(f"[red]Invalid letter:[/red] {e}")
                raise typer.Exit(code=1)

        config = load_app_config()
        session = get_session(config.db_config)

        # Get count for confirmation message
        if validated_letter:
            count = crud.count_entry_urls_by_letter(session, str(validated_letter))
            msg = f"all {count} entry URLs for letter '{validated_letter}'"
        else:
            count = crud.count_entry_urls(session)
            msg = f"all {count} entry URLs"

        # Confirm deletion
        if not force:
            confirm = typer.confirm(
                f"Are you sure you want to delete {msg}?",
                default=False,
            )
            if not confirm:
                console.print("[yellow]Cancelled[/yellow]")
                raise typer.Exit(0)

        # Delete entries efficiently
        if validated_letter:
            deleted = crud.delete_entry_urls_by_letter(
                session, str(validated_letter)
            )
            success_msg = (
                f"[green]✓[/green] Deleted {deleted} entry URLs "
                f"for letter '{validated_letter}'"
            )
            console.print(success_msg)
        else:
            deleted = crud.delete_all_entry_urls(session)
            console.print(f"[green]✓[/green] Deleted {deleted} entry URLs")

        session.close()

    except Exception as e:
        console.print(f"[red]Failed:[/red] {e}")
        raise typer.Exit(1)
