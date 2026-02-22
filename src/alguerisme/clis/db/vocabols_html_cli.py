"""CLI for inspecting vocabols_raw_html table."""

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
    from alguerisme.core.database.models import VocabolsRawHTML

app = typer.Typer(
    name="vocabols-html",
    help="Inspect vocabols_raw_html table",
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
    show_html: bool = typer.Option(
        False,
        "--show-html",
        "-H",
        help="Show raw HTML content (truncated)",
    ),
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR"] = typer.Option(
        "WARNING",
        "--log-level",
        "-L",
        help="Logging level",
    ),
) -> None:
    """Display contents of the vocabols_raw_html table.

    By default shows all letters (A-Z) unless --letters is specified.
    """
    setup_logging(log_level)

    try:
        config = load_app_config()
        validated_letters = get_letters_or_default(letters, console)

        with get_session(config.db_config) as session:
            all_entries: list["VocabolsRawHTML"] = []
            total_count = 0
            for letter in validated_letters:
                count = crud.count_vocabols_raw_html_by_letter(session, letter)
                total_count += count
                letter_entries = crud.get_vocabols_raw_html_paginated(
                    session,
                    limit=limit,
                    offset=0,
                    letter=letter,
                )
                all_entries.extend(letter_entries)

            # Create table
            title = (
                f"Vocabols Raw HTML for {', '.join(validated_letters)} "
                f"(showing {len(all_entries)} of {total_count})"
            )

            rich_table = Table(title=title)
            rich_table.add_column("ID", style="cyan", no_wrap=True, overflow="fold")
            rich_table.add_column("URL", style="blue", overflow="fold")
            rich_table.add_column("Letter", style="green", justify="center")
            rich_table.add_column("Status", style="yellow", justify="center")
            rich_table.add_column("Hash", style="magenta", no_wrap=True)
            rich_table.add_column("Collected At", style="yellow")
            if show_html:
                rich_table.add_column("HTML Preview", style="dim", overflow="fold")

            for entry in all_entries:
                # Determine status
                if entry.error_message:
                    status = f"❌ {entry.http_status_code or 'Error'}"
                elif entry.raw_html:
                    status = f"✓ {entry.http_status_code or 200}"
                else:
                    status = "⚠ No data"

                # Truncate ID and hash for display
                entry_id = str(entry.id)[:8]
                content_hash = (entry.content_hash[:8] if entry.content_hash else "-")

                # Truncate URL for display
                url_display = (
                    entry.url[-40:] if len(entry.url) > 40 else entry.url
                )

                row_data = [
                    entry_id,
                    url_display,
                    entry.letter or "-",
                    status,
                    content_hash,
                    entry.collected_at.strftime("%Y-%m-%d %H:%M"),
                ]

                if show_html:
                    if entry.raw_html:
                        html_preview = entry.raw_html[:50].replace("\n", " ")
                        row_data.append(f"{html_preview}...")
                    else:
                        row_data.append("-")

                rich_table.add_row(*row_data)

            console.print(rich_table)
            console.print(
                f"\n[bold]Total:[/bold] {len(all_entries)} entries shown "
                f"out of {total_count} total"
            )

    except ValueError as e:
        console.print(f"[bold red]Invalid letters:[/bold red] {e}")
        raise typer.Exit(1) from e
    except Exception as e:
        console.print(f"[bold red]Error:[/bold red] {e}")
        raise typer.Exit(1) from e


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
    """Count vocabols_raw_html entries by letter.

    By default counts all letters (A-Z) unless --letters is specified.
    """
    setup_logging(log_level)

    try:
        config = load_app_config()
        validated_letters = get_letters_or_default(letters, console)

        with get_session(config.db_config) as session:
            letter_counts = []
            total_count = 0

            for letter in validated_letters:
                count = crud.count_vocabols_raw_html_by_letter(session, letter)
                letter_counts.append((letter, count))
                total_count += count

            for letter, count in letter_counts:
                console.print(f"  Letter {letter}: {count}")
            console.print(f"[green]✓[/green] Total: {total_count}")

    except ValueError as e:
        console.print(f"[red]Invalid letters:[/red] {e}")
        raise typer.Exit(1) from e
    except Exception as e:
        console.print(f"[red]Failed:[/red] {e}")
        raise typer.Exit(1) from e


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
    """Delete all rows from the vocabols_raw_html table.

    By default, deletes ALL vocabols HTML (A-Z) unless --letters is specified.
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
                    f"Are you sure you want to delete vocabols HTML for letters "
                    f"{', '.join(validated_letters)}"
                )
                confirm = typer.confirm(msg, default=False)
                if not confirm:
                    console.print("[yellow]Cancelled[/yellow]")
                    raise typer.Exit(0)

            # Delete entries
            total_deleted = 0
            for letter in validated_letters:
                deleted = crud.delete_vocabols_raw_html_by_letter(session, letter)
                total_deleted += deleted

            success_msg = (
                f"[green]✓[/green] Deleted {total_deleted} vocabols HTML entries "
                f"for letters {', '.join(validated_letters)}"
            )
            console.print(success_msg)

    except ValueError as e:
        console.print(f"[red]Invalid letters:[/red] {e}")
        raise typer.Exit(1) from e
    except Exception as e:
        console.print(f"[red]Failed:[/red] {e}")
        raise typer.Exit(1) from e


@app.command()
def stats(
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR"] = typer.Option(
        "WARNING",
        "--log-level",
        "-L",
        help="Logging level",
    ),
) -> None:
    """Show statistics about collected vocabols HTML data."""
    setup_logging(log_level)

    try:
        config = load_app_config()

        with get_session(config.db_config) as session:
            # Get overall stats
            total_count = crud.count_all_vocabols_raw_html(session)

            # Create stats table
            rich_table = Table(title="Vocabols HTML Collection Statistics")
            rich_table.add_column("Letter", style="green", justify="center")
            rich_table.add_column("Count", style="cyan", justify="right")
            rich_table.add_column("% of Total", style="yellow", justify="right")

            # Get stats per letter
            alphabet = Alphabet()
            letter_stats = []
            for letter_obj in alphabet:
                letter = str(letter_obj)
                count = crud.count_vocabols_raw_html_by_letter(session, letter)
                if count > 0:
                    percentage = (count / total_count * 100) if total_count > 0 else 0
                    letter_stats.append((letter, count, percentage))
                    rich_table.add_row(
                        letter,
                        str(count),
                        f"{percentage:.1f}%"
                    )

            console.print(rich_table)
            console.print(f"\n[bold]Total HTML entries:[/bold] {total_count}")
            console.print(f"[bold]Letters with data:[/bold] {len(letter_stats)}/29")

    except Exception as e:
        console.print(f"[red]Failed:[/red] {e}")
        raise typer.Exit(1) from e


@app.command()
def inspect(
    url: str = typer.Argument(..., help="URL or URL ID to inspect"),
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR"] = typer.Option(
        "WARNING",
        "--log-level",
        "-L",
        help="Logging level",
    ),
) -> None:
    """Inspect a specific vocabols HTML entry by URL or ID."""
    setup_logging(log_level)

    try:
        config = load_app_config()

        with get_session(config.db_config) as session:
            # Try to find by URL first
            entry = crud.find_vocabols_raw_html_by_url(session, url)

            # If not found, try by ID (if it looks like a UUID)
            if not entry and len(url) >= 8:
                from uuid import UUID
                try:
                    # Try full UUID or partial
                    if len(url) == 36:
                        entry_id = UUID(url)
                        entry = crud.find_vocabols_raw_html_by_id(session, entry_id)
                except ValueError:
                    pass

            if not entry:
                console.print(f"[bold red]Error:[/bold red] No entry found for: {url}")
                raise typer.Exit(1)

            # Display entry details
            console.print("\n[bold]Vocabols HTML Entry Details[/bold]\n")
            console.print(f"[cyan]ID:[/cyan] {entry.id}")
            console.print(f"[cyan]Entry URL ID:[/cyan] {entry.entry_url_id}")
            console.print(f"[cyan]URL:[/cyan] {entry.url}")
            console.print(f"[cyan]Letter:[/cyan] {entry.letter or 'Not set'}")
            console.print(
                f"[cyan]Content Hash:[/cyan] {entry.content_hash or 'None'}"
            )
            console.print(
                f"[cyan]HTTP Status:[/cyan] {entry.http_status_code or 'N/A'}"
            )
            console.print(f"[cyan]Collected At:[/cyan] {entry.collected_at}")
            console.print(f"[cyan]Last Updated:[/cyan] {entry.last_updated_at}")

            if entry.error_message:
                console.print(
                    f"\n[bold red]Error Message:[/bold red]\n"
                    f"{entry.error_message}"
                )

            if entry.raw_html:
                html_length = len(entry.raw_html)
                console.print(
                    f"\n[bold]Raw HTML:[/bold] ({html_length} characters)"
                )
                console.print("\n[dim]First 500 characters:[/dim]")
                console.print(entry.raw_html[:500])
                if html_length > 500:
                    console.print(
                        f"\n[dim]... ({html_length - 500} more "
                        f"characters)[/dim]"
                    )
            else:
                console.print("\n[bold yellow]No HTML content[/bold yellow]")

    except Exception as e:
        console.print(f"[red]Failed:[/red] {e}")
        raise typer.Exit(1) from e
