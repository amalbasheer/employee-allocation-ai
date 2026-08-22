"""
recommend.py
Main entry point your teammate's FastAPI endpoint will call.
Ties together project_taxonomy (who's needed), db.py (real data),
and matching.py (the ranking math).
"""

from sqlalchemy import text
from db import (
    engine,
    get_project,
    get_project_requirements,
    get_available_mentors,
    get_available_interns,
    get_person_skills,
    _parse_embedding,
)
from matching import rank_candidates
from project_taxonomy import get_required_roles


def recommend_candidates_for_project(project_id: str) -> dict:
    """
    Given a project, returns ranked candidates for whichever roles it
    actually needs — mentors only for training engagements, or both
    interns and team-lead-eligible mentors for work engagements.
    """
    project = get_project(project_id)
    if not project:
        raise ValueError(f"No project found with id {project_id}")

    requirements = get_project_requirements(project_id)
    roles_needed = get_required_roles(project["project_type"])

    result = {"project_title": project["title"], "roles_needed": roles_needed}

    mentors = get_available_mentors()
    for m in mentors:
        m["skills"] = get_person_skills(m["id"], "employee")
    result["mentors"] = rank_candidates(mentors, requirements)

    if "intern" in roles_needed:
        interns = get_available_interns()
        for i in interns:
            i["skills"] = get_person_skills(i["id"], "intern")
        result["interns"] = rank_candidates(interns, requirements)

        result["eligible_team_leads"] = [
            m for m in result["mentors"] if m.get("is_team_lead")
        ]

    return result


def recommend_projects_for_person(person_id: str, person_type: str, open_projects: list[dict]) -> list[dict]:
    """
    Reverse direction: given a person (right after resume parsing),
    rank all open projects by how well they fit.
    """
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
    Skill-based ranking for webinars/demos/workshops.
    TEAM LEADS ONLY — business rule, not every mentor is eligible.
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

    requirements = [
        {
            "skill_id": r["skill_id"],
            "embedding": _parse_embedding(r["requirement_embedding"]),
            "min_proficiency": r["min_proficiency"],
            "is_mandatory": r["is_mandatory"],
        }
        for r in requirements_rows
    ]

    mentors = get_available_mentors()
    team_leads = [m for m in mentors if m.get("is_team_lead")]  # ← team-lead-only filter

    for tl in team_leads:
        tl["skills"] = get_person_skills(tl["id"], "employee")

    return rank_candidates(team_leads, requirements)


def get_next_mentor_for_batch(domain: str) -> dict:
    """
    Round-robin: picks the team lead in this domain with the fewest
    current batch assignments — pure fairness, no skill matching.
    """
    with engine.connect() as conn:
        row = conn.execute(
            text("""
                SELECT ce.employee_id, ce.name, COUNT(sb.batch_id) AS batch_count
                FROM company_employees ce
                LEFT JOIN student_batches sb ON sb.mentor_id = ce.employee_id
                WHERE ce.is_team_lead = TRUE AND ce.department = :domain
                GROUP BY ce.employee_id, ce.name
                ORDER BY batch_count ASC, ce.employee_id ASC
                LIMIT 1
            """),
            {"domain": domain},
        ).mappings().fetchone()
    return dict(row) if row else None


if __name__ == "__main__":
    print("Import recommend_candidates_for_project, recommend_projects_for_person,")
    print("recommend_mentor_for_training, or get_next_mentor_for_batch to use.")