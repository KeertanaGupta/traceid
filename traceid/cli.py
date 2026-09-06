"""Face-to-blockchain provenance verification CLI tool."""

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import typer
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

# Force UTF-8 output encoding for Windows terminal
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")

from traceid.config import (
    SERPAPI_KEY,
    PINATA_API_KEY,
    PINATA_API_SECRET,
    POLYGON_AMOY_RPC_URL,
    DEPLOYER_PRIVATE_KEY,
    CONTRACT_ADDRESS,
    FACE_MATCH_THRESHOLD,
)
from traceid.face import load_and_detect, get_embedding
from traceid.discovery import fetch_candidate_image, search_web_for_face
from traceid.verification import verify_candidates
from traceid.evidence import (
    build_manifest,
    save_manifest,
    sha256_json,
    combine_hash,
)
from traceid.storage import pin_json_to_ipfs, fetch_from_ipfs
from traceid.chain import (
    register_evidence,
    verify_evidence,
)

app = typer.Typer(
    name="traceid",
    help="Face-to-blockchain provenance verification CLI tool",
    add_completion=False,
)
console = Console()


def get_canonical_hash(manifest_dict: dict) -> str:
    """Compute canonical SHA-256 hash of manifest dict excluding runtime metadata like ipfs_cid."""
    clean_dict = dict(manifest_dict)
    clean_dict.pop("ipfs_cid", None)
    return sha256_json(clean_dict)


@app.callback()
def main():
    """Face-to-blockchain provenance verification CLI tool."""
    pass


