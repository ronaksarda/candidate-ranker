import re

# Boilerplate sentences that appear across many candidates — never quote these
_BOILERPLATE_FRAGMENTS = {
    "internal knowledge base of ~500k",
    "50m+ queries per month for an internal recruiter",
    "ranking layer for an e-commerce search product",
    "rag-based customer support chatbot",
    "mlflow for experiment tracking, kubeflow",
    "content recommendation system serving 10m+ users",
    "ranking models for our product's discovery feed using xgboost and lightgbm",
    "recommendation-style features at a mid-stage startup",
    "migration from keyword-based to embedding-based search across a 30m+",
    "35m+ items. migrated the existing bm25",
    "200k high-quality preference pairs from recruiter labels",
    "time-series forecasting models for supply-chain",
    "fraud-detection product",
    "nlp pipelines for sentiment analysis",
    "worked on customer-facing predictive modeling",
    "offline experimentation to live a/b test in 5 months",
    "built and operated production ml pipelines using mlflow",
}

_EVIDENCE_RE = re.compile(
    r'[^.]*(\b\d+%|\b\d+ms|\b\d+[kmb]\b|\b\d+x\b|\bshipped\b|\bdeployed\b|\breduced\b|\bimproved\b|\bincreased\b|\blatency\b|\bthroughput\b|\bprecision\b|\brecall\b|\bndcg\b|\bmrr\b)[^.]*\.',
    re.IGNORECASE
)


def _is_boilerplate(text):
    t = text.lower()
    return any(frag in t for frag in _BOILERPLATE_FRAGMENTS)


def _extract_unique_evidence(candidate, seen_evidence=None):
    """
    Extract a genuinely unique, quantified evidence sentence.
    Skips known boilerplate patterns.
    Returns (sentence, company) or (None, None).
    """
    for job in candidate.get("career_history", [])[:4]:
        desc = job.get("description", "").strip()
        if not desc:
            continue
        matches = list(_EVIDENCE_RE.finditer(desc))
        if not matches:
            continue
        valid_matches = []
        for m in matches:
            sent = m.group(0).strip()
            if _is_boilerplate(sent):
                continue
            if len(sent) > 150:
                sent = sent[:147] + "..."
            if seen_evidence is not None and sent in seen_evidence:
                continue
            valid_matches.append(sent)
        if valid_matches:
            best_sent = max(valid_matches, key=len)
            return best_sent, job.get("company", "")
    return None, None


def _build_skill_narrative(candidate, jd_core_norm, jd_strong_norm, normalize_text, is_valid_match):
    """
    Build unique skill narrative using actual skill names, durations, proficiencies,
    and assessment scores — not generic JD category labels.
    """
    skills = candidate.get("skills", [])
    signals = candidate.get("redrob_signals", {})
    assessments = signals.get("skill_assessment_scores", {})

    sorted_skills = sorted(skills, key=lambda s: s.get("duration_months", 0), reverse=True)

    relevant = []
    for s in sorted_skills:
        name = s.get("name", "")
        norm = normalize_text(name)
        dur = s.get("duration_months", 0)
        prof = s.get("proficiency", "")
        score = assessments.get(name, -1)

        is_core = any(is_valid_match(jd_skill, norm) for jd_skill in jd_core_norm)
        is_strong = any(is_valid_match(jd_skill, norm) for jd_skill in jd_strong_norm)

        if is_core or is_strong:
            relevant.append({
                "name": name, "duration": dur,
                "proficiency": prof, "score": score, "is_core": is_core,
            })

    if not relevant:
        return None

    top = relevant[:3]
    parts = []
    for sk in top:
        part = sk["name"]
        if sk["duration"] >= 48:
            part += f" ({sk['duration']}mo)"
        if sk["score"] > 80:
            part += f" [assessed {sk['score']:.0f}]"
        elif sk["proficiency"] == "expert":
            part += " [expert]"
        parts.append(part)

    return ", ".join(parts)


def _build_career_trail(candidate):
    """Career trail from company names + tenures — always unique per candidate."""
    career = candidate.get("career_history", [])
    if not career:
        return None

    trail = []
    for job in career[:3]:
        co = job.get("company", "")
        dur = job.get("duration_months", 0)
        if co and dur:
            trail.append(f"{co} ({dur}mo)")
        elif co:
            trail.append(co)

    if len(trail) >= 2:
        return " → ".join(trail)
    return trail[0] if trail else None


