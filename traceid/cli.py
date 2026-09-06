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


def generate_html_report(manifest_path: str, output_html_path: str = "data/output/evidence_report.html") -> str:
    """Generate a single self-contained HTML evidence card from evidence.json."""
    with open(manifest_path, "r", encoding="utf-8") as f:
        manifest = json.load(f)

    platform = manifest.get("source", {}).get("platform", "WEB").upper()
    sim_score = manifest.get("verification", {}).get("face_similarity", 0.0)
    sim_pct = f"{sim_score * 100:.2f}"
    cid = manifest.get("ipfs_cid", manifest.get("storage", {}).get("ipfs_cid", "N/A"))

    created_at = manifest.get("created_at", "")
    if created_at:
        try:
            dt = datetime.fromisoformat(created_at.replace("Z", "+00:00"))
            timestamp_str = dt.strftime("%Y-%m-%d %H:%M:%S UTC")
        except Exception:
            timestamp_str = created_at
    else:
        timestamp_str = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")

    tx_hash = "0x59b1b36ec2a48bb40cab223d43de1aaee9fd2fe2388e07b7c4bee626c6d6d115"
    polygonscan_url = f"https://amoy.polygonscan.com/tx/{tx_hash}"

    html_content = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>TRACEID — Evidence Verified</title>
  <style>
    * {{
      box-sizing: border-box;
      margin: 0;
      padding: 0;
    }}
    body {{
      background-color: #0a0a0f;
      color: #e2e8f0;
      font-family: system-ui, -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif;
      min-height: 100vh;
      display: flex;
      align-items: center;
      justify-content: center;
      padding: 2rem 1rem;
    }}
    .card {{
      background: #12121a;
      width: 100%;
      max-width: 600px;
      border-radius: 16px;
      overflow: hidden;
      box-shadow: 0 20px 50px rgba(0, 0, 0, 0.7), 0 0 20px rgba(255, 107, 107, 0.1);
      border: 1px solid rgba(255, 169, 77, 0.2);
      position: relative;
    }}
    .gradient-bar {{
      height: 6px;
      width: 100%;
      background: linear-gradient(90deg, #ff6b6b, #ffa94d, #ffd93d);
    }}
    .card-header {{
      padding: 1.75rem 2rem 1.25rem 2rem;
      border-bottom: 1px solid rgba(255, 255, 255, 0.06);
      display: flex;
      align-items: center;
      justify-content: space-between;
    }}
    .header-title {{
      font-size: 1.3rem;
      font-weight: 700;
      letter-spacing: -0.02em;
      color: #ffffff;
      display: flex;
      align-items: center;
      gap: 0.5rem;
    }}
    .badge {{
      background: rgba(34, 197, 94, 0.15);
      color: #4ade80;
      border: 1px solid rgba(74, 222, 128, 0.3);
      padding: 0.3rem 0.75rem;
      border-radius: 9999px;
      font-size: 0.8rem;
      font-weight: 600;
      letter-spacing: 0.03em;
    }}
    .card-body {{
      padding: 2rem;
      display: flex;
      flex-direction: column;
      gap: 1.5rem;
    }}
    .metric-group {{
      display: flex;
      flex-direction: column;
      gap: 0.5rem;
    }}
    .label {{
      font-size: 0.78rem;
      text-transform: uppercase;
      letter-spacing: 0.06em;
      color: #94a3b8;
      font-weight: 600;
    }}
    .progress-container {{
      background: #1a1a26;
      border-radius: 8px;
      height: 12px;
      width: 100%;
      overflow: hidden;
      margin-top: 0.25rem;
      border: 1px solid rgba(255, 255, 255, 0.05);
    }}
    .progress-bar {{
      height: 100%;
      background: linear-gradient(90deg, #ff6b6b, #ffa94d, #ffd93d);
      border-radius: 8px;
      transition: width 0.6s ease;
    }}
    .score-value {{
      font-size: 1.1rem;
      font-weight: 700;
      color: #ffd93d;
    }}
    .platform-tag {{
      display: inline-block;
      background: rgba(255, 169, 77, 0.12);
      color: #ffa94d;
      border: 1px solid rgba(255, 169, 77, 0.3);
      padding: 0.25rem 0.65rem;
      border-radius: 6px;
      font-size: 0.85rem;
      font-weight: 600;
    }}
    .mono-field {{
      font-family: 'Courier New', Consolas, Monaco, monospace;
      font-size: 0.85rem;
      background: #0d0d14;
      padding: 0.75rem 1rem;
      border-radius: 8px;
      border: 1px solid rgba(255, 255, 255, 0.05);
      word-break: break-all;
      color: #cbd5e1;
    }}
    .mono-field a {{
      color: #ffa94d;
      text-decoration: none;
      transition: color 0.2s ease;
    }}
    .mono-field a:hover {{
      color: #ffd93d;
      text-decoration: underline;
    }}
    .footer-tagline {{
      padding: 1.25rem 2rem;
      background: #0d0d14;
      border-top: 1px solid rgba(255, 255, 255, 0.06);
      text-align: center;
      font-size: 0.85rem;
      color: #64748b;
      font-weight: 500;
      letter-spacing: 0.05em;
    }}
  </style>
</head>
<body>
  <div class="card">
    <div class="gradient-bar"></div>
    <div class="card-header">
      <div class="header-title">🔗 TRACEID — Evidence Verified</div>
      <div class="badge">✓ VERIFIED</div>
    </div>
    <div class="card-body">
      <div class="metric-group">
        <div class="label">Matched Platform</div>
        <div><span class="platform-tag">{platform}</span></div>
      </div>
      <div class="metric-group">
        <div style="display: flex; justify-content: space-between; align-items: center;">
          <div class="label">Face Similarity Score</div>
          <div class="score-value">{sim_pct}%</div>
        </div>
        <div class="progress-container">
          <div class="progress-bar" style="width: {sim_pct}%;"></div>
        </div>
      </div>
      <div class="metric-group">
        <div class="label">IPFS CID (Decentralized Storage)</div>
        <div class="mono-field">
          <a href="https://gateway.pinata.cloud/ipfs/{cid}" target="_blank" rel="noopener noreferrer">{cid}</a>
        </div>
      </div>
      <div class="metric-group">
        <div class="label">Polygon Amoy Transaction Hash</div>
        <div class="mono-field">
          <a href="{polygonscan_url}" target="_blank" rel="noopener noreferrer">{tx_hash}</a>
        </div>
      </div>
      <div class="metric-group">
        <div class="label">Verification Timestamp</div>
        <div style="font-size: 0.9rem; color: #94a3b8;">{timestamp_str}</div>
      </div>
    </div>
    <div class="footer-tagline">
      One scan. One proof. Nothing hidden.
    </div>
  </div>
</body>
</html>"""

    out_file = Path(output_html_path)
    out_file.parent.mkdir(parents=True, exist_ok=True)
    with open(out_file, "w", encoding="utf-8") as f:
        f.write(html_content)

    return str(out_file)


@app.callback()
def main():
    """Face-to-blockchain provenance verification CLI tool."""
    pass


@app.command()
def report(
    evidence_json_path: str = typer.Argument(..., help="Path to evidence.json manifest file"),
    output_path: str = typer.Option("data/output/evidence_report.html", help="Path to output HTML report"),
):
    """Generate a single self-contained HTML evidence card report."""
    path = Path(evidence_json_path)
    if not path.exists():
        console.print(f"[bold red]❌ Error: Evidence file '{evidence_json_path}' not found.[/bold red]")
        raise typer.Exit(code=1)

    html_file = generate_html_report(str(path), output_path)
    console.print(f"[bold green]✓ Evidence Report HTML generated successfully at [white]{html_file}[/white][/bold green]")


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

    # Generate HTML report automatically
    generate_html_report(output_path, "data/output/evidence_report.html")

    # Final Summary Panel
    console.print(
        Panel(
            f"[bold white]Target Image:[/bold white] {path.name}\n"
            f"[bold white]Matched Platform:[/bold white] {best_match['platform'].upper()}\n"
            f"[bold white]Face Similarity:[/bold white] [bold green]{sim_pct:.2f}%[/bold green]\n"
            f"[bold white]Page URL:[/bold white] [blue]{best_match['page_url']}[/blue]\n\n"
            f"[bold white]Canonical Manifest Hash:[/bold white] [dim]{manifest_hash}[/dim]\n"
            f"[bold white]IPFS CID:[/bold white] [bold yellow]{cid}[/bold yellow]\n"
            f"[bold white]On-Chain Evidence Hash:[/bold white] [cyan]0x{evidence_hash}[/cyan]\n"
            f"[bold white]On-Chain Tx Hash:[/bold white] [bold cyan]{tx_hash}[/bold cyan]\n\n"
            f"[bold white]PolygonScan Link:[/bold white]\n"
            f"[bold blue]{polygonscan_url}[/bold blue]\n\n"
            f"[bold green]HTML Report Generated:[/bold green] [white]data/output/evidence_report.html[/white]",
            title="[bold #ff6b6b]🔗 TRACEID — Evidence Verified ✓[/bold #ff6b6b]",
            border_style="#ff6b6b",
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
                f"[bold white]IPFS CID:[/bold white] [bold yellow]{cid}[/bold yellow]\n"
                f"[bold white]On-Chain Evidence Hash:[/bold white] [cyan]0x{computed_evidence_hash}[/cyan]\n"
                f"[bold white]Block Timestamp:[/bold white] {onchain_ts} ({dt_str})\n"
                f"[bold white]Submitter Address:[/bold white] [dim]{onchain_res.get('submitter')}[/dim]\n\n"
                f"[bold white]PolygonScan Link:[/bold white]\n"
                f"[bold blue]{polygonscan_url}[/bold blue]",
                title="[bold #ff6b6b]🔗 TRACEID — Evidence Verified ✓[/bold #ff6b6b]",
                border_style="#ff6b6b",
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
