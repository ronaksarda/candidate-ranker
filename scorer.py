import datetime
import re
import string

# is_valid_match has been moved down below JD_SKILLS_NORM definitions

SKILL_SYNONYMS = {
    "vector db": "vector database",
    "elastic": "elasticsearch",
    "knn": "vector search",
    "k nearest neighbor": "vector search",
    "k nearest neighbors": "vector search",
    "hf": "hugging face",
    "huggingface": "hugging face",
    "llms": "llm",
    "sklearn": "scikit learn",
    "scikitlearn": "scikit learn",
    "chatgpt": "gpt",
    "k8s": "kubernetes"
}

SYN_PATTERN = re.compile(r'\b(' + '|'.join(map(re.escape, SKILL_SYNONYMS.keys())) + r')\b')


def normalize_text(text: str) -> str:
    text = text.lower()
    text = text.translate(str.maketrans(string.punctuation, ' ' * len(string.punctuation)))
    text = ' '.join(text.split())
    return SYN_PATTERN.sub(lambda m: SKILL_SYNONYMS[m.group(1)], text)


TARGET_CITIES = {
    "pune", "noida", "delhi", "new delhi", "ncr", "mumbai", "hyderabad",
    "bengaluru", "bangalore", "gurgaon", "gurugram", "chennai", "kolkata"
}

# ============================================================================
# Title relevance - hard gate against irrelevant job titles
# ============================================================================
STRONG_TITLE_MATCHES = {
    "machine learning", "ml engineer", "ml ", "deep learning", "nlp",
    "natural language", "ai engineer", "ai research", "search engineer",
    "ranking engineer", "recommendation", "data scientist", "applied ml",
    "research engineer", "research scientist", "applied scientist",
}

SENIOR_TITLE_KEYWORDS = {
    "senior", "staff", "lead", "principal", "head",
}

JUNIOR_TITLE_KEYWORDS = {
    "junior", "intern", "trainee", "fresher", "associate",
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
    "computer vision", "cv engineer", "robotics", "speech"
}

# ============================================================================
# JD skill matching - explicit overlap with the job description
# ============================================================================
JD_CORE_SKILLS = {
    "sentence-transformers", "sentence transformers", "faiss", "pinecone",
    "weaviate", "qdrant", "milvus", "opensearch", "elasticsearch",
    "embeddings", "embedding", "vector search", "vector database",
    "rag", "retrieval augmented", "retrieval-augmented",
    "ranking", "ndcg", "mrr", "learning to rank", "learning-to-rank",
    "information retrieval",
    "map",
    "mean average precision",
    "a/b test",
    "a/b testing",
    "evaluation framework",
    "hybrid search",
    "hybrid retrieval",
    "bge",
    "openai embeddings",
}

JD_STRONG_SKILLS = {
    "pytorch", "tensorflow", "transformers", "bert", "llm", "llms",
    "hugging face", "huggingface", "lora", "qlora", "peft",
    "nlp", "natural language processing", "xgboost",
    "deep learning", "neural network", "machine learning",
    "scikit learn", "sklearn",
}

JD_NICE_SKILLS = {
    "python", "docker", "kubernetes", "k8s", "aws", "mlops", "ci/cd",
    "distributed systems", "microservices", "langchain", "llamaindex"
}

JD_CORE_SKILLS_NORM = {normalize_text(s) for s in JD_CORE_SKILLS}
JD_STRONG_SKILLS_NORM = {normalize_text(s) for s in JD_STRONG_SKILLS}
JD_NICE_SKILLS_NORM = {normalize_text(s) for s in JD_NICE_SKILLS}
JD_ALL_NORM = JD_CORE_SKILLS_NORM | JD_STRONG_SKILLS_NORM

JD_REGEX_PATTERNS = {}
for jd_set in [JD_CORE_SKILLS_NORM, JD_STRONG_SKILLS_NORM, JD_NICE_SKILLS_NORM]:
    for skill in jd_set:
        JD_REGEX_PATTERNS[skill] = re.compile(r'\b' + re.escape(skill) + r'\b')


def is_valid_match(jd_skill_norm, candidate_string_norm):
    if jd_skill_norm == candidate_string_norm:
        return True
    pattern = JD_REGEX_PATTERNS.get(jd_skill_norm)
    if pattern and pattern.search(candidate_string_norm):
        return True
    if candidate_string_norm and f" {candidate_string_norm} " in f" {jd_skill_norm} ":
        return True
    return False


