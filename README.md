# 🎯 Candidate Ranking System

An offline-first, AI-powered candidate ranking pipeline built for the **Hack2Skill × Redrob AI Hackathon** — *Intelligent Candidate Discovery & Ranking Challenge*.

Ranks **100,000 synthetic candidates in under 5 minutes** on CPU-only hardware using semantic embeddings, deterministic scoring, and honeypot detection — no cloud APIs, no LLM calls, no internet required at inference time.

---

## Table of Contents

- [Overview](#overview)
- [How It Works](#how-it-works)
- [Architecture](#architecture)
- [Tech Stack](#tech-stack)
- [Prerequisites](#prerequisites)
- [Getting Started](#getting-started)
- [Pipeline Stages](#pipeline-stages)
- [Scoring Formula](#scoring-formula)
- [Repository Structure](#repository-structure)
- [Constraints & Design Decisions](#constraints--design-decisions)

---

## Overview

Most candidate ranking systems either rely on expensive LLM API calls or naive keyword matching. This pipeline takes a different approach — combining **semantic embeddings** with **deterministic heuristics** and **behavioral signals** to produce a robust, explainable ranking that runs entirely offline.

### Key Features

- ✅ **Fully offline** — no API keys, no network calls at inference time
- ✅ **Honeypot detection** — filters impossible/fake candidate profiles before scoring
- ✅ **Multi-vector semantic matching** — embeds candidates against 3 separate JD vectors
- ✅ **Dynamic score fusion** — AI score + explicit skill match + behavioral signals
- ✅ **Reasoning generation** — 2-sentence human-readable rationale per candidate
- ✅ **Scales to 100k candidates** — streaming JSONL parser keeps RAM under 16GB
- ✅ **CPU-only** — no GPU required

---

## How It Works

```
100,000 candidates
        │
        ▼
┌─────────────────────┐
│  Plausibility Filter │  ← Remove honeypots (impossible timelines, skill fraud)
└─────────────────────┘
        │
        ▼ ~remaining candidates
┌─────────────────────┐
│   Fast Pre-filter   │  ← Keyword heuristic → top 3,000 technical candidates
└─────────────────────┘
        │
        ▼ 3,000 candidates
┌─────────────────────┐
│  Semantic Embedding │  ← all-MiniLM-L6-v2 against 3 JD vectors (local model)
└─────────────────────┘
        │
        ▼
┌─────────────────────┐
│  Dynamic Score Fusion│  ← 50% semantic + 30% skill match + 20% behavioral
└─────────────────────┘
        │
        ▼
┌─────────────────────┐
│ Reasoning Generator │  ← 2-sentence rationale from extracted data points
└─────────────────────┘
        │
        ▼
   Top 100 ranked candidates → submission.csv
```

---

## Architecture

### Pipeline Stages

#### 1. Plausibility Filter (`plausibility_filter.py`)
Aggressively removes **honeypot candidates** — synthetic profiles designed to fool naive rankers:
- Candidates with expert-level skills but 0 months of experience
- Overlapping job timelines creating impossible total durations
- Mismatched seniority signals (e.g. 10 years experience, entry-level roles only)

#### 2. Fast Pre-filter (`main.py`)
A deterministic keyword heuristic that downsizes the pool from 100k → ~3,000 by eliminating non-technical profiles (HR, Sales, Marketing, etc.) before the expensive embedding step.

#### 3. AI Semantic Embedding (`embedding_engine.py`)
Loads `all-MiniLM-L6-v2` from a pre-downloaded local directory and encodes each candidate against **three distinct vectors** derived from the Job Description:
- **Core ML skills vector** — primary technical requirements
- **Infrastructure vector** — tooling, cloud, DevOps requirements
- **Nice-to-haves vector** — bonus qualifications

Multi-vector matching prevents candidates who are strong in one area from drowning out those with broader coverage.

#### 4. Dynamic Score Fusion (`scorer.py`)
Combines three signal sources into a final composite score:

| Signal | Weight | Purpose |
|--------|--------|---------|
| Semantic similarity | 50% | AI-based match quality |
| Explicit JD skill match | 30% | Penalizes buzzword stuffing |
| Behavioral signals | 20% | Response rate, GitHub activity, notice period |

#### 5. Reasoning Generator (`reasoning_generator.py`)
Generates a 2-sentence rationale for each top candidate based on **actual extracted data points** — specific skills matched, exact notice period, GitHub activity score — not templated filler text.

---

## Tech Stack

- **Language:** Python 3.10+
- **Embeddings:** `sentence-transformers` with `all-MiniLM-L6-v2` (90MB, local)
- **Numerics:** `numpy`
- **Data format:** Streaming JSONL (RAM-efficient for 100k candidates)
- **Output:** CSV (`submission.csv`)
- **Execution:** CPU-only, offline, `TRANSFORMERS_OFFLINE=1`

---

## Prerequisites

- Python 3.10 or higher
- pip
- ~500MB disk space (for model weights + data)
- 16GB RAM (as per hackathon constraints)
- **No GPU required**
- **No internet required at inference time** (only for initial model download)

---

## Getting Started

### 1. Clone the Repository

```bash
git clone https://github.com/ronaksarda/candidate-ranker.git
cd candidate-ranker
```

### 2. Install Dependencies

```bash
pip install -r requirements.txt
```

This installs:
```
sentence-transformers>=2.2.0
numpy>=1.24.0
nbformat>=5.9.0
```

### 3. Pre-download the Model

This step requires internet. Run it **once** before going offline:

```bash
python download_model.py
```

This fetches the `all-MiniLM-L6-v2` model weights (~90MB) from HuggingFace and saves them to `local_model/`. Per hackathon spec Section 10.3, pre-computation is allowed before the offline ranking stage.

### 4. Run the Ranking Pipeline

```bash
python main.py --candidates ./candidates.jsonl --out ./submission.csv
```

Expected output:
```
[1/5] Loading candidates...       100,000 loaded in 12.3s
[2/5] Plausibility filter...      83,241 passed
[3/5] Fast pre-filter...          2,987 technical candidates
[4/5] Semantic embedding...       Encoded in 47.2s (CPU)
[5/5] Score fusion + ranking...   Done
Output: submission.csv (100 candidates)
```

### 5. Validate Submission

```bash
python validate_submission.py submission.csv
```

---

## Pipeline Stages

### Plausibility Filter

The filter catches honeypot candidates using rule-based checks:

```python
# Example: impossible skill/experience combination
if candidate.skill_level == "expert" and candidate.months_experience == 0:
    discard(candidate)

# Example: overlapping job timelines
if has_overlapping_roles(candidate.work_history):
    discard(candidate)
```

### Embedding Strategy

Three separate JD vectors are computed to avoid single-point scoring:

```python
jd_vectors = {
    "core_ml":  embed(jd.core_requirements),
    "infra":    embed(jd.infrastructure_requirements),
    "nice":     embed(jd.nice_to_haves)
}

candidate_score = (
    0.5 * cosine_sim(candidate_vec, jd_vectors["core_ml"]) +
    0.3 * cosine_sim(candidate_vec, jd_vectors["infra"]) +
    0.2 * cosine_sim(candidate_vec, jd_vectors["nice"])
)
```

### Score Fusion

```python
final_score = (
    0.50 * semantic_score +
    0.30 * explicit_skill_match_score +
    0.20 * behavioral_score  # response_rate, github_activity, notice_period
)
```

---

## Scoring Formula

| Component | Weight | How Computed |
|-----------|--------|-------------|
| Semantic similarity | 50% | Cosine similarity between candidate embedding and 3 JD vectors |
| Explicit skill match | 30% | Keyword overlap between candidate skills and JD requirements |
| Behavioral signals | 20% | Normalized composite of response rate + GitHub activity + notice period |

The explicit skill match at 30% deliberately **penalizes buzzword stuffing** — candidates who list many skills but have low semantic similarity to the actual JD get a lower combined score than candidates with genuine alignment.

---

## Repository Structure

```
candidate-ranker/
├── main.py                    # Pipeline orchestrator — entry point
├── plausibility_filter.py     # Honeypot detection logic
├── embedding_engine.py        # SentenceTransformer wrapper + batch encoding
├── scorer.py                  # Score fusion: semantic + skill + behavioral
├── reasoning_generator.py     # 2-sentence rationale generator
├── profile_builder.py         # Candidate profile construction from raw JSONL
├── data_loader.py             # Streaming JSONL parser (RAM-efficient)
├── download_model.py          # One-time model weight downloader
├── validate_submission.py     # Submission format validator
├── requirements.txt           # Python dependencies
├── sample_submission.csv      # Example output format
├── submission_metadata.yaml   # Team methodology + hardware declaration
├── local_model/               # Downloaded HuggingFace model weights (git-ignored)
└── .gitignore
```

---

## Constraints & Design Decisions

This system was built under strict hackathon constraints:

| Constraint | Solution |
|-----------|---------|
| 5 minute time limit | Fast pre-filter cuts 100k → 3k before embedding |
| CPU-only execution | `all-MiniLM-L6-v2` is fast enough on CPU for 3k candidates |
| 16GB RAM limit | Streaming JSONL parser — never loads full dataset into memory |
| Offline execution | Model weights pre-downloaded to `local_model/`, `TRANSFORMERS_OFFLINE=1` |
| Honeypot candidates | Plausibility filter catches impossible profiles before scoring |

### Why Not Use an LLM?

LLMs are slow, expensive, and inconsistent for structured ranking tasks. A 100k candidate set evaluated by GPT-4 would cost hundreds of dollars and take hours. Semantic embeddings + deterministic scoring gives reproducible, explainable results in minutes on commodity hardware.

---

## Built for Hack2Skill × Redrob AI Hackathon
