import csv
import json
import os

csv_path = "submission.csv"
jsonl_path = r"C:\Users\rocky\OneDrive\Documents\Hackathon_RedrobAI\[PUB] India_runs_data_and_ai_challenge\India_runs_data_and_ai_challenge\candidates.jsonl"
output_path = "top_100_candidates.json"

def main():
    if not os.path.exists(csv_path):
        print(f"Error: {csv_path} not found.")
        return
        
    if not os.path.exists(jsonl_path):
        print(f"Error: {jsonl_path} not found.")
        return

    # Extract top 100 IDs from CSV
    top_ids = set()
    top_list = []
    with open(csv_path, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for i, row in enumerate(reader):
            if i >= 100:
                break
            top_ids.add(row['candidate_id'])
            top_list.append(row['candidate_id'])

    # Extract full JSON for those IDs
    extracted = {}
    with open(jsonl_path, 'r', encoding='utf-8') as f:
        for line in f:
            data = json.loads(line)
            cid = str(data.get('candidate_id'))
            if cid in top_ids:
                extracted[cid] = data
                if len(extracted) == len(top_ids):
                    break # Found all we need

    # Order them as they appeared in CSV
    final_output = []
    for cid in top_list:
        if cid in extracted:
            final_output.append(extracted[cid])

    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(final_output, f, indent=4)

    print(f"Successfully extracted {len(final_output)} candidates to {output_path}")

if __name__ == "__main__":
    main()
