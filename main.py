import sys
import os
import time
import argparse
import csv
from data_loader import load_candidates_stream
from plausibility_filter import is_honeypot
from profile_builder import build_candidate_text
from embedding_engine import EmbeddingEngine
from scorer import score_candidate
from reasoning_generator import generate_reasoning

# Disable all network access from sentence-transformers
os.environ["TRANSFORMERS_OFFLINE"] = "1"
os.environ["HF_HUB_OFFLINE"] = "1"

# ML-relevant keywords with weights for cheap pre-scoring
JD_KEYWORDS = {
    "machine learning": 5, "deep learning": 5, "nlp": 4, "natural language": 4,
    "pytorch": 5, "tensorflow": 4, "scikit": 3, "xgboost": 3,
    "embedding": 5, "vector": 4, "faiss": 5, "rag": 5,
    "retrieval": 4, "ranking": 4, "recommendation": 3,
    "neural": 4, "transformer": 5, "bert": 5, "llm": 4,
    "fine-tun": 4, "lora": 5, "peft": 5, "qlora": 5,
    "hugging": 3, "search engine": 3, "information retrieval": 4,
    "data scien": 3, "computer vision": 3,
    "pinecone": 5, "weaviate": 5, "qdrant": 5, "milvus": 5,
    "opensearch": 4, "elasticsearch": 3,
    "sentence-transformers": 5, "cosine similarity": 4,
    "python": 2, "aws": 1, "docker": 1, "mlops": 3,
    "ndcg": 5, "mrr": 5, "map": 3,
}

SHORTLIST_SIZE = 3000


def cheap_keyword_score(text_lower):
    """Fast keyword-weighted score — no AI model involved."""
    score = 0
    for keyword, weight in JD_KEYWORDS.items():
        if keyword in text_lower:
            score += weight
    return score


def main():
    parser = argparse.ArgumentParser(description="Redrob AI Candidate Ranking System")
    parser.add_argument("--candidates", type=str, default="candidates.jsonl", help="Path to candidates.jsonl")
    parser.add_argument("--out", type=str, default="team_TeamClover.csv", help="Output CSV path")
    args = parser.parse_args()

    start_time = time.time()

    # ---- Stage 1: Cheap keyword scan on ALL 100k candidates ----
    print("Stage 1: Fast keyword scan on all candidates...", flush=True)
    shortlist = []
    total = 0
    honeypots = 0

    for candidate in load_candidates_stream(args.candidates):
        total += 1
        if total % 20000 == 0:
            print(f"  ... scanned {total}", flush=True)

        if is_honeypot(candidate):
            honeypots += 1
            continue

        text_profile = build_candidate_text(candidate)
        text_lower = text_profile.lower()
        kscore = cheap_keyword_score(text_lower)

        if kscore > 0:
            shortlist.append((kscore, candidate, text_profile[:256]))

    print(f"Stage 1 done: {total} scanned, {honeypots} honeypots, {len(shortlist)} have ML keywords", flush=True)

    shortlist.sort(key=lambda x: x[0], reverse=True)
    shortlist = shortlist[:SHORTLIST_SIZE]
    print(f"Shortlisted top {len(shortlist)} for AI embedding", flush=True)

    stage1_time = time.time()
    print(f"Stage 1 took {stage1_time - start_time:.1f}s", flush=True)

    # ---- Stage 2: AI embedding on shortlisted candidates only ----
    print("Stage 2: Loading AI model...", flush=True)
    engine = EmbeddingEngine()
    print("Model loaded. Encoding shortlisted candidates...", flush=True)

    texts = [item[2] for item in shortlist]
    candidates = [item[1] for item in shortlist]

    batch_size = 512
    all_scores = []
    for batch_start in range(0, len(texts), batch_size):
        batch_end = min(batch_start + batch_size, len(texts))
        batch_texts = texts[batch_start:batch_end]
        batch_cands = candidates[batch_start:batch_end]

        embeddings = engine.batch_encode(batch_texts)
        semantic_scores = engine.compute_similarity(embeddings)

        for i, c in enumerate(batch_cands):
            final_score, sem_s, sig_s = score_candidate(c, semantic_scores[i])
            all_scores.append({
                "candidate_id": c["candidate_id"],
                "score": final_score,
                "semantic": sem_s,
                "signal": sig_s,
                "candidate": c
            })

        print(f"  ... embedded {batch_end}/{len(texts)}", flush=True)

    # Sort descending by score
    all_scores.sort(key=lambda x: x["score"], reverse=True)
    top_100 = all_scores[:100]

    # Generate CSV
    print(f"Writing top 100 to {args.out}...", flush=True)
    with open(args.out, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow(["candidate_id", "rank", "score", "reasoning"])

        for rank, item in enumerate(top_100, start=1):
            reasoning = generate_reasoning(
                item["candidate"], rank, item["score"], item["semantic"], item["signal"]
            )
            writer.writerow([item["candidate_id"], rank, float(item["score"]), reasoning])

    end_time = time.time()
    print(f"Finished in {end_time - start_time:.1f}s (Stage 1: {stage1_time - start_time:.1f}s, Stage 2: {end_time - stage1_time:.1f}s)", flush=True)

if __name__ == "__main__":
    main()
