import json

filepath = r"c:\Users\rocky\OneDrive\Documents\Hackathon_RedrobAI\[PUB] India_runs_data_and_ai_challenge\India_runs_data_and_ai_challenge\candidates.jsonl"

count = 0
with open(filepath, 'r', encoding='utf-8') as f:
    for line in f:
        c = json.loads(line)
        for s in c.get('skills', []):
            name = s.get('name', '').lower()
            dur = s.get('duration_months', 0)
            if (name == 'qlora' and dur > 40) or (name == 'langchain' and dur > 60) or (name == 'chatgpt' and dur > 48):
                print(f"{c['candidate_id']} - {name}: {dur} months")
                count += 1
                break

print(f"Total candidates claiming impossible modern tech timelines: {count}")
