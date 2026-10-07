"""
recommend.py
Main entry point your teammate's FastAPI endpoint will call.
Ties together project_taxonomy (who's needed), db.py (real data),
and matching.py (the ranking math).
"""

import re

from sqlalchemy import text
from datetime import date, datetime
from .matching import cosine_similarity

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

from datetime import datetime, timedelta
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
    training_session: str,
    current_engagement_id: str = None
) -> dict:
    """
    Calculates real, schedule-based occupied hours for a mentor on a
    specific training date/session, using ACTUAL day/session data from
    both projects and student_batches (not just active-count approximations).
    Also flags training-to-training conflicts for the caller to act on.
    """
    session_lower = training_session.lower().strip()
    day_full = training_date.strftime("%A")
    day_abbr = training_date.strftime("%a")

    # -------------------------------------------------------------
    # 1. PROJECT OCCUPIED HOURS — real day/session overlap check,
    # flat 1 hour if ANY active project overlaps (not multiplied by count)
    # -------------------------------------------------------------
    project_query = text("""
        SELECT p.title
        FROM allocations a
        JOIN projects p ON p.project_id = a.reference_id
        WHERE a.resource_id = :mentor_id
          AND a.reference_type = 'project'
          AND LOWER(p.status) != 'completed'
          AND LOWER(p.session) = :session
          AND (
              LOWER(p.day_of_week) LIKE '%' || :day_full || '%'
              OR LOWER(p.day_of_week) LIKE '%' || :day_abbr || '%'
          )
    """)
    project_rows = conn.execute(
        project_query,
        {"mentor_id": mentor_id, "session": session_lower,
         "day_full": day_full.lower(), "day_abbr": day_abbr.lower()}
    ).fetchall()
    project_conflict_name = ", ".join(r[0] for r in project_rows) if project_rows else None
    project_hours = 1.0 if project_rows else 0.0
    
    # -------------------------------------------------------------
    # 2. STUDENT BATCH OCCUPIED HOURS — fixed to match abbreviated
    # day names (e.g. "Tue, Fri") correctly
    # -------------------------------------------------------------
    batch_query = text("""
        SELECT day_of_week, batch_name FROM student_batches
        WHERE mentor_id = :mentor_id
          AND status IN ('open', 'in_progress', 'active')
          AND start_date <= :t_date AND end_date >= :t_date
          AND LOWER(session) = :session
    """)
    batch_rows = conn.execute(
        batch_query, {"mentor_id": mentor_id, "t_date": training_date, "session": session_lower}
    ).fetchall()

    matching_batch_count = 0
    batch_conflict_name = None
    for row in batch_rows:
        days_lower = (row[0] or "").lower()
        if day_full.lower() in days_lower or day_abbr.lower() in days_lower:
            matching_batch_count += 1
            batch_conflict_name = row[1]

    batch_hours = float(matching_batch_count) * 2.0

    # -------------------------------------------------------------
    # 3. OTHER TRAINING CONFLICTS — same-session (hard) vs
    # different-session-offline (soft) on the SAME date
    # -------------------------------------------------------------
    training_conflict_query = text("""
        SELECT te.title, LOWER(te.session) AS t_session, LOWER(te.mode) AS t_mode
        FROM allocations a
        JOIN training_engagements te ON te.engagement_id = a.reference_id
        WHERE a.resource_id = :mentor_id AND a.reference_type = 'training'
          AND a.status IN ('proposed', 'assigned')
          AND te.start_date = :t_date
          AND te.engagement_id != :current_eid
    """)
    training_rows = conn.execute(
        training_conflict_query,
        {"mentor_id": mentor_id, "t_date": training_date, "current_eid": current_engagement_id or ""}
    ).fetchall()

    same_session_training_conflict = None
    has_offline_diff_session = False
    for row in training_rows:
        title, t_session, t_mode = row[0], row[1], row[2]
        if t_session == session_lower:
            same_session_training_conflict = title
        elif t_mode == "offline":
            has_offline_diff_session = True

    return {
        "project_hours": project_hours,
        "batch_hours": batch_hours,
        "batch_conflict_name": batch_conflict_name,
        "total_occupied_hours": project_hours + batch_hours,
        "same_session_training_conflict": same_session_training_conflict,
        "has_offline_diff_session": has_offline_diff_session,
        "project_conflict_name": project_conflict_name,
    }


