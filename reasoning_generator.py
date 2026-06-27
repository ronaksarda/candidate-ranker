import random

def generate_reasoning(candidate, rank, score, semantic_score, signal_score, evidence_pair=None):
    from scorer import (
        TARGET_CITIES, JD_CORE_SKILLS_NORM, JD_STRONG_SKILLS_NORM,
        JD_NICE_SKILLS_NORM, normalize_text, is_valid_match
    )

    profile = candidate.get("profile", {})
    title = profile.get("current_title", "Professional")
    cid = candidate.get("candidate_id", "Unknown")
    
    # Seed randomness so output is deterministic for a specific candidate ID, but heavily varied across candidates
    random.seed(cid)
    
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

    company = ""
    if career_history:
        company = career_history[0].get("company", "")

    # Gather skills text
    skills_text = ""
    if core_found_career:
        skills_text = ", ".join(core_found_career[:3])
    elif core_found_claimed:
        skills_text = ", ".join(core_found_claimed[:3])
    elif strong_found_career:
        skills_text = ", ".join(strong_found_career[:3])
    elif strong_found_claimed:
        skills_text = ", ".join(strong_found_claimed[:3])
    else:
        skills_text = "generalist software engineering"

    # Gather gaps
    gaps = []
    if notice > 60:
        gaps.append(random.choice([f"a {notice}-day notice period", f"availability delayed by {notice} days", f"requires {notice} days notice"]))
    if resp_rate < 0.4:
        gaps.append(random.choice(["low recruiter responsiveness", "poor response rates", "historically unresponsive to outreach"]))
    if not is_local and not will_relocate:
        gaps.append(random.choice(["significant relocation risk", "not locally based and unwilling to move", "geo-mismatch"]))
    if not core_found_career and rank > 50:
        if yoe < 4:
            gaps.append(random.choice(["needs more scale exposure", "insufficient production mileage"]))
        elif strong_found_career:
            gaps.append(random.choice(["missing dedicated retrieval background", "lacks core search-engine expertise"]))
        else:
            gaps.append(random.choice(["lacks core production ML evidence", "no verified production AI deployment"]))

    # Gather strengths
    strengths = []
    if notice <= 30:
        strengths.append(f"available in {notice} days")
    if resp_rate > 0.6:
        strengths.append(f"highly responsive ({int(resp_rate*100)}%)")
    if gh_score > 60:
        strengths.append(f"strong GitHub activity ({gh_score:.0f})")
    if is_local:
        strengths.append(f"based in {profile.get('location', 'target city')}")

    # Start building the story based on templates!
    structure = random.randint(1, 4)
    story = ""

    comp_str = f" at {company}" if company else ""
    startup_str = " with a startup background" if any(kw in career_text for kw in ["startup", "0 to 1", "0-to-1", "founding", "early stage"]) else ""

    if rank <= 20:
        # Top-tier structures
        if structure == 1:
            story = f"Exceptional {yoe:.1f}-year {title}{comp_str}{startup_str}. Demonstrates clear production experience in {skills_text}."
        elif structure == 2:
            story = f"Top-tier candidate currently working as a {title}{comp_str} ({yoe:.1f} yrs). Stood out due to deep expertise in {skills_text}."
        elif structure == 3:
            story = f"A highly capable {title}{startup_str} bringing {yoe:.1f} years of experience, primarily focused on {skills_text}."
        else:
            story = f"With {yoe:.1f} years of tenure, this {title}{comp_str} shows outstanding command of {skills_text}."
            
        if strengths:
            story += " " + random.choice(["Additionally, they are ", "Bonus: ", "Further highlights: "]) + ", ".join(strengths) + "."
            
        if evidence:
            story += f" Evidence: \"{evidence}\""

    elif rank <= 50:
        # Mid-tier structures
        if structure == 1:
            story = f"Solid {yoe:.1f}-year {title}{comp_str}{startup_str} offering skills in {skills_text}."
        elif structure == 2:
            story = f"A viable {title} with {yoe:.1f} years under their belt, demonstrating capability in {skills_text}."
        elif structure == 3:
            story = f"Currently a {title}{comp_str}, bringing {yoe:.1f} years of experience and a foundation in {skills_text}."
        else:
            story = f"Brings {yoe:.1f} years of experience to the table as a {title}, showing competence with {skills_text}."

        if gaps:
            story += " " + random.choice(["However, consider: ", "Drawbacks include ", "Areas of concern: "]) + ", ".join(gaps) + "."
            
        if evidence and evidence_company:
            story += f" Highlight at {evidence_company}: \"{evidence}\""

    else:
        # Bottom-tier structures
        if structure == 1:
            story = f"This {yoe:.1f}-year {title}{comp_str} lists {skills_text}."
        elif structure == 2:
            story = f"While they have {yoe:.1f} years as a {title}, their profile mainly covers {skills_text}."
        elif structure == 3:
            story = f"A {title}{startup_str} ({yoe:.1f} yrs) whose primary exposure is {skills_text}."
        else:
            story = f"Evaluated as a {yoe:.1f}-year {title}{comp_str} familiar with {skills_text}."

        if gaps:
            story += " " + random.choice(["They were penalized for ", "Significant gaps: ", "Limitations: "]) + ", ".join(gaps) + "."

    return f"Score {score:.3f}: {story}"