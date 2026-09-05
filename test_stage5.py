import json
import sys
from pathlib import Path
from rich.console import Console
from rich.panel import Panel

# Force UTF-8 output encoding for Windows terminal
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")

from traceid.config import SERPAPI_KEY, PINATA_API_KEY, PINATA_API_SECRET
from traceid.face import load_and_detect, get_embedding
from traceid.discovery import fetch_candidate_image, search_web_for_face
from traceid.verification import verify_candidates
from traceid.evidence import build_manifest, save_manifest, sha256_json
from traceid.storage import pin_json_to_ipfs, fetch_from_ipfs

console = Console()


def get_or_generate_manifest() -> tuple[dict, str]:
    """Retrieve existing evidence.json or generate it if missing."""
    output_path = "data/output/evidence.json"
    if Path(output_path).exists():
        console.print(f"[dim]Loading existing manifest from {output_path}...[/dim]")
        with open(output_path, "r", encoding="utf-8") as f:
            manifest = json.load(f)
        return manifest, output_path

    console.print("[bold yellow]Generating new evidence manifest (Stage 4)...[/bold yellow]")
    input_dir = Path("data/input")
    found_images = list(input_dir.glob("*.jpg")) + list(input_dir.glob("*.png")) + list(input_dir.glob("*.jpeg"))
    if not found_images:
        console.print("[bold red]Error: No images found in data/input/[/bold red]")
        sys.exit(1)

    target_image = str(found_images[0])
    orig_emb = get_embedding(target_image)
    candidates = search_web_for_face(target_image)

    candidates_with_paths = []
    for cand in candidates[:15]:
        local_path = fetch_candidate_image(cand["page_url"], cand["image_url"])
        c_copy = dict(cand)
        c_copy["local_path"] = local_path
        candidates_with_paths.append(c_copy)

    verif_res = verify_candidates(orig_emb, candidates_with_paths)
    best_match = verif_res["best_match"]
    if not best_match:
        console.print("[bold red]Error: No candidate cleared face verification threshold.[/bold red]")
        sys.exit(1)

    manifest = build_manifest(target_image, best_match)
    save_manifest(manifest, output_path)
    return manifest, output_path


def run_stage5_test():
    console.print(
        Panel(
            "[bold cyan]Stage 5: IPFS Evidence Pinning & Gateway Verification[/bold cyan]",
            expand=False,
        )
    )

    if not PINATA_API_KEY or not PINATA_API_SECRET:
        console.print(
            "[bold red]Error: PINATA_API_KEY or PINATA_API_SECRET is not set in environment or .env file.[/bold red]"
        )
        sys.exit(1)

    # 1. Get or generate evidence manifest
    manifest, manifest_path = get_or_generate_manifest()
    orig_hash = sha256_json(manifest)

    # 2. Pin manifest to IPFS via Pinata
    console.print(f"[bold yellow]1. Pinning [white]{manifest_path}[/white] to IPFS via Pinata...[/bold yellow]")
    try:
        cid = pin_json_to_ipfs(manifest)
    except Exception as e:
        console.print(f"[bold red]Pinning failed: {e}[/bold red]")
        sys.exit(1)

    console.print(f"[bold green]✓ Successfully pinned to IPFS![/bold green]")
    console.print(f"[bold white]IPFS CID:[/bold white] [bold yellow]{cid}[/bold yellow]\n")

    pinata_gateway_url = f"https://gateway.pinata.cloud/ipfs/{cid}"
    ipfs_io_gateway_url = f"https://ipfs.io/ipfs/{cid}"

    # 3. Fetch manifest back from IPFS Gateway
    console.print(f"[bold yellow]2. Fetching manifest back from public IPFS Gateway...[/bold yellow]")
    try:
        fetched_manifest = fetch_from_ipfs(cid)
    except Exception as e:
        console.print(f"[bold red]Fetching from IPFS failed: {e}[/bold red]")
        sys.exit(1)

    fetched_hash = sha256_json(fetched_manifest)
    console.print(f"[bold green]✓ Manifest fetched from IPFS successfully![/bold green]\n")

    # 4. Compare Integrity Hashes
    console.print("[bold yellow]3. Verifying Cryptographic Integrity...[/bold yellow]")
    match_status = orig_hash == fetched_hash

    if match_status:
        console.print(
            Panel(
                f"[bold green]🏆 IPFS VERIFICATION PASSED[/bold green]\n\n"
                f"[bold white]IPFS CID:[/bold white] [bold yellow]{cid}[/bold yellow]\n\n"
                f"[bold white]Public Gateway URL (Click to Open in Browser):[/bold white]\n"
                f"[bold blue]{pinata_gateway_url}[/bold blue]\n"
                f"[bold blue]{ipfs_io_gateway_url}[/bold blue]\n\n"
                f"[bold white]Original SHA-256 Hash:[/bold white] [dim]{orig_hash}[/dim]\n"
                f"[bold white]Fetched  SHA-256 Hash:[/bold white] [dim]{fetched_hash}[/dim]\n"
                f"[bold green]Integrity Match: CONFIRMED (Canonical JSON hashes are identical)[/bold green]",
                title="[bold green]Pinata & IPFS Verification Result[/bold green]",
                expand=False,
            )
        )
    else:
        console.print(
            Panel(
                f"[bold red]❌ INTEGRITY MATCH FAILED[/bold red]\n"
                f"Original Hash: {orig_hash}\n"
                f"Fetched Hash:  {fetched_hash}",
                title="[bold red]Verification Result[/bold red]",
                expand=False,
            )
        )


if __name__ == "__main__":
    run_stage5_test()
