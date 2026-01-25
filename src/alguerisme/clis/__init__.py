"""Command-line interfaces for alguerisme."""

import typer

from .crawler_cli import app as crawler_app

app = typer.Typer(
    name="alguerisme",
    help="Command-line interfaces for Alguerisme",
    add_completion=False,
)

app.add_typer(crawler_app, name="crawler", help="Run the web crawler")


def main():
    """Entry point for the alguerisme CLI."""
    app()


if __name__ == "__main__":
    main()
