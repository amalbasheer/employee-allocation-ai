"""
recommend.py
Main entry point your teammate's FastAPI endpoint will call.
Ties together project_taxonomy (who's needed), db.py (real data),
and matching.py (the ranking math).
"""

from sqlalchemy import text
from datetime import date, datetime
from ai_engine.db import (
    engine,
    get_project,
    get_project_requirements,
    get_available_mentors,
    get_available_interns,
    get_person_skills,
    get_next_mentor_for_batch,
    _parse_embedding,
    category_to_department,
    get_all_mentors_with_project_count,
    check_project_readiness,
    get_project_assignments,
    get_bulk_person_skills,

)

from datetime import timedelta
from ai_engine.matching import rank_candidates, score_with_workload_penalty, score_with_training_load_penalty
from ai_engine.project_taxonomy import get_required_roles


def _strip_embeddings(candidates: list[dict]) -> list[dict]:
    """Remove embedding vectors before returning to the API, but keep
    readable skill names instead of raw skill_ids."""
    with engine.connect() as conn:
        skill_names = dict(
            conn.execute(text("SELECT skill_id, skill_name FROM skills")).fetchall()
        )

    cleaned = []
    for c in candidates:
        c_copy = {k: v for k, v in c.items() if k != "skills"}
        c_copy["skills"] = [
            skill_names.get(s["skill_id"], s["skill_id"])
            for s in c.get("skills", [])
        ]
        cleaned.append(c_copy)
    return cleaned

def get_this_weeks_monday() -> date:
    today = date.today()
    return today - timedelta(days=today.weekday())


def recommend_candidates_for_project(project_id: str) -> dict:
    project = get_project(project_id)
    if not project:
        raise ValueError(f"No project found with id {project_id}")

    requirements = get_project_requirements(project_id)
    roles_needed = get_required_roles(project["project_type"])
    domain = category_to_department(project.get("category"))
    current_monday = get_this_weeks_monday()

    result = {"project_title": project["title"], "roles_needed": roles_needed}

    # -------------------------------------------------------------
    # 1. MENTORS (EMPLOYEES) — Fetch skills & session availability.
    # Project mentors are team-leads-only — this is decided HERE,
    # not by the caller/frontend, so it's clear from this file alone.
    # -------------------------------------------------------------
    all_mentors = get_all_mentors_with_project_count(domain=domain)
    mentor_ids = [m["id"] for m in all_mentors]
    mentor_skills_map = get_bulk_person_skills(mentor_ids, "employee")

    # Bulk fetch session availability ONLY for employees
    mentor_availability_map = {}
    if mentor_ids:
        with engine.connect() as conn:
            avail_rows = conn.execute(
                text("""
                    SELECT resource_id, available_hours, session
                    FROM availability
                    WHERE week_start_date = :week_start
                      AND resource_id = ANY(:resource_ids)
                """),
                {"week_start": current_monday, "resource_ids": mentor_ids}
            ).fetchall()

            for row in avail_rows:
                res_id, hrs, session = row[0], float(row[1] or 0.0), str(row[2]).lower().strip()
                if res_id not in mentor_availability_map:
                    mentor_availability_map[res_id] = {
                        "morning_hours": 0.0,
                        "evening_hours": 0.0,
                    }
                if session == "morning":
                    mentor_availability_map[res_id]["morning_hours"] = hrs
                elif session == "evening":
                    mentor_availability_map[res_id]["evening_hours"] = hrs

    for m in all_mentors:
        m["skills"] = mentor_skills_map.get(m["id"], [])

        m_avail = mentor_availability_map.get(
            m["id"],
            {"morning_hours": 20.0, "evening_hours": 20.0}
        )

        m["session_availability"] = {
            "morning": m_avail["morning_hours"],
            "evening": m_avail["evening_hours"]
        }
        morning_hrs = m_avail["morning_hours"]
        evening_hrs = m_avail["evening_hours"]

        if morning_hrs >= evening_hrs and morning_hrs > 1:
            m["session"] = "morning"
        elif evening_hrs > morning_hrs and evening_hrs > 1:
            m["session"] = "evening"
        else:
            m["session"] = "morning"

    ranked_mentors = rank_candidates(all_mentors, requirements)
    for candidate in ranked_mentors:
        raw_skill_score = candidate["suitability_score"]
        candidate["suitability_score"] = score_with_workload_penalty(
            raw_skill_score, candidate.get("active_project_count", 0)
        )
    ranked_mentors.sort(key=lambda c: c["suitability_score"], reverse=True)

    # Filter to team-leads-only HERE, the single source of truth
    team_lead_mentors = [m for m in ranked_mentors if m.get("is_team_lead")]
    result["mentors"] = _strip_embeddings(team_lead_mentors)
    result["eligible_team_leads"] = result["mentors"]  # same data, kept for backward compatibility

    # -------------------------------------------------------------
    # 2. INTERNS — Fetch skills only (NO availability check)
    # -------------------------------------------------------------
    if "intern" in roles_needed:
        interns = get_available_interns(domain=domain)
        intern_ids = [i["id"] for i in interns]
        intern_skills_map = get_bulk_person_skills(intern_ids, "intern")

        for i in interns:
            i["skills"] = intern_skills_map.get(i["id"], [])

        result["interns"] = _strip_embeddings(rank_candidates(interns, requirements))

        with engine.connect() as conn:
            completed_counts = conn.execute(
                text("""
                    SELECT resource_id, COUNT(*) AS completed_count
                    FROM allocations
                    WHERE resource_type = 'intern' AND reference_type = 'project' AND status = 'completed'
                    GROUP BY resource_id
                """)
            ).fetchall()
        completed_count_map = {row[0]: row[1] for row in completed_counts}
        for intern in result["interns"]:
            intern["completed_projects_count"] = completed_count_map.get(intern["id"], 0)

        assignments = get_project_assignments(project_id)
        current_interns = [a for a in assignments if a["resource_type"] == "intern"]

        missing_ids = [i["resource_id"] for i in current_interns if i["resource_id"] not in intern_skills_map]
        if missing_ids:
            extra_skills_map = get_bulk_person_skills(missing_ids, "intern")
            intern_skills_map.update(extra_skills_map)

        current_interns_with_scores = []
        for i in current_interns:
            i_skills = intern_skills_map.get(i["resource_id"], [])
            ranked = rank_candidates([{"id": i["resource_id"], "skills": i_skills}], requirements)
            real_score = ranked[0]["suitability_score"] if ranked else 0.0
            current_interns_with_scores.append({
                "id": i["resource_id"],
                "name": i["name"],
                "score": real_score,
            })
        result["currently_assigned_interns"] = current_interns_with_scores

    return result


