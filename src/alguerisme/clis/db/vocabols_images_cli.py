"""CLI for inspecting vocabols_images table."""

from typing import Literal, Optional

import typer
from rich.console import Console
from rich.table import Table
from sqlalchemy import func
from sqlmodel import Session, select

from alguerisme.clis.utils import get_letters_or_default, setup_logging
from alguerisme.configs.loader import load_app_config
from alguerisme.core.database import crud
from alguerisme.core.database.database import get_session
from alguerisme.core.database.models import ParsedVocabols, VocabolsImages
from alguerisme.utils.alphabet import normalize_letter

app = typer.Typer(
    name="images",
    help="Inspect vocabols_images table",
    no_args_is_help=True,
    add_completion=False,
)

console = Console()


@app.command()
def stats(
    letters: Optional[str] = typer.Option(
        None,
        "--letters",
        "-l",
        help="Letters to filter by (e.g., 'ABC'). Uses all if omitted.",
    ),
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR"] = typer.Option(
        "WARNING",
        "--log-level",
        "-L",
        help="Logging level",
    ),
) -> None:
    """Show statistics about collected images."""
    setup_logging(log_level)

    try:
        config = load_app_config()

        with get_session(config.db_config) as session:
            if letters:
                validated_letters = get_letters_or_default(letters, console)
                _show_stats_by_letters(session, validated_letters)
            else:
                _show_overall_stats(session)

    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        raise typer.Exit(1) from e


@app.command(name="list")
def list_entries(
    limit: int = typer.Option(
        50,
        "--limit",
        "-n",
        help="Maximum number of rows to display",
    ),
    letters: Optional[str] = typer.Option(
        None,
        "--letters",
        "-l",
        help="Letters to filter by (e.g., 'ABC'). Uses all if omitted.",
    ),
    status: Optional[str] = typer.Option(
        None,
        "--status",
        "-s",
        help="Filter by collection status (success, failed)",
    ),
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR"] = typer.Option(
        "WARNING",
        "--log-level",
        "-L",
        help="Logging level",
    ),
) -> None:
    """List collected images with optional filters."""
    setup_logging(log_level)

    try:
        config = load_app_config()

        with get_session(config.db_config) as session:
            # Get results for each letter if specified, otherwise all
            all_results = []
            if letters:
                validated_letters = get_letters_or_default(letters, console)
                for letter in validated_letters:
                    results = crud.get_vocabols_images_with_vocabol_info(
                        session, limit=limit, letter=letter, status=status
                    )
                    all_results.extend(results)
            else:
                all_results = crud.get_vocabols_images_with_vocabol_info(
                    session, limit=limit, status=status
                )

            # Display results
            _display_images_table(all_results)

    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        raise typer.Exit(1) from e


@app.command()
def show(
    image_id: str = typer.Argument(..., help="UUID of the image to show"),
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR"] = typer.Option(
        "WARNING",
        "--log-level",
        "-L",
        help="Logging level",
    ),
) -> None:
    """Show detailed information for a specific image by ID."""
    setup_logging(log_level)

    try:
        config = load_app_config()

        with get_session(config.db_config) as session:
            from uuid import UUID

            result = crud.get_vocabols_image_with_vocabol_by_id(
                session, UUID(image_id)
            )

            if not result:
                console.print(f"[red]No image found with ID: {image_id}[/red]")
                raise typer.Exit(1)

            image, vocabol = result
            _display_image_details(image, vocabol)

    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        raise typer.Exit(1) from e


