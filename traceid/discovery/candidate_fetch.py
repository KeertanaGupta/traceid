import hashlib
import os
import urllib.parse
from pathlib import Path
from bs4 import BeautifulSoup
import requests

OUTPUT_CANDIDATES_DIR = Path("data/output/candidates")

_session: requests.Session | None = None


def get_session() -> requests.Session:
    """Get or initialize a shared requests Session with browser User-Agent."""
    global _session
    if _session is None:
        _session = requests.Session()
        _session.headers.update({
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/120.0.0.0 Safari/537.36"
            )
        })
    return _session


def _download_image_to_file(url: str, target_path: Path) -> bool:
    """Download an image from a URL and save it to target_path.

    Args:
        url: Image URL.
        target_path: Path destination file.

    Returns:
        bool: True if downloaded and saved successfully, False otherwise.
    """
    session = get_session()
    try:
        resp = session.get(url, timeout=10)
        if resp.status_code == 200 and len(resp.content) > 100:
            target_path.parent.mkdir(parents=True, exist_ok=True)
            with open(target_path, "wb") as f:
                f.write(resp.content)
            return True
    except Exception:
        pass
    return False


def fetch_candidate_image(page_url: str, image_url: str | None = None) -> str | None:
    """Fetch candidate image from direct image_url or scrape page_url for target image.

    Args:
        page_url: Web page URL of candidate result.
        image_url: Optional direct image URL.

    Returns:
        str | None: Local file path of downloaded candidate image, or None if download failed.
    """
    OUTPUT_CANDIDATES_DIR.mkdir(parents=True, exist_ok=True)

    # Derive unique filename hash based on page_url or image_url
    url_key = page_url or image_url or "unknown"
    url_hash = hashlib.sha256(url_key.encode("utf-8")).hexdigest()[:16]
    target_file = OUTPUT_CANDIDATES_DIR / f"candidate_{url_hash}.jpg"

    # Attempt 1: Direct image download if image_url is supplied
    if image_url:
        if _download_image_to_file(image_url, target_file):
            return str(target_file)

    # Attempt 2: Fetch page_url HTML and extract og:image or candidate <img> tags
    if not page_url:
        return None

    session = get_session()
    try:
        resp = session.get(page_url, timeout=10)
        if resp.status_code != 200:
            return None

        soup = BeautifulSoup(resp.text, "html.parser")

        # 1. Search for OpenGraph / Twitter meta image tags
        extracted_url: str | None = None

        og_meta = (
            soup.find("meta", property="og:image")
            or soup.find("meta", attrs={"name": "og:image"})
            or soup.find("meta", attrs={"name": "twitter:image"})
            or soup.find("meta", property="twitter:image")
        )

        if og_meta and og_meta.get("content"):
            extracted_url = og_meta["content"]

        # 2. Fallback: Search <img> tags if meta image is missing
        if not extracted_url:
            img_tags = soup.find_all("img")
            best_img_src: str | None = None
            for img in img_tags:
                src = img.get("src") or img.get("data-src")
                if src and not src.startswith("data:"):
                    best_img_src = src
                    break
            extracted_url = best_img_src

        if extracted_url:
            # Resolve relative URLs
            full_img_url = urllib.parse.urljoin(page_url, extracted_url)
            if _download_image_to_file(full_img_url, target_file):
                return str(target_file)

    except Exception:
        pass

    return None
