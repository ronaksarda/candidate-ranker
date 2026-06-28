# Intelligent Candidate Discovery & Ranking
**Redrob Hackathon - Team Clover**

An offline-first, highly optimized two-stage neural ranking architecture to evaluate 100,000 candidate profiles against a complex Job Description in under 3.5 minutes on CPU.

## Key Features
- **Plausibility & Fraud Detection:** Instantly drops honeypots, keyword-stuffers, and "time-traveling" resumes (e.g., claiming 4 years in a 2-year-old framework).
- **Two-Stage Neural Retrieval:** 
  - *Stage 1 (Retrieval):* Blazing fast deterministic keyword filtering to reduce 100k candidates to a 3.5k shortlist.
  - *Stage 2 (Scoring):* Local AI Bi-Encoder (`all-MiniLM-L6-v2`) computes dense vector similarity.
  - *Stage 3 (Re-ranking):* State-of-the-Art Cross-Encoder (`ms-marco-MiniLM-L-6-v2`) performs deep contextual evaluation on the Top 300.
- **Explainability:** Deterministic, regex-driven reasoning generator extracts mathematically verified quotes and metrics (e.g., *reduced p95 latency by 60%*) without LLM hallucinations.
- **Behavioral Signal Fusion:** Integrates recruiter response rates, GitHub activity, and notice periods to prioritize high-intent, reachable candidates.
- **Offline & Private:** Zero external API calls. Runs fully offline on standard CPU hardware.

## Tech Stack
- **Language**: Python 3.11
- **ML/AI Models**: PyTorch, HuggingFace Transformers (SentenceTransformers)
- **Data Processing**: Pandas, native JSON parsing, deterministic regex
- **Platform/Environment**: Windows 11 / Any standard CPU environment
- **Sandbox Environment**: Google Colab / Jupyter Notebooks

## Prerequisites
- Python 3.9+
- ~16GB RAM for optimal batch processing
- `candidates.jsonl` dataset in the appropriate directory

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
*(Dependencies primarily include `torch`, `sentence-transformers`, `pandas`, and `jupyter`)*

### 3. Download Offline Models
The system relies on heavily quantized, offline ML models. Run the download script to fetch them locally before disconnecting from the network:
```bash
python download_model.py
```

### 4. Run the Pipeline
To execute the end-to-end pipeline on the full dataset and generate the Top 100 ranked candidates CSV:
```bash
python main.py --candidates ./candidates.jsonl --out ./team_TeamClover.csv
```

### 5. Jupyter Sandbox (Test Environment)
To run the ranker on a smaller test sample (`test.jsonl`), use the generated notebook:
```bash
jupyter notebook submission.ipynb
```
Or view the hosted Colab sandbox linked in our submission metadata.

## Architecture

### Directory Structure
```
├── main.py                  # Orchestrator & Fast Pre-filter
├── plausibility_filter.py   # "Hard Rules" fraud and honeypot detection
├── embedding_engine.py      # Local PyTorch inference (Bi-Encoder)
├── scorer.py                # Vibe Engine (business logic, behavioral gates)
├── reasoning_generator.py   # Regex-driven hallucination-free report writer
├── download_model.py        # Utility to fetch models for offline use
├── generate_notebook.py     # Script to package the pipeline into an .ipynb
├── extract_top100.py        # Utility to generate final submission JSON/CSV
├── submission.ipynb         # Hosted Sandbox Notebook (Generated)
└── submission_metadata.yaml # Hackathon submission details
```

### End-to-End Workflow

1. **Ingestion & Plausibility Filter (100k → ~99.5k)**: `plausibility_filter.py` deletes honeypots and mathematically impossible timelines.
2. **Fast Keyword Pre-Filter (~99.5k → 3.5k)**: `main.py` performs a deterministic scan to drop candidates lacking basic ML terminology.
3. **Bi-Encoder Semantic Extraction**: `embedding_engine.py` encodes the 3,500 candidates into dense vectors and scores them.
4. **Business Logic Scoring (3.5k → 300)**: `scorer.py` fuses semantic scores with behavioral signals and persona gates (e.g., job-hopper penalties).
5. **Cross-Encoder Re-Ranking (Top 300 → Top 100)**: The `ms-marco-MiniLM-L-6-v2` cross-encoder scrutinizes exact contextual overlap.
6. **Reasoning Generation**: `reasoning_generator.py` extracts raw metrics directly from candidate descriptions to write a comprehensive, evidence-grounded justification.

## System Performance
- **Runtime:** ~205 seconds (3.4 minutes) on an 8-core CPU.
- **Accuracy:** Zero false-positives on keyword traps (LangChain wrappers, pure academics).
- **Scale:** Processes 100,000 JSON candidates without massive cloud compute costs.

---
*Built for the Redrob Hackathon: India Runs on Data and AI Challenge.*