@app.command()
def scan(image_path: str = typer.Argument(..., help="Path to input target face image")):
    """Scan a target face image, verify web matches, pin evidence to IPFS, and register on Polygon Amoy."""
    path = Path(image_path)
    if not path.exists():
        console.print(f"[bold red]❌ Error: Target image file '{image_path}' does not exist.[/bold red]")
        raise typer.Exit(code=1)

    if not SERPAPI_KEY:
        console.print("[bold red]❌ Error: SERPAPI_KEY is not set in environment or .env file.[/bold red]")
        raise typer.Exit(code=1)

    if not PINATA_API_KEY or not PINATA_API_SECRET:
        console.print("[bold red]❌ Error: PINATA_API_KEY or PINATA_API_SECRET is not set in .env file.[/bold red]")
        raise typer.Exit(code=1)

    if not POLYGON_AMOY_RPC_URL or not DEPLOYER_PRIVATE_KEY or not CONTRACT_ADDRESS:
        console.print("[bold red]❌ Error: Blockchain configuration (RPC URL, Private Key, or Contract Address) missing in .env.[/bold red]")
        raise typer.Exit(code=1)

    console.print(
        Panel(
            "[bold cyan]traceid :: Face-to-Blockchain Provenance Scan[/bold cyan]\n"
            f"[dim]Target Image: {path.name} | Threshold: {FACE_MATCH_THRESHOLD:.2f}[/dim]",
            expand=False,
        )
    )

    # Stage 1: Detect & Quality-Check Face
    console.print(f"[bold yellow]⏳ Stage 1: Detecting & quality-checking face in [white]{path.name}[/white]...[/bold yellow]")
    det_res = load_and_detect(str(path))
    if not det_res.get("face_found"):
        console.print(f"[bold red]❌ Stage 1 Failed: No valid face detected in {path.name}.[/bold red]")
        raise typer.Exit(code=1)

    orig_emb = get_embedding(str(path))
    if orig_emb is None:
        console.print(f"[bold red]❌ Stage 1 Failed: Unable to extract 512-d face embedding.[/bold red]")
        raise typer.Exit(code=1)

    console.print("[bold green]✓ Stage 1: Face detected & 512-d embedding extracted successfully.[/bold green]\n")

    # Stage 2: Web Search via SerpApi Google Lens
    console.print("[bold yellow]⏳ Stage 2: Searching web via SerpApi Google Lens...[/bold yellow]")
    try:
        raw_candidates = search_web_for_face(str(path))
    except Exception as e:
        console.print(f"[bold red]❌ Stage 2 Failed: Web search failed: {e}[/bold red]")
        raise typer.Exit(code=1)

    if not raw_candidates:
        console.print("[bold red]❌ Stage 2 Failed: No visual match candidates discovered on the web.[/bold red]")
        raise typer.Exit(code=1)

    console.print(f"[bold green]✓ Stage 2: Discovered {len(raw_candidates)} candidate match(es).[/bold green]\n")

    # Stage 3: Fetch & Verify Candidates
    console.print("[bold yellow]⏳ Stage 3: Fetching and verifying candidate images...[/bold yellow]")
    candidates_with_paths = []
    for cand in raw_candidates[:15]:
        local_path = fetch_candidate_image(cand.get("page_url", ""), cand.get("image_url"))
        cand_copy = dict(cand)
        cand_copy["local_path"] = local_path
        candidates_with_paths.append(cand_copy)

    verif_res = verify_candidates(orig_emb, candidates_with_paths)
    ranked = verif_res.get("ranked_candidates", [])
    best_match = verif_res.get("best_match")

    # Print Rich Table of Candidates
    table = Table(title="[bold magenta]Candidate Face Matching Evaluation[/bold magenta]", show_header=True, header_style="bold cyan")
    table.add_column("#", style="dim", width=4)
    table.add_column("Platform", style="bold white", width=12)
    table.add_column("URL", style="blue", no_wrap=True)
    table.add_column("Similarity", justify="right", width=12)
    table.add_column("Threshold", justify="right", width=10)
    table.add_column("Status", justify="center", width=14)

    for idx, cand in enumerate(ranked, start=1):
        sim = cand.get("face_similarity", 0.0)
        accepted = cand.get("accepted", False)
        status_str = "[bold green]✓ MATCH[/bold green]" if accepted else "[bold red]✗ REJECTED[/bold red]"
        sim_str = f"{sim:.4f}"
        thresh_str = f"{FACE_MATCH_THRESHOLD:.2f}"
        url_display = cand.get("page_url", "")
        if len(url_display) > 45:
            url_display = url_display[:42] + "..."

        table.add_row(
            str(idx),
            cand.get("platform", "web").upper(),
            url_display,
            sim_str,
            thresh_str,
            status_str,
        )

    console.print(table)

    if not best_match:
        console.print(f"[bold red]❌ Stage 3 Failed: No web candidate cleared face match threshold ({FACE_MATCH_THRESHOLD:.2f}). Match rejected.[/bold red]")
        raise typer.Exit(code=1)

    sim_pct = best_match["face_similarity"] * 100
    console.print(f"[bold green]✓ Stage 3: Top candidate verified: {best_match['platform'].upper()} (Similarity: {sim_pct:.2f}%)[/bold green]\n")

    # Stage 4: Build & Save Evidence Manifest
    console.print("[bold yellow]⏳ Stage 4: Building & saving evidence manifest...[/bold yellow]")
    output_path = "data/output/evidence.json"
    manifest = build_manifest(str(path), best_match)
    save_manifest(manifest, output_path)
    console.print(f"[bold green]✓ Stage 4: Evidence manifest saved to [white]{output_path}[/white].[/bold green]\n")

    # Stage 5: Pin to IPFS via Pinata
    console.print("[bold yellow]⏳ Stage 5: Pinning evidence manifest to IPFS via Pinata...[/bold yellow]")
    try:
        cid = pin_json_to_ipfs(manifest)
    except Exception as e:
        console.print(f"[bold red]❌ Stage 5 Failed: IPFS pinning error: {e}[/bold red]")
        raise typer.Exit(code=1)

    # Attach ipfs_cid to manifest and resave so manifest file is self-contained
    manifest["ipfs_cid"] = cid
    save_manifest(manifest, output_path)

    gateway_url = f"https://gateway.pinata.cloud/ipfs/{cid}"
    console.print(f"[bold green]✓ Stage 5: Manifest pinned to IPFS![/bold green]")
    console.print(f"[bold white]  IPFS CID:[/bold white] [bold yellow]{cid}[/bold yellow]")
    console.print(f"[bold white]  Gateway Link:[/bold white] [bold blue]{gateway_url}[/bold blue]\n")

    # Stage 6/7: Register on Polygon Amoy Smart Contract
    console.print("[bold yellow]⏳ Stage 6/7: Registering evidence on Polygon Amoy testnet...[/bold yellow]")
    manifest_hash = get_canonical_hash(manifest)
    evidence_hash = combine_hash(manifest_hash, cid)

    existing = verify_evidence(evidence_hash)
    if existing["exists"]:
        console.print("[bold yellow]Notice: Evidence hash is already registered on-chain.[/bold yellow]")
        tx_hash = "Already Registered"
        polygonscan_url = f"https://amoy.polygonscan.com/address/{CONTRACT_ADDRESS}"
    else:
        try:
            tx_info = register_evidence(evidence_hash, cid)
            tx_hash = tx_info["tx_hash"]
            polygonscan_url = tx_info["polygonscan_url"]
        except Exception as e:
            console.print(f"[bold red]❌ Stage 6/7 Failed: Smart contract registration failed: {e}[/bold red]")
            raise typer.Exit(code=1)

    console.print(f"[bold green]✓ Stage 6/7: Registered on Polygon Amoy![/bold green]")
    console.print(f"[bold white]  Tx Hash:[/bold white] [bold cyan]{tx_hash}[/bold cyan]")
    console.print(f"[bold white]  PolygonScan Link:[/bold white] [bold blue]{polygonscan_url}[/bold blue]\n")

    # Final Summary Panel
    console.print(
        Panel(
            f"[bold green]🏆 SCAN & PROVENANCE REGISTRATION COMPLETE[/bold green]\n\n"
            f"[bold white]Target Image:[/bold white] {path.name}\n"
            f"[bold white]Matched Platform:[/bold white] {best_match['platform'].upper()}\n"
            f"[bold white]Face Similarity:[/bold white] [bold green]{sim_pct:.2f}%[/bold green]\n"
            f"[bold white]Page URL:[/bold white] [blue]{best_match['page_url']}[/blue]\n\n"
            f"[bold white]Canonical Manifest Hash:[/bold white] [dim]{manifest_hash}[/dim]\n"
            f"[bold white]IPFS CID:[/bold white] [bold yellow]{cid}[/bold yellow]\n"
            f"[bold white]On-Chain Evidence Hash:[/bold white] [cyan]0x{evidence_hash}[/cyan]\n"
            f"[bold white]On-Chain Tx Hash:[/bold white] [bold cyan]{tx_hash}[/bold cyan]\n\n"
            f"[bold white]PolygonScan Link:[/bold white]\n"
            f"[bold blue]{polygonscan_url}[/bold blue]",
            title="[bold cyan]traceid Verification Summary[/bold cyan]",
            expand=False,
        )
    )


