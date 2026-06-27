import pandas as pd
import json
from reasoning_generator import generate_reasoning
from data_loader import load_candidates_stream
from profile_builder import extract_evidence_sentence

print("Loading existing CSV...")
df = pd.read_csv("team_TeamClover.csv")

top100_map = {}
for idx, row in df.iterrows():
    top100_map[row["candidate_id"]] = (row["rank"], row["score"])

print("Scanning candidates.jsonl for top 100 profiles...")
candidates = {}
candidates_file = r"C:\Users\rocky\OneDrive\Documents\Hackathon_RedrobAI\[PUB] India_runs_data_and_ai_challenge\India_runs_data_and_ai_challenge\candidates.jsonl"
for cand in load_candidates_stream(candidates_file):
    cid = cand["candidate_id"]
    if cid in top100_map:
        candidates[cid] = cand
        if len(candidates) == len(top100_map):
            break

print("Regenerating differentiated reasoning texts...")
new_rows = []
seen_evidence = set()
for cid, cand in candidates.items():
    rank, score = top100_map[cid]
    
    # Extract evidence pair
    evidence, company = extract_evidence_sentence(cand)
    evidence_pair = None
    if evidence and evidence not in seen_evidence:
        seen_evidence.add(evidence)
        evidence_pair = (evidence, company)
            
    # Regenerate reasoning with latest reasoning_generator.py logic
    new_reasoning = generate_reasoning(cand, rank, score, semantic_score=score, signal_score=0, evidence_pair=evidence_pair)
    new_rows.append({"candidate_id": cid, "rank": rank, "score": score, "reasoning": new_reasoning})

new_rows.sort(key=lambda x: x["rank"])

new_df = pd.DataFrame(new_rows)
new_df.to_csv("team_TeamClover.csv", index=False)
print("Converting to XLSX...")
new_df.to_excel("team_TeamClover.xlsx", index=False)
print("All done!")
