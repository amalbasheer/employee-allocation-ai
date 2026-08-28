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
)
from ai_engine.matching import rank_candidates
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
    domain = category_to_department(project.get("category"))  # 'Data Analytics' or 'Data Science'

    result = {"project_title": project["title"], "roles_needed": roles_needed}

    mentors = get_available_mentors(domain=domain)
    for m in mentors:
        m["skills"] = get_person_skills(m["id"], "employee")
    result["mentors"] = _strip_embeddings(rank_candidates(mentors, requirements))

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


def recommend_mentor_for_training(engagement_id: str) -> list[dict]:
    """
    Skill-based ranking for webinars/demos/workshops — TEAM LEADS ONLY,
    filtered to the training's inferred domain (DA or DS, based on
    which domain's skills the training actually requires).
    """
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

        # Infer domain: which department's employees most commonly have
        # these required skills — majority vote across the required skill_ids
        skill_ids = [r["skill_id"] for r in requirements_rows]
        domain_row = conn.execute(
            text("""
                SELECT ce.department, COUNT(*) as cnt
                FROM employee_skills es
                JOIN company_employees ce ON ce.employee_id = es.employee_id
                WHERE es.skill_id = ANY(:skill_ids)
                GROUP BY ce.department
                ORDER BY cnt DESC
                LIMIT 1
            """),
            {"skill_ids": skill_ids},
        ).mappings().fetchone()
        inferred_domain = domain_row["department"] if domain_row else None

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

    mentors = get_available_mentors(domain=inferred_domain, check_project_conflicts=False)
    team_leads = [
        m for m in mentors
        if m.get("is_team_lead") and m["id"] not in conflicting_ids
    ]

    for tl in team_leads:
        tl["skills"] = get_person_skills(tl["id"], "employee")

    return rank_candidates(team_leads, requirements)

if __name__ == "__main__":
    print("Import recommend_candidates_for_project, recommend_projects_for_person,")
    print("recommend_mentor_for_training, or get_next_mentor_for_batch to use.")