@app.command()
def verify(
    evidence_json_path: str = typer.Argument(..., help="Path to evidence.json manifest file"),
    tamper: bool = typer.Option(False, "--tamper", help="Simulate data tampering before verification"),
):
    """Verify an evidence.json manifest against IPFS and Polygon Amoy smart contract."""
    path = Path(evidence_json_path)
    if not path.exists():
        console.print(f"[bold red]❌ Error: Evidence file '{evidence_json_path}' not found.[/bold red]")
        raise typer.Exit(code=1)

    console.print(
        Panel(
            "[bold cyan]traceid :: Evidence Integrity Verification[/bold cyan]\n"
            f"[dim]Manifest: {path.name} | Tamper Mode: {'ENABLED' if tamper else 'DISABLED'}[/dim]",
            expand=False,
        )
    )

    with open(path, "r", encoding="utf-8") as f:
        manifest = json.load(f)

    if tamper:
        console.print("[bold yellow]⚠ TAMPER MODE: modifying evidence before verification[/bold yellow]\n")
        manifest["source"]["platform"] = "fake_tampered_platform"
        manifest["verification"]["face_similarity"] = 0.99999

    # 1. Compute local canonical hash
    local_manifest_hash = get_canonical_hash(manifest)

    # 2. Extract IPFS CID
    cid = manifest.get("ipfs_cid")
    if not cid:
        cid = manifest.get("storage", {}).get("ipfs_cid")

    if not cid:
        console.print("[bold red]❌ Error: No IPFS CID found in evidence manifest.[/bold red]")
        raise typer.Exit(code=1)

    # 3. Fetch canonical content from IPFS
    console.print(f"[bold yellow]1. Fetching canonical manifest from IPFS (CID: [white]{cid}[/white])...[/bold yellow]")
    try:
        ipfs_manifest = fetch_from_ipfs(cid)
        ipfs_manifest_hash = get_canonical_hash(ipfs_manifest)
        ipfs_fetch_ok = True
    except Exception as e:
        console.print(f"[bold red]Fetch from IPFS failed: {e}[/bold red]")
        ipfs_manifest_hash = "FETCH_FAILED"
        ipfs_fetch_ok = False

    # 4. Check on-chain record
    console.print("[bold yellow]2. Querying Polygon Amoy EvidenceRegistry smart contract...[/bold yellow]")
    computed_evidence_hash = combine_hash(local_manifest_hash, cid)
    try:
        onchain_res = verify_evidence(computed_evidence_hash)
    except Exception as e:
        console.print(f"[bold red]On-chain query failed: {e}[/bold red]")
        onchain_res = {"exists": False, "cid": "", "timestamp": 0, "submitter": ""}

    # 5. Evaluate checks
    ipfs_match = ipfs_fetch_ok and (local_manifest_hash == ipfs_manifest_hash)
    local_integrity_pass = ipfs_match
    onchain_found = onchain_res["exists"] and (onchain_res["cid"] == cid)

    all_passed = local_integrity_pass and ipfs_match and onchain_found

    # 6. Display Rich Table of Checks
    table = Table(title="[bold magenta]Evidence Cryptographic Verification[/bold magenta]", show_header=True, header_style="bold cyan")
    table.add_column("Verification Check", style="bold white", width=32)
    table.add_column("Status", justify="center", width=16)
    table.add_column("Details", style="dim")

    table.add_row(
        "Local Manifest Integrity",
        "[bold green]✓ PASS[/bold green]" if local_integrity_pass else "[bold red]✗ FAIL[/bold red]",
        f"SHA-256: {local_manifest_hash[:16]}...",
    )
    table.add_row(
        "IPFS Content Hash Match",
        "[bold green]✓ PASS[/bold green]" if ipfs_match else "[bold red]✗ FAIL[/bold red]",
        f"IPFS Hash: {ipfs_manifest_hash[:16]}...",
    )
    table.add_row(
        "On-Chain Record Found",
        "[bold green]✓ PASS[/bold green]" if onchain_found else "[bold red]✗ FAIL[/bold red]",
        f"Block Timestamp: {onchain_res.get('timestamp', 0)}",
    )

    console.print(table)
    console.print()

    # 7. Final Summary Panel
    if all_passed:
        onchain_ts = onchain_res.get("timestamp", 0)
        dt_str = (
            datetime.fromtimestamp(onchain_ts, tz=timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
            if onchain_ts > 0
            else "N/A"
        )
        polygonscan_url = f"https://amoy.polygonscan.com/address/{CONTRACT_ADDRESS}"

        console.print(
            Panel(
                f"[bold green]✓ EVIDENCE VERIFIED[/bold green]\n\n"
                f"[bold white]IPFS CID:[/bold white] [bold yellow]{cid}[/bold yellow]\n"
                f"[bold white]On-Chain Evidence Hash:[/bold white] [cyan]0x{computed_evidence_hash}[/cyan]\n"
                f"[bold white]Block Timestamp:[/bold white] {onchain_ts} ({dt_str})\n"
                f"[bold white]Submitter Address:[/bold white] [dim]{onchain_res.get('submitter')}[/dim]\n\n"
                f"[bold white]PolygonScan Link:[/bold white]\n"
                f"[bold blue]{polygonscan_url}[/bold blue]",
                title="[bold green]Verification Result[/bold green]",
                expand=False,
            )
        )
    else:
        console.print(
            Panel(
                f"[bold red]⚠ INTEGRITY CHECK FAILED[/bold red]\n\n"
                f"The evidence manifest does NOT match the IPFS / On-Chain records!\n"
                f"[bold white]Local Manifest Hash:[/bold white] {local_manifest_hash}\n"
                f"[bold white]IPFS Manifest Hash:[/bold white]  {ipfs_manifest_hash}\n"
                f"[bold white]On-Chain Record Found:[/bold white] {'YES' if onchain_res['exists'] else 'NO'}",
                title="[bold red]Verification Result[/bold red]",
                expand=False,
            )
        )

        raise typer.Exit(code=1)


if __name__ == "__main__":
    app()
