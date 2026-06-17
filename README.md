# Candidate Ranking System (Redrob Hackathon)

This repository contains the complete offline implementation of an AI Candidate Ranking System built for the Redrob Intelligent Candidate Discovery & Ranking Challenge.

## Architecture

Our ranking pipeline leverages a custom-built, offline-first execution strategy to accurately rank 100,000 synthetic candidates within strict compute constraints (5 minutes, CPU-only, 16GB RAM). 

1. **Plausibility Filter**: We aggressively filter out honeypot candidates (e.g. 5 expert skills with 0 months duration, overlapping timelines creating impossible durations).
2. **Fast Pre-filter**: A deterministic keyword heuristic rapidly downsizes the candidate pool from 100k to the top 3,000, eliminating non-technical candidates (e.g. HR, Sales).
3. **AI Semantic Embedding**: We embed the remaining 3,000 candidates using a locally-hosted `all-MiniLM-L6-v2` model against three distinct vectors derived directly from the official Job Description (Core ML, Infra, Nice-to-Haves).
4. **Dynamic Score Fusion**: The final composite score fuses 50% AI semantic match, 30% explicit JD skill match (to penalize buzzword stuffing), and 20% Redrob behavioral signals (response rate, GitHub activity, notice period).
5. **Reasoning Generation**: Generates 2-sentence rationale based on specific data points (extracted skills, exact notice periods).

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
To reproduce our top 100 ranking and generate the final `submission.csv` output within the 5-minute offline window:

```bash
python main.py --candidates ./candidates.jsonl --out ./submission.csv
```

### 4. Validate
```bash
python validate_submission.py submission.csv
```

## Repository Structure
* `main.py` - Primary orchestrator. Handles file IO and executes stages.
* `scorer.py` - Fuses semantic scores with behavioral signals and handles weighting.
* `embedding_engine.py` - Wrapper for the SentenceTransformer model and batch encoding.
* `plausibility_filter.py` - Core logic for identifying impossible candidate timelines (Honeypot detection).
* `reasoning_generator.py` - Dynamic text generator for candidate rationale.
* `data_loader.py` - Streaming JSONL parser to conserve RAM.
* `local_model/` - The locally saved HuggingFace model weights. 
* `submission_metadata.yaml` - Team methodology and hardware declaration.