@app.command()
def needs_collection(
    letters: Optional[str] = typer.Option(
        None,
        "--letters",
        "-l",
        help="Letters to filter by (e.g., 'ABC'). Uses all if omitted.",
    ),
    limit: int = typer.Option(
        50,
        "--limit",
        "-n",
        help="Maximum number of rows to display",
    ),
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR"] = typer.Option(
        "WARNING",
        "--log-level",
        "-L",
        help="Logging level",
    ),
) -> None:
    """List parsed vocabols that need image collection or re-collection."""
    setup_logging(log_level)

    try:
        config = load_app_config()

        with get_session(config.db_config) as session:
            # Use the same CRUD function that the service uses
            all_needing = crud.find_parsed_vocabols_without_images(session)

            # Filter by letters if provided
            if letters:
                validated_letters = get_letters_or_default(letters, console)
                entry_urls = []
                for letter in validated_letters:
                    entry_urls.extend(crud.get_entry_urls_by_letter(session, letter))

                entry_url_ids = {eu.id for eu in entry_urls}
                all_needing = [
                    v for v in all_needing if v.entry_url_id in entry_url_ids
                ]

            # Apply limit
            vocabols = all_needing[:limit]

            _display_needs_collection_table(vocabols)

    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        raise typer.Exit(1) from e


def _show_overall_stats(session: Session) -> None:
    """Show overall statistics for all collected images."""
    total_images = session.exec(
        select(func.count()).select_from(VocabolsImages)
    ).one()

    # Count by status
    successful = session.exec(
        select(func.count())
        .select_from(VocabolsImages)
        .where(VocabolsImages.collection_status == "success")
    ).one()

    failed = session.exec(
        select(func.count())
        .select_from(VocabolsImages)
        .where(VocabolsImages.collection_status == "failed")
    ).one()

    # Count vocabols with images
    vocabols_with_images = session.exec(
        select(func.count(func.distinct(VocabolsImages.parsed_vocabol_id)))
        .select_from(VocabolsImages)
    ).one()

    # Total storage size
    total_size = session.exec(
        select(func.sum(VocabolsImages.size_bytes)).select_from(VocabolsImages)
    ).one() or 0

    # Create stats table
    table = Table(title="Vocabols Images Statistics")
    table.add_column("Metric", style="cyan")
    table.add_column("Count", style="green", justify="right")
    table.add_column("Percentage", style="yellow", justify="right")

    table.add_row("Total Images", str(total_images), "100%")
    table.add_row(
        "Successful",
        str(successful),
        f"{successful/total_images*100:.1f}%" if total_images > 0 else "0%",
    )
    table.add_row(
        "Failed",
        str(failed),
        f"{failed/total_images*100:.1f}%" if total_images > 0 else "0%",
    )
    table.add_row("Vocabols with Images", str(vocabols_with_images), "-")
    table.add_row(
        "Total Storage Size",
        f"{total_size / 1024 / 1024:.2f} MB",
        "-",
    )

    console.print(table)


def _show_stats_by_letters(session: Session, letters: list[str]) -> None:
    """Show statistics broken down by letter."""
    table = Table(title=f"Images Statistics for {', '.join(letters)}")
    table.add_column("Letter", style="cyan", justify="center")
    table.add_column("Total Images", style="green", justify="right")
    table.add_column("Successful", style="blue", justify="right")
    table.add_column("Failed", style="red", justify="right")
    table.add_column("Storage (MB)", style="yellow", justify="right")

    for letter in letters:
        normalized = normalize_letter(letter)

        # Get entry_url_ids for this letter
        entry_urls = crud.get_entry_urls_by_letter(session, normalized)
        entry_url_ids = [eu.id for eu in entry_urls]

        if not entry_url_ids:
            table.add_row(normalized, "0", "0", "0", "0.00")
            continue

        # Get parsed vocabol IDs for this letter
        parsed_vocabol_ids = session.exec(
            select(ParsedVocabols.id)
            .where(ParsedVocabols.entry_url_id.in_(entry_url_ids))  # type: ignore[attr-defined]
        ).all()

        if not parsed_vocabol_ids:
            table.add_row(normalized, "0", "0", "0", "0.00")
            continue

        # Count total images
        total = session.exec(
            select(func.count())
            .select_from(VocabolsImages)
            .where(VocabolsImages.parsed_vocabol_id.in_(parsed_vocabol_ids))  # type: ignore[attr-defined]
        ).one()

        # Count successful
        successful = session.exec(
            select(func.count())
            .select_from(VocabolsImages)
            .where(VocabolsImages.parsed_vocabol_id.in_(parsed_vocabol_ids))  # type: ignore[attr-defined]
            .where(VocabolsImages.collection_status == "success")
        ).one()

        # Count failed
        failed = session.exec(
            select(func.count())
            .select_from(VocabolsImages)
            .where(VocabolsImages.parsed_vocabol_id.in_(parsed_vocabol_ids))  # type: ignore[attr-defined]
            .where(VocabolsImages.collection_status == "failed")
        ).one()

        # Total size
        total_size = session.exec(
            select(func.sum(VocabolsImages.size_bytes))
            .select_from(VocabolsImages)
            .where(VocabolsImages.parsed_vocabol_id.in_(parsed_vocabol_ids))  # type: ignore[attr-defined]
        ).one() or 0

        table.add_row(
            normalized,
            str(total),
            str(successful),
            str(failed),
            f"{total_size / 1024 / 1024:.2f}",
        )

    console.print(table)


