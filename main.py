import sys
import os
import time
import argparse
import csv
from data_loader import load_candidates_stream
from plausibility_filter import is_honeypot, get_penalty_reasons
from profile_builder import build_candidate_text
from scorer import score_candidate
from reasoning_generator import generate_reasoning

# Disable all network access to enforce strict offline execution
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
    "ndcg": 5, "mrr": 5, "map": 5,
    "a/b test": 4, "evaluation framework": 4, "hybrid search": 4, "bge": 4,
}

CORE_KEYWORDS = [
    "embedding", "vector", "faiss", "rag", "retrieval", "ndcg", "mrr", 
    "transformer", "bert", "llm", "sentence-transformers", "pinecone", 
    "weaviate", "qdrant", "milvus", "opensearch",
    "nearest neighbour", "ann index", "approximate nearest", "dense retrieval",
    "semantic search", "bi-encoder", "cross-encoder", "reranker", "nmslib", "scann"
]

SHORTLIST_SIZE = 3500


def cheap_keyword_score(text_lower):
    """Fast keyword-weighted score - no AI model involved."""
    score = 0
    for keyword, weight in JD_KEYWORDS.items():
        if keyword in text_lower:
            score += weight
    return score


def main():
    parser = argparse.ArgumentParser(description="Redrob AI Candidate Ranking System")
    parser.add_argument("--candidates", type=str, default="candidates.jsonl", help="Path to candidates.jsonl")
    parser.add_argument("--out", type=str, default="team_TeamClover.csv", help="Output CSV path")
    parser.add_argument("--audit-honeypots", action="store_true", help="Audit honeypots and write to honeypot_audit.csv")
    parser.add_argument("--debug-stage1", action="store_true", help="Write stage1_debug.csv")
    args = parser.parse_args()

    start_time = time.time()

    if args.audit_honeypots:
        print("Auditing honeypots...", flush=True)
        from collections import Counter
        reason_counts = Counter()
        with open("honeypot_audit.csv", "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(["candidate_id", "reason_code"])
            for candidate in load_candidates_stream(args.candidates):
                is_hp, reason = is_honeypot(candidate)
                if is_hp:
                    reason_counts[reason] += 1
                    writer.writerow([candidate.get("candidate_id"), reason])

        print("Honeypot Audit Results:", flush=True)
        for reason, count in reason_counts.most_common():
            print(f"  {reason}: {count}")
        return

    # ---- Stage 1: Cheap keyword scan on ALL 100k candidates ----
    print("Stage 1: Fast keyword scan on all candidates...", flush=True)
    shortlist = []
    total = 0
    honeypots = 0

    for candidate in load_candidates_stream(args.candidates):
        total += 1
        if total % 20000 == 0:
            print(f"  ... scanned {total}", flush=True)

        is_hp, reason = is_honeypot(candidate)
        if is_hp:
            honeypots += 1
            continue

        text_profile = build_candidate_text(candidate)
        text_lower = text_profile.lower()
        kscore = cheap_keyword_score(text_lower)

        if kscore > 0:
            has_core = any(ck in text_lower for ck in CORE_KEYWORDS)

            # Discount keyword-stuffers: if core keywords appear in skills but
            # not in career descriptions, halve the keyword score
            career_desc_text = " ".join(
                j.get("description", "").lower() for j in candidate.get("career_history", [])
            )
            core_in_career = any(ck in career_desc_text for ck in CORE_KEYWORDS)
            if has_core and not core_in_career:
                kscore = kscore // 2

            shortlist.append((kscore, candidate, text_profile[:600], has_core))

    print(f"Stage 1 done: {total} scanned, {honeypots} honeypots, {len(shortlist)} have ML keywords", flush=True)

    shortlist.sort(key=lambda x: x[0], reverse=True)

    # Two-bucket shortlist
    bucket_1_size = int(SHORTLIST_SIZE * 0.8)
    bucket_1 = shortlist[:bucket_1_size]

    bucket_2_size = SHORTLIST_SIZE - bucket_1_size
    bucket_2 = []
    bucket_2_ids = set()

    for item in shortlist[bucket_1_size:]:
        if item[3]:
            bucket_2.append(item)
            bucket_2_ids.add(item[1]["candidate_id"])
            if len(bucket_2) == bucket_2_size:
                break

    if len(bucket_2) < bucket_2_size:
        needed = bucket_2_size - len(bucket_2)
        remaining_bucket = [
            x for x in shortlist[bucket_1_size:]
            if x[1]["candidate_id"] not in bucket_2_ids
        ]
        bucket_2.extend(remaining_bucket[:needed])

    final_shortlist = bucket_1 + bucket_2

    if args.debug_stage1:
        with open("stage1_debug.csv", "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(["candidate_id", "kscore", "has_core_skill_keyword", "in_shortlist"])
            final_ids = {x[1]["candidate_id"] for x in final_shortlist}
            for item in shortlist:
                writer.writerow([item[1]["candidate_id"], item[0], item[3], item[1]["candidate_id"] in final_ids])

    shortlist = final_shortlist
    print(f"Shortlisted top {len(shortlist)} for AI embedding", flush=True)

    stage1_time = time.time()
    print(f"Stage 1 took {stage1_time - start_time:.1f}s", flush=True)

    # ---- Stage 2: AI embedding on shortlisted candidates only ----
    print("Stage 2: Loading AI model...", flush=True)
    from embedding_engine import EmbeddingEngine
    engine = EmbeddingEngine()
    print("Model loaded. Encoding shortlisted candidates...", flush=True)

    texts = [item[2] for item in shortlist]
    candidates = [item[1] for item in shortlist]

    batch_size = 1024
    all_scores = []
    for batch_start in range(0, len(texts), batch_size):
        batch_end = min(batch_start + batch_size, len(texts))
        batch_texts = texts[batch_start:batch_end]
        batch_cands = candidates[batch_start:batch_end]

        embeddings = engine.batch_encode(batch_texts, batch_size=batch_size)
        semantic_scores = engine.compute_similarity(embeddings)

        for i, c in enumerate(batch_cands):
            pen = get_penalty_reasons(c)
            final_score, sem_s, sig_s, reason = score_candidate(c, semantic_scores[i], penalty_reasons=pen)
            all_scores.append({
                "candidate_id": c["candidate_id"],
                "score": final_score,
                "semantic": sem_s,
                "signal": sig_s,
                "candidate": c
            })

        print(f"  ... embedded {batch_end}/{len(texts)}", flush=True)

    # Sort descending by score, ascending by candidate_id for tiebreak (submission spec)
    all_scores.sort(key=lambda x: (-x["score"], x["candidate_id"]))
    
    # ---- Stage 3: Cross-Encoder Re-ranking on Top 300 ----
    print("Stage 3: Cross-Encoder Re-ranking...", flush=True)
    top_300 = all_scores[:300]
    local_cross_path = os.path.join(os.path.dirname(__file__), "local_model", "ms-marco-MiniLM-L-6-v2")

    if not os.path.isdir(local_cross_path):
        print(f"  WARN: Cross-Encoder model not found at {local_cross_path}.", flush=True)
        print("  Run 'python download_model.py' first. Falling back to Bi-Encoder ranking.", flush=True)
        top_100 = all_scores[:100]
    else:
        try:
            from sentence_transformers import CrossEncoder
            cross_encoder = CrossEncoder(local_cross_path, max_length=512)

            query = (
                "Senior AI Engineer Founding Team Production Embeddings Vector Database "
                "Python Evaluation Shipped Code A/B Test"
            )
            cross_inp = []
            for item in top_300:
                c = item["candidate"]
                career_text = " ".join([j.get("description", "") for j in c.get("career_history", [])])
                doc = c.get("profile", {}).get("summary", "") + " " + career_text
                cross_inp.append([query, doc[:1500]])

            print("  Running Cross-Encoder prediction...", flush=True)
            cross_scores = cross_encoder.predict(cross_inp)
            
            min_cross = float(min(cross_scores))
            max_cross = float(max(cross_scores))
            range_cross = max_cross - min_cross if max_cross > min_cross else 1.0

            for idx, item in enumerate(top_300):
                norm_cross = (cross_scores[idx] - min_cross) / range_cross
                item["score"] = item["score"] * 0.7 + norm_cross * 0.3

            top_300.sort(key=lambda x: (-x["score"], x["candidate_id"]))
            top_100 = top_300[:100]
            print("  Stage 3 complete.", flush=True)
        except Exception as e:
            print(f"  ERROR in Stage 3: {e}", flush=True)
            print("  Falling back to Bi-Encoder ranking.", flush=True)
            top_100 = all_scores[:100]

    # Generate CSV with deduplicated evidence sentences
    print(f"Writing top 100 to {args.out}...", flush=True)
    from profile_builder import extract_evidence_sentence
    seen_evidence = set()

    with open(args.out, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow(["candidate_id", "rank", "score", "reasoning"])

        for rank, item in enumerate(top_100, start=1):
            evidence, company = extract_evidence_sentence(item["candidate"])
            evidence_pair = None
            if evidence and evidence not in seen_evidence:
                seen_evidence.add(evidence)
                evidence_pair = (evidence, company)

            reasoning = generate_reasoning(
                item["candidate"], rank, item["score"], item["semantic"], item["signal"],
                evidence_pair=evidence_pair
            )
            writer.writerow([item["candidate_id"], rank, float(item["score"]), reasoning])

    end_time = time.time()
    print(f"Finished in {end_time - start_time:.1f}s (Stage 1: {stage1_time - start_time:.1f}s, Stage 2: {end_time - stage1_time:.1f}s)", flush=True)


if __name__ == "__main__":
    main()