def recommend_projects_for_person(person_id: str, person_type: str, open_projects: list[dict]) -> list[dict]:
    person_skills = get_person_skills(person_id, person_type)

    scored = []
    for project in open_projects:
        requirements = get_project_requirements(project["project_id"])
        ranked = rank_candidates(
            [{"id": person_id, "skills": person_skills}], requirements
        )
        score = ranked[0]["suitability_score"] if ranked else 0.0
        scored.append({**project, "suitability_score": score})

    return sorted(scored, key=lambda p: p["suitability_score"], reverse=True)

def score_with_audience_preference(skill_score: float, candidate_audience: str, training_audience: str) -> float:
    """
    Combines skill match with audience preference into one weighted
    score. Treats preferred_audience as a comma-separated list and
    checks genuine membership, not just substring matching.
    """
    if not training_audience:
        return skill_score  # nothing to compare against, leave score untouched

    if not candidate_audience:
        multiplier = 0.85  # no preference set at all, treat as mismatch
    else:
        candidate_list = [a.strip().lower() for a in candidate_audience.split(",")]
        training_value = training_audience.strip().lower()
        audience_matches = training_value in candidate_list
        multiplier = 1.0 if audience_matches else 0.85

    return round(skill_score * multiplier, 2)

def calculate_daily_occupied_hours(
    conn, 
    mentor_id: str, 
    domain: str, 
    training_date: datetime.date, 
    training_session: str
) -> float:
    session_lower = training_session.lower().strip()
    day_name = training_date.strftime("%A")

    # 1. PROJECT OCCUPIED HOURS — session column doesn't exist, remove that filter
    project_query = text("""
        SELECT COUNT(p.project_id) AS active_project_count
        FROM allocations a
        JOIN projects p ON p.project_id = a.reference_id
        WHERE a.resource_id = :mentor_id
          AND a.reference_type = 'project'
          AND LOWER(p.status) = 'in progress'
    """)
    project_res = conn.execute(
        project_query, 
        {"mentor_id": mentor_id}
    ).fetchone()
    
    active_projects = project_res[0] if project_res else 0
    project_hours = 0.0

    if active_projects > 0:
        if domain.lower() in ["data science", "datascience", "ds"]:
            project_hours = 1.0
        else:
            project_hours = float(active_projects) * 1.0

    # 2. STUDENT BATCH OCCUPIED HOURS — this column genuinely exists, keep as-is
    batch_query = text("""
        SELECT day_of_week
        FROM student_batches
        WHERE mentor_id = :mentor_id
          AND status IN ('open', 'in_progress', 'active')
          AND start_date <= :t_date
          AND end_date >= :t_date
          AND LOWER(session) = :session
    """)
    batch_rows = conn.execute(
        batch_query, 
        {"mentor_id": mentor_id, "t_date": training_date, "session": session_lower}
    ).fetchall()

    matching_batch_count = 0
    for row in batch_rows:
        days = row[0]
        if isinstance(days, list):
            if day_name in days or day_name[:3] in days:
                matching_batch_count += 1
        elif isinstance(days, str):
            if day_name.lower() in days.lower():
                matching_batch_count += 1

    batch_hours = float(matching_batch_count) * 2.0

    return project_hours + batch_hours