def calculate_title_multiplier(candidate):
    """Returns a multiplier based on how relevant the job title is to the JD."""
    profile = candidate.get("profile", {})
    title = profile.get("current_title", "").lower()

    base_mult = 0.45
    for t in STRONG_TITLE_MATCHES:
        if t in title:
            base_mult = 1.0
            break

    if base_mult < 1.0:
        for t in WEAK_TITLE_MATCHES:
            if t in title:
                base_mult = 0.70
                break

    if base_mult < 1.0:
        for t in IRRELEVANT_TITLES:
            if t in title:
                base_mult = 0.10
                break

    # JD is for "Senior AI Engineer — Founding Team": penalize junior titles
    for jt in JUNIOR_TITLE_KEYWORDS:
        if jt in title:
            base_mult *= 0.70
            break

    # Bonus for senior-level titles (founding team needs senior judgment)
    for st in SENIOR_TITLE_KEYWORDS:
        if st in title:
            base_mult = min(1.0, base_mult * 1.10)
            break

    return base_mult


SERVICES_FIRMS = {
    "tcs", "tata consultancy services", "infosys", "wipro", "cognizant",
    "accenture", "capgemini", "hcl", "tech mahindra", "ibm", "l&t infotech",
    "lti", "mindtree", "mphasis", "syntel", "genpact", "genpact ai"
}


def calculate_services_penalty(candidate):
    """
    Graduated services penalty:
    100% services → 0.4x, >80% → 0.55x, >60% → 0.75x.
    """
    career_history = candidate.get("career_history", [])
    if not career_history:
        return 1.0

    total_months = 0
    service_months = 0

    for job in career_history:
        dur = job.get("duration_months", 0)
        total_months += dur
        company = job.get("company", "").lower()
        is_service = False
        for firm in SERVICES_FIRMS:
            if re.search(r'\b' + re.escape(firm) + r'\b', company):
                is_service = True
                break
        if is_service:
            service_months += dur

    if total_months == 0:
        return 1.0

    ratio = service_months / total_months
    if ratio >= 0.99:
        return 0.4
    if ratio > 0.80:
        return 0.55
    if ratio > 0.60:
        return 0.75
    return 1.0


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

    career_text = ""
    for job in candidate.get("career_history", []):
        career_text += " " + job.get("description", "").lower()

    norm_career_text = normalize_text(career_text)

    core_hits = 0
    strong_hits = 0
    nice_hits = 0

    for sname in skill_names:
        norm_sname = normalize_text(sname)
        for jd_skill in JD_CORE_SKILLS_NORM:
            if is_valid_match(jd_skill, norm_sname):
                core_hits += 1
                break
        for jd_skill in JD_STRONG_SKILLS_NORM:
            if is_valid_match(jd_skill, norm_sname):
                strong_hits += 1
                break
        for jd_skill in JD_NICE_SKILLS_NORM:
            if is_valid_match(jd_skill, norm_sname):
                nice_hits += 1
                break

    # Also check career descriptions for core skill evidence
    for jd_skill in JD_CORE_SKILLS_NORM:
        if is_valid_match(jd_skill, norm_career_text):
            core_hits += 0.5

    core_score = min(1.0, core_hits / 3)
    strong_score = min(1.0, strong_hits / 3)
    nice_score = min(1.0, nice_hits / 2)

    base_score = (core_score * 0.50) + (strong_score * 0.35) + (nice_score * 0.15)

    skill_assessments = candidate.get("redrob_signals", {}).get("skill_assessment_scores", {})
    assessment_bonus = 0.0
    for sname, sscore in skill_assessments.items():
        sname_lower = normalize_text(sname)
        is_relevant = False
        for jd_skill in JD_ALL_NORM:
            if is_valid_match(jd_skill, sname_lower):
                is_relevant = True
                break
        if is_relevant:
            if sscore > 85:
                assessment_bonus += 0.1
            elif sscore > 70:
                assessment_bonus += 0.05

    return min(1.0, base_score + min(0.2, assessment_bonus))


