"""CLI commands for triggering Celery tasks."""

import typer

app = typer.Typer(
    name="alguerisme-tasks",
    help="Trigger Celery tasks for Alguerisme",
    no_args_is_help=True,
    add_completion=False,
)

# Import command modules to register them with the app
from alguerisme.clis.tasks import collector, crawler, image_collector, parser  # noqa: E402, F401

__all__ = ["app", "collector", "crawler", "image_collector", "parser"]
