def build_candidate_text(candidate):
    """
    Converts candidate JSON into a dense, clean text profile optimized for embedding.
    """
    profile = candidate.get("profile", {})
    title = profile.get("current_title", "")
    yoe = profile.get("years_of_experience", 0)
    summary = profile.get("summary", "")
    
    lines = []
    lines.append(f"Title: {title}")
    lines.append(f"Experience: {yoe} years")
    if summary:
        lines.append(f"Summary: {summary}")
        
    career = candidate.get("career_history", [])
    if career:
        lines.append("Career History:")
        for job in career[:4]: # Take top 4 recent roles to avoid context overflow
            job_title = job.get("title", "")
            company = job.get("company", "")
            desc = job.get("description", "")
            lines.append(f"- {job_title} at {company}. {desc}")
            
    skills = candidate.get("skills", [])
    if skills:
        # Filter top skills to avoid keyword dumping
        # Prioritize expert/advanced or high duration
        top_skills = sorted(skills, key=lambda x: x.get("duration_months", 0), reverse=True)[:15]
        skill_strs = [f"{s.get('name')} ({s.get('proficiency')}, {s.get('duration_months', 0)} months)" for s in top_skills]
        lines.append("Top Skills: " + ", ".join(skill_strs))
        
    return "\n".join(lines)
