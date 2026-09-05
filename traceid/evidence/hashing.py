import hashlib
import json
from pathlib import Path


class Hasher:
    """Compute cryptographic hashes for evidence files."""

    pass


def sha256_file(path: str) -> str:
    """Compute SHA-256 hash of a file.

    Args:
        path: Path to local file.

    Returns:
        str: Hexadecimal SHA-256 string.

    Raises:
        FileNotFoundError: If file does not exist.
    """
    file_path = Path(path)
    if not file_path.exists() or not file_path.is_file():
        raise FileNotFoundError(f"File not found for hashing: {path}")

    sha256 = hashlib.sha256()
    with open(file_path, "rb") as f:
        while chunk := f.read(65536):
            sha256.update(chunk)
    return sha256.hexdigest()


def sha256_json(data: dict) -> str:
    """Compute SHA-256 hash of canonical JSON data (sorted keys).

    Args:
        data: Dictionary data to hash.

    Returns:
        str: Hexadecimal SHA-256 string of the canonical JSON string.
    """
    canonical_json = json.dumps(data, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical_json.encode("utf-8")).hexdigest()


def combine_hash(*parts: str) -> str:
    """Compute SHA-256 hash of concatenated hash strings for final on-chain commit.

    Args:
        *parts: String hash components to combine.

    Returns:
        str: Hexadecimal SHA-256 string of concatenated parts.
    """
    combined_string = "".join(parts)
    return hashlib.sha256(combined_string.encode("utf-8")).hexdigest()