def recommend_mentor_for_training(engagement_id: str, session_capacity_hours: float = 4.0) -> list[dict]:
    with engine.connect() as conn:
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

        requirements_rows = conn.execute(
            text("SELECT * FROM training_requirements WHERE engagement_id = :eid"),
            {"eid": engagement_id},
        ).mappings().fetchall()

        # Fetch ALL mentors in the domain — team leads AND regular mentors
        region_filter = None if engagement.get("mode") == "online" else engagement.get("region")
        all_mentors = get_available_mentors(domain=domain, region=region_filter, check_project_conflicts=False)

        for m in all_mentors:
            occ = calculate_daily_occupied_hours(
                conn=conn,
                mentor_id=m["id"],
                domain=domain,
                training_date=training_date,
                training_session=training_session,
                current_engagement_id=engagement_id
            )

            daily_available_hrs = max(0.0, session_capacity_hours - occ["total_occupied_hours"])

            # Determine availability and reason
            if occ["same_session_training_conflict"]:
                m["can_propose"] = False
                m["unavailable_reason"] = f"Committed to another training this session ({occ['same_session_training_conflict']})"
            elif occ["batch_conflict_name"]:
                m["can_propose"] = False
                m["unavailable_reason"] = f"Batch class scheduled this session ({occ['batch_conflict_name']})"
            elif occ["project_conflict_name"]:
                m["can_propose"] = False
                m["unavailable_reason"] = f"Project meeting scheduled this session ({occ['project_conflict_name']})"
            elif daily_available_hrs < required_hours:
                m["can_propose"] = False
                m["unavailable_reason"] = f"Only {daily_available_hrs:g}h free, needs {required_hours:g}h [v2]"
            else:
                m["can_propose"] = True
                m["unavailable_reason"] = None

            m["has_offline_penalty"] = occ["has_offline_diff_session"]
            m["skills"] = get_person_skills(m["id"], "employee")

        requirements = [
            {
                "skill_id": r["skill_id"],
                "embedding": _parse_embedding(r["requirement_embedding"]),
                "min_proficiency": r["min_proficiency"],
                "is_mandatory": r["is_mandatory"],
            }
            for r in requirements_rows
        ]

        ranked = rank_candidates(all_mentors, requirements)

        training_audience = engagement.get("audience")
        for candidate in ranked:
            raw_skill_score = candidate["suitability_score"]
            candidate["suitability_score"] = score_with_audience_preference(
                raw_skill_score, candidate.get("preferred_audience"), training_audience
            )
            if candidate.get("has_offline_penalty"):
                candidate["suitability_score"] *= 0.90

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

from datetime import datetime, timedelta

def get_mentor_availability_for_date(date_str: str, session: str = "") -> list[dict]:
    """Who is free on a specific date (YYYY-MM-DD). Optional session: morning or evening.
    Checks leave, student batches, project meetings and other trainings.
    If no session is given, both morning and evening are checked."""
    target = datetime.strptime(date_str, "%Y-%m-%d").date()
    week_start = target - timedelta(days=target.weekday())
    sessions = [session.lower().strip()] if session else ["morning", "evening"]

    results = []
    with engine.connect() as conn:
        mentors = conn.execute(
            text("SELECT employee_id, name, department FROM company_employees ORDER BY employee_id")
        ).mappings().fetchall()

        leave_rows = conn.execute(
            text("""
                SELECT DISTINCT resource_id FROM availability
                WHERE resource_type = 'employee'
                  AND week_start_date = :w
                  AND is_on_leave = TRUE
            """),
            {"w": week_start},
        ).fetchall()
        on_leave = {r[0] for r in leave_rows}

        for m in mentors:
            entry = {
                "employee_id": m["employee_id"],
                "name": m["name"],
                "department": m["department"],
                "date": date_str,
                "sessions": {},
            }
            for s in sessions:
                occ = calculate_daily_occupied_hours(
                    conn=conn,
                    mentor_id=m["employee_id"],
                    domain=m["department"] or "",
                    training_date=target,
                    training_session=s,
                )
                if m["employee_id"] in on_leave:
                    reason = "On leave this week"
                elif occ["same_session_training_conflict"]:
                    reason = f"Training: {occ['same_session_training_conflict']}"
                elif occ["batch_conflict_name"]:
                    reason = f"Batch class: {occ['batch_conflict_name']}"
                elif occ["project_conflict_name"]:
                    reason = f"Project meeting: {occ['project_conflict_name']}"
                else:
                    reason = None

                entry["sessions"][s] = {
                    "free": reason is None,
                    "reason": reason,
                    "free_hours": max(0.0, 4.0 - occ["total_occupied_hours"]),
                }
            results.append(entry)
    return results


_DAYS = ["mon", "tue", "wed", "thu", "fri", "sat", "sun"]


def _days_set(value):
    t = (value or "").lower()
    return {d for d in _DAYS if d in t}