def calculate_signal_score(candidate):
    """Calculates the behavioral signal score (max 1.0)."""
    score = 0.0
    signals = candidate.get("redrob_signals", {})
    profile = candidate.get("profile", {})

    last_active_str = signals.get("last_active_date")
    resp_rate = signals.get("recruiter_response_rate", 0.0)
    interview_rate = signals.get("interview_completion_rate", 0.0)

    days_inactive = 180
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

    offer_acceptance = signals.get("offer_acceptance_rate", -1)
    if offer_acceptance > 0.7:
        score += 0.15
    elif 0 <= offer_acceptance < 0.3:
        score -= 0.20

    notice_days = signals.get("notice_period_days", 90)
    if notice_days <= 30:
        score += 0.16
    elif notice_days <= 60:
        score += 0.08
    elif notice_days <= 90:
        score += 0.03
    else:
        # aggressive penalty for 90+
        score -= 0.15

    loc = profile.get("location", "").lower()
    will_relocate = signals.get("willing_to_relocate", False)
    is_compatible = any(city in loc for city in TARGET_CITIES)

    if is_compatible or will_relocate:
        score += 0.17

    gh_score = signals.get("github_activity_score", -1)
    if gh_score > 60:
        score += 0.25
    elif gh_score > 40:
        score += 0.10

    saved_30d = signals.get("saved_by_recruiters_30d", 0)
    if saved_30d and saved_30d > 20:
        score += 0.08
    elif saved_30d and saved_30d > 5:
        score += 0.04

    apps_30d = signals.get("applications_submitted_30d", 0)
    if apps_30d and apps_30d > 3:
        score += 0.05

    avg_resp_time = signals.get("avg_response_time_hours", 999)
    if avg_resp_time and avg_resp_time < 6:
        score += 0.05
    elif avg_resp_time and avg_resp_time < 24:
        score += 0.02

    # P3: Soft availability gate for ghost candidates
    if days_inactive > 90 and resp_rate < 0.25:
        score *= 0.5

    return min(1.0, score)


def calculate_experience_band_multiplier(candidate):
    """JD says 5-9 years ideal. Apply a bell-curve-style multiplier."""
    yoe = candidate.get("profile", {}).get("years_of_experience", 0)
    if 6.0 <= yoe <= 8.0:
        return 1.05  # Absolute sweet spot for Senior Founding Team
    elif 5.0 <= yoe <= 9.0:
        return 1.0
    elif 4.0 <= yoe < 5.0 or 9.0 < yoe <= 11.0:
        return 0.90
    elif 3.0 <= yoe < 4.0 or 11.0 < yoe <= 14.0:
        return 0.75
    elif yoe < 3.0:
        return 0.50
    else:
        return 0.60

def calculate_startup_bonus(candidate):
    """Bonus for startup, 0-to-1, or founding experience."""
    career_text = " ".join([job.get("description", "").lower() for job in candidate.get("career_history", [])])
    if any(kw in career_text for kw in ["startup", "0 to 1", "0-to-1", "founding", "built from scratch", "early stage"]):
        return 0.05
    return 0.0


def calculate_education_bonus(candidate):
    """Small bonus for tier_1 education."""
    education = candidate.get("education", [])
    for edu in education:
        tier = edu.get("tier", "unknown")
        if tier == "tier_1":
            return 0.06
        if tier == "tier_2":
            return 0.03
    return 0.0


def calculate_certification_bonus(candidate):
    """Bonus for relevant ML/AI certifications."""
    certs = candidate.get("certifications", [])
    relevant_keywords = {
        "machine learning", "deep learning", "nlp", "natural language",
        "tensorflow", "pytorch", "ai ", "artificial intelligence",
        "data science", "aws machine", "google cloud ai",
    }
    bonus = 0.0
    for cert in certs:
        name = cert.get("name", "").lower()
        if any(kw in name for kw in relevant_keywords):
            bonus += 0.02
    return min(0.06, bonus)


DEPTH_EVIDENCE_PHRASES = [
    "production", "deployed", "shipped", "a/b test", "offline eval",
    "ndcg", "retrieval", "ranking", "recommendation system", "embedding"
]


def calculate_depth_bonus(candidate):
    """Multiplicative bonus for candidates with deep production evidence."""
    career_text = " ".join([job.get("description", "").lower() for job in candidate.get("career_history", [])])
    hits = sum(1 for phrase in DEPTH_EVIDENCE_PHRASES if phrase in career_text)
    if hits >= 3:
        return 1.10
    return 1.0


