# TRACEID

No hardcoded results, no staged data — real face detection, real web discovery, real on-chain proof.


## What This Proves (and Doesn't)

- **AI (face matching) proves**: This candidate image contains the same face as the input image.
- **Web search proves**: This content exists publicly at this URL at the time of discovery.
- **Blockchain proves**: Our evidence record has not changed since we anchored it. It does **NOT** prove the original social media post itself is authentic or unedited.

## Architecture

```
[ Input Face Image ]
         │
         ▼
[ Stage 1: InsightFace Detection & Embedding (512-d ArcFace) ]
         │
         ▼
[ Stage 2: SerpApi Google Lens Web Search ]
         │
         ▼
[ Stage 3: Candidate Image Re-verification (Cosine Similarity >= 0.40) ]
         │
         ▼
[ Stage 4: Evidence Manifest Generation (Canonical JSON) ]
         │
         ▼
[ Stage 5: IPFS Decentralized Pinning (Pinata Gateway) ]
         │
         ▼
[ Stage 6/7: Polygon Amoy Smart Contract Anchoring (EvidenceRegistry.sol) ]
         │
         ▼
[ Stage 8: Independent Verification & Tamper Detection (traceid verify) ]
```

## Tech Stack

| Layer | Technology / Tools |
| --- | --- |
| **Language** | Python 3.11 |
| **CLI & Terminal UI** | Typer, Rich |
| **Face Analysis** | InsightFace (`buffalo_l`), OpenCV |
| **Web Discovery** | SerpApi Google Lens API |
| **Decentralized Storage** | Pinata IPFS Gateway |
| **Smart Contract & Tooling** | Solidity 0.8.20, Hardhat |
| **Blockchain Client** | Web3.py |
| **Network** | Polygon Amoy Testnet (Chain ID `80002`) |

## Setup

1. **Clone repository**:
   ```bash
   git clone https://github.com/KeertanaGupta/traceid.git
   cd traceid
   ```

2. **Create and activate virtual environment**:
   ```bash
   python -m venv venv
   # On Windows:
   venv\Scripts\activate
   # On Linux/macOS:
   source venv/bin/activate
   ```

3. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   pip install -e .
   ```

4. **Configure Environment Variables**:
   Copy `.env.example` to `.env` and fill in your API keys and credentials:
   ```env
   SERPAPI_KEY=your_serpapi_key
   PINATA_API_KEY=your_pinata_api_key
   PINATA_API_SECRET=your_pinata_api_secret
   POLYGON_AMOY_RPC_URL=https://polygon-amoy-bor-rpc.publicnode.com
   DEPLOYER_PRIVATE_KEY=your_testnet_private_key
   CONTRACT_ADDRESS=0xAaeC9ACCa00fdf1d9d01902BBCDECd1Ab06F4517
   FACE_MATCH_THRESHOLD=0.40
   ```

5. **Smart Contract Status**:
   The contract is already deployed on Polygon Amoy at `0xAaeC9ACCa00fdf1d9d01902BBCDECd1Ab06F4517`. No redeployment is needed unless you wish to test a fresh contract deployment.

## Usage

### 1. Scan & Register Evidence
```bash
traceid scan <image_path>
```

### 2. Verify Evidence Integrity
```bash
traceid verify <evidence_json_path>
```

### 3. Demonstrate Tamper Detection
```bash
traceid verify <evidence_json_path> --tamper
```

## Blockchain

- **Network**: Polygon Amoy Testnet (Chain ID `80002`)
- **Contract Address**: [`0xAaeC9ACCa00fdf1d9d01902BBCDECd1Ab06F4517`](https://amoy.polygonscan.com/address/0xAaeC9ACCa00fdf1d9d01902BBCDECd1Ab06F4517)
- **Example Transaction**: [`0xbedcb20931e557b3d6a34bc542fc43fa66ccdc2ed00142413888520d81c7a4af`](https://amoy.polygonscan.com/tx/0xbedcb20931e557b3d6a34bc542fc43fa66ccdc2ed00142413888520d81c7a4af)

## Ethics & Scope

This is a consent-based self-verification tool, demonstrated only on consenting subjects using their own public posts. It is not designed or intended for searching or identifying non-consenting individuals. Production use would require legal review, an opt-in registry, and certified liveness detection.

## Known Limitations

- No certified liveness/anti-spoofing detection (planned future work).
- Search coverage limited to what SerpApi/Google Lens has indexed.
- Face-match threshold (`0.40` for raw ArcFace cosine similarity) is a heuristic tuned and validated against real genuine/impostor test pairs, not a legal-grade identity proof.
- Discovered image hashes reflect the indexed/cached copy of an image at time of verification, which may differ from the current live copy on the source platform.
- Testnet only — not deployed to mainnet.

## Demo

Link: https://drive.google.com/file/d/1V2K2saIhAT5S3ok3zNyLer7Bi3HDKQ2E/view?usp=sharing
