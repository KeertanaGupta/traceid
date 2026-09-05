import requests
from traceid.config import PINATA_API_KEY, PINATA_API_SECRET


class IPFSClient:
    """Pin items to IPFS via Pinata."""

    pass


def pin_json_to_ipfs(data: dict) -> str:
    """Pin a JSON dictionary to IPFS using the Pinata API.

    Args:
        data: Dictionary payload to pin on IPFS.

    Returns:
        str: IPFS CID hash (IpfsHash).

    Raises:
        ValueError: If PINATA_API_KEY or PINATA_API_SECRET is missing.
        RuntimeError: If the Pinata API request fails.
    """
    if not PINATA_API_KEY or not PINATA_API_SECRET:
        raise ValueError(
            "Pinata credentials missing. Please set PINATA_API_KEY and PINATA_API_SECRET in your .env file."
        )

    url = "https://api.pinata.cloud/pinning/pinJSONToIPFS"
    headers = {
        "pinata_api_key": PINATA_API_KEY,
        "pinata_secret_api_key": PINATA_API_SECRET,
        "Content-Type": "application/json",
    }
    payload = {"pinataContent": data}

    try:
        response = requests.post(url, json=payload, headers=headers, timeout=20)
    except requests.exceptions.RequestException as e:
        raise RuntimeError(f"Network error connecting to Pinata API: {e}") from e

    if response.status_code != 200:
        err_msg = response.text.strip()
        raise RuntimeError(
            f"Pinata API pinning failed with status code {response.status_code}: {err_msg}"
        )

    try:
        res_data = response.json()
        cid = res_data.get("IpfsHash")
        if not cid:
            raise RuntimeError("Pinata API response did not contain 'IpfsHash'.")
        return str(cid)
    except Exception as e:
        raise RuntimeError(f"Failed to parse Pinata API response: {e}") from e


def fetch_from_ipfs(cid: str) -> dict:
    """Fetch and parse JSON from IPFS public gateways.

    Args:
        cid: IPFS Content Identifier string.

    Returns:
        dict: Parsed JSON payload.

    Raises:
        RuntimeError: If all IPFS gateways fail or return invalid data.
    """
    if not cid:
        raise ValueError("CID parameter cannot be empty.")

    gateways = [
        f"https://gateway.pinata.cloud/ipfs/{cid}",
        f"https://ipfs.io/ipfs/{cid}",
        f"https://cloudflare-ipfs.com/ipfs/{cid}",
    ]

    last_error = None
    for gateway_url in gateways:
        try:
            response = requests.get(gateway_url, timeout=15)
            if response.status_code == 200:
                return response.json()
            else:
                last_error = f"HTTP {response.status_code} from {gateway_url}"
        except Exception as e:
            last_error = f"Error from {gateway_url}: {e}"

    raise RuntimeError(
        f"Failed to fetch content for CID '{cid}' from IPFS gateways. Last error: {last_error}"
    )
