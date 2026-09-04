import os
from pathlib import Path
from dotenv import load_dotenv

# Load .env file from project root or current working directory
env_path = Path(__file__).resolve().parent.parent / ".env"
load_dotenv(dotenv_path=env_path if env_path.exists() else None)

SERPAPI_KEY: str | None = os.getenv("SERPAPI_KEY")
PINATA_API_KEY: str | None = os.getenv("PINATA_API_KEY")
PINATA_API_SECRET: str | None = os.getenv("PINATA_API_SECRET")
POLYGON_AMOY_RPC_URL: str | None = os.getenv("POLYGON_AMOY_RPC_URL")
DEPLOYER_PRIVATE_KEY: str | None = os.getenv("DEPLOYER_PRIVATE_KEY")
CONTRACT_ADDRESS: str | None = os.getenv("CONTRACT_ADDRESS")


_threshold_raw = os.getenv("FACE_MATCH_THRESHOLD", "0.40")
try:
    FACE_MATCH_THRESHOLD: float = float(_threshold_raw)
except ValueError:
    FACE_MATCH_THRESHOLD: float = 0.40

