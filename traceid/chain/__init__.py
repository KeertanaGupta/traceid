"""Blockchain integration module."""

from traceid.chain.web3_client import w3, contract, account
from traceid.chain.registry import register_evidence, verify_evidence

__all__ = [
    "w3",
    "contract",
    "account",
    "register_evidence",
    "verify_evidence",
]
