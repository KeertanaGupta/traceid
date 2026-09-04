import sys
from pathlib import Path
import numpy as np
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from traceid.face import load_and_detect, get_embedding, cosine_similarity

console = Console()


def run_stage1_test(image_paths: list[str]):
    console.print(
        Panel(
            "[bold cyan]Stage 1: Face Detection, Quality Check & Embedding Verification[/bold cyan]",
            expand=False,
        )
    )

    embeddings: dict[str, np.ndarray] = {}

    for img_path in image_paths:
        path = Path(img_path)
        console.rule(f"[bold yellow]Processing: {path.name}[/bold yellow]")

        res = load_and_detect(img_path)
        emb = get_embedding(img_path)

        table = Table(title=f"Results for [bold white]{path.name}[/bold white]", show_header=True)
        table.add_column("Property", style="bold cyan")
        table.add_column("Value", style="white")
        table.add_column("Status", style="bold")

        # Face Found
        found_str = "Yes" if res["face_found"] else "No"
        found_status = "[green]PASS[/green]" if res["face_found"] else "[red]FAIL[/red]"
        table.add_row("Face Detected", found_str, found_status)

        # Bounding Box
        bbox_str = str(res["bbox"]) if res["bbox"] else "N/A"
        table.add_row("Bounding Box [x1, y1, x2, y2]", bbox_str, "[blue]INFO[/blue]")

        # Detection Confidence
        conf_str = f"{res['det_confidence']:.4f}" if res["det_confidence"] else "N/A"
        conf_status = (
            "[green]PASS[/green]"
            if res["det_confidence"] >= 0.5
            else "[red]LOW[/red]"
        )
        table.add_row("Detection Confidence", conf_str, conf_status)

        # Quality Gate OK
        quality_str = "PASSED" if res["quality_ok"] else "FAILED"
        quality_status = (
            "[bold green]OK[/bold green]"
            if res["quality_ok"]
            else "[bold red]FAILED[/bold red]"
        )
        table.add_row("Quality Gate", quality_str, quality_status)

        # Quality Reasons
        reasons_str = (
            "; ".join(res["quality_reasons"])
            if res["quality_reasons"]
            else "None (All quality checks passed)"
        )
        reasons_status = (
            "[green]CLEAN[/green]"
            if not res["quality_reasons"]
            else "[yellow]FLAGGED[/yellow]"
        )
        table.add_row("Quality Issues", reasons_str, reasons_status)

        # Embedding Info
        if emb is not None:
            embeddings[path.name] = emb
            l2_norm = float(np.linalg.norm(emb))
            table.add_row(
                "Embedding Vector",
                f"Shape: {emb.shape}, dtype: {emb.dtype}, L2 Norm: {l2_norm:.4f}",
                "[green]GENERATED[/green]",
            )
        else:
            table.add_row("Embedding Vector", "None", "[red]NONE[/red]")

        console.print(table)
        console.print()

    # Pairwise Cosine Similarity Table if 2 or more embeddings obtained
    if len(embeddings) >= 2:
        sim_table = Table(title="[bold magenta]Pairwise Cosine Similarity[/bold magenta]", show_header=True)
        sim_table.add_column("Image A", style="cyan")
        sim_table.add_column("Image B", style="cyan")
        sim_table.add_column("Cosine Similarity", style="bold yellow")
        sim_table.add_column("Interpretation", style="bold")

        img_names = list(embeddings.keys())
        for i in range(len(img_names)):
            for j in range(i + 1, len(img_names)):
                name1, name2 = img_names[i], img_names[j]
                sim = cosine_similarity(embeddings[name1], embeddings[name2])
                interp = (
                    "[bold green]High Match[/bold green]"
                    if sim >= 0.5
                    else "[yellow]Low / No Match[/yellow]"
                )
                sim_table.add_row(name1, name2, f"{sim:.4f}", interp)

        console.print(sim_table)


if __name__ == "__main__":
    if len(sys.argv) > 1:
        target_images = sys.argv[1:]
    else:
        input_dir = Path("data/input")
        extensions = ["*.jpg", "*.jpeg", "*.png"]
        target_images = []
        for ext in extensions:
            target_images.extend([str(p) for p in input_dir.glob(ext)])

    if not target_images:
        console.print("[red]No images found in data/input/ and no arguments provided.[/red]")
        sys.exit(1)

    run_stage1_test(target_images)
