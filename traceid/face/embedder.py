from pathlib import Path
import cv2
import numpy as np
from traceid.face.detector import get_face_app


def get_embedding(image_path: str) -> np.ndarray | None:
    """Extract 512-d InsightFace embedding for the largest face detected in image.

    Args:
        image_path: Path to the image file.

    Returns:
        np.ndarray | None: 512-dimensional float32 numpy array or None if no face found.
    """
    path_obj = Path(image_path)
    if not path_obj.exists() or not path_obj.is_file():
        return None

    img = cv2.imread(str(path_obj))
    if img is None:
        return None

    app = get_face_app()
    faces = app.get(img)

    if not faces:
        return None

    # Select largest face by bounding box area
    largest_face = max(
        faces,
        key=lambda f: (f.bbox[2] - f.bbox[0]) * (f.bbox[3] - f.bbox[1])
    )

    embedding = getattr(largest_face, "embedding", None)
    if embedding is None:
        embedding = getattr(largest_face, "normed_embedding", None)

    if embedding is not None:
        return np.array(embedding, dtype=np.float32)

    return None


def cosine_similarity(emb1: np.ndarray, emb2: np.ndarray) -> float:
    """Compute cosine similarity between two feature embeddings.

    Args:
        emb1: First embedding array.
        emb2: Second embedding array.

    Returns:
        float: Cosine similarity score between -1.0 and 1.0.
    """
    if emb1 is None or emb2 is None:
        return 0.0

    vec1 = np.asarray(emb1, dtype=np.float32).flatten()
    vec2 = np.asarray(emb2, dtype=np.float32).flatten()

    norm1 = np.linalg.norm(vec1)
    norm2 = np.linalg.norm(vec2)

    if norm1 == 0.0 or norm2 == 0.0:
        return 0.0

    dot_product = np.dot(vec1, vec2)
    similarity = dot_product / (norm1 * norm2)

    # Clip to valid cosine range [-1.0, 1.0] to guard against floating-point inaccuracies
    return float(np.clip(similarity, -1.0, 1.0))
