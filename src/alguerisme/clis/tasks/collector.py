"""CLI commands for collector tasks."""

import typer
from rich.console import Console

from alguerisme.clis.tasks import app
from alguerisme.utils.alphabet import Alphabet, normalize_letters

console = Console()


@app.command(name="collect")
def trigger_collector(
    letters: str = typer.Option(
        None,
        "--letters",
        "-l",
        help="Specific letters to collect (e.g. 'ABC'). "
        "If not provided, collects all letters A-Z.",
    ),
    limit: int = typer.Option(
        None,
        "--limit",
        help="Maximum URLs to collect per letter (default: all pending)",
    ),
):
    """Trigger HTML collection for new vocabols URLs.

    Collects HTML content for URLs that haven't been collected yet.
    Processes letters in parallel.

    Parameters
    ----------
    letters : str, optional
        String of letters to collect (e.g. 'ABC'). If not provided,
        collects all letters A-Z.
    limit : int, optional
        Maximum number of URLs to collect per letter
    """
    from alguerisme.celery.tasks.html_collector_tasks import collect_new_vocabols

    try:
        if letters is not None:
            if not letters:
                console.print("[red]Error:[/red] Letters string cannot be empty")
                raise typer.Exit(code=1)

            letters_to_collect = normalize_letters(list(letters), unique=True)
            console.print(
                f"[yellow]→[/yellow] Collecting {len(letters_to_collect)} "
                f"letter(s): {', '.join(letters_to_collect)}"
            )
        else:
            # Use default alphabet (all letters A-Z)
            letters_to_collect = [str(letter) for letter in Alphabet.standard()]
            console.print(
                f"[yellow]→[/yellow] Collecting ALL {len(letters_to_collect)} "
                f"letters: {', '.join(letters_to_collect)}"
            )

        if limit:
            console.print(f"[yellow]→[/yellow] Limit: {limit} URLs per letter")

        result = collect_new_vocabols.delay(letters_to_collect, limit=limit)
        console.print(
            f"[green]✓[/green] Triggered collection (task_id: {result.id})"
        )
        console.print(
            "[yellow]→[/yellow] Notification will be sent when all tasks complete"
        )

    except ValueError as e:
        console.print(f"[red]Validation error:[/red] {e}")
        raise typer.Exit(code=1)
    except Exception as e:
        console.print(f"[red]Failed to trigger collection:[/red] {e}")
        raise typer.Exit(code=1)


@app.command(name="check-updates")
def trigger_update_check(
    letters: str = typer.Option(
        None,
        "--letters",
        "-l",
        help="Specific letters to check (e.g. 'ABC'). "
        "If not provided, checks all letters A-Z.",
    ),
    limit: int = typer.Option(
        None,
        "--limit",
        help="Maximum URLs to check per letter (default: all)",
    ),
):
    """Trigger update check for existing vocabols URLs.

    Checks existing HTML content for changes and detects updates.
    Processes letters in parallel.

    Parameters
    ----------
    letters : str, optional
        String of letters to check (e.g. 'ABC'). If not provided,
        checks all letters A-Z.
    limit : int, optional
        Maximum number of URLs to check per letter
    """
    from alguerisme.celery.tasks.html_update_tasks import check_vocabols_updates

    try:
        if letters is not None:
            if not letters:
                console.print("[red]Error:[/red] Letters string cannot be empty")
                raise typer.Exit(code=1)

            letters_to_check = normalize_letters(list(letters), unique=True)
            console.print(
                f"[yellow]→[/yellow] Checking {len(letters_to_check)} letter(s): "
                f"{', '.join(letters_to_check)}"
            )
        else:
            # Use default alphabet (all letters A-Z)
            letters_to_check = [str(letter) for letter in Alphabet.standard()]
            console.print(
                f"[yellow]→[/yellow] Checking ALL {len(letters_to_check)} letters: "
                f"{', '.join(letters_to_check)}"
            )

        if limit:
            console.print(f"[yellow]→[/yellow] Limit: {limit} URLs per letter")

        result = check_vocabols_updates.delay(letters_to_check, limit=limit)
        console.print(
            f"[green]✓[/green] Triggered update check (task_id: {result.id})"
        )
        console.print(
            "[yellow]→[/yellow] Notification will be sent when all tasks complete"
        )

    except ValueError as e:
        console.print(f"[red]Validation error:[/red] {e}")
        raise typer.Exit(code=1)
    except Exception as e:
        console.print(f"[red]Failed to trigger update check:[/red] {e}")
        raise typer.Exit(code=1)


@app.command(name="apply-changes")
def trigger_apply_changes():
    """Apply approved HTML changes to production.

    This command should be run manually after reviewing and approving
    changes in the vocabols_html_changes table.

    It will:
    1. Find all APPROVED changes
    2. Apply them to the vocabols_raw_html table
    3. Update the change status to APPLIED
    """
    from alguerisme.celery.tasks.html_update_tasks import (
        apply_approved_changes_task,
    )

    try:
        console.print(
            "[yellow]→[/yellow] Triggering apply approved changes task..."
        )

        result = apply_approved_changes_task.delay()
        console.print(
            f"[green]✓[/green] Triggered apply changes (task_id: {result.id})"
        )
        console.print(
            "[yellow]→[/yellow] Check logs for detailed results"
        )

    except Exception as e:
        console.print(f"[red]Failed to trigger apply changes:[/red] {e}")
        raise typer.Exit(code=1)
