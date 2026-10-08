# ai_engine/optimizer_integration.py
"""
Wires optimizer.py's PuLP-based allocation solving into REAL data —
takes a list of currently open project IDs (or training engagement IDs),
ranks real candidates for each using existing recommendation logic, then
finds the best OVERALL assignment across all of them simultaneously.
"""

from ai_engine.db import engine, get_project, get_training_engagement
from ai_engine.recommend import recommend_candidates_for_project, recommend_mentor_for_training
from ai_engine.optimizer import build_score_matrix, optimize_allocations
from sqlalchemy import text
from concurrent.futures import ThreadPoolExecutor, as_completed
import time
import logging

logging.basicConfig(level=logging.INFO)


def get_bulk_person_skills(person_ids: list[str], person_type: str = "employee") -> dict[str, list[str]]:
    """Fetches skill names for multiple employees or interns in a single bulk SQL query."""
    if not person_ids:
        return {}

    table_name = "employee_skills" if person_type == "employee" else "intern_skills"
    id_col = "employee_id" if person_type == "employee" else "intern_id"

    query = text(f"""
        SELECT ps.{id_col}, s.skill_name 
        FROM {table_name} ps
        JOIN skills s ON ps.skill_id = s.skill_id
        WHERE ps.{id_col} = ANY(:ids)
    """)

    skills_by_person = {pid: [] for pid in person_ids}
    with engine.connect() as conn:
        rows = conn.execute(query, {"ids": person_ids}).fetchall()
        for pid, skill_name in rows:
            if pid in skills_by_person:
                skills_by_person[pid].append(skill_name)

    return skills_by_person


def get_bulk_names(employee_ids: list[str]) -> dict[str, str]:
    """Fetches names for a list of employee IDs in a single bulk SQL query."""
    if not employee_ids:
        return {}
    with engine.connect() as conn:
        rows = conn.execute(
            text("SELECT employee_id, name FROM company_employees WHERE employee_id = ANY(:ids)"),
            {"ids": employee_ids},
        ).fetchall()
    return {r[0]: r[1] for r in rows}


def _fetch_single_project_candidates(project_id: str):
    """Helper worker to fetch candidate team-leads and ALL ranked interns for one project concurrently."""
    t_start = time.time()
    project = get_project(project_id)
    if not project:
        return None

    result = recommend_candidates_for_project(project_id)
    eligible = result.get("eligible_team_leads", [])
    interns = result.get("interns", [])  # MUST return the full ranked list of interns
    session = result.get("session", None)
    day_of_week = result.get("day_of_week", None)

    logging.info(f"Project {project_id} candidate fetch took: {time.time() - t_start:.2f}s")
    return {
        "project_id": project_id,
        "eligible": eligible,
        "interns": interns,  # Pass entire ranked list
        "session": session,
        "day_of_week": day_of_week,
    }


