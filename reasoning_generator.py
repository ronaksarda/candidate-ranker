def generate_reasoning(candidate, rank, score, semantic_score, signal_score, evidence_pair=None):
    from scorer import (
        TARGET_CITIES, JD_CORE_SKILLS_NORM, JD_STRONG_SKILLS_NORM,
        JD_NICE_SKILLS_NORM, normalize_text, is_valid_match
    )

    profile = candidate.get("profile", {})
    title = profile.get("current_title", "Professional")
    cid = candidate.get("candidate_id", "Unknown")
    yoe = profile.get("years_of_experience", 0)
    signals = candidate.get("redrob_signals", {})
    career_history = candidate.get("career_history", [])

    skill_names = set(s.get("name", "") for s in candidate.get("skills", []))
    career_text = " ".join([job.get("description", "").lower() for job in career_history])
    norm_career_text = normalize_text(career_text)

    def find_hits(jd_set, require_in_career=False):
        found = []
        for sname in skill_names:
            norm_sname = normalize_text(sname)
            for jd_skill in jd_set:
                if is_valid_match(jd_skill, norm_sname) and jd_skill not in found:
                    if require_in_career and not is_valid_match(jd_skill, norm_career_text):
                        continue
                    found.append(jd_skill)
                    break
        return found

    core_found_career = find_hits(JD_CORE_SKILLS_NORM, require_in_career=True)
    core_found_claimed = find_hits(JD_CORE_SKILLS_NORM, require_in_career=False)
    strong_found_career = find_hits(JD_STRONG_SKILLS_NORM, require_in_career=True)
    strong_found_claimed = find_hits(JD_STRONG_SKILLS_NORM, require_in_career=False)

    notice = signals.get("notice_period_days", 90)
    resp_rate = signals.get("recruiter_response_rate", 0.0)
    gh_score = signals.get("github_activity_score", 0)

    loc = profile.get("location", "").lower()
    will_relocate = signals.get("willing_to_relocate", False)
    is_local = any(city in loc for city in TARGET_CITIES)

    # Use pre-extracted, deduplicated evidence
    evidence = evidence_pair[0] if evidence_pair else None
    evidence_company = evidence_pair[1] if evidence_pair else None

    # ---- Rank-aware reasoning generation ----
    parts = []

    # Lead: career identity
    career_desc = f"{yoe:.1f}-year {title}"
    if any(kw in career_text for kw in ["startup", "0 to 1", "0-to-1", "founding", "early stage"]):
        career_desc += ", founding/startup background"
    parts.append(career_desc)

    if rank <= 20:
        # Top-20: lead with what makes them exceptional
        if core_found_career:
            parts.append(f"production experience with {', '.join(core_found_career[:3])}")
        elif core_found_claimed:
            parts.append(f"skilled in {', '.join(core_found_claimed[:3])}")
            
        if strong_found_career:
            parts.append(f"deep {', '.join(strong_found_career[:2])} expertise")
        elif strong_found_claimed:
            parts.append(f"strong foundation in {', '.join(strong_found_claimed[:2])}")
            
        if evidence and evidence_company:
            parts.append(f'at {evidence_company}: "{evidence}"')
        elif evidence:
            parts.append(f'"{evidence}"')

        # Availability strength
        if notice <= 30:
            parts.append(f"available in {notice} days")
        if resp_rate > 0.6:
            parts.append(f"{int(resp_rate*100)}% response rate")
        if gh_score > 60:
            parts.append(f"GitHub activity {gh_score:.0f}")
        if is_local:
            parts.append(f"in {profile.get('location', '')}")
        elif will_relocate:
            parts.append("willing to relocate")

    elif rank <= 50:
        # Mid-tier: balanced view with honest gaps
        if core_found_career:
            parts.append(f"has {', '.join(core_found_career[:2])}")
        elif core_found_claimed:
            parts.append(f"knows {', '.join(core_found_claimed[:2])}")
            
        if strong_found_claimed:
            parts.append(f"{', '.join(strong_found_claimed[:2])}")
        if evidence and evidence_company:
            parts.append(f'[{evidence_company}]: "{evidence}"')

        # Note gaps honestly
        gaps = []
        if notice > 60:
            gaps.append(f"{notice}-day notice")
        if resp_rate < 0.4:
            gaps.append(f"low response ({int(resp_rate*100)}%)")
        if not is_local and not will_relocate:
            gaps.append("location mismatch")
        if gaps:
            parts.append(f"concerns: {', '.join(gaps)}")

    else:
        # Rank 51-100: lead with the gap that explains why they're here
        if core_found_claimed:
            parts.append(f"{', '.join(core_found_claimed[:2])}")
        elif strong_found_claimed:
            parts.append(f"only {', '.join(strong_found_claimed[:2])}, no core retrieval skills")
        else:
            parts.append("limited relevant skill overlap")

        gaps = []
        if notice > 60:
            gaps.append(f"{notice}-day notice")
        if resp_rate < 0.3:
            gaps.append(f"{int(resp_rate*100)}% response rate")
        if not is_local and not will_relocate:
            gaps.append("location mismatch")
        if not core_found_career:
            gaps.append("no production evidence for vector DB/retrieval")
        if gaps:
            parts.append(f"gaps: {', '.join(gaps)}")
        if evidence and evidence_company:
            parts.append(f'but has evidence [{evidence_company}]: "{evidence}"')

    story = ", ".join(parts)
    return f"Score {score:.3f}: {story}."