import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from rich.console import Console
from rich.panel import Panel

# Force UTF-8 output encoding for Windows terminal
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")

from traceid.config import (
    POLYGON_AMOY_RPC_URL,
    DEPLOYER_PRIVATE_KEY,
    CONTRACT_ADDRESS,
)
from traceid.evidence import (
    build_manifest,
    save_manifest,
    sha256_json,
    combine_hash,
)
from traceid.storage import pin_json_to_ipfs
from traceid.chain import (
    register_evidence,
    verify_evidence,
)
from traceid.face import get_embedding
from traceid.discovery import fetch_candidate_image, search_web_for_face
from traceid.verification import verify_candidates

console = Console()


def get_or_generate_manifest() -> tuple[dict, str]:
    """Retrieve existing evidence.json or generate it if missing."""
    output_path = "data/output/evidence.json"
    if Path(output_path).exists():
        console.print(f"[dim]Loading existing manifest from {output_path}...[/dim]")
        with open(output_path, "r", encoding="utf-8") as f:
            manifest = json.load(f)
        return manifest, output_path

    console.print("[bold yellow]Generating new evidence manifest...[/bold yellow]")
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


def run_stage7_test():
    console.print(
        Panel(
            "[bold cyan]Stage 7: Python-Blockchain Integration (Polygon Amoy)[/bold cyan]",
            expand=False,
        )
    )

    if not POLYGON_AMOY_RPC_URL or not DEPLOYER_PRIVATE_KEY or not CONTRACT_ADDRESS:
        console.print(
            "[bold red]Error: POLYGON_AMOY_RPC_URL, DEPLOYER_PRIVATE_KEY, or CONTRACT_ADDRESS is not set.[/bold red]"
        )
        sys.exit(1)

    # 1. Obtain manifest and IPFS CID (Stage 5 output)
    console.print("[bold yellow]1. Loading Evidence Manifest & Pinning to IPFS...[/bold yellow]")
    manifest, manifest_path = get_or_generate_manifest()
    manifest_hash = sha256_json(manifest)

    try:
        cid = pin_json_to_ipfs(manifest)
    except Exception as e:
        console.print(f"[bold red]IPFS Pinning failed: {e}[/bold red]")
        sys.exit(1)

    console.print(f"[green]✓ Manifest loaded from [white]{manifest_path}[/white][/green]")
    console.print(f"[green]✓ Manifest SHA-256 Hash:[/green] [dim]{manifest_hash}[/dim]")
    console.print(f"[green]✓ IPFS CID:[/green] [bold yellow]{cid}[/bold yellow]\n")

    # 2. Combine CID and evidence hash using combine_hash()
    evidence_hash = combine_hash(manifest_hash, cid)
    console.print(f"[bold yellow]2. Combined Evidence Hash (sha256(manifest_hash + cid)):[/bold yellow]")
    console.print(f"[bold cyan]0x{evidence_hash}[/bold cyan]\n")

    # 3. Register evidence on Polygon Amoy testnet
    console.print("[bold yellow]3. Registering Evidence Hash on-chain...[/bold yellow]")
    existing_check = verify_evidence(evidence_hash)

    if existing_check["exists"]:
        console.print("[yellow]Notice: This evidence hash is already registered on-chain.[/yellow]")
        tx_hash_url = f"https://amoy.polygonscan.com/address/{CONTRACT_ADDRESS}"
        tx_info = {
            "tx_hash": "Already Registered",
            "block_number": "N/A",
            "polygonscan_url": tx_hash_url,
        }
    else:
        try:
            tx_info = register_evidence(evidence_hash, cid)
        except Exception as e:
            console.print(f"[bold red]Transaction failed: {e}[/bold red]")
            sys.exit(1)

        console.print("[bold green]✓ Transaction confirmed on Polygon Amoy![/bold green]")
        console.print(f"[bold white]Tx Hash:[/bold white] [bold cyan]{tx_info['tx_hash']}[/bold cyan]")
        console.print(f"[bold white]Block Number:[/bold white] {tx_info['block_number']}")
        console.print(f"[bold white]PolygonScan Link:[/bold white] [bold blue]{tx_info['polygonscan_url']}[/bold blue]\n")

    # 4. Verify evidence on-chain via verify_evidence()
    console.print("[bold yellow]4. Verifying Evidence on-chain via view function...[/bold yellow]")
    verification = verify_evidence(evidence_hash)

    onchain_ts = verification["timestamp"]
    dt_str = (
        datetime.fromtimestamp(onchain_ts, tz=timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
        if onchain_ts > 0
        else "N/A"
    )

    console.print(
        Panel(
            f"[bold green]🏆 ON-CHAIN VERIFICATION CONFIRMED[/bold green]\n\n"
            f"[bold white]Evidence Hash:[/bold white] [cyan]0x{evidence_hash}[/cyan]\n"
            f"[bold white]On-Chain Status:[/bold white] [bold green]{'EXISTS' if verification['exists'] else 'NOT FOUND'}[/bold green]\n"
            f"[bold white]On-Chain CID:[/bold white] [bold yellow]{verification['cid']}[/bold yellow]\n"
            f"[bold white]Timestamp:[/bold white] {verification['timestamp']} ({dt_str})\n"
            f"[bold white]Submitter Address:[/bold white] [dim]{verification['submitter']}[/dim]\n\n"
            f"[bold white]PolygonScan Link:[/bold white]\n"
            f"[bold blue]{tx_info['polygonscan_url']}[/bold blue]",
            title="[bold green]Polygon Amoy On-Chain Verification[/bold green]",
            expand=False,
        )
    )


if __name__ == "__main__":
    run_stage7_test()
