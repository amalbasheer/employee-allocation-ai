# ai_engine/optimizer_integration.py
"""
Wires optimizer.py's PuLP-based allocation solving into REAL data —
takes a list of currently open project IDs (or training engagement IDs),
ranks real candidates for each using existing recommendation logic, then
finds the best OVERALL assignment across all of them simultaneously,
preventing any one person from being over-assigned across the batch.

Interns are NOT run through the optimizer — since they're already
restricted to one project at a time by get_available_interns(), the
over-concentration problem doesn't apply to them, so the existing
per-project intern recommendation is used directly instead.
"""

from ai_engine.db import engine, get_project, get_training_engagement, get_person_skills
from ai_engine.recommend import recommend_candidates_for_project, recommend_mentor_for_training
from ai_engine.optimizer import build_score_matrix, optimize_allocations
from sqlalchemy import text


def get_skill_names(skill_ids: list[str]) -> list[str]:
    """Resolves raw skill_ids into readable skill names for display."""
    if not skill_ids:
        return []
    with engine.connect() as conn:
        rows = conn.execute(
            text("SELECT skill_id, skill_name FROM skills WHERE skill_id = ANY(:ids)"),
            {"ids": skill_ids},
        ).fetchall()
    return [r[1] for r in rows]


def optimize_multiple_projects(project_ids: list[str]) -> dict:
    """
    Optimizes team-lead assignment across multiple open projects at once,
    then attaches the best available intern per project (using existing
    logic, since interns don't need optimization).
    """
    projects_for_optimizer = []
    projects_with_ranked_candidates = {}
    intern_suggestions = {}

    for project_id in project_ids:
        project = get_project(project_id)
        if not project:
            continue

        projects_for_optimizer.append({"project_id": project_id})

        result = recommend_candidates_for_project(project_id)
        projects_with_ranked_candidates[project_id] = result.get("eligible_team_leads", [])

        interns = result.get("interns", [])
        intern_suggestions[project_id] = interns[0] if interns else None

    score_matrix = build_score_matrix(projects_with_ranked_candidates, min_score=40.0)

    all_candidates_by_id = {}
    for ranked in projects_with_ranked_candidates.values():
        for c in ranked:
            all_candidates_by_id[c["id"]] = {
                "id": c["id"],
                "active_project_count": c.get("active_project_count", 0),
            }

    raw_assignments = optimize_allocations(
        projects_for_optimizer, list(all_candidates_by_id.values()), score_matrix
    )

    with engine.connect() as conn:
        name_lookup = {}
        if raw_assignments:
            ids = [a["candidate_id"] for a in raw_assignments]
            rows = conn.execute(
                text("SELECT employee_id, name FROM company_employees WHERE employee_id = ANY(:ids)"),
                {"ids": ids},
            ).fetchall()
            name_lookup = {r[0]: r[1] for r in rows}

    enriched_assignments = []
    for a in raw_assignments:
        skills = get_person_skills(a["candidate_id"], "employee")
        skill_names = get_skill_names([s["skill_id"] for s in skills])

        top_intern = intern_suggestions.get(a["project_id"])
        intern_skill_names = []
        if top_intern:
            intern_skills = get_person_skills(top_intern["id"], "intern")
            intern_skill_names = get_skill_names([s["skill_id"] for s in intern_skills])

        enriched_assignments.append({
            "project_id": a["project_id"],
            "candidate_id": a["candidate_id"],
            "candidate_name": name_lookup.get(a["candidate_id"], "Unknown"),
            "candidate_skills": skill_names,
            "score": a["score"],
            "suggested_intern_id": top_intern["id"] if top_intern else None,
            "suggested_intern_name": top_intern["name"] if top_intern else None,
            "suggested_intern_skills": intern_skill_names,
        })

    assigned_project_ids = {a["project_id"] for a in raw_assignments}
    unstaffed = [pid for pid in project_ids if pid not in assigned_project_ids]

    return {"assignments": enriched_assignments, "unstaffed_projects": unstaffed}


def optimize_multiple_trainings(engagement_ids: list[str]) -> dict:
    """
    Optimizes team-lead assignment across multiple training engagements
    at once — same concept as project optimization, preventing the same
    team lead from being over-assigned across simultaneous trainings.
    """
    trainings_for_optimizer = []
    trainings_with_ranked_candidates = {}

    for engagement_id in engagement_ids:
        engagement = get_training_engagement(engagement_id)
        if not engagement:
            continue

        trainings_for_optimizer.append({"project_id": engagement_id})

        ranked = recommend_mentor_for_training(engagement_id)
        trainings_with_ranked_candidates[engagement_id] = ranked

    score_matrix = build_score_matrix(trainings_with_ranked_candidates, min_score=40.0)

    all_candidates_by_id = {}
    for ranked in trainings_with_ranked_candidates.values():
        for c in ranked:
            all_candidates_by_id[c["id"]] = {
                "id": c["id"],
                "active_project_count": c.get("active_training_count", 0),
            }

    raw_assignments = optimize_allocations(
        trainings_for_optimizer, list(all_candidates_by_id.values()), score_matrix
    )

    with engine.connect() as conn:
        name_lookup = {}
        if raw_assignments:
            ids = [a["candidate_id"] for a in raw_assignments]
            rows = conn.execute(
                text("SELECT employee_id, name FROM company_employees WHERE employee_id = ANY(:ids)"),
                {"ids": ids},
            ).fetchall()
            name_lookup = {r[0]: r[1] for r in rows}

    enriched_assignments = []
    for a in raw_assignments:
        skills = get_person_skills(a["candidate_id"], "employee")
        skill_names = get_skill_names([s["skill_id"] for s in skills])
        enriched_assignments.append({
            "engagement_id": a["project_id"],
            "candidate_id": a["candidate_id"],
            "candidate_name": name_lookup.get(a["candidate_id"], "Unknown"),
            "candidate_skills": skill_names,
            "score": a["score"],
        })

    assigned_ids = {a["project_id"] for a in raw_assignments}
    unstaffed = [eid for eid in engagement_ids if eid not in assigned_ids]

    return {"assignments": enriched_assignments, "unstaffed_engagements": unstaffed}