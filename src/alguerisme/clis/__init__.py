"""Command-line interfaces for alguerisme."""

import typer

from .crawler_cli import app as crawler_app
from .db import app as db_app
from .tasks_cli import app as tasks_app

app = typer.Typer(
    name="alguerisme",
    help="Command-line interfaces for Alguerisme",
    no_args_is_help=True,
    add_completion=False,
)

app.add_typer(crawler_app, name="crawler", help="Run the web crawler")
app.add_typer(db_app, name="db", help="Database operations and management")
app.add_typer(tasks_app, name="tasks", help="Trigger Celery tasks")


def main():
    """Entry point for the alguerisme CLI."""
    app()


if __name__ == "__main__":
    main()
