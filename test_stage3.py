import sys
from pathlib import Path
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

# Force UTF-8 output encoding for Windows terminal
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")

from traceid.config import SERPAPI_KEY, FACE_MATCH_THRESHOLD
from traceid.face import load_and_detect, get_embedding
from traceid.discovery import fetch_candidate_image, search_web_for_face
from traceid.verification import verify_candidates

console = Console()


def _clean_str(text: str) -> str:
    """Sanitize string for terminal display."""
    if not text:
        return ""
    return text.encode("utf-8", "ignore").decode("utf-8", "ignore")


def run_stage3_test(image_path: str):
    console.print(
        Panel(
            "[bold cyan]Stage 3: Full Chain Verification & Candidate Ranking[/bold cyan]\n"
            f"[dim]FACE_MATCH_THRESHOLD = {FACE_MATCH_THRESHOLD:.2f}[/dim]",
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

    # Step 1: Detect & embed original face
    console.print(f"[bold yellow]1. Extracting embedding for original image:[bold yellow] [white]{path.name}[/white]")
    det_res = load_and_detect(str(path))
    if not det_res.get("face_found"):
        console.print("[bold red]Error: No face detected in original image.[/bold red]")
        sys.exit(1)

    orig_emb = get_embedding(str(path))
    if orig_emb is None:
        console.print("[bold red]Error: Failed to generate embedding for original face.[/bold red]")
        sys.exit(1)

    console.print(f"[green]✓ Original face detected and 512-d embedding generated.[/green]\n")

    # Step 2: Web Discovery via SerpApi
    console.print(f"[bold yellow]2. Running Google Lens web search...[/bold yellow]")
    try:
        raw_candidates = search_web_for_face(str(path))
    except Exception as e:
        console.print(f"[bold red]Web search failed: {e}[/bold red]")
        sys.exit(1)

    if not raw_candidates:
        console.print("[yellow]No visual matches returned by SerpApi Google Lens.[/yellow]")
        return

    console.print(f"[green]✓ Discovered {len(raw_candidates)} candidate match(es).[/green]\n")

    # Step 3: Fetch candidate images locally
    console.print(f"[bold yellow]3. Fetching candidate images locally...[/bold yellow]")
    candidates_to_process = raw_candidates[:15]  # Process top 15 results
    candidates_with_paths = []

    for cand in candidates_to_process:
        page_url = cand["page_url"]
        image_url = cand["image_url"]
        local_path = fetch_candidate_image(page_url, image_url)
        cand_copy = dict(cand)
        cand_copy["local_path"] = local_path
        candidates_with_paths.append(cand_copy)

    console.print(f"[green]✓ Candidate images downloaded/cached.[/green]\n")

    # Step 4: Verification & Ranking
    console.print(f"[bold yellow]4. Verifying candidates against original embedding...[/bold yellow]")
    verification_output = verify_candidates(orig_emb, candidates_with_paths)
    ranked_candidates = verification_output["ranked_candidates"]
    best_match = verification_output["best_match"]

    console.print(f"[green]✓ Verification & ranking complete.[/green]\n")

    # Step 5: Render Results Table
    table = Table(
        title=f"[bold magenta]Candidate Face Verification & Ranking Results (Threshold >= {FACE_MATCH_THRESHOLD:.2f})[/bold magenta]",
        show_header=True,
    )
    table.add_column("#", style="dim")
    table.add_column("Platform", style="bold cyan")
    table.add_column("Title / Source", style="white")
    table.add_column("Page URL", style="blue")
    table.add_column("Similarity Score", style="bold yellow")
    table.add_column("Match Status", style="bold")

    for idx, cand in enumerate(ranked_candidates, 1):
        page_url = cand["page_url"]
        platform = cand["platform"]
        raw_title = cand["title"] or "N/A"
        title = _clean_str(raw_title)
        sim = cand["face_similarity"]
        accepted = cand["accepted"]
        reason = cand["reason"]

        sim_str = f"{sim:.4f}" if sim > 0 else "0.0000"

        if accepted:
            status_str = f"[bold green]ACCEPTED[/bold green]"
        else:
            status_str = f"[bold red]REJECTED[/bold red] [dim]({reason})[/dim]"

        table.add_row(
            str(idx),
            platform.upper(),
            title[:35] + ("..." if len(title) > 35 else ""),
            page_url[:55] + ("..." if len(page_url) > 55 else ""),
            sim_str,
            status_str,
        )

    console.print(table)
    console.print()

    # Summary Panel for Best Match
    if best_match:
        console.print(
            Panel(
                f"[bold green]🏆 BEST MATCH FOUND[/bold green]\n\n"
                f"[bold white]Platform:[/bold white] [cyan]{best_match['platform'].upper()}[/cyan]\n"
                f"[bold white]Similarity Score:[/bold white] [yellow]{best_match['face_similarity']:.4f}[/yellow]\n"
                f"[bold white]Page URL:[/bold white] [blue]{best_match['page_url']}[/blue]\n"
                f"[bold white]Title:[/bold white] {_clean_str(best_match['title'] or 'N/A')}",
                title="[bold green]Verification Result[/bold green]",
                expand=False,
            )
        )
    else:
        console.print(
            Panel(
                f"[bold yellow]⚠️ NO MATCH CONFIRMED[/bold yellow]\n"
                f"No candidate images cleared the similarity threshold of {FACE_MATCH_THRESHOLD:.2f}.",
                title="[bold yellow]Verification Result[/bold yellow]",
                expand=False,
            )
        )


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

    run_stage3_test(target_image)
