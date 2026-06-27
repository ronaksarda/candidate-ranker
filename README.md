# Team Clover - Candidate Ranking System 🍀

A high-performance, strictly offline, Two-Stage Neural Retrieval pipeline designed to rank 100,000 synthetic software engineering candidates in under 3 minutes on a standard CPU. 

This system was explicitly engineered to defeat keyword stuffing, time-traveling honeypots, and pure-academic wrappers, identifying the true "scrappy product-engineers" who have actually shipped production code.

## 🚀 Quick Start (Running Offline)

The system is designed to run completely offline, satisfying strict privacy and hackathon execution constraints.

### 1. Install Dependencies
```bash
pip install -r requirements.txt
```

### 2. Download the Models (Run Once with Internet)
Before going offline, cache the local neural networks (`all-MiniLM-L6-v2` and `ms-marco-MiniLM-L-6-v2`).
```bash
python download_model.py
```
*Note: This saves the models to the `./local_model/` directory.*

### 3. Run the Pipeline (Offline)
You can now disconnect from the internet. The pipeline is hardcoded to block all HuggingFace network requests (`TRANSFORMERS_OFFLINE="1"`).
```bash
python main.py --candidates "path/to/candidates.jsonl"
```
The final Top 100 candidates will be written to `team_TeamClover.csv` in ~2.5 minutes.

---

## 🧠 System Architecture (Two-Stage Neural Retrieval)

Unlike traditional ATS systems that rely on keyword density or slow, hallucination-prone LLMs, this system utilizes a highly optimized 3-step funnel:

### Stage 1: Plausibility & Keyword Filter (100k → 3.5k)
*   **The Plausibility Filter (`plausibility_filter.py`)**: Runs chronological math checks to instantly destroy honeypots. If a candidate claims 4 years of experience in a 2-year-old framework (like Llama-2), or claims to be an "Expert" with 0 months of duration, they are permanently deleted.
*   **The Fast Scan**: Drops candidates lacking basic ML terminology to save expensive AI compute.

### Stage 2: Bi-Encoder Semantic Extraction (3.5k → 300)
*   **The Model**: A local PyTorch instance of `all-MiniLM-L6-v2`.
*   **The Logic (`scorer.py`)**: The Bi-Encoder calculates the dense vector similarity between the candidate's career and the JD. This base score is then multiplied by **Persona Gates**. We mathematically penalize job-hoppers (tenure < 18m), hands-off architects, and consulting-only careers, while boosting candidates in the exact 5-9 year experience band.

### Stage 3: Cross-Encoder Re-Ranking (300 → 100)
*   **The Model**: A local instance of `cross-encoder/ms-marco-MiniLM-L-6-v2`.
*   **The Logic**: The Top 300 candidates are passed to the Cross-Encoder, which simultaneously analyzes the JD and the candidate's career history word-by-word. This cross-attention mechanism provides State-of-the-Art contextual precision, finalizing the exact Top 100 ranking.

---

## 🛡️ Differentiators & Defense

### 1. Preventing Hallucinations
We do not use Generative AI (like ChatGPT) to summarize candidates. The justifications in the output CSV are generated deterministically by `reasoning_generator.py`. The engine uses strict Regex to extract mathematically verified quotes (e.g., *"reduced latency by 60%"*) directly from the candidate's raw text. **If they didn't write it, the system cannot output it.**

### 2. Defeating the "LangChain Wrapper"
The JD explicitly disqualifies developers whose only AI experience is wrapping APIs in the last 12 months. Our system mathematically slashes scores for candidates who list "LangChain" but lack foundational ML skills (PyTorch, Scikit-learn, etc.), ensuring only true engineers rise to the top.

### 3. The "Vibe" Check (Behavioral Reality)
A perfect resume is useless if the candidate won't reply. The final score directly integrates live behavioral signals. "Ghosts" (candidates with terrible recruiter response rates, high notice periods, or inactive logins) are aggressively downranked to save recruiter time.

---

## 🛠️ File Structure

```text
Candidate_Ranking_Submission/
├── main.py                     # Orchestrator & Two-Stage Pipeline
├── scorer.py                   # Business logic, multipliers, and persona gates
├── plausibility_filter.py      # Hard rules and honeypot detection
├── embedding_engine.py         # PyTorch inference for Bi-Encoder vectors
├── reasoning_generator.py      # Regex-driven deterministic justification writer
├── download_model.py           # Pre-caches models for offline execution
├── local_model/                # Cached weights for offline inference
└── README.md                   # Documentation
```
