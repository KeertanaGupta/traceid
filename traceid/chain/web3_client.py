"""Web3 client initialization and contract instantiation for Polygon Amoy."""

import json
from pathlib import Path
from web3 import Web3

from traceid.config import (
    POLYGON_AMOY_RPC_URL,
    DEPLOYER_PRIVATE_KEY,
    CONTRACT_ADDRESS,
)

# Project root directory
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
ABI_PATH = PROJECT_ROOT / "contracts" / "EvidenceRegistry.abi.json"

if not POLYGON_AMOY_RPC_URL:
    raise ValueError("POLYGON_AMOY_RPC_URL is not set in environment or .env file.")

w3 = Web3(Web3.HTTPProvider(POLYGON_AMOY_RPC_URL))

if not ABI_PATH.exists():
    raise FileNotFoundError(f"EvidenceRegistry ABI file not found at {ABI_PATH}")

with open(ABI_PATH, "r", encoding="utf-8") as f:
    contract_abi = json.load(f)

if not CONTRACT_ADDRESS:
    raise ValueError("CONTRACT_ADDRESS is not set in environment or .env file.")

checksum_address = Web3.to_checksum_address(CONTRACT_ADDRESS)
contract = w3.eth.contract(address=checksum_address, abi=contract_abi)

if not DEPLOYER_PRIVATE_KEY:
    raise ValueError("DEPLOYER_PRIVATE_KEY is not set in environment or .env file.")

pkey = DEPLOYER_PRIVATE_KEY.strip()
if not pkey.startswith("0x"):
    pkey = f"0x{pkey}"

account = w3.eth.account.from_key(pkey)
