import datetime

CURRENT_YEAR = 2026


def is_honeypot(candidate) -> tuple[bool, str | None]:
    """
    Returns (True, reason_code) ONLY for mathematically impossible profiles.
    ~80 real honeypots in dataset. Everything else is a scoring penalty.
    """
    profile = candidate.get("profile", {})
    yoe = profile.get("years_of_experience", 0)
    skills = candidate.get("skills", [])
    career_history = candidate.get("career_history", [])

    # Check 1: Expert proficiency in 5+ skills with 0 months duration
    # Spec literally names this pattern.
    expert_zero = sum(
        1 for s in skills
        if s.get("proficiency") == "expert" and s.get("duration_months", 0) == 0
    )
    if expert_zero >= 5:
        return True, "check_1_expert_zero_months"

    # Check 2: Claimed YoE wildly exceeds career history
    # Only kill if difference is extreme (>8 years unaccounted)
    total_career_months = sum(job.get("duration_months", 0) for job in career_history)
    if total_career_months > 0 and (yoe * 12) > (total_career_months + 96):
        return True, "check_2_yoe_exceeds_career"

    # Check 3: Overlapping dates — claiming 1.5x+ more duration than calendar time
    if career_history:
        try:
            min_date = None
            max_date = None
            for job in career_history:
                start_str = job.get("start_date")
                if start_str:
                    s_date = datetime.datetime.strptime(start_str, "%Y-%m-%d")
                    if min_date is None or s_date < min_date:
                        min_date = s_date

                end_str = job.get("end_date")
                is_current = job.get("is_current", False)
                if is_current or not end_str:
                    e_date = datetime.datetime.now()
                else:
                    e_date = datetime.datetime.strptime(end_str, "%Y-%m-%d")
                if max_date is None or e_date > max_date:
                    max_date = e_date

            if min_date and max_date:
                chronological_months = (max_date.year - min_date.year) * 12 + (max_date.month - min_date.month)
                if chronological_months > 0 and total_career_months > (chronological_months * 2.0 + 36):
                    return True, "check_3_overlapping_career_dates"
        except ValueError:
            pass

    # Check 4: Time-traveling tech — claiming impossible duration for recent tech
    for s in skills:
        name = s.get("name", "").lower()
        dur = s.get("duration_months", 0)
        if name == "qlora" and dur > 38:
            return True, "check_4_time_traveling_tech"
        if name == "langchain" and dur > 50:
            return True, "check_4_time_traveling_tech"
        if name == "chatgpt" and dur > 46:
            return True, "check_4_time_traveling_tech"
        if name == "llama-2" and dur > 38:
            return True, "check_4_time_traveling_tech"

    return False, None


def get_penalty_reasons(candidate) -> list[str]:
    """
    Returns list of penalty reason codes for heuristic red flags.
    These are NOT honeypots — scorer.py applies multipliers.
    """
    reasons = []
    profile = candidate.get("profile", {})
    skills = candidate.get("skills", [])
    career_history = candidate.get("career_history", [])
    yoe = profile.get("years_of_experience", 0)

    career_text = " ".join([job.get("description", "").lower() for job in career_history])
    summary_text = profile.get("summary", "").lower()
    full_text = career_text + " " + summary_text

    # Duplicate descriptions across roles
    if len(career_history) >= 2:
        descriptions = [job.get("description", "").strip().lower() for job in career_history]
        valid = [d for d in descriptions if len(d) > 40]
        if len(set(valid)) < len(valid):
            reasons.append("duplicate_descriptions")

    # Skill duration exceeds career by large margin
    total_career_months = sum(job.get("duration_months", 0) for job in career_history)
    max_skill_dur = max((s.get("duration_months", 0) for s in skills), default=0)
    if max_skill_dur > (total_career_months + 48):
        reasons.append("skill_duration_exceeds_career")

    # CV/speech without NLP/IR
    title = profile.get("current_title", "").lower()
    if any(t in title for t in ["computer vision", "cv engineer", "robotics", "speech engineer"]):
        nlp_signals = ["nlp", "retrieval", "ranking", "embedding", "transformer", "vector", "natural language", "llm", "search"]
        if not any(sig in full_text for sig in nlp_signals):
            reasons.append("cv_without_nlp")

    # Fake proficiency: expert claim but terrible assessment
    skill_assessments = candidate.get("redrob_signals", {}).get("skill_assessment_scores", {})
    for s in skills:
        name = s.get("name")
        prof = s.get("proficiency", "beginner")
        if name in skill_assessments:
            sc = skill_assessments[name]
            if prof == "expert" and sc < 40:
                reasons.append("fake_proficiency")
                break
            if prof == "advanced" and sc < 25:
                reasons.append("fake_proficiency")
                break

    # Wrong persona: "enthusiast"/"aspiring" with 3+ years
    headline = profile.get("headline", "").lower()
    if ("enthusiast" in headline or "aspiring" in headline) and yoe > 3:
        reasons.append("wrong_persona_enthusiast")

    # Transitioning persona
    if "interested in transitioning toward" in full_text and "learning modern ml practice" in full_text:
        reasons.append("transitioning_persona")

    # LangChain-only without foundations
    skill_names_lower = {s.get("name", "").lower() for s in skills}
    llm_wrappers = {"langchain", "llamaindex", "openai", "chatgpt"}
    core_ml = {
        "embedding", "embeddings", "faiss", "vector", "retrieval",
        "ranking", "sentence-transformers", "nlp", "information retrieval",
        "recommendation", "search", "bert", "pytorch", "tensorflow"
    }
    if (any(s in skill_names_lower for s in llm_wrappers)
        and not any(s in skill_names_lower for s in core_ml)
        and not any(kw in career_text for kw in [
            "retrieval", "ranking", "embedding", "search engine",
            "recommendation", "nlp", "neural", "production ml"
        ])):
        reasons.append("langchain_only")

    # CV disqualifier (explicit admission)
    if "professional experience there is limited" in full_text and "transitioning toward nlp" in full_text:
        reasons.append("cv_disqualifier_explicit")
    if "most of my project work has been in cv" in full_text:
        reasons.append("cv_disqualifier_explicit")

    return reasons
