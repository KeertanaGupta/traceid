from pathlib import Path
import numpy as np

from traceid.config import FACE_MATCH_THRESHOLD
from traceid.face.detector import load_and_detect
from traceid.face.embedder import get_embedding, cosine_similarity


class FaceMatcher:
    """Compare and match face embeddings."""

    pass


def verify_candidates(
    original_embedding: np.ndarray, candidates: list[dict]
) -> dict:
    """Verify candidate images against the original target face embedding.

    For each candidate image:
    1. Check if local_path exists.
    2. Detect face in candidate image.
    3. Extract embedding if face detected.
    4. Compute cosine similarity against original_embedding.
    5. Evaluate acceptance against FACE_MATCH_THRESHOLD.

    Args:
        original_embedding: 512-d feature vector of target query face.
        candidates: List of candidate dicts with keys 'page_url', 'image_url',
            'platform', 'local_path', 'title'.

    Returns:
        dict: {
            "ranked_candidates": list[dict sorted by similarity descending],
            "best_match": top accepted candidate dict or None
        }
    """
    evaluated: list[dict] = []

    for cand in candidates:
        page_url = cand.get("page_url", "")
        image_url = cand.get("image_url")
        platform = cand.get("platform", "web")
        local_path = cand.get("local_path")
        title = cand.get("title")

        item_result = {
            "page_url": page_url,
            "image_url": image_url,
            "platform": platform,
            "local_path": local_path,
            "title": title,
            "face_similarity": 0.0,
            "accepted": False,
            "reason": "no_face_detected",
        }

        if not local_path or not Path(local_path).exists():
            item_result["accepted"] = False
            item_result["reason"] = "image_fetch_failed"
            item_result["face_similarity"] = 0.0
            evaluated.append(item_result)
            continue

        det_res = load_and_detect(local_path)
        if not det_res.get("face_found", False):
            item_result["accepted"] = False
            item_result["reason"] = "no_face_detected"
            item_result["face_similarity"] = 0.0
            evaluated.append(item_result)
            continue

        cand_emb = get_embedding(local_path)
        if cand_emb is None:
            item_result["accepted"] = False
            item_result["reason"] = "no_face_detected"
            item_result["face_similarity"] = 0.0
            evaluated.append(item_result)
            continue

        sim = cosine_similarity(original_embedding, cand_emb)
        item_result["face_similarity"] = float(sim)

        if sim >= FACE_MATCH_THRESHOLD:
            item_result["accepted"] = True
            item_result["reason"] = "passed"
        else:
            item_result["accepted"] = False
            item_result["reason"] = "below_threshold"

        evaluated.append(item_result)

    # Sort candidates by similarity descending
    ranked_candidates = sorted(
        evaluated, key=lambda x: x["face_similarity"], reverse=True
    )

    # Find top accepted candidate
    best_match = None
    for cand in ranked_candidates:
        if cand["accepted"]:
            best_match = cand
            break

    return {
        "ranked_candidates": ranked_candidates,
        "best_match": best_match,
    }