def calculate_academic_penalty(candidate):
    """Penalize pure research/academic backgrounds with no production evidence."""
    career_text = " ".join([job.get("description", "").lower() for job in candidate.get("career_history", [])])
    academic_words = ["paper", "conference", "research", "lab", "publication", "thesis"]
    production_words = ["shipped", "deployed", "production", "users", "scale", "infrastructure"]
    
    has_academic = sum(1 for w in academic_words if w in career_text) >= 2
    has_production = any(w in career_text for w in production_words)
    
    if has_academic and not has_production:
        return 0.7
    return 1.0


# Penalty multipliers for heuristic red flags from plausibility_filter
PENALTY_MULTIPLIERS = {
    "duplicate_descriptions": 0.80,
    "skill_duration_exceeds_career": 0.75,
    "cv_without_nlp": 0.15,
    "fake_proficiency": 0.15,
    "wrong_persona_enthusiast": 0.15,
    "transitioning_persona": 0.15,
    "langchain_only": 0.15,
    "cv_disqualifier_explicit": 0.10,
}


def score_candidate(candidate, semantic_score, penalty_reasons=None):
    """
    Final scoring: fuses semantic similarity, explicit skill match,
    title relevance, experience band, and behavioral signals.
    """
    skill_match = calculate_skill_match_score(candidate)
    signal_score = calculate_signal_score(candidate)
    title_mult = calculate_title_multiplier(candidate)

    raw_score = (0.50 * semantic_score) + (0.30 * skill_match) + (0.20 * signal_score)

    # Education, certification, and startup bonuses (additive before multipliers)
    raw_score += calculate_education_bonus(candidate)
    raw_score += calculate_certification_bonus(candidate)
    raw_score += calculate_startup_bonus(candidate)

    final_score = raw_score * title_mult

    # Experience band fit
    final_score *= calculate_experience_band_multiplier(candidate)

    # P5: Graduated services penalty
    final_score *= calculate_services_penalty(candidate)

    # Title-chaser penalty
    career_history = candidate.get("career_history", [])
    if len(career_history) >= 3:
        durations = [j.get("duration_months", 0) for j in career_history]
        avg_tenure = sum(durations) / len(durations)
        if avg_tenure < 18:
            final_score *= 0.6

    profile = candidate.get("profile", {})
    signals = candidate.get("redrob_signals", {})
    loc = profile.get("location", "").lower()
    country = profile.get("country", "").lower()
    will_relocate = signals.get("willing_to_relocate", False)
    is_compatible = any(city in loc for city in TARGET_CITIES)

    if not is_compatible and not will_relocate:
        if country and country != "india":
            final_score *= 0.05
        else:
            final_score *= 0.1

    last_active_str = signals.get("last_active_date")
    resp_rate = signals.get("recruiter_response_rate", 0.0)

    days_inactive = 180
    if last_active_str:
        try:
            last_active = datetime.datetime.strptime(last_active_str, "%Y-%m-%d")
            days_inactive = max(0, (datetime.datetime(2026, 6, 16) - last_active).days)
        except ValueError:
            days_inactive = 180

    if days_inactive > 180 and resp_rate < 0.1:
        final_score *= 0.1
    elif days_inactive > 180 or resp_rate < 0.1:
        final_score *= 0.5

    if not signals.get("open_to_work_flag", True):
        final_score *= 0.1

    # Academic penalty
    final_score *= calculate_academic_penalty(candidate)

    # Apply heuristic penalties from plausibility_filter
    if penalty_reasons:
        for reason in penalty_reasons:
            mult = PENALTY_MULTIPLIERS.get(reason, 0.85)
            final_score *= mult

    # Closed source penalty
    gh_score = signals.get("github_activity_score", -1)
    yoe = profile.get("years_of_experience", 0)
    career_text = " ".join([job.get("description", "").lower() for job in career_history])
    if gh_score == 0 and yoe >= 8 and "open source" not in career_text:
        final_score *= 0.85

    # Profile completeness
    completeness = signals.get("profile_completeness_score", 50)
    if completeness < 40:
        final_score *= 0.85

    # Vector DB claim without career evidence
    skills = candidate.get("skills", [])
    vector_dbs = {"qdrant", "milvus", "pinecone", "weaviate", "faiss", "semantic search"}
    claimed_vector_dbs = [s.get("name", "").lower() for s in skills if s.get("name", "").lower() in vector_dbs]
    if len(claimed_vector_dbs) >= 2:
        if not any(db in career_text for db in vector_dbs):
            final_score *= 0.6

    # P4: Apply depth bonus multiplicatively at the end
    final_score *= calculate_depth_bonus(candidate)

    return final_score, semantic_score, signal_score, None