def get_unassigned_items() -> dict:
    """Projects, trainings and student batches that have no mentor yet."""
    with engine.connect() as conn:
        projects = conn.execute(text("""
            SELECT p.title, p.status, p.start_date
            FROM projects p
            WHERE LOWER(p.status) NOT IN ('completed', 'cancelled')
              AND NOT EXISTS (
                SELECT 1 FROM allocations a
                WHERE a.reference_type = 'project'
                  AND a.reference_id = p.project_id
                  AND a.status IN ('proposed', 'accepted', 'assigned')
                  AND a.resource_id IN (SELECT employee_id FROM company_employees)
              )
            ORDER BY p.start_date
        """)).mappings().fetchall()

        trainings = conn.execute(text("""
            SELECT title, status, start_date, session
            FROM training_engagements
            WHERE mentor_id IS NULL
              AND LOWER(status) NOT IN ('completed', 'cancelled')
              AND start_date >= CURRENT_DATE
            ORDER BY start_date
        """)).mappings().fetchall()

        batches = conn.execute(text("""
            SELECT batch_name, start_date, session, day_of_week
            FROM student_batches
            WHERE mentor_id IS NULL
              AND LOWER(status) NOT IN ('completed', 'cancelled')
              AND end_date >= CURRENT_DATE
            ORDER BY start_date
        """)).mappings().fetchall()

    def clean(rows):
        return [{k: (str(v) if v is not None else None) for k, v in r.items()} for r in rows]

    result = {
        "projects_without_mentor": clean(projects),
        "trainings_without_mentor": clean(trainings),
        "batches_without_mentor": clean(batches),
    }
    result["total"] = sum(len(v) for v in result.values())
    return result


def _base_name(name):
    return re.sub(r"\s*(online|offline)\s*$", "", name or "", flags=re.I).lower()


def find_double_bookings() -> dict:
    """Mentors with two different commitments on the same day and session, with overlapping dates.
    Offline and Online copies of the same batch are not counted, and neither are two soft skill batches."""
    far_past, far_future = date(2000, 1, 1), date(2100, 1, 1)
    commitments = {}

    def add(mentor_id, kind, name, days, session, start, end, group=None, softskill=False):
        if not mentor_id or not session or not days:
            return
        commitments.setdefault(mentor_id, []).append({
            "kind": kind, "name": name, "days": days,
            "session": session.lower().strip(),
            "start": start or far_past, "end": end or far_future,
            "group": group, "softskill": softskill,
        })

    with engine.connect() as conn:
        names = {r[0]: r[1] for r in conn.execute(
            text("SELECT employee_id, name FROM company_employees")).fetchall()}

        for r in conn.execute(text("""
            SELECT mentor_id, batch_name, day_of_week, session, start_date, end_date, domain
            FROM student_batches
            WHERE mentor_id IS NOT NULL
              AND LOWER(status) NOT IN ('completed', 'cancelled')
              AND end_date >= CURRENT_DATE
        """)).fetchall():
            is_soft = ((r[6] or "").lower() == "softskill"
                       or "softskill" in (r[1] or "").lower().replace(" ", ""))
            add(r[0], "batch", r[1], _days_set(r[2]), r[3], r[4], r[5],
                group=(r[6], r[4], _base_name(r[1])), softskill=is_soft)

        for r in conn.execute(text("""
            SELECT a.resource_id, p.title, p.day_of_week, p.session, p.start_date, p.end_date
            FROM allocations a
            JOIN projects p ON p.project_id = a.reference_id
            WHERE a.reference_type = 'project'
              AND a.status IN ('proposed', 'accepted', 'assigned')
              AND LOWER(p.status) NOT IN ('completed', 'cancelled')
              AND a.resource_id IN (SELECT employee_id FROM company_employees)
        """)).fetchall():
            add(r[0], "project meeting", r[1], _days_set(r[2]), r[3], r[4], r[5])

        for r in conn.execute(text("""
            SELECT mentor_id, title, session, start_date
            FROM training_engagements
            WHERE mentor_id IS NOT NULL
              AND LOWER(status) NOT IN ('completed', 'cancelled')
              AND start_date >= CURRENT_DATE
        """)).fetchall():
            add(r[0], "training", r[1], {_DAYS[r[3].weekday()]}, r[2], r[3], r[3])

    conflicts = []
    for mentor_id, items in commitments.items():
        for i in range(len(items)):
            for j in range(i + 1, len(items)):
                a, b = items[i], items[j]
                if a["group"] is not None and a["group"] == b["group"]:
                    continue
                if a["softskill"] and b["softskill"]:
                    continue
                shared_days = a["days"] & b["days"]
                if (a["session"] == b["session"] and shared_days
                        and a["start"] <= b["end"] and b["start"] <= a["end"]):
                    conflicts.append({
                        "mentor": names.get(mentor_id, mentor_id),
                        "first": f"{a['name']} ({a['kind']})",
                        "second": f"{b['name']} ({b['kind']})",
                        "days": sorted(shared_days),
                        "session": a["session"],
                        "overlap_from": str(max(a["start"], b["start"])),
                        "overlap_to": str(min(a["end"], b["end"])),
                    })

    return {
        "double_bookings": conflicts[:20],
        "count": len(conflicts),
        "message": "No double-booking found." if not conflicts else None,
    }


