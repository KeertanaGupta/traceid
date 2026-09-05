import os
import urllib.parse
from pathlib import Path
import requests
from serpapi import GoogleSearch

from traceid.config import SERPAPI_KEY


def upload_temp_public(image_path: str) -> str:
    """Upload a local image to a free, anonymous public file host.

    Tries 0x0.st first, then catbox.moe, then tmpfiles.org as fallback.

    Args:
        image_path: Path to the local image file.

    Returns:
        str: Direct public URL of the uploaded image.

    Raises:
        RuntimeError: If image file does not exist or all upload services fail.
    """
    path_obj = Path(image_path)
    if not path_obj.exists() or not path_obj.is_file():
        raise RuntimeError(f"Image file not found: {image_path}")

    # Primary Host: 0x0.st
    try:
        with open(path_obj, "rb") as f:
            resp = requests.post("https://0x0.st", files={"file": f}, timeout=15)
        if resp.status_code == 200 and resp.text.strip().startswith("http"):
            url = resp.text.strip()
            return url
    except Exception:
        pass

    # Fallback Host 1: catbox.moe
    try:
        with open(path_obj, "rb") as f:
            resp = requests.post(
                "https://catbox.moe/user/api.php",
                data={"reqtype": "fileupload"},
                files={"fileToUpload": f},
                timeout=15,
            )
        if resp.status_code == 200 and resp.text.strip().startswith("http"):
            return resp.text.strip()
    except Exception:
        pass

    # Fallback Host 2: tmpfiles.org
    try:
        with open(path_obj, "rb") as f:
            resp = requests.post(
                "https://tmpfiles.org/api/v1/upload",
                files={"file": f},
                timeout=15,
            )
        if resp.status_code == 200:
            data = resp.json()
            raw_url = data.get("data", {}).get("url")
            if raw_url and "tmpfiles.org/" in raw_url:
                # Convert page URL to direct download URL (tmpfiles.org/123/img.jpg -> tmpfiles.org/dl/123/img.jpg)
                direct_url = raw_url.replace("tmpfiles.org/", "tmpfiles.org/dl/")
                return direct_url
    except Exception:
        pass

    raise RuntimeError(
        f"Failed to upload image {image_path} to temporary public hosts (0x0.st, catbox.moe, tmpfiles.org)."
    )


def classify_platform(url: str) -> str:
    """Classify the platform of a URL based on its domain.

    Args:
        url: Page URL string.

    Returns:
        str: Platform name ('instagram', 'x', 'linkedin', 'facebook', 'pinterest', 'reddit', 'tiktok', 'youtube', or 'web').
    """
    if not url:
        return "web"

    parsed = urllib.parse.urlparse(url)
    domain = parsed.netloc.lower()
    if ":" in domain:
        domain = domain.split(":")[0]

    if "pinterest." in domain or "pin.it" in domain:
        return "pinterest"
    elif "instagram." in domain or "instagr.am" in domain:
        return "instagram"
    elif "linkedin." in domain:
        return "linkedin"
    elif "facebook." in domain or "fb.com" in domain or "fb.watch" in domain:
        return "facebook"
    elif "reddit." in domain:
        return "reddit"
    elif "tiktok." in domain:
        return "tiktok"
    elif "youtube." in domain or "youtu.be" in domain:
        return "youtube"
    elif domain == "x.com" or domain.endswith(".x.com") or "twitter." in domain or domain == "t.co" or domain.endswith(".t.co"):
        return "x"
    else:
        return "web"


def search_web_for_face(image_path: str) -> list[dict]:
    """Perform Google Lens visual search via SerpApi for a given image.

    Args:
        image_path: Local path to the query face image.

    Returns:
        list[dict]: List of candidate matches:
            [{"page_url": str, "image_url": str | None, "platform": str, "title": str | None}]

    Raises:
        ValueError: If SERPAPI_KEY is not configured.
        RuntimeError: If temporary upload or SerpApi request fails.
    """
    if not SERPAPI_KEY:
        raise ValueError(
            "SERPAPI_KEY is not configured. Please set SERPAPI_KEY in your .env file."
        )

    # Step A: Upload image to temporary public host
    public_url = upload_temp_public(image_path)

    # Step B: Perform Google Lens visual search via SerpApi
    params = {
        "engine": "google_lens",
        "url": public_url,
        "api_key": SERPAPI_KEY,
    }

    try:
        search = GoogleSearch(params)
        results = search.get_dict()
    except Exception as e:
        raise RuntimeError(f"SerpApi Google Lens search failed: {e}") from e

    # Check for API error response from SerpApi
    if "error" in results:
        raise RuntimeError(f"SerpApi returned error: {results['error']}")

    visual_matches = results.get("visual_matches", [])
    if not visual_matches:
        # Check alternative keys if visual_matches is absent
        visual_matches = results.get("images_results", [])

    candidates: list[dict] = []
    seen_urls: set[str] = set()

    for item in visual_matches:
        page_url = item.get("link") or item.get("source") or item.get("source_url")
        if not page_url or page_url in seen_urls:
            continue

        seen_urls.add(page_url)

        # Extract image URL if available
        image_url = (
            item.get("thumbnail")
            or item.get("image")
            or item.get("original")
            or item.get("source_image")
        )
        if isinstance(image_url, dict):
            image_url = image_url.get("link") or image_url.get("src")

        title = item.get("title") or item.get("source")

        platform = classify_platform(page_url)

        candidates.append({
            "page_url": page_url,
            "image_url": image_url if isinstance(image_url, str) else None,
            "platform": platform,
            "title": title if isinstance(title, str) else None,
        })

    return candidates
