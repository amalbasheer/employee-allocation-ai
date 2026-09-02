"""
recommend.py
Main entry point your teammate's FastAPI endpoint will call.
Ties together project_taxonomy (who's needed), db.py (real data),
and matching.py (the ranking math).
"""

from sqlalchemy import text
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
)

from ai_engine.matching import rank_candidates, score_with_workload_penalty
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

def recommend_candidates_for_project(project_id: str) -> dict:
    project = get_project(project_id)
    if not project:
        raise ValueError(f"No project found with id {project_id}")

    requirements = get_project_requirements(project_id)
    roles_needed = get_required_roles(project["project_type"])
    domain = category_to_department(project.get("category"))

    result = {"project_title": project["title"], "roles_needed": roles_needed}

    # Get ALL mentors (no hard exclusion), then rank by skill, then apply
    # a workload penalty based on how many active projects they already have
    all_mentors = get_all_mentors_with_project_count(domain=domain)
    for m in all_mentors:
        m["skills"] = get_person_skills(m["id"], "employee")

    ranked_mentors = rank_candidates(all_mentors, requirements)
    for candidate in ranked_mentors:
        raw_skill_score = candidate["suitability_score"]
        candidate["suitability_score"] = score_with_workload_penalty(
            raw_skill_score, candidate.get("active_project_count", 0)
        )
    ranked_mentors.sort(key=lambda c: c["suitability_score"], reverse=True)

    result["mentors"] = _strip_embeddings(ranked_mentors)

    if "intern" in roles_needed:
        interns = get_available_interns(domain=domain)
        for i in interns:
            i["skills"] = get_person_skills(i["id"], "intern")
        result["interns"] = _strip_embeddings(rank_candidates(interns, requirements))

        result["eligible_team_leads"] = [
            m for m in result["mentors"] if m.get("is_team_lead")
        ]

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

def recommend_mentor_for_training(engagement_id: str) -> list[dict]:
    with engine.connect() as conn:
        engagement = conn.execute(
            text("SELECT * FROM training_engagements WHERE engagement_id = :eid"),
            {"eid": engagement_id},
        ).mappings().fetchone()

        if not engagement:
            raise ValueError(f"No training engagement found with id {engagement_id}")

        requirements_rows = conn.execute(
            text("""
                SELECT tr.skill_id, tr.min_proficiency, tr.is_mandatory, tr.requirement_embedding
                FROM training_requirements tr
                WHERE tr.engagement_id = :eid
            """),
            {"eid": engagement_id},
        ).mappings().fetchall()

        conflicting_leads = conn.execute(
            text("""
                SELECT DISTINCT a.resource_id
                FROM allocations a
                JOIN training_engagements te ON te.engagement_id = a.reference_id
                WHERE a.reference_type = 'training'
                  AND a.status IN ('proposed', 'assigned')
                  AND te.engagement_id != :eid
                  AND te.start_date <= :end_date
                  AND te.end_date >= :start_date
            """),
            {"eid": engagement_id, "start_date": engagement["start_date"], "end_date": engagement["end_date"]},
        ).fetchall()
        conflicting_ids = {row[0] for row in conflicting_leads}

    requirements = [
        {
            "skill_id": r["skill_id"],
            "embedding": _parse_embedding(r["requirement_embedding"]),
            "min_proficiency": r["min_proficiency"],
            "is_mandatory": r["is_mandatory"],
        }
        for r in requirements_rows
    ]

    # Online sessions: no region filtering, anyone eligible.
    # Offline sessions: filter to mentors whose location matches.
    region_filter = None if engagement.get("mode") == "online" else engagement.get("region")

    mentors = get_available_mentors(domain=engagement.get("domain"), region=region_filter, check_project_conflicts=False)
    team_leads = [
        m for m in mentors
        if m.get("is_team_lead") and m["id"] not in conflicting_ids
    ]

    for tl in team_leads:
        tl["skills"] = get_person_skills(tl["id"], "employee")

    ranked = rank_candidates(team_leads, requirements)

    training_audience = engagement.get("audience")
    for candidate in ranked:
        raw_skill_score = candidate["suitability_score"]
        print(f"DEBUG: {candidate['name']}, candidate_audience={candidate.get('preferred_audience')!r}, training_audience={training_audience!r}")
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