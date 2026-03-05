"""CLI commands for image collector operations."""

import typer
from rich.console import Console

from alguerisme.clis.tasks import app
from alguerisme.utils.alphabet import Alphabet, normalize_letters

console = Console()


@app.command(name="collect-images")
def trigger_image_collector(
    letters: str = typer.Option(
        None,
        "--letters",
        "-l",
        help="Specific letters to collect images for (e.g. 'ABC'). "
        "If not provided, collects for all letters A-Z.",
    ),
):
    """Trigger image collection for specified letters.

    Collects images for parsed vocabols that have image URLs but
    no collected images yet.

    Parameters
    ----------
    letters : str, optional
        String of letters to collect (e.g. 'ABC'). If not provided,
        collects for all letters A-Z.

    """
    from alguerisme.celery.tasks.image_collector_tasks import collect_images_for_letters

    try:
        if letters is not None:
            if not letters:
                console.print("[red]Error:[/red] Letters string cannot be empty")
                raise typer.Exit(code=1)

            letters_to_collect = normalize_letters(list(letters), unique=True)
            console.print(
                "[yellow]→[/yellow] Collecting images for "
                f"{len(letters_to_collect)} letter(s): "
                f"{', '.join(letters_to_collect)}"
            )
        else:
            # Use default alphabet (all letters A-Z)
            alphabet = Alphabet.standard()
            letters_to_collect = [str(letter) for letter in alphabet]
            console.print(
                "[yellow]→[/yellow] Collecting images for ALL "
                f"{len(letters_to_collect)} letters"
            )

        result = collect_images_for_letters.delay(letters_to_collect)
        console.print(
            f"[green]✓[/green] Triggered image collection (task_id: {result.id})"
        )
        console.print(
            "[yellow]→[/yellow] Notification will be sent when all tasks complete"
        )

    except ValueError as e:
        console.print(f"[red]Validation error:[/red] {e}")
        raise typer.Exit(code=1)
    except Exception as e:
        console.print(f"[red]Failed to trigger image collection:[/red] {e}")
        raise typer.Exit(code=1)
