"""Evidence registry smart contract interaction module."""

from traceid.chain.web3_client import w3, contract, account


def hex_to_bytes32(hex_str: str) -> bytes:
    """Convert hex string to 32-byte representation for Solidity bytes32.

    Args:
        hex_str: Hexadecimal string (with or without 0x prefix).

    Returns:
        bytes: 32-byte binary data.
    """
    clean_hex = hex_str.strip()
    if clean_hex.startswith("0x") or clean_hex.startswith("0X"):
        clean_hex = clean_hex[2:]
    if len(clean_hex) != 64:
        raise ValueError(f"Hex string must be 64 characters (32 bytes) long, got {len(clean_hex)} chars.")
    return bytes.fromhex(clean_hex)


class RegistryContract:
    """Interact with EvidenceRegistry smart contract."""

    pass


def register_evidence(evidence_hash_hex: str, cid: str) -> dict:
    """Build and send registerEvidence transaction to Polygon Amoy.

    Args:
        evidence_hash_hex: SHA-256 evidence hash as hex string.
        cid: IPFS CID string.

    Returns:
        dict: Transaction receipt details including tx_hash, block_number, polygonscan_url.
    """
    evidence_hash_bytes = hex_to_bytes32(evidence_hash_hex)
    nonce = w3.eth.get_transaction_count(account.address)

    tx_params = {
        "from": account.address,
        "nonce": nonce,
        "chainId": 80002,
    }

    try:
        latest_block = w3.eth.get_block("latest")
        base_fee = latest_block.get("baseFeePerGas", w3.to_wei(30, "gwei"))
        priority_fee = getattr(w3.eth, "max_priority_fee", w3.to_wei(30, "gwei"))
        max_fee = base_fee * 2 + priority_fee
        tx_params["maxFeePerGas"] = max_fee
        tx_params["maxPriorityFeePerGas"] = priority_fee
    except Exception:
        tx_params["gasPrice"] = w3.eth.gas_price

    tx = contract.functions.registerEvidence(evidence_hash_bytes, cid).build_transaction(tx_params)
    signed_tx = account.sign_transaction(tx)

    raw_bytes = getattr(signed_tx, "raw_transaction", getattr(signed_tx, "rawTransaction", None))
    tx_hash_bytes = w3.eth.send_raw_transaction(raw_bytes)

    receipt = w3.eth.wait_for_transaction_receipt(tx_hash_bytes)

    tx_hash_hex = tx_hash_bytes.hex()
    if not tx_hash_hex.startswith("0x"):
        tx_hash_hex = f"0x{tx_hash_hex}"

    polygonscan_url = f"https://amoy.polygonscan.com/tx/{tx_hash_hex}"

    print(f"Transaction Hash: {tx_hash_hex}")
    print(f"PolygonScan Link: {polygonscan_url}")

    return {
        "tx_hash": tx_hash_hex,
        "block_number": receipt["blockNumber"],
        "polygonscan_url": polygonscan_url,
    }


def verify_evidence(evidence_hash_hex: str) -> dict:
    """Call verifyEvidence view function on EvidenceRegistry smart contract.

    Args:
        evidence_hash_hex: SHA-256 evidence hash as hex string.

    Returns:
        dict: Dictionary containing exists (bool), cid (str), timestamp (int), submitter (str).
    """
    evidence_hash_bytes = hex_to_bytes32(evidence_hash_hex)
    exists, cid, timestamp, submitter = contract.functions.verifyEvidence(evidence_hash_bytes).call()

    return {
        "exists": bool(exists),
        "cid": str(cid),
        "timestamp": int(timestamp),
        "submitter": str(submitter),
    }
