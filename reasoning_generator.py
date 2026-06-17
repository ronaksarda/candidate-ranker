def generate_reasoning(candidate, rank, score, semantic_score, signal_score):
    """
    Generates a concise, specific, and accurate 2-sentence rationale.
    """
    profile = candidate.get("profile", {})
    title = profile.get("current_title", "Professional")
    yoe = profile.get("years_of_experience", 0)

    # Get JD-relevant skills specifically, not just top-by-duration
    JD_RELEVANT = {
        "faiss", "pinecone", "weaviate", "qdrant", "milvus", "opensearch",
        "elasticsearch", "embeddings", "embedding", "vector search", "rag",
        "ranking", "ndcg", "mrr", "pytorch", "tensorflow", "transformers",
        "bert", "llm", "llms", "hugging face", "huggingface", "lora", "qlora",
        "peft", "nlp", "xgboost", "deep learning", "machine learning",
        "scikit-learn", "sklearn", "sentence-transformers", "sentence transformers",
        "langchain", "llamaindex", "information retrieval", "learning to rank",
        "python", "docker", "kubernetes", "mlops",
    }

    skills = candidate.get("skills", [])
    relevant_skills = []
    other_skills = []
    for s in sorted(skills, key=lambda x: x.get("duration_months", 0), reverse=True):
        name = s.get("name", "")
        if name.lower() in JD_RELEVANT or any(jd in name.lower() for jd in JD_RELEVANT):
            relevant_skills.append(name)
        else:
            other_skills.append(name)

    # Pick top 3 relevant skills; fall back to top skills if none match
    display_skills = relevant_skills[:3] if relevant_skills else other_skills[:3]

    signals = candidate.get("redrob_signals", {})
    notice = signals.get("notice_period_days", 90)
    resp_rate = signals.get("recruiter_response_rate", 1.0)
    gh_score = signals.get("github_activity_score", 0)

    # Sentence 1: Specific background with JD-relevant skills
    skill_text = f"with production experience in {', '.join(display_skills)}" if display_skills else "with a broad technical background"
    sentence1 = f"{yoe}-year {title} {skill_text}."

    # Sentence 2: Specific, data-driven justification
    parts = []

    # Semantic fit
    if semantic_score > 0.65:
        parts.append("strong semantic alignment with the JD's core ML and retrieval requirements")
    elif semantic_score > 0.5:
        parts.append("solid semantic overlap with the JD's technical requirements")
    else:
        parts.append("moderate technical overlap with the JD")

    # Notice period
    if notice <= 30:
        parts.append("available within 30 days")
    elif notice <= 60:
        parts.append(f"{notice}-day notice period")
    else:
        parts.append(f"longer {notice}-day notice period")

    # Response rate
    if resp_rate > 0.7:
        parts.append("high recruiter responsiveness")
    elif resp_rate < 0.3:
        parts.append(f"low historical response rate ({int(resp_rate*100)}%)")

    # GitHub
    if gh_score > 70:
        parts.append("active open-source contributor")

    sentence2 = "; ".join(parts) + "."
    sentence2 = sentence2[0].upper() + sentence2[1:]

    return f"{sentence1} {sentence2}"
