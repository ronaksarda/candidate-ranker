import json
import logging

logger = logging.getLogger(__name__)

def load_candidates_stream(filepath):
    """
    Generator that stream-loads candidates from the JSONL file.
    """
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            for line in f:
                if line.strip():
                    try:
                        candidate = json.loads(line)
                        yield candidate
                    except json.JSONDecodeError as e:
                        logger.error('Failed to decode line in candidates.jsonl', extra={"error": str(e)})
                        continue
    except FileNotFoundError:
        logger.error('candidates.jsonl not found', extra={"filepath": filepath})
        raise

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    count = 0
    import sys
    if len(sys.argv) > 1:
        filepath = sys.argv[1]
    else:
        filepath = 'candidates.jsonl'
        
    for _ in load_candidates_stream(filepath):
        count += 1
    print(f"Loaded {count} candidates.")
