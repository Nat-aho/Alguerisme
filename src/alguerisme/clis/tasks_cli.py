"""CLI to trigger Celery tasks."""

import typer
from rich.console import Console

from alguerisme.utils.alphabet import Letter

app = typer.Typer(
    name="alguerisme-tasks",
    help="Trigger Celery tasks for Alguerisme",
    no_args_is_help=True,
    add_completion=False,
)

console = Console()


@app.command()
def trigger_crawler(
    letters: list[str] = typer.Option(
        ...,
        "--letters",
        "-l",
        help="Specific letters to crawl (e.g., -l a -l b -l c)",
    ),
):
    """Enqueue crawler tasks for the specified letters."""
    from alguerisme.celery.app import crawl_letter_task

    try:
        validated_letters = [Letter(letter) for letter in letters]

        # Convert to strings at Celery boundary (for JSON serialization)
        for letter in validated_letters:
            crawl_letter_task.delay(str(letter))
            console.print(f"[green]✓[/green] Enqueued task for {letter}")

    except ValueError as e:
        console.print(f"[red]Invalid letter:[/red] {e}")
        raise typer.Exit(code=1)