def generate_reasoning(candidate, rank, score, semantic_score, signal_score, evidence_pair=None, seen_evidence=None):
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
    assessments = signals.get("skill_assessment_scores", {})

    notice = signals.get("notice_period_days", 90)
    resp_rate = signals.get("recruiter_response_rate", 0.0)
    gh_score = signals.get("github_activity_score", -1)
    days_inactive = signals.get("days_since_last_active", None)
    saved_30d = signals.get("saved_by_recruiters_30d", 0) or 0

    loc = profile.get("location", "").lower()
    will_relocate = signals.get("willing_to_relocate", False)
    is_local = any(city in loc for city in TARGET_CITIES)

    has_founding = False
    for job in career_history:
        co = job.get("company", "").lower()
        if any(cf in co for cf in ["mahindra", "tcs", "tata", "infosys", "wipro", "accenture", "cognizant", "capgemini", "hcl", "l&t"]):
            continue
        desc = job.get("description", "").lower()
        if any(kw in desc for kw in ["startup", "0 to 1", "0-to-1", "founding", "early stage"]):
            has_founding = True
            break

    comp_str = f" at {company}" if company else ""
    founding_str = " (founding background)" if has_founding else ""
    identity = f"{yoe:.1f}-year {title}{comp_str}{founding_str}"

    skill_narrative = _build_skill_narrative(
        candidate, JD_CORE_SKILLS_NORM, JD_STRONG_SKILLS_NORM, normalize_text, is_valid_match
    )
    career_trail = _build_career_trail(candidate)
    high_assessments = {k: v for k, v in assessments.items() if v > 82}

    # Evidence — unique quantified sentence, never boilerplate
    evidence = None
    evidence_company = None

    if evidence_pair and evidence_pair[0] and not _is_boilerplate(evidence_pair[0]):
        ev = evidence_pair[0]
        if seen_evidence is None or ev not in seen_evidence:
            evidence = ev
            evidence_company = evidence_pair[1]
            if seen_evidence is not None:
                seen_evidence.add(ev)

    if not evidence:
        ev, ev_co = _extract_unique_evidence(candidate, seen_evidence)
        if ev and (seen_evidence is None or ev not in seen_evidence):
            evidence = ev
            evidence_company = ev_co
            if seen_evidence is not None:
                seen_evidence.add(ev)

    story = f"{identity}."

    if rank <= 20:
        if skill_narrative:
            story += f" Core skills: {skill_narrative}."

        if evidence and evidence_company:
            if evidence_company.lower() != company.lower():
                story += f" Evidence (formerly at {evidence_company}): \"{evidence}\"."
            else:
                story += f" Evidence at {evidence_company}: \"{evidence}\"."
        elif evidence:
            story += f" Evidence: \"{evidence}\"."

        sig_parts = []
        if notice == 0:
            sig_parts.append("immediately available")
        elif notice <= 15:
            sig_parts.append(f"available in {notice} days")
        elif notice <= 30:
            sig_parts.append(f"{notice}-day notice")

        if resp_rate > 0.75:
            sig_parts.append(f"highly responsive ({int(resp_rate*100)}%)")
        elif resp_rate > 0.6:
            sig_parts.append(f"responsive ({int(resp_rate*100)}%)")

        if gh_score > 70:
            sig_parts.append(f"GitHub {gh_score:.0f}")

        if high_assessments:
            best = max(high_assessments.items(), key=lambda x: x[1])
            sig_parts.append(f"assessed {best[1]:.0f}/100 on {best[0]}")

        if is_local:
            sig_parts.append(f"based in {profile.get('location','').split(',')[0]}")
        elif will_relocate:
            sig_parts.append("willing to relocate")

        if saved_30d > 15:
            sig_parts.append(f"saved by {saved_30d} recruiters this month")

        if sig_parts:
            story += f" Signals: {', '.join(sig_parts)}."

    elif rank <= 50:
        if skill_narrative:
            story += f" Skills: {skill_narrative}."

        if career_trail:
            story += f" Trail: {career_trail}."

        if evidence and evidence_company:
            if evidence_company.lower() != company.lower():
                story += f" Evidence (formerly at {evidence_company}): \"{evidence}\"."
            else:
                story += f" Evidence: \"{evidence}\"."
        elif evidence:
            story += f" Evidence: \"{evidence}\"."

        gaps = []
        if notice > 60:
            gaps.append(f"{notice}-day notice")
        if resp_rate < 0.4:
            gaps.append(f"low response ({int(resp_rate*100)}%)")
        if not is_local and not will_relocate:
            gaps.append("location mismatch")
        if days_inactive and days_inactive > 120:
            gaps.append(f"inactive {days_inactive}d")
        if gaps:
            story += f" Gaps: {', '.join(gaps)}."

        sig_parts = []
        if notice <= 30:
            sig_parts.append(f"{notice}-day notice")
        if resp_rate > 0.7:
            sig_parts.append(f"responsive ({int(resp_rate*100)}%)")
        if gh_score > 65:
            sig_parts.append(f"GitHub {gh_score:.0f}")
        if high_assessments:
            best = max(high_assessments.items(), key=lambda x: x[1])
            sig_parts.append(f"assessed {best[1]:.0f}/100 on {best[0]}")
        if sig_parts:
            story += f" Positives: {', '.join(sig_parts)}."

    else:
        if skill_narrative:
            story += f" Relevant skills: {skill_narrative}."
        else:
            story += " Limited JD skill overlap."

        if career_trail:
            story += f" Background: {career_trail}."

        if evidence:
            story += f" Evidence: \"{evidence}\"."

        limits = []
        if notice > 90:
            limits.append(f"{notice}-day notice")
        if resp_rate < 0.25:
            limits.append(f"low response ({int(resp_rate*100)}%)")
        if not is_local and not will_relocate:
            limits.append("location mismatch")
        if days_inactive and days_inactive > 150:
            limits.append(f"inactive {days_inactive}d")
        if limits:
            story += f" Flags: {', '.join(limits)}."

        if high_assessments:
            best = max(high_assessments.items(), key=lambda x: x[1])
            story += f" Assessed {best[1]:.0f}/100 on {best[0]}."

    story_clean = story.rstrip('.')
    return f"Score {score:.3f}: {story_clean}."