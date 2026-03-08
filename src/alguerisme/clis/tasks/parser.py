"""CLI commands for parser tasks."""

import typer
from rich.console import Console

from alguerisme.clis.tasks import app
from alguerisme.utils.alphabet import Alphabet, normalize_letters

console = Console()


@app.command(name="parse")
def trigger_parser(
    letters: str = typer.Option(
        None,
        "--letters",
        "-l",
        help="Specific letters to parse (e.g. 'ABC'). "
        "If not provided, parses all letters A-Z.",
    ),
):
    """Trigger HTML parsing for raw vocabols.

    Parses raw HTML content into structured vocabol data.
    Processes letters in parallel.

    Parameters
    ----------
    letters : str, optional
        String of letters to parse (e.g. 'ABC'). If not provided,
        parses all letters A-Z.

    """
    from alguerisme.celery.tasks.parser_tasks import parse_vocabols

    try:
        if letters is not None:
            if not letters:
                console.print("[red]Error:[/red] Letters string cannot be empty")
                raise typer.Exit(code=1)

            letters_to_parse = normalize_letters(list(letters), unique=True)
            console.print(
                f"[yellow]→[/yellow] Parsing {len(letters_to_parse)} "
                f"letter(s): {', '.join(letters_to_parse)}"
            )
        else:
            # Use default alphabet (all letters A-Z)
            letters_to_parse = [str(letter) for letter in Alphabet.standard()]
            console.print(
                f"[yellow]→[/yellow] Parsing ALL {len(letters_to_parse)} "
                f"letters: {', '.join(letters_to_parse)}"
            )

        result = parse_vocabols.delay(letters_to_parse)
        console.print(f"[green]✓[/green] Triggered parsing (task_id: {result.id})")
        console.print(
            "[yellow]→[/yellow] Notification will be sent when all tasks complete"
        )

    except ValueError as e:
        console.print(f"[red]Validation error:[/red] {e}")
        raise typer.Exit(code=1)
    except Exception as e:
        console.print(f"[red]Failed to trigger parsing:[/red] {e}")
        raise typer.Exit(code=1)