def _display_images_table(results) -> None:
    """Display images in a table format."""
    table = Table(title=f"Collected Images ({len(results)} entries)")
    table.add_column("Vocabol", style="cyan")
    table.add_column("Status", style="green")
    table.add_column("Size", style="blue", justify="right")
    table.add_column("S3 Key", style="magenta", overflow="fold")
    table.add_column("Collected At", style="yellow")

    for image, algueres_word, url in results:
        status_style = "green" if image.collection_status == "success" else "red"
        size_mb = (
            f"{image.size_bytes / 1024:.2f} KB" if image.size_bytes else "-"
        )

        table.add_row(
            algueres_word or url[:30],
            f"[{status_style}]{image.collection_status}[/{status_style}]",
            size_mb,
            image.s3_key or "-",
            image.collected_at.strftime("%Y-%m-%d %H:%M"),
        )

    console.print(table)


def _display_needs_collection_table(vocabols) -> None:
    """Display vocabols that need image collection."""
    table = Table(
        title=f"Vocabols Needing Image Collection ({len(vocabols)} entries)"
    )
    table.add_column("Alguerés", style="cyan")
    table.add_column("Images", style="magenta", justify="center")
    table.add_column("Parsed At", style="yellow")
    table.add_column("URL", style="dim", overflow="fold")

    for vocabol in vocabols:
        table.add_row(
            vocabol.algueres_word or "-",
            str(vocabol.image_url_count),
            vocabol.parsed_at.strftime("%Y-%m-%d %H:%M"),
            vocabol.url,
        )

    console.print(table)


def _display_image_details(image: VocabolsImages, vocabol: ParsedVocabols) -> None:
    """Display detailed information for a single image."""
    console.print("\n[bold cyan]Image Details[/bold cyan]\n")

    # Basic info
    console.print(f"[bold]ID:[/bold] {image.id}")
    console.print(f"[bold]Status:[/bold] {image.collection_status}")
    console.print(f"[bold]Collected At:[/bold] {image.collected_at}")
    console.print(f"[bold]Source Parsed At:[/bold] {image.source_parsed_at}")

    # Vocabol info
    console.print("\n[bold cyan]Associated Vocabol:[/bold cyan]")
    console.print(f"  Alguerés: {vocabol.algueres_word or '-'}")
    console.print(f"  URL: {vocabol.url}")
    console.print(f"  Parsed At: {vocabol.parsed_at}")

    # Image info
    console.print("\n[bold magenta]Image Details:[/bold magenta]")
    console.print(f"  Source URL: {image.source_url}")
    console.print(f"  S3 Bucket: {image.s3_bucket}")
    console.print(f"  S3 Key: {image.s3_key}")
    console.print(f"  Content Type: {image.content_type or '-'}")
    console.print(
        f"  Size: {image.size_bytes / 1024:.2f} KB" if image.size_bytes else "  Size: -"
    )
    console.print(f"  Content Hash: {image.content_hash or '-'}")

    # Error info
    if image.error_message:
        console.print("\n[bold red]Error:[/bold red]")
        console.print(f"  {image.error_message}")

    console.print()
