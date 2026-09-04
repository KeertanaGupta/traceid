"""Web discovery and candidate image fetching module."""

from traceid.discovery.candidate_fetch import fetch_candidate_image
from traceid.discovery.web_search import (
    classify_platform,
    search_web_for_face,
    upload_temp_public,
)

__all__ = [
    "upload_temp_public",
    "search_web_for_face",
    "fetch_candidate_image",
    "classify_platform",
]
