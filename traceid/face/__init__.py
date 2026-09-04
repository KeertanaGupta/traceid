"""Face detection, quality gate, and embedding extraction module."""

from traceid.face.detector import load_and_detect
from traceid.face.embedder import get_embedding, cosine_similarity

__all__ = ["load_and_detect", "get_embedding", "cosine_similarity"]
