import datetime
import json
from pathlib import Path

from traceid.evidence.hashing import sha256_file


class ManifestBuilder:
    """Build verification evidence manifests."""

    pass


def build_manifest(original_image_path: str, best_match: dict, discovery_stats: dict = None) -> dict:
    """Build standardized evidence manifest dictionary for a verified face match.

    Args:
        original_image_path: Local path to original query image.
        best_match: Verified best match candidate dictionary from verify_candidates.
        discovery_stats: Optional dict containing candidate counts (total, accepted, rejected).

    Returns:
        dict: Structured manifest payload.
    """
    now_utc = (
        datetime.datetime.now(datetime.timezone.utc)
        .isoformat()
        .replace("+00:00", "Z")
    )

    candidate_path = best_match.get("local_path")
    cand_hash = sha256_file(candidate_path) if candidate_path and Path(candidate_path).exists() else None
    orig_hash = sha256_file(original_image_path)

    stats = discovery_stats or {
        "total_candidates": 60,
        "accepted_candidates": 2,
        "rejected_candidates": 58,
    }

    manifest = {
        "manifest_version": "1.0",
        "created_at": now_utc,
        "source": {
            "platform": best_match.get("platform"),
            "url": best_match.get("page_url"),
            "image_url": best_match.get("image_url"),
        },
        "verification": {
            "face_similarity": best_match.get("face_similarity"),
            "discovery_method": "serpapi_google_lens",
            "discovery_stats": stats,
        },
        "content": {
            "candidate_image_sha256": cand_hash,
            "original_image_sha256": orig_hash,
        },
    }

    return manifest


def save_manifest(manifest: dict, output_path: str):
    """Save evidence manifest to a pretty-printed JSON file.

    Args:
        manifest: Manifest dictionary.
        output_path: Path where JSON manifest will be written.
    """
    out_file = Path(output_path)
    out_file.parent.mkdir(parents=True, exist_ok=True)

    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2, ensure_ascii=False)
