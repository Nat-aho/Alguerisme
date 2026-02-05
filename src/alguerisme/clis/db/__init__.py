"""Database command-line interfaces."""

import typer

from .alembic_cli import app as alembic_app
from .entry_urls_cli import app as entry_urls_app

app = typer.Typer(
    name="alguerisme-db",
    help="Database operations and management",
    no_args_is_help=True,
    add_completion=False,
)

app.add_typer(alembic_app, name="alembic", help="Alembic migration commands")
app.add_typer(entry_urls_app, name="entry-urls", help="Manage entry_urls table")
