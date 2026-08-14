"""
recommend.py
Main entry point your teammate's FastAPI endpoint will call.
Ties together project_taxonomy (who's needed), db.py (real data),
and matching.py (the ranking math).
"""

from db import (
    get_project,
    get_project_requirements,
    get_available_mentors,
    get_available_interns,
    get_person_skills,
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
            m for m in result["mentors"] if m.get("can_lead_projects")
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


if __name__ == "__main__":
    print("Import recommend_candidates_for_project or recommend_projects_for_person to use.")