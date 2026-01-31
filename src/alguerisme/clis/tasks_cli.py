"""CLI to trigger Celery tasks."""


import typer
from rich.console import Console


app = typer.Typer(
    name="alguerisme-tasks",
    help="Trigger Celery tasks for Alguerisme",
    no_args_is_help=True,
    add_completion=False,
)

console = Console()

@app.command()
def trigger_crawler(letters: list[str] = typer.Option(...)):
    """Enqueue crawler tasks for the specified letters."""
    from alguerisme.celery.tasks import crawl_letter_task

    for letter in letters:
        crawl_letter_task.delay(letter)
        console.print(f"Enqueued task for {letter}")
