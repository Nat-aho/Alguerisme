"""CLI commands for crawler tasks."""

import typer
from rich.console import Console

from alguerisme.clis.tasks import app
from alguerisme.utils.alphabet import Alphabet, normalize_letters

console = Console()


@app.command(name="crawl")
def trigger_crawler(
    letters: str = typer.Option(
        None,
        "--letters",
        "-l",
        help="Specific letters to crawl (e.g. 'ABC'). "
        "If not provided, crawls all letters A-Z.",
    ),
):
    """Trigger crawler on specified letters.

    Parameters
    ----------
    letters : str, optional
        String of letters to crawl (e.g. 'ABC'). If not provided, crawls
        all letters A-Z.
    """
    from alguerisme.celery.tasks.crawler_tasks import crawl_letters

    try:
        if letters is not None:
            if not letters:
                console.print("[red]Error:[/red] Letters string cannot be empty")
                raise typer.Exit(code=1)

            letters_to_crawl = normalize_letters(list(letters), unique=True)
            console.print(
                f"[yellow]→[/yellow] Crawling {len(letters_to_crawl)} letter(s): "
                f"{', '.join(letters_to_crawl)}"
            )
        else:
            # Use default alphabet (all letters A-Z)
            letters_to_crawl = [str(letter) for letter in Alphabet.standard()]
            console.print(
                f"[yellow]→[/yellow] Crawling ALL {len(letters_to_crawl)} letters: "
                f"{', '.join(letters_to_crawl)}"
            )

        result = crawl_letters.delay(letters_to_crawl)
        console.print(f"[green]✓[/green] Triggered crawl (task_id: {result.id})")
        console.print(
            "[yellow]→[/yellow] Notification will be sent when all tasks complete"
        )

    except ValueError as e:
        console.print(f"[red]Validation error:[/red] {e}")
        raise typer.Exit(code=1)
    except Exception as e:
        console.print(f"[red]Failed to trigger crawl:[/red] {e}")
        raise typer.Exit(code=1)
