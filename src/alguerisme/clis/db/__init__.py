"""Database command-line interfaces."""

import typer

from .alembic_cli import app as alembic_app
from .entry_urls_cli import app as entry_urls_app
from .parsed_vocabols_cli import app as parsed_vocabols_app
from .vocabols_html_cli import app as vocabols_html_app
from .vocabols_images_cli import app as vocabols_images_app

app = typer.Typer(
    name="alguerisme-db",
    help="Database operations and management",
    no_args_is_help=True,
    add_completion=False,
)

app.add_typer(alembic_app, name="alembic", help="Alembic migration commands")
app.add_typer(entry_urls_app, name="entry-urls", help="Manage entry_urls table")
app.add_typer(
    vocabols_html_app,
    name="vocabols-html",
    help="Inspect vocabols_raw_html table"
)
app.add_typer(
    parsed_vocabols_app,
    name="parsed-vocabols",
    help="Inspect parsed_vocabols table"
)
app.add_typer(
    vocabols_images_app,
    name="images",
    help="Inspect vocabols_images table"
)