def optimize_multiple_projects(project_ids: list[str]) -> dict:
    """Optimizes team-lead and intern recommendations across multiple open projects in parallel."""
    MAX_BATCH_SIZE = 10
    if len(project_ids) > MAX_BATCH_SIZE:
        logging.warning(f"Batch size {len(project_ids)} exceeds limit. Capping to {MAX_BATCH_SIZE}.")
        project_ids = project_ids[:MAX_BATCH_SIZE]

    t0 = time.time()
    projects_for_optimizer = []
    projects_with_ranked_candidates = {}
    all_project_interns = {}

    # 1. PARALLEL FETCH: Fetch candidate team leads and ranked interns concurrently
    max_workers = min(len(project_ids), 8)
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        future_to_pid = {
            executor.submit(_fetch_single_project_candidates, pid): pid 
            for pid in project_ids
        }
        for future in as_completed(future_to_pid):
            res = future.result()
            if res:
                pid = res["project_id"]
                projects_for_optimizer.append({"project_id": pid})
                projects_with_ranked_candidates[pid] = res["eligible"]
                all_project_interns[pid] = res.get("interns", [])  # Store ranked interns
                
                projects_for_optimizer[-1]["session"] = res["session"]
                projects_for_optimizer[-1]["day_of_week"] = res["day_of_week"]

    logging.info(f"All candidate recommendations fetched concurrently in: {time.time() - t0:.2f}s")

    if not projects_for_optimizer:
        return {"assignments": [], "unstaffed_projects": project_ids}

    # 2. RUN TEAM LEAD OPTIMIZER
    score_matrix = build_score_matrix(projects_with_ranked_candidates, min_score=40.0)

    all_candidates_by_id = {}
    for ranked in projects_with_ranked_candidates.values():
        for c in ranked:
            c_id = str(c.get("id") or c.get("candidate_id"))
            all_candidates_by_id[c_id] = {
                "id": c_id,
                "active_project_count": c.get("active_project_count", 0),
            }

    raw_assignments = optimize_allocations(
        projects_for_optimizer, list(all_candidates_by_id.values()), score_matrix
    )

    # 3. SEQUENTIAL UNIQUE INTERN SELECTION (PREVIEW STAGE)
    assigned_intern_ids = set()
    project_intern_map = {}

    # Process in the order of assignments returned by the optimizer
    for a in raw_assignments:
        pid = a["project_id"]
        candidate_interns = all_project_interns.get(pid, [])
        
        selected_intern = None
        for intern in candidate_interns:
            # Safely extract intern ID (supports 'id', 'intern_id', or 'user_id')
            raw_id = intern.get("id") or intern.get("intern_id") or intern.get("user_id")
            if raw_id is None:
                continue
            
            norm_id = str(raw_id)
            
            # Pick the top recommended intern that hasn't been suggested to another project in this batch
            if norm_id not in assigned_intern_ids:
                selected_intern = intern
                assigned_intern_ids.add(norm_id)
                logging.info(f"[Optimization Preview] Suggested Intern {norm_id} ({intern.get('name')}) for Project {pid}")
                break
        
        if not selected_intern and candidate_interns:
            logging.warning(f"[Optimization Preview] No unassigned intern remaining for Project {pid}.")

        project_intern_map[pid] = selected_intern

    # 4. BULK DATA ENRICHMENT FOR DISPLAY
    candidate_ids = [str(a["candidate_id"]) for a in raw_assignments]
    intern_ids = [
        str(intern.get("id") or intern.get("intern_id") or intern.get("user_id"))
        for intern in project_intern_map.values()
        if intern is not None
    ]

    employee_names = get_bulk_names(candidate_ids)
    candidate_skills_map = get_bulk_person_skills(candidate_ids, person_type="employee")
    intern_skills_map = get_bulk_person_skills(intern_ids, person_type="intern")

    enriched_assignments = []
    for a in raw_assignments:
        pid = a["project_id"]
        cand_id = str(a["candidate_id"])
        
        top_intern = project_intern_map.get(pid)
        top_intern_raw_id = (
            top_intern.get("id") or top_intern.get("intern_id") or top_intern.get("user_id")
            if top_intern else None
        )
        top_intern_id = str(top_intern_raw_id) if top_intern_raw_id is not None else None

        enriched_assignments.append({
            "project_id": pid,
            "candidate_id": cand_id,
            "candidate_name": employee_names.get(cand_id, "Unknown"),
            "candidate_skills": candidate_skills_map.get(cand_id, []),
            "score": a["score"],
            "suggested_intern_id": top_intern_id,
            "suggested_intern_name": top_intern.get("name") if top_intern else None,
            "suggested_intern_skills": intern_skills_map.get(top_intern_id, []) if top_intern_id else [],
        })

    assigned_project_ids = {a["project_id"] for a in raw_assignments}
    unstaffed = [pid for pid in project_ids if pid not in assigned_project_ids]

    return {"assignments": enriched_assignments, "unstaffed_projects": unstaffed}


def _fetch_single_training_candidates(engagement_id: str):
    """Helper worker to fetch mentor candidates for one training engagement concurrently."""
    t_start = time.time()
    engagement = get_training_engagement(engagement_id)
    if not engagement:
        return None

    ranked = recommend_mentor_for_training(engagement_id)
    logging.info(f"Training engagement {engagement_id} mentor fetch took: {time.time() - t_start:.2f}s")
    return {"engagement_id": engagement_id, "ranked": ranked}


def optimize_multiple_trainings(engagement_ids: list[str]) -> dict:
    """Optimizes team-lead assignment across multiple training engagements in parallel."""
    MAX_BATCH_SIZE = 10
    if len(engagement_ids) > MAX_BATCH_SIZE:
        logging.warning(f"Batch size {len(engagement_ids)} exceeds limit. Capping to {MAX_BATCH_SIZE}.")
        engagement_ids = engagement_ids[:MAX_BATCH_SIZE]

    trainings_for_optimizer = []
    trainings_with_ranked_candidates = {}

    max_workers = min(len(engagement_ids), 8)
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        future_to_eid = {
            executor.submit(_fetch_single_training_candidates, eid): eid 
            for eid in engagement_ids
        }
        for future in as_completed(future_to_eid):
            res = future.result()
            if res:
                eid = res["engagement_id"]
                trainings_for_optimizer.append({"project_id": eid})
                trainings_with_ranked_candidates[eid] = res["ranked"]

    if not trainings_for_optimizer:
        return {"assignments": [], "unstaffed_engagements": engagement_ids}

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

    candidate_ids = list({a["candidate_id"] for a in raw_assignments})
    employee_names = get_bulk_names(candidate_ids)
    candidate_skills_map = get_bulk_person_skills(candidate_ids, person_type="employee")

    enriched_assignments = []
    for a in raw_assignments:
        cand_id = a["candidate_id"]
        enriched_assignments.append({
            "engagement_id": a["project_id"],
            "candidate_id": cand_id,
            "candidate_name": employee_names.get(cand_id, "Unknown"),
            "candidate_skills": candidate_skills_map.get(cand_id, []),
            "score": a["score"],
        })

    assigned_ids = {a["project_id"] for a in raw_assignments}
    unstaffed = [eid for eid in engagement_ids if eid not in assigned_ids]

    return {"assignments": enriched_assignments, "unstaffed_engagements": unstaffed}