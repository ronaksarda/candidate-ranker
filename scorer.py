import datetime
from plausibility_filter import is_honeypot

# ============================================================================
# Title relevance — hard gate against irrelevant job titles
# ============================================================================
STRONG_TITLE_MATCHES = {
    "machine learning", "ml engineer", "ml ", "deep learning", "nlp",
    "natural language", "ai engineer", "ai research", "search engineer",
    "ranking engineer", "recommendation", "data scientist", "applied ml",
    "research engineer", "research scientist", "applied scientist",
}

WEAK_TITLE_MATCHES = {
    "software engineer", "backend engineer", "data engineer", "platform engineer",
    "devops", "full stack", "python developer", "infrastructure",
}

IRRELEVANT_TITLES = {
    "hr ", "human resource", "recruiter", "talent acquisition",
    "accountant", "finance", "sales", "marketing", "business development",
    "civil", "mechanical", "electrical engineer", "procurement",
    "legal", "compliance", "admin", "office manager", "receptionist",
    "content writer", "graphic design", "ui/ux", "teacher", "professor",
    "computer vision", "cv engineer", "robotics", "speech", "vision"
}

# ============================================================================
# JD skill matching — explicit overlap with the job description
# These are the skills from the ACTUAL job_description.md
# ============================================================================
JD_CORE_SKILLS = {
    "sentence-transformers", "sentence transformers", "faiss", "pinecone",
    "weaviate", "qdrant", "milvus", "opensearch", "elasticsearch",
    "embeddings", "embedding", "vector search", "vector database",
    "rag", "retrieval augmented", "retrieval-augmented",
    "ranking", "ndcg", "mrr", "learning to rank", "learning-to-rank",
    "information retrieval",
}

JD_STRONG_SKILLS = {
    "pytorch", "tensorflow", "transformers", "bert", "llm", "llms",
    "hugging face", "huggingface", "lora", "qlora", "peft",
    "nlp", "natural language processing", "xgboost",
    "deep learning", "neural network", "machine learning",
    "scikit-learn", "sklearn",
}

JD_NICE_SKILLS = {
    "python", "docker", "kubernetes", "aws", "mlops", "ci/cd",
    "distributed systems", "microservices", "langchain", "llamaindex",
}


def calculate_title_multiplier(candidate):
    """Returns a multiplier based on how relevant the job title is to the JD."""
    profile = candidate.get("profile", {})
    title = profile.get("current_title", "").lower()

    for t in IRRELEVANT_TITLES:
        if t in title:
            return 0.10

    for t in STRONG_TITLE_MATCHES:
        if t in title:
            return 1.0

    for t in WEAK_TITLE_MATCHES:
        if t in title:
            return 0.70

    return 0.45


def calculate_skill_match_score(candidate):
    """
    Calculates explicit skill overlap with the JD requirements.
    Returns a score from 0.0 to 1.0.
    """
    skills = candidate.get("skills", [])
    skill_names = set()
    for s in skills:
        name = s.get("name", "").lower()
        skill_names.add(name)
        # Also check career descriptions for skill mentions
    
    # Also scan career history descriptions for skill evidence
    career_text = ""
    for job in candidate.get("career_history", []):
        career_text += " " + job.get("description", "").lower()
    
    core_hits = 0
    strong_hits = 0
    nice_hits = 0

    for sname in skill_names:
        for jd_skill in JD_CORE_SKILLS:
            if jd_skill in sname or sname in jd_skill:
                core_hits += 1
                break
        for jd_skill in JD_STRONG_SKILLS:
            if jd_skill in sname or sname in jd_skill:
                strong_hits += 1
                break
        for jd_skill in JD_NICE_SKILLS:
            if jd_skill in sname or sname in jd_skill:
                nice_hits += 1
                break

    # Also check career descriptions for core skill evidence
    for jd_skill in JD_CORE_SKILLS:
        if jd_skill in career_text:
            core_hits += 0.5

    core_score = min(1.0, core_hits / 3)
    strong_score = min(1.0, strong_hits / 3)
    nice_score = min(1.0, nice_hits / 2)

    return (core_score * 0.50) + (strong_score * 0.35) + (nice_score * 0.15)


def calculate_signal_score(candidate):
    """Calculates the behavioral signal score (max 1.0)."""
    score = 0.0
    signals = candidate.get("redrob_signals", {})
    profile = candidate.get("profile", {})

    last_active_str = signals.get("last_active_date")
    resp_rate = signals.get("recruiter_response_rate", 0.0)
    interview_rate = signals.get("interview_completion_rate", 0.0)

    if last_active_str:
        try:
            last_active = datetime.datetime.strptime(last_active_str, "%Y-%m-%d")
            days_inactive = max(0, (datetime.datetime(2026, 6, 16) - last_active).days)
            if days_inactive <= 30 and resp_rate > 0.5:
                score += 0.33
            elif days_inactive <= 90 and resp_rate > 0.3:
                score += 0.15
        except ValueError:
            pass

    if interview_rate > 0.8:
        score += 0.17

    notice_days = signals.get("notice_period_days", 90)
    if notice_days <= 30:
        score += 0.16

    loc = profile.get("location", "").lower()
    will_relocate = signals.get("willing_to_relocate", False)
    is_compatible = any(city in loc for city in ["pune", "noida", "delhi", "mumbai", "hyderabad"])
    if is_compatible or will_relocate:
        score += 0.17
    else:
        score *= 0.1 # Disqualifying penalty

    gh_score = signals.get("github_activity_score", -1)
    if gh_score > 50:
        score += 0.17

    # If not open to work, massive penalty to signals
    if not signals.get("open_to_work_flag", True):
        score *= 0.1

    return min(1.0, score)


def score_candidate(candidate, semantic_score):
    """
    Final scoring: fuses semantic similarity, explicit skill match,
    title relevance, and behavioral signals.

    Weights:
      50% semantic similarity (AI contextual matching)
      30% explicit skill match (deterministic, reproducible)
      20% behavioral signals (engagement, availability)
    """
    if is_honeypot(candidate):
        return -100.0, -100.0, 0.0

    skill_match = calculate_skill_match_score(candidate)
    signal_score = calculate_signal_score(candidate)
    title_mult = calculate_title_multiplier(candidate)

    raw_score = (0.50 * semantic_score) + (0.30 * skill_match) + (0.20 * signal_score)

    # Title gate
    final_score = raw_score * title_mult

    # Heavy penalty for dead profiles
    signals = candidate.get("redrob_signals", {})
    last_active_str = signals.get("last_active_date")
    resp_rate = signals.get("recruiter_response_rate", 0.0)

    days_inactive = 180
    if last_active_str:
        try:
            last_active = datetime.datetime.strptime(last_active_str, "%Y-%m-%d")
            days_inactive = max(0, (datetime.datetime(2026, 6, 16) - last_active).days)
        except ValueError:
            days_inactive = 180

    if days_inactive > 180 or resp_rate < 0.1:
        final_score *= 0.5

    return final_score, semantic_score, signal_score