def recommend_mentor_for_training(engagement_id: str, session_capacity_hours: float = 4.0) -> list[dict]:
    with engine.connect() as conn:
        # Fetch training details
        engagement = conn.execute(
            text("SELECT * FROM training_engagements WHERE engagement_id = :eid"),
            {"eid": engagement_id},
        ).mappings().fetchone()

        if not engagement:
            raise ValueError(f"No training engagement found with id {engagement_id}")

        training_date = engagement["start_date"]
        training_session = engagement.get("session", "morning")
        required_hours = float(engagement.get("required_hours") or engagement.get("duration_hours") or 1.0)
        domain = engagement.get("domain", "")

        # Fetch requirements & conflict checks
        requirements_rows = conn.execute(
            text("SELECT * FROM training_requirements WHERE engagement_id = :eid"),
            {"eid": engagement_id},
        ).mappings().fetchall()

        # Fetch candidate mentors / team leads
        region_filter = None if engagement.get("mode") == "online" else engagement.get("region")
        mentors = get_available_mentors(domain=domain, region=region_filter, check_project_conflicts=False)
        team_leads = [m for m in mentors if m.get("is_team_lead")]

        # -------------------------------------------------------------
        # FILTER BY DAILY SESSION AVAILABILITY
        # -------------------------------------------------------------
        available_team_leads = []
        for tl in team_leads:
            occupied_hrs = calculate_daily_occupied_hours(
                conn=conn,
                mentor_id=tl["id"],
                domain=domain,
                training_date=training_date,
                training_session=training_session
            )
            
            daily_available_hrs = max(0.0, session_capacity_hours - occupied_hrs)
            
            # Keep candidate ONLY if daily available hours >= training required hours
            if daily_available_hrs >= required_hours:
                tl["occupied_hours"] = occupied_hrs
                tl["daily_available_hours"] = daily_available_hrs
                tl["skills"] = get_person_skills(tl["id"], "employee")
                available_team_leads.append(tl)

        # Parse requirements and rank remaining candidates
        requirements = [
            {
                "skill_id": r["skill_id"],
                "embedding": _parse_embedding(r["requirement_embedding"]),
                "min_proficiency": r["min_proficiency"],
                "is_mandatory": r["is_mandatory"],
            }
            for r in requirements_rows
        ]

        ranked = rank_candidates(available_team_leads, requirements)

        # Apply scoring adjustments
        training_audience = engagement.get("audience")
        for candidate in ranked:
            raw_skill_score = candidate["suitability_score"]
            candidate["suitability_score"] = score_with_audience_preference(
                raw_skill_score, candidate.get("preferred_audience"), training_audience
            )

        ranked.sort(key=lambda c: c["suitability_score"], reverse=True)
        return ranked

