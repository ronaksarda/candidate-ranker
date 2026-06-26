import re

# Evidence-rich sentence detection — compiled once
_EVIDENCE_RE = re.compile(
    r'[^.]*\b(\d+%|\d+ms|\d+k|\d+x|shipped|deployed|built|production|reduced|improved|increased|launched|served|scale)\b[^.]*\.',
    re.IGNORECASE
)


def build_candidate_text(candidate):
    """
    Dense text profile optimized for 600-char embedding window.
    Front-loads: title + years, first sentence from top job, top 5 skills by duration.
    Uses simple string split (no regex) for speed on 100k candidates.
    """
    profile = candidate.get("profile", {})
    title = profile.get("current_title", "")
    yoe = profile.get("years_of_experience", 0)

    parts = [f"{yoe} years {title}"]

    # First sentence of most recent job — fast, no regex
    career = candidate.get("career_history", [])
    if career:
        desc = career[0].get("description", "").strip()
        if desc:
            first = desc.split(".")[0].strip()
            if len(first) > 120:
                first = first[:117] + "..."
            parts.append(first + ".")

    # Top 5 skills by duration
    skills = candidate.get("skills", [])
    if skills:
        top = sorted(skills, key=lambda x: x.get("duration_months", 0), reverse=True)[:5]
        skill_str = ", ".join(s.get("name", "") for s in top if s.get("name"))
        if skill_str:
            parts.append(f"Skills: {skill_str}")

    return " ".join(parts)


def extract_evidence_sentence(candidate):
    """
    Extract the single most evidence-rich sentence from career history.
    Called only on shortlisted candidates (2500), not all 100k.
    Returns (sentence, company) or (None, None).
    """
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
