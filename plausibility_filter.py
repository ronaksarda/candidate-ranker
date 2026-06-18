import datetime
import difflib

CURRENT_YEAR = 2026

def has_duplicate_descriptions(candidate):
    """
    Returns True if the candidate has highly similar (>0.9 ratio) descriptions
    across multiple distinct roles in their career history.
    """
    career_history = candidate.get("career_history", [])
    if len(career_history) < 2:
        return False
        
    descriptions = [job.get("description", "").strip() for job in career_history]
    valid_descriptions = [d for d in descriptions if len(d) > 40]
    
    for i in range(len(valid_descriptions)):
        for j in range(i + 1, len(valid_descriptions)):
            ratio = difflib.SequenceMatcher(None, valid_descriptions[i].lower(), valid_descriptions[j].lower()).ratio()
            if ratio > 0.9:
                return True
                
    return False

def is_honeypot(candidate):
    """
    Returns True if the candidate exhibits impossible patterns (honeypot), else False.
    """
    profile = candidate.get("profile", {})
    yoe = profile.get("years_of_experience", 0)
    
    # Check 1: Expert proficiency in many skills with 0 months duration
    skills = candidate.get("skills", [])
    expert_zero_months = 0
    max_skill_duration = 0
    for s in skills:
        if s.get("proficiency") == "expert" and s.get("duration_months", 0) == 0:
            expert_zero_months += 1
        if s.get("duration_months", 0) > max_skill_duration:
            max_skill_duration = s.get("duration_months", 0)
            
    if expert_zero_months >= 5:
        return True
        
    career_history = candidate.get("career_history", [])
    total_career_months = sum(job.get("duration_months", 0) for job in career_history)
    
    # Check 2: Skill duration greater than total career duration by a large margin (allow some overlap or pre-career learning, but not 10 years extra)
    # e.g., skill duration = 120 months (10 years), but career history sum = 24 months.
    if max_skill_duration > (total_career_months + 48): # 4 years padding for college
        return True
        
    # Check 3: Years of experience claimed is way larger than sum of career history + padding
    # yoe is in years, total_career_months is in months
    if (yoe * 12) > (total_career_months + 60): # allow 5 years missing from history
        return True
        
    # Check 4: Education vs Experience paradox and Education Timeline Weirdness
    education = candidate.get("education", [])
    if education:
        earliest_start = min((edu.get("start_year", CURRENT_YEAR) for edu in education), default=CURRENT_YEAR)
        max_end = max((edu.get("end_year", 0) for edu in education), default=0)
        
        # Assuming typical college start is 18, so candidate age is roughly (CURRENT_YEAR - earliest_start) + 18
        # If experience > age - 15 (started working at 15) -> impossible
        estimated_age = (CURRENT_YEAR - earliest_start) + 18
        if yoe > (estimated_age - 15):
            return True

        # Education Weirdness: Bachelors after Masters
        # We can loosely check if a lower degree starts after a higher degree ends
        bachelors_start = 2050
        masters_start = 0
        for edu in education:
            deg = edu.get("degree", "").lower()
            if deg in ["b.e.", "b.tech", "b.sc", "bachelors"]:
                bachelors_start = min(bachelors_start, edu.get("start_year", 2050))
            if deg in ["m.e.", "m.tech", "m.sc", "masters"]:
                masters_start = max(masters_start, edu.get("start_year", 0))

        if masters_start > 0 and bachelors_start != 2050:
            if masters_start < bachelors_start:
                return True # Started Masters before Bachelors!

        # Massive Gap: If they finished education 10+ years before their first job but have low YoE
        if career_history and max_end > 0:
            first_job_start = 2050
            for job in career_history:
                st = job.get("start_date")
                if st:
                    try:
                        yr = int(st.split("-")[0])
                        first_job_start = min(first_job_start, yr)
                    except:
                        pass
            
            if first_job_start != 2050:
                gap = first_job_start - max_end
                if gap > 10 and yoe < 6:
                    # e.g., graduated 2009, started working 2022 (gap 13), but only 4.2 YoE
                    return True
            
    # Check 5: Overlapping dates producing excessive duration
    # Simple check: max end date - min start date across career history
    # If this chronological span is much smaller than sum of durations, they are claiming multiple full-time roles simultaneously
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
                # If they claim 2x more duration than chronological time
                if total_career_months > (chronological_months * 1.5 + 24):
                    return True
        except ValueError:
            pass # ignore date parse errors
            
    # Check 6: "Time-Traveling Tech Liars" (Honeypot keyword stuffers)
    # E.g. claiming 80 months of QLoRA (released 2023) or LangChain (released late 2022)
    # Assuming current year is ~2026, max possible duration is ~36-48 months
    for s in skills:
        name = s.get("name", "").lower()
        dur = s.get("duration_months", 0)
        if name == "qlora" and dur > 36:
            return True
        if name == "langchain" and dur > 48:
            return True
        if name == "chatgpt" and dur > 44:
            return True
        if name == "llama-2" and dur > 36:
            return True

    # Check 7: Skills Without Evidence Trap
    # If they claim advanced/expert in vector DBs but never mention them in career history
    career_text = " ".join([job.get("description", "").lower() for job in career_history])
    summary_text = profile.get("summary", "").lower()
    full_text = career_text + " " + summary_text
    
    vector_dbs = {"qdrant", "milvus", "pinecone", "weaviate", "faiss", "semantic search"}
    claimed_vector_dbs = [s.get("name", "").lower() for s in skills if s.get("name", "").lower() in vector_dbs]
    
    # If they claim multiple vector DBs in skills, but have ZERO mentions of any vector DBs in career_history
    if len(claimed_vector_dbs) >= 2:
        evidence_found = False
        for db in vector_dbs:
            if db in career_text:
                evidence_found = True
                break
        if not evidence_found:
            return True # Keyword stuffer trap!

    # Check 8: Computer Vision Disqualifier
    # JD explicitly rejects primary CV without NLP/IR. If they admit limited NLP experience or transitioning to NLP.
    if "professional experience there is limited" in full_text and "transitioning toward nlp" in full_text:
        return True
    
    # If they explicitly state their primary expertise is CV
    if "most of my project work has been in cv" in full_text:
        return True

    return False



