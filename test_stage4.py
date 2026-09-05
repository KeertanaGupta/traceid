import json
import sys
from pathlib import Path
from rich.console import Console
from rich.panel import Panel
from rich.syntax import Syntax

# Force UTF-8 output encoding for Windows terminal
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")

from traceid.config import SERPAPI_KEY, FACE_MATCH_THRESHOLD
from traceid.face import load_and_detect, get_embedding
from traceid.discovery import fetch_candidate_image, search_web_for_face
from traceid.verification import verify_candidates
from traceid.evidence import build_manifest, save_manifest, sha256_json, combine_hash

console = Console()


def run_stage4_test(image_path: str):
    console.print(
        Panel(
            "[bold cyan]Stage 4: Evidence Manifest Generation & Hashing[/bold cyan]\n"
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

    # 1. Detect & embed original face
    console.print(f"[bold yellow]1. Extracting original face embedding:[bold yellow] [white]{path.name}[/white]")
    det_res = load_and_detect(str(path))
    if not det_res.get("face_found"):
        console.print("[bold red]Error: No face detected in original image.[/bold red]")
        sys.exit(1)

    orig_emb = get_embedding(str(path))
    if orig_emb is None:
        console.print("[bold red]Error: Failed to generate embedding for original face.[/bold red]")
        sys.exit(1)
    console.print("[green]✓ Original face embedding generated.[/green]\n")

    # 2. Web search via SerpApi
    console.print("[bold yellow]2. Searching web via SerpApi Google Lens...[/bold yellow]")
    try:
        raw_candidates = search_web_for_face(str(path))
    except Exception as e:
        console.print(f"[bold red]Web search failed: {e}[/bold red]")
        sys.exit(1)

    if not raw_candidates:
        console.print("[yellow]No visual matches returned.[/yellow]")
        return

    console.print(f"[green]✓ Discovered {len(raw_candidates)} candidate match(es).[/green]\n")

    # 3. Fetch candidate images locally
    console.print("[bold yellow]3. Fetching candidate images locally...[/bold yellow]")
    candidates_with_paths = []
    for cand in raw_candidates[:15]:
        local_path = fetch_candidate_image(cand["page_url"], cand["image_url"])
        cand_copy = dict(cand)
        cand_copy["local_path"] = local_path
        candidates_with_paths.append(cand_copy)

    console.print("[green]✓ Candidate images downloaded/cached.[/green]\n")

    # 4. Verify & Rank candidates
    console.print("[bold yellow]4. Verifying & ranking candidates...[/bold yellow]")
    verification_output = verify_candidates(orig_emb, candidates_with_paths)
    best_match = verification_output["best_match"]

    if not best_match:
        console.print(
            "[bold yellow]No candidate cleared the threshold. Cannot generate evidence manifest.[/bold yellow]"
        )
        return

    console.print(
        f"[green]✓ Best match found: {best_match['platform'].upper()} (similarity = {best_match['face_similarity']:.4f})[/green]\n"
    )

    # 5. Build & Save Evidence Manifest
    console.print("[bold yellow]5. Building & saving evidence manifest...[/bold yellow]")
    manifest = build_manifest(str(path), best_match)

    output_path = "data/output/evidence.json"
    save_manifest(manifest, output_path)

    manifest_hash = sha256_json(manifest)
    onchain_combined_hash = combine_hash(
        manifest["content"]["original_image_sha256"],
        manifest["content"]["candidate_image_sha256"],
    )

    console.print(f"[green]✓ Evidence manifest saved to [bold white]{output_path}[/bold white][/green]\n")

    # Read and print generated file nicely
    with open(output_path, "r", encoding="utf-8") as f:
        file_content = f.read()

    syntax = Syntax(file_content, "json", theme="monokai", line_numbers=True)
    console.print(
        Panel(
            syntax,
            title=f"[bold green]Generated Evidence Manifest ({output_path})[/bold green]",
            expand=False,
        )
    )

    console.print(
        Panel(
            f"[bold white]Canonical Manifest Hash (SHA-256):[/bold white]\n[yellow]{manifest_hash}[/yellow]\n\n"
            f"[bold white]On-Chain Combined Hash (SHA-256):[/bold white]\n[cyan]{onchain_combined_hash}[/cyan]",
            title="[bold magenta]Evidence Cryptographic Hashes[/bold magenta]",
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

    run_stage4_test(target_image)