def find_people_by_skills(skills: str, person_type: str = "mentor") -> dict:
    """Find people who have the given skills. skills is comma-separated,
    for example 'Power BI, SQL'. person_type is 'mentor' or 'intern'."""
    wanted = [s.strip() for s in skills.split(",") if s.strip()]
    if not wanted:
        return {"error": "Give at least one skill name."}

    with engine.connect() as conn:
        skill_names = {r[0]: r[1] for r in conn.execute(
            text("SELECT skill_id, skill_name FROM skills")).fetchall()}

    wanted_ids = {}
    for w in wanted:
        exact = {sid for sid, nm in skill_names.items() if nm.lower() == w.lower()}
        if not exact and len(w) > 3:
            exact = {sid for sid, nm in skill_names.items() if w.lower() in nm.lower()}
        wanted_ids[w] = exact

    unknown = [w for w, ids in wanted_ids.items() if not ids]
    if len(unknown) == len(wanted):
        return {"error": f"No skill named {', '.join(unknown)} exists in the system."}

    if person_type.lower().startswith("intern"):
        people = [{"id": p["id"], "name": p["name"]} for p in get_available_interns(domain=None)]
        skill_map = get_bulk_person_skills([p["id"] for p in people], "intern")
        note = "Only interns without an active project are searched."
    else:
        with engine.connect() as conn:
            people = [{"id": r[0], "name": r[1], "department": r[2]} for r in conn.execute(
                text("SELECT employee_id, name, department FROM company_employees")).fetchall()]
        skill_map = get_bulk_person_skills([p["id"] for p in people], "employee")
        note = None

    matches = []
    for p in people:
        have_ids = {s.get("skill_id") for s in skill_map.get(p["id"], [])}
        found = [w for w, ids in wanted_ids.items() if ids and (ids & have_ids)]
        if found:
            entry = dict(p)
            entry["skills_matched"] = found
            entry["has_all"] = len(found) == len([w for w in wanted if wanted_ids[w]])
            matches.append(entry)

    matches.sort(key=lambda m: len(m["skills_matched"]), reverse=True)
    return {
        "searched_for": wanted,
        "not_found_in_system": unknown,
        "matches": matches[:10],
        "note": note,
    }


def get_skill_gap(mentor_name: str, project_title: str) -> dict:
    """Which of a project's required skills a mentor is missing or weak in."""
    with engine.connect() as conn:
        emp = conn.execute(
            text("SELECT employee_id, name FROM company_employees WHERE LOWER(name) = LOWER(:n)"),
            {"n": mentor_name.strip()},
        ).mappings().fetchone()
        proj = conn.execute(
            text("SELECT project_id, title FROM projects WHERE title ILIKE :t LIMIT 1"),
            {"t": f"%{project_title.strip()}%"},
        ).mappings().fetchone()
        skill_names = {r[0]: r[1] for r in conn.execute(
            text("SELECT skill_id, skill_name FROM skills")).fetchall()}

    if not emp:
        return {"error": f"No mentor named {mentor_name} found."}
    if not proj:
        return {"error": f"No project matching '{project_title}' found."}

    requirements = get_project_requirements(proj["project_id"])
    if not requirements:
        return {"error": f"{proj['title']} has no required skills saved."}

    person_skills = get_person_skills(emp["employee_id"], "employee")
    levels = {s.get("skill_id"): s.get("proficiency_level") for s in person_skills}

    covered, below, related, missing_mandatory, missing_optional = [], [], [], [], []
    for req in requirements:
        sid = req.get("skill_id")
        name = skill_names.get(sid, sid)
        mandatory = bool(req.get("is_mandatory"))
        needed = req.get("min_proficiency")

        if sid in levels:
            have = levels[sid]
            try:
                is_below = bool(have and needed and float(have) < float(needed))
            except (TypeError, ValueError):
                is_below = False
            if is_below:
                below.append(f"{name} (has {have}, needs {needed})")
            else:
                covered.append(name)
            continue

        closest, best = None, 0.0
        try:
            for s in person_skills:
                sim = cosine_similarity(req.get("embedding"), s.get("embedding"))
                if sim > best:
                    best, closest = sim, skill_names.get(s.get("skill_id"))
        except Exception:
            pass
        if closest and best >= 0.75:
            related.append(f"{name} (closest: {closest})")
        elif mandatory:
            missing_mandatory.append(name)
        else:
            missing_optional.append(name)

    return {
        "mentor": emp["name"],
        "project": proj["title"],
        "covered": covered,
        "below_required_level": below,
        "related_skill_only": related,
        "missing_mandatory": missing_mandatory,
        "missing_optional": missing_optional,
    }