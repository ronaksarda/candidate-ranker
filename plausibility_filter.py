import datetime

CURRENT_YEAR = 2026

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
        
    # Check 4: Education vs Experience paradox
    education = candidate.get("education", [])
    if education:
        earliest_start = min((edu.get("start_year", CURRENT_YEAR) for edu in education), default=CURRENT_YEAR)
        # Assuming typical college start is 18, so candidate age is roughly (CURRENT_YEAR - earliest_start) + 18
        # If experience > age - 15 (started working at 15) -> impossible
        estimated_age = (CURRENT_YEAR - earliest_start) + 18
        if yoe > (estimated_age - 15):
            return True
            
    # Check 5: Overlapping dates producing excessive duration
    # Simple check: max end date - min start date across career history
    # If this chronological span is much smaller than sum of durations, they are claiming multiple full-time roles simultaneously
    # We will skip complex date parsing for speed if not strictly necessary, but let's do a basic check.
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
            
    return False

