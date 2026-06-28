import re

_EVIDENCE_RE = re.compile(
    r'[^.]*\b(\d+%|\d+ms|\d+k|\d+x|shipped|deployed|built|production|reduced|improved|increased|launched|served|scale)\b[^.]*\.',
    re.IGNORECASE
)

def _extract_best_evidence(candidate):
    for job in candidate.get("career_history", [])[:3]:
        desc = job.get("description", "").strip()
        if not desc:
            continue
        m = _EVIDENCE_RE.search(desc)
        if m:
            sent = m.group(0).strip()
            if len(sent) > 140:
                sent = sent[:137] + "..."
            return sent, job.get("company", "")
    return None, None

def generate_reasoning(candidate, rank, score, semantic_score, signal_score, evidence_pair=None):
    from scorer import (
        TARGET_CITIES, JD_CORE_SKILLS_NORM, JD_STRONG_SKILLS_NORM,
        JD_NICE_SKILLS_NORM, normalize_text, is_valid_match
    )

    profile = candidate.get("profile", {})
    title = profile.get("current_title", "Professional")
    yoe = profile.get("years_of_experience", 0)
    company = profile.get("current_company", "")
    
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
        if require_in_career:
            for jd_skill in jd_set:
                if jd_skill not in found and is_valid_match(jd_skill, norm_career_text):
                    found.append(jd_skill)
        return found

    core_found_career = find_hits(JD_CORE_SKILLS_NORM, require_in_career=True)
    core_found_claimed = find_hits(JD_CORE_SKILLS_NORM, require_in_career=False)
    strong_found_career = find_hits(JD_STRONG_SKILLS_NORM, require_in_career=True)
    strong_found_claimed = find_hits(JD_STRONG_SKILLS_NORM, require_in_career=False)

    if len(core_found_career) == 1 and core_found_career[0] == "ranking":
        if strong_found_career:
            core_found_career = strong_found_career
        elif strong_found_claimed:
            core_found_career = strong_found_claimed
        else:
            if career_history:
                first_desc = career_history[0].get("description", "")
                if first_desc:
                    first_sent = first_desc.split('.')[0][:100].strip()
                    if first_sent:
                        core_found_career = [f'"{first_sent}..."']

    evidence = evidence_pair[0] if evidence_pair else None
    evidence_company = evidence_pair[1] if evidence_pair else None

    if not evidence and rank <= 30:
        evidence, evidence_company = _extract_best_evidence(candidate)

    notice = signals.get("notice_period_days", 90)
    resp_rate = signals.get("recruiter_response_rate", 0.0)
    gh_score = signals.get("github_activity_score", -1)

    loc = profile.get("location", "").lower()
    will_relocate = signals.get("willing_to_relocate", False)
    is_local = any(city in loc for city in TARGET_CITIES)

    comp_str = f" at {company}" if company else ""
    startup_str = " (founding background)" if any(kw in career_text for kw in ["startup", "0 to 1", "0-to-1", "founding", "early stage"]) else ""
    identity = f"{yoe:.1f}-year {title}{comp_str}{startup_str}"
    
    story = ""

    if rank <= 20:
        story = f"{identity}."
        skills_parts = []
        if core_found_career:
            skills_parts.append(f"production exposure in {', '.join(core_found_career)}")
        if strong_found_career:
            skills_parts.append(f"strong hits in {', '.join(strong_found_career)}")
        elif strong_found_claimed:
            skills_parts.append(f"familiarity with {', '.join(strong_found_claimed)}")
            
        if skills_parts:
            story += f" Demonstrated {', and '.join(skills_parts)}."
            
        if evidence and evidence_company:
            if company and evidence_company.lower() != company.lower():
                story += f" Evidence (formerly at {evidence_company}): \"{evidence}\"."
            else:
                story += f" Evidence at {evidence_company}: \"{evidence}\"."
        elif evidence:
            story += f" Evidence: \"{evidence}\"."
            
        signal_parts = []
        if notice <= 30:
            signal_parts.append(f"available in {notice} days")
        if resp_rate > 0.6:
            signal_parts.append(f"responsive ({int(resp_rate*100)}%)")
        if gh_score > 60:
            signal_parts.append(f"GitHub score {gh_score:.0f}")
        if is_local:
            signal_parts.append("locally based")
            
        if signal_parts:
            story += f" Signals: {', '.join(signal_parts)}."
            
    elif rank <= 50:
        story = f"{identity}."
        has_skills = core_found_career or strong_found_career or core_found_claimed
        if has_skills:
            top = (core_found_career or core_found_claimed or strong_found_career)[:3]
            story += f" Key overlap: {', '.join(top)}."
            
        if evidence and rank <= 30:
            if evidence_company and company and evidence_company.lower() != company.lower():
                story += f" Evidence (formerly at {evidence_company}): \"{evidence}\"."
            else:
                story += f" Evidence: \"{evidence}\"."
            
        gaps = []
        if notice > 60:
            gaps.append(f"{notice}-day notice")
        if resp_rate < 0.4:
            gaps.append("low response rate")
        if not is_local and not will_relocate:
            gaps.append("location mismatch")
            
        if gaps:
            story += f" Gaps: {', '.join(gaps)}."
            
    else:
        has_skills = core_found_career or strong_found_career or core_found_claimed
        if has_skills:
            top = (core_found_career or core_found_claimed or strong_found_career)[:3]
            story = f"{identity} with {', '.join(top)}."
        else:
            story = f"{identity} with general ML background, limited retrieval overlap."
            
        gaps = []
        if notice > 60:
            gaps.append(f"{notice}-day notice")
        if resp_rate < 0.4:
            gaps.append("low response rate")
        if not is_local and not will_relocate:
            gaps.append("location mismatch")
            
        if gaps:
            story += f" Notes: {', '.join(gaps)}."
            
        if evidence:
            story += f" Evidence: \"{evidence}\"."

    # Output format exact match to prompt, removing trailing period from story if it exists to avoid '..'
    story_clean = story.rstrip('.')
    return f"Score {score:.3f}: {story_clean}."