if __name__ == "__main__":
    print("Import recommend_candidates_for_project, recommend_projects_for_person,")
    print("recommend_mentor_for_training, or get_next_mentor_for_batch to use.")

def compare_mentors_for_project(project_id: str, mentor_name_1: str, mentor_name_2: str) -> dict:
    """
    Compares two specific mentors for a project, using the same real
    scoring as recommend_candidates_for_project — just filtered to
    the two named people, with a direct verdict on who's the better fit.
    """
    from ai_engine.recommend import recommend_candidates_for_project
    result = recommend_candidates_for_project(project_id)
    all_candidates = result.get("mentors", []) + result.get("eligible_team_leads", [])

    m1 = next((c for c in all_candidates if c["name"].lower() == mentor_name_1.lower()), None)
    m2 = next((c for c in all_candidates if c["name"].lower() == mentor_name_2.lower()), None)

    if not m1 or not m2:
        return {"error": f"One or both mentors not found in the candidate pool for this project."}

    winner = mentor_name_1 if m1["suitability_score"] > m2["suitability_score"] else mentor_name_2
    return {
        "mentor_1": {"name": m1["name"], "score": m1["suitability_score"], "skills": m1.get("skills", [])},
        "mentor_2": {"name": m2["name"], "score": m2["suitability_score"], "skills": m2.get("skills", [])},
        "recommended": winner,
    }

def explain_exclusion(project_id: str, mentor_name: str) -> dict:
    from ai_engine.db import get_employee_by_name

    project = get_project(project_id)
    person = get_employee_by_name(mentor_name)

    if not person:
        return {"error": f"No employee found with name '{mentor_name}'."}

    reasons = []
    with engine.connect() as conn:
        busy = conn.execute(
            text("SELECT 1 FROM allocations WHERE resource_id = :id AND status IN ('proposed','assigned') AND reference_type = 'project'"),
            {"id": person["employee_id"]},
        ).fetchone()
    if busy:
        reasons.append("Already assigned to another active project")

    expected_domain = category_to_department(project.get("category"))
    if expected_domain and person.get("department") != expected_domain:
        reasons.append(f"Wrong domain — project needs {expected_domain}, this person is in {person.get('department')}")

    requirements = get_project_requirements(project_id)
    person_skills = {s["skill_id"] for s in get_person_skills(person["employee_id"], "employee")}
    missing_mandatory = [r["skill_id"] for r in requirements if r["is_mandatory"] and r["skill_id"] not in person_skills]
    if missing_mandatory:
        reasons.append(f"Missing mandatory skill(s) (skill_ids): {', '.join(missing_mandatory)}")

    if not reasons:
        # Person IS eligible — compute their real score and compare to who WAS recommended
        result = recommend_candidates_for_project(project_id)
        all_candidates = result.get("mentors", []) + result.get("eligible_team_leads", [])

        this_person = next((c for c in all_candidates if c["name"].lower() == mentor_name.lower()), None)
        top_candidate = all_candidates[0] if all_candidates else None

        if this_person and top_candidate:
            reasons.append(
                f"Eligible, but ranked lower — {mentor_name} scored {this_person['suitability_score']}, "
                f"while the top recommendation, {top_candidate['name']}, scored {top_candidate['suitability_score']}."
            )
        else:
            reasons.append("Eligible, but ranked lower than the selected candidate(s) on overall skill match.")

    return {"mentor": mentor_name, "project": project["title"], "reasons": reasons}

def recommend_backup_for_project(project_id: str) -> dict:
    """
    Given a project, finds who's currently the team lead, and recommends
    the next best replacement, explicitly naming both people.
    """
    assignments = get_project_assignments(project_id)
    current_lead = next((a for a in assignments if a["resource_type"] == "employee"), None)

    result = recommend_candidates_for_project(project_id)
    candidates = result.get("eligible_team_leads", [])
    replacement = next((c for c in candidates if not current_lead or c["name"] != current_lead["name"]), None)

    return {
        "current_mentor": current_lead["name"] if current_lead else "No one currently assigned",
        "recommended_replacement": replacement["name"] if replacement else None,
        "replacement_score": replacement["suitability_score"] if replacement else None,
    }