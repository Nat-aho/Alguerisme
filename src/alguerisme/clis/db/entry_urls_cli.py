"""CLI for managing the entry_urls table."""

from typing import TYPE_CHECKING, Literal, Optional

import typer
from rich.console import Console
from rich.table import Table

from alguerisme.clis.utils import get_letters_or_default, setup_logging
from alguerisme.configs.loader import load_app_config
from alguerisme.core.database import crud
from alguerisme.core.database.database import get_session
from alguerisme.utils.alphabet import Alphabet

if TYPE_CHECKING:
    from alguerisme.core.database.models import EntryURLs

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
        help="Maximum number of rows to display per letter",
    ),
    letters: Optional[str] = typer.Option(
        None,
        "--letters",
        "-l",
        help="Letters to filter by (e.g., 'ABC'). Uses A-Z if omitted.",
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
        config = load_app_config()
        validated_letters = get_letters_or_default(letters, console)

        with get_session(config.db_config) as session:
            all_entries: list["EntryURLs"] = []
            total_count = 0
            for letter in validated_letters:
                count = crud.count_entry_urls_by_letter(session, letter)
                total_count += count
                letter_entries = crud.get_entry_urls_paginated(
                    session,
                    limit=limit,
                    offset=0,
                    letter=letter,
                )
                all_entries.extend(letter_entries)

            # Create table
            title = (
                f"Entry URLs for {', '.join(validated_letters)} "
                f"(showing {len(all_entries)} of {total_count})"
            )

            rich_table = Table(title=title)
            rich_table.add_column("ID", style="cyan", no_wrap=True)
            rich_table.add_column("URL", style="blue")
            rich_table.add_column("Letter", style="green")
            rich_table.add_column("Discovered At", style="yellow")

            for entry in all_entries:
                rich_table.add_row(
                    str(entry.id)[:8] + "...",
                    entry.url[:60] + "...",
                    entry.letter or "N/A",
                    entry.discovered_at.strftime("%Y-%m-%d %H:%M:%S"),
                )

            console.print(rich_table)

            if total_count > len(all_entries):
                note = (
                    f"\n[yellow]Note:[/yellow] Showing {len(all_entries)} of "
                    f"{total_count} entries. Use --limit to show more per letter."
                )
                console.print(note)

    except ValueError as e:
        console.print(f"[red]Invalid letters:[/red] {e}")
        raise typer.Exit(1)
    except Exception as e:
        console.print(f"[red]Failed:[/red] {e}")
        raise typer.Exit(1)


@app.command()
def count(
    letters: Optional[str] = typer.Option(
        None,
        "--letters",
        "-l",
        help="Letters to filter by (e.g., 'ABC'). Uses A-Z if omitted.",
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
        config = load_app_config()
        validated_letters = get_letters_or_default(letters, console)

        with get_session(config.db_config) as session:
            letter_counts = []
            total_count = 0

            for letter in validated_letters:
                count = crud.count_entry_urls_by_letter(session, letter)
                letter_counts.append((letter, count))
                total_count += count

            for letter, count in letter_counts:
                console.print(f"  Letter {letter}: {count}")
            console.print(f"[green]✓[/green] Total: {total_count}")

    except ValueError as e:
        console.print(f"[red]Invalid letters:[/red] {e}")
        raise typer.Exit(1)
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

        with get_session(config.db_config) as session:
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

    except Exception as e:
        console.print(f"[red]Failed:[/red] {e}")
        raise typer.Exit(1)


@app.command()
def clean(
    letters: Optional[str] = typer.Option(
        None,
        "--letters",
        "-l",
        help="Letters to filter by (e.g., 'ABC'). Uses A-Z if omitted.",
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
    """Delete all rows from the entry_urls table.

    By default, deletes ALL entry URLs (A-Z) unless --letters is specified.
    Always requires confirmation unless --force is used.
    """
    setup_logging(log_level)

    try:
        config = load_app_config()
        validated_letters = get_letters_or_default(letters, console)

        with get_session(config.db_config) as session:
            # Confirm deletion
            if not force:
                msg = (
                    f"Are you sure you want to delete entry URLs for letters "
                    f"{', '.join(validated_letters)}"
                )
                confirm = typer.confirm(msg, default=False)
                if not confirm:
                    console.print("[yellow]Cancelled[/yellow]")
                    raise typer.Exit(0)

            # Delete entries
            total_deleted = 0
            for letter in validated_letters:
                deleted = crud.delete_entry_urls_by_letter(session, letter)
                total_deleted += deleted

            success_msg = (
                f"[green]✓[/green] Deleted {total_deleted} entry URLs "
                f"for letters {', '.join(validated_letters)}"
            )
            console.print(success_msg)

    except ValueError as e:
        console.print(f"[red]Invalid letters:[/red] {e}")
        raise typer.Exit(1)
    except Exception as e:
        console.print(f"[red]Failed:[/red] {e}")
        raise typer.Exit(1)
