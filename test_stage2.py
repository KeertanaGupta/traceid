import sys
from pathlib import Path
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from traceid.config import SERPAPI_KEY
from traceid.discovery import fetch_candidate_image, search_web_for_face

console = Console()


def run_stage2_test(image_path: str):
    console.print(
        Panel(
            "[bold cyan]Stage 2: Web Discovery via SerpApi Google Lens & Candidate Fetching[/bold cyan]",
            expand=False,
        )
    )

    path = Path(image_path)
    if not path.exists():
        console.print(f"[bold red]Error: Image file {image_path} not found.[/bold red]")
        sys.exit(1)

    if not SERPAPI_KEY:
        console.print(
            "[bold red]Error: SERPAPI_KEY is not set in environment or .env file.[/bold red]"
        )
        sys.exit(1)

    console.print(f"[bold yellow]Running Google Lens web search for:[bold yellow] [white]{path.name}[/white]")
    
    try:
        candidates = search_web_for_face(str(path))
    except Exception as e:
        console.print(f"[bold red]Web search failed: {e}[/bold red]")
        sys.exit(1)

    if not candidates:
        console.print("[yellow]No visual matches returned by SerpApi Google Lens.[/yellow]")
        return

    console.print(f"[green]Found {len(candidates)} candidate match(es).[/green]\n")

    # Table displaying found candidates and platform classification
    table = Table(title="[bold magenta]Discovered Candidates & Platform Classification[/bold magenta]", show_header=True)
    table.add_column("#", style="dim")
    table.add_column("Platform", style="bold cyan")
    table.add_column("Title / Source", style="white")
    table.add_column("Page URL", style="blue")
    table.add_column("Image Fetch Status", style="bold")

    results_to_display = candidates[:15]  # Display top 15 results

    for idx, cand in enumerate(results_to_display, 1):
        page_url = cand["page_url"]
        image_url = cand["image_url"]
        platform = cand["platform"]
        title = cand["title"] or "N/A"

        # Attempt to fetch candidate image
        local_path = fetch_candidate_image(page_url, image_url)
        if local_path:
            fetch_status = f"[bold green]SAVED[/bold green] ({Path(local_path).name})"
        else:
            fetch_status = "[bold red]FAILED[/bold red]"

        table.add_row(
            str(idx),
            platform.upper(),
            title[:40] + ("..." if len(title) > 40 else ""),
            page_url[:60] + ("..." if len(page_url) > 60 else ""),
            fetch_status,
        )

    console.print(table)


if __name__ == "__main__":
    if len(sys.argv) > 1:
        target_image = sys.argv[1]
    else:
        input_dir = Path("data/input")
        extensions = ["*.jpg", "*.jpeg", "*.png"]
        found_images = []
        for ext in extensions:
            found_images.extend(list(input_dir.glob(ext)))

        if not found_images:
            console.print("[red]No images found in data/input/[/red]")
            sys.exit(1)
        target_image = str(found_images[0])

    run_stage2_test(target_image)
