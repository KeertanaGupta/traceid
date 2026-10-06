# TRACEID

> **Face-to-blockchain provenance verification.** Give TRACEID a photo of your face and it finds where that face appears publicly on the web, re-verifies each match with face recognition, and anchors a tamper-evident evidence record on IPFS and the Polygon blockchain.

Real face detection, real web discovery, real on-chain proof.

![Python](https://img.shields.io/badge/Python-3.11-3776AB?logo=python&logoColor=white)
![InsightFace](https://img.shields.io/badge/InsightFace-ArcFace-FF6F00)
![Solidity](https://img.shields.io/badge/Solidity-0.8.20-363636?logo=solidity)
![Polygon](https://img.shields.io/badge/Polygon-Amoy_Testnet-8247E5?logo=polygon&logoColor=white)
![IPFS](https://img.shields.io/badge/IPFS-Pinata-65C2CB?logo=ipfs&logoColor=white)

🎥 **[Watch the demo](https://drive.google.com/file/d/1V2K2saIhAT5S3ok3zNyLer7Bi3HDKQ2E/view?usp=sharing)**

---

## Why?

People's photos get reposted, scraped and misused across the web, and it's hard to prove *where* and *when* an image of you appeared. TRACEID lets a person find public copies of their own face and produce an evidence record that anyone can independently check has not been altered since it was created.

## What This Proves (and Doesn't)

| Layer | Proves | Does **not** prove |
|---|---|---|
| **AI face matching** | The candidate image contains the same face as the input image (cosine similarity ≥ threshold) | Legal-grade identity |
| **Web search** | The content existed publicly at this URL at the time of discovery | That it still exists, or who posted it |
| **Blockchain** | Our evidence record has not changed since we anchored it | That the original social media post is authentic or unedited |

---

## How It Works

```
[ Input Face Image ]
         │
         ▼
[ Stage 1: Face detection, quality check & 512-d ArcFace embedding (InsightFace) ]
         │
         ▼
[ Stage 2: Reverse image search (SerpApi Google Lens) ]
         │
         ▼
[ Stage 3: Download candidates & re-verify each face (cosine similarity ≥ 0.40) ]
         │
         ▼
[ Stage 4: Evidence manifest (canonical JSON + SHA-256 hashes of both images) ]
         │
         ▼
[ Stage 5: Pin manifest to IPFS (Pinata) → CID ]
         │
         ▼
[ Stage 6: Evidence hash = SHA-256(manifest_hash + CID) ]
         │
         ▼
[ Stage 7: Register hash + CID on Polygon Amoy (EvidenceRegistry.sol) ]
         │
         ▼
[ Stage 8: Independent verification & tamper detection (traceid verify) ]
```

**Verification** (`traceid verify`) recomputes the manifest hash locally, combines it with the IPFS CID, and checks that exact hash exists on-chain. If even one field of `evidence.json` is changed, the hash no longer matches and verification fails.

---

## Tech Stack

| Layer | Technology / Tools |
| --- | --- |
| **Language** | Python 3.11 |
| **CLI & Terminal UI** | Typer, Rich |
| **Face Analysis** | InsightFace (`buffalo_l`, ArcFace), OpenCV, ONNX Runtime |
| **Web Discovery** | SerpApi Google Lens API |
| **Decentralized Storage** | Pinata IPFS |
| **Smart Contract & Tooling** | Solidity 0.8.20, Hardhat |
| **Blockchain Client** | Web3.py |
| **Network** | Polygon Amoy Testnet (Chain ID `80002`) |

---

## Project Structure

```
traceid/
├── traceid/
│   ├── cli.py              # scan, verify, report commands
│   ├── config.py           # loads settings from .env
│   ├── face/               # detection, quality check, embeddings
│   ├── discovery/          # Google Lens search, candidate download
│   ├── verification/       # face re-verification against threshold
│   ├── evidence/           # manifest building, canonical hashing
│   ├── storage/            # IPFS pinning and retrieval
│   └── chain/              # Web3 client, EvidenceRegistry calls
├── contracts/
│   ├── EvidenceRegistry.sol
│   ├── EvidenceRegistry.abi.json
│   └── hardhat.config.js
├── data/
│   ├── input/              # put your query images here
│   └── output/             # evidence.json, HTML report, candidates/
├── test_stage*.py          # per-stage test scripts
└── setup.py
```

---

## Setup

### Prerequisites
- Python **3.11**
- API keys for [SerpApi](https://serpapi.com) and [Pinata](https://pinata.cloud)
- A **testnet-only** wallet with some Amoy POL for gas ([faucet](https://faucet.polygon.technology))
- Node.js 18+ (only if you want to redeploy the contract)

### 1. Clone

```bash
git clone https://github.com/KeertanaGupta/traceid.git
cd traceid
```

### 2. Create a virtual environment

```bash
python -m venv venv
# Windows
venv\Scripts\activate
# Linux / macOS
source venv/bin/activate
```

### 3. Install

```bash
pip install -r requirements.txt
pip install -e .
```

The first run downloads the InsightFace `buffalo_l` model (~300 MB).

### 4. Configure environment variables

Copy `.env.example` to `.env` and fill in your values:

```env
SERPAPI_KEY=your_serpapi_key
PINATA_API_KEY=your_pinata_api_key
PINATA_API_SECRET=your_pinata_api_secret
POLYGON_AMOY_RPC_URL=https://polygon-amoy-bor-rpc.publicnode.com
DEPLOYER_PRIVATE_KEY=your_testnet_private_key
CONTRACT_ADDRESS=0xAaeC9ACCa00fdf1d9d01902BBCDECd1Ab06F4517
FACE_MATCH_THRESHOLD=0.40
```

> ⚠️ **Never use a wallet that holds real funds.** `DEPLOYER_PRIVATE_KEY` should belong to a throwaway testnet wallet, and `.env` must never be committed (it is already in `.gitignore`).

### 5. Smart contract

The contract is already deployed on Polygon Amoy at `0xAaeC9ACCa00fdf1d9d01902BBCDECd1Ab06F4517`, so no deployment is needed.

To deploy your own copy:

```bash
cd contracts
npm install
npx hardhat run scripts/deploy.js --network amoy
```

Then put the new address in `CONTRACT_ADDRESS`.

---

## Usage

### 1. Scan and register evidence

```bash
traceid scan data/input/me.jpg
```

Runs the full pipeline and writes:

| Output | Description |
|---|---|
| `data/output/evidence.json` | Evidence manifest (source URL, similarity score, image hashes, IPFS CID) |
| `data/output/evidence_report.html` | Visual evidence report with side-by-side face comparison |
| `data/output/candidates/` | Downloaded candidate images |

It also prints the IPFS CID and the Polygon transaction hash.

### 2. Verify evidence integrity

```bash
traceid verify data/output/evidence.json
```

Checks the manifest against IPFS and the on-chain record.

### 3. Demonstrate tamper detection

```bash
traceid verify data/output/evidence.json --tamper
```

Changes a field in memory before verifying, so you can see the check fail. The file on disk is not modified.

### 4. Regenerate the HTML report

```bash
traceid report data/output/evidence.json
```

---

## Testing

Each pipeline stage has a standalone test script:

```bash
python test_stage1.py   # face detection, quality check & embeddings
python test_stage2.py   # web discovery
python test_stage3.py   # candidate re-verification
python test_stage4.py   # manifest & hashing
python test_stage5.py   # IPFS pinning
python test_stage7.py   # blockchain registration & lookup
```

Stages 2, 5 and 7 call real external services and need valid keys in `.env`.

---

## Blockchain

- **Network:** Polygon Amoy Testnet (Chain ID `80002`)
- **Contract:** [`0xAaeC9ACCa00fdf1d9d01902BBCDECd1Ab06F4517`](https://amoy.polygonscan.com/address/0xAaeC9ACCa00fdf1d9d01902BBCDECd1Ab06F4517)
- **Example transaction:** [`0xbedcb209…c7a4af`](https://amoy.polygonscan.com/tx/0xbedcb20931e557b3d6a34bc542fc43fa66ccdc2ed00142413888520d81c7a4af)

`EvidenceRegistry.sol` stores `evidenceHash → (cid, timestamp, submitter)`, rejects duplicate registrations, and exposes a public `verifyEvidence(hash)` view so anyone can check a record without trusting this tool.

---

## Privacy, Ethics & Scope

TRACEID is a **consent-based self-verification tool**. It has been demonstrated only on consenting subjects using their own public posts, and it is not designed or intended for searching for or identifying non-consenting individuals. Production use would require legal review, an opt-in registry, and certified liveness detection.

**What leaves your machine:**
- To run a Google Lens search, the input image is uploaded to a **free public image host** (freeimage.host, with fallbacks) so SerpApi can fetch it. Only use images you are comfortable making publicly accessible.
- The evidence manifest (URLs, scores and image **hashes**, not the images themselves) is pinned **publicly** on IPFS.
- The evidence hash, CID and your wallet address are written **permanently** to a public blockchain.

---

## Known Limitations

- No certified liveness or anti-spoofing detection (planned).
- Search coverage is limited to what SerpApi / Google Lens has indexed.
- The face-match threshold (`0.40` raw ArcFace cosine similarity) is a heuristic tuned against real genuine/impostor test pairs. It is not a legal-grade identity proof.
- Image hashes reflect the indexed or cached copy at the time of verification, which may differ from the current live copy on the source platform.
- Testnet only. Not deployed to mainnet.

---

## Roadmap

- [ ] Liveness / anti-spoofing check on the input image
- [ ] Remove the need for a public temp host for search
- [ ] Batch scanning and scheduled re-checks
- [ ] Unit tests with mocked external services (pytest)

---

## 👩‍💻 Author

**Keertana Gupta** · [GitHub](https://github.com/KeertanaGupta) · [LinkedIn](https://www.linkedin.com/in/keertanagupta/)