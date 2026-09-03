import typer
from rich.console import Console

app = typer.Typer(
    name="traceid",
    help="Face-to-blockchain provenance verification CLI tool",
    add_completion=False,
)
console = Console()


@app.callback()
def main():
    """Face-to-blockchain provenance verification CLI tool."""
    pass


@app.command()
def info():
    """Display system info and config status."""
    console.print("[bold green]traceid[/bold green] - Face-to-blockchain provenance verification")


if __name__ == "__main__":
    app()

