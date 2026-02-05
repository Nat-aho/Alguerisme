"""CLI for Alembic database migrations."""

import subprocess

import typer
from rich.console import Console

app = typer.Typer(
    name="alembic",
    help="Alembic migration commands",
    no_args_is_help=True,
    add_completion=False,
)

console = Console()


@app.command()
def migrate(
    message: str = typer.Argument(
        ...,
        help="Migration message/description",
    ),
    autogenerate: bool = typer.Option(
        True,
        "--autogenerate/--no-autogenerate",
        help="Auto-generate migration from model changes",
    ),
) -> None:
    """Create a new Alembic migration."""
    try:
        cmd = ["alembic", "revision"]
        if autogenerate:
            cmd.append("--autogenerate")
        cmd.extend(["-m", message])

        console.print(f"[blue]Creating migration:[/blue] {message}")
        result = subprocess.run(cmd, check=True, capture_output=True, text=True)
        console.print(result.stdout)
        console.print("[green]✓[/green] Migration created")

    except subprocess.CalledProcessError as e:
        console.print(f"[red]Failed:[/red] {e.stderr}")
        raise typer.Exit(1)


@app.command()
def upgrade(
    revision: str = typer.Argument(
        "head",
        help="Revision to upgrade to (default: head)",
    ),
) -> None:
    """Upgrade database to a later version."""
    try:
        console.print(f"[blue]Upgrading database to:[/blue] {revision}")
        result = subprocess.run(
            ["alembic", "upgrade", revision],
            check=True,
            capture_output=True,
            text=True,
        )
        console.print(result.stdout)
        console.print("[green]✓[/green] Database upgraded")

    except subprocess.CalledProcessError as e:
        console.print(f"[red]Failed:[/red] {e.stderr}")
        raise typer.Exit(1)


@app.command()
def downgrade(
    revision: str = typer.Argument(
        "-1",
        help="Revision to downgrade to (default: -1 for one step back)",
    ),
) -> None:
    """Downgrade database to a previous version."""
    try:
        console.print(f"[blue]Downgrading database to:[/blue] {revision}")
        result = subprocess.run(
            ["alembic", "downgrade", revision],
            check=True,
            capture_output=True,
            text=True,
        )
        console.print(result.stdout)
        console.print("[green]✓[/green] Database downgraded")

    except subprocess.CalledProcessError as e:
        console.print(f"[red]Failed:[/red] {e.stderr}")
        raise typer.Exit(1)


@app.command()
def history(
    verbose: bool = typer.Option(
        False,
        "--verbose",
        "-v",
        help="Show verbose output",
    ),
) -> None:
    """Show migration history."""
    try:
        cmd = ["alembic", "history"]
        if verbose:
            cmd.append("-v")

        result = subprocess.run(cmd, check=True, capture_output=True, text=True)
        console.print(result.stdout)

    except subprocess.CalledProcessError as e:
        console.print(f"[red]Failed:[/red] {e.stderr}")
        raise typer.Exit(1)


@app.command()
def current() -> None:
    """Show current database revision."""
    try:
        result = subprocess.run(
            ["alembic", "current"],
            check=True,
            capture_output=True,
            text=True,
        )
        console.print(result.stdout)

    except subprocess.CalledProcessError as e:
        console.print(f"[red]Failed:[/red] {e.stderr}")
        raise typer.Exit(1)


@app.command()
def heads() -> None:
    """Show current available heads in the script directory."""
    try:
        result = subprocess.run(
            ["alembic", "heads"],
            check=True,
            capture_output=True,
            text=True,
        )
        console.print(result.stdout)

    except subprocess.CalledProcessError as e:
        console.print(f"[red]Failed:[/red] {e.stderr}")
        raise typer.Exit(1)


@app.command()
def stamp(
    revision: str = typer.Argument(
        ...,
        help="Revision to stamp (e.g., 'head', specific revision)",
    ),
) -> None:
    """Stamp the database with a specific revision without running migrations."""
    try:
        console.print(f"[blue]Stamping database with:[/blue] {revision}")
        result = subprocess.run(
            ["alembic", "stamp", revision],
            check=True,
            capture_output=True,
            text=True,
        )
        console.print(result.stdout)
        console.print("[green]✓[/green] Database stamped")

    except subprocess.CalledProcessError as e:
        console.print(f"[red]Failed:[/red] {e.stderr}")
        raise typer.Exit(1)
