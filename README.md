# Candidate Ranking System (Redrob Hackathon)

This repository contains the complete offline implementation of an AI Candidate Ranking System built for the Redrob Intelligent Candidate Discovery & Ranking Challenge.

## Architecture

Our ranking pipeline leverages a custom-built, offline-first execution strategy to accurately rank 100,000 synthetic candidates within strict compute constraints (5 minutes, CPU-only, 16GB RAM). 

1. **Plausibility Filter**: We aggressively filter out honeypot candidates via 12 checks (expert skills with 0 months duration, overlapping timelines, time-traveling tech claims, education paradoxes, duplicate career descriptions, LangChain-only wrappers, wrong persona).
2. **Fast Pre-filter**: A deterministic keyword-weighted heuristic rapidly downsizes the candidate pool from 100k to the top 3,000, with a two-bucket strategy prioritizing core retrieval/ranking keywords while preserving recall.
3. **AI Semantic Embedding**: The shortlisted 3,000 candidates are batch-encoded using a locally-hosted `all-MiniLM-L6-v2` model (via direct Transformers inference, not SentenceTransformer) against three distinct JD-derived facet vectors (Core ML, Engineering Infrastructure, Nice-to-Haves).
4. **Dynamic Score Fusion**: Final composite score fuses semantic similarity (50%), explicit JD skill match (30%), and behavioral signals (20%), then applies multiplicative gates: seniority-aware title matching, 5-9 year experience band fit, services-only career penalty, tenure stability check, location compatibility, recency/responsiveness, profile completeness, and unverified vector-DB claim detection. Additive bonuses for tier-1/2 education and relevant certifications.
5. **Reasoning Generation**: Each top-100 candidate receives an evidence-grounded rationale citing specific skills, career evidence, notice period, and behavioral signals.

## Known Dataset-Quality Edge Cases
During analysis, we identified occasional dataset generation artifacts (e.g., identical, lengthy job descriptions copy-pasted across multiple distinct roles in a candidate's career history). Rather than allowing these unverified clones to pollute the ranking, our `plausibility_filter.py` explicitly traps and disqualifies candidates exhibiting this "duplicate-description" anomaly. This ensures the integrity of the top candidate pool.

## Setup & Reproduction

We strictly enforce offline network execution to comply with Stage 3 rules via `TRANSFORMERS_OFFLINE` environment variables embedded in the code.

### 1. Install Dependencies
```bash
pip install -r requirements.txt
```

### 2. Pre-computation (Download Model)
As per Section 10.3 of the spec, we must pre-compute/download our model weights before the strictly offline ranking stage begins.
Run this script to fetch the 90MB `all-MiniLM-L6-v2` model from HuggingFace to the `local_model/` directory:

```bash
python download_model.py
```

### 3. Run the Ranking Pipeline (Offline)
To reproduce our top 100 ranking and generate the final `team_TeamClover.csv` output within the 5-minute offline window:

```bash
python main.py --candidates ./candidates.jsonl --out ./team_TeamClover.csv
```

### 4. Validate
```bash
python validate_submission.py team_TeamClover.csv
```

## Repository Structure
* `main.py` - Primary orchestrator. Handles file IO and executes stages.
* `scorer.py` - Multi-signal scoring: semantic similarity, skill matching, title/experience/location gates, behavioral signals, education/certification bonuses.
* `embedding_engine.py` - Wrapper for the SentenceTransformer model and batch encoding.
* `plausibility_filter.py` - Core logic for identifying impossible candidate timelines (Honeypot detection).
* `reasoning_generator.py` - Dynamic text generator for candidate rationale.
* `data_loader.py` - Streaming JSONL parser to conserve RAM.
* `local_model/` - The locally saved HuggingFace model weights. 
* `submission_metadata.yaml` - Team methodology and hardware declaration.
