"""
db.py
All the raw database reads live here — one place, so if TM renames a
column later, you only fix it in this file.
"""

import os
import json
from dotenv import load_dotenv
from sqlalchemy import create_engine, text

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    raise EnvironmentError("DATABASE_URL not set in .env")

engine = create_engine(DATABASE_URL)


def _parse_embedding(val):
    """
    Normalizes an embedding value into a real Python list, regardless
    of whether it comes back from Postgres as a string representation
    or an actual list/array.
    """
    if val is None:
        return None
    if isinstance(val, str):
        return json.loads(val)
    return list(val)


def get_project(project_id: str) -> dict:
    with engine.connect() as conn:
        row = conn.execute(
            text("SELECT * FROM projects WHERE project_id = :pid"),
            {"pid": project_id},
        ).mappings().fetchone()
    return dict(row) if row else None


def get_project_requirements(project_id: str) -> list[dict]:
    with engine.connect() as conn:
        rows = conn.execute(
            text("""
                SELECT pr.skill_id, pr.min_proficiency, pr.is_mandatory,
                       s.skill_name, pr.requirement_embedding
                FROM project_requirements pr
                JOIN skills s ON pr.skill_id = s.skill_id
                WHERE pr.project_id = :pid
            """),
            {"pid": project_id},
        ).mappings().fetchall()
    return [
        {
            "skill_id": r["skill_id"],
            "embedding": _parse_embedding(r["requirement_embedding"]),
            "min_proficiency": r["min_proficiency"],
            "is_mandatory": r["is_mandatory"],
        }
        for r in rows
    ]


def get_available_mentors(domain: str = None) -> list[dict]:
    """
    Mentors not already excluded by active allocations, with remaining
    hours calculated from this week's availability entry (if one exists).
    If no availability row exists for this week, falls back to their
    full weekly_capacity_hours (assumes fully free).
    """
    query = """
        SELECT
            ce.employee_id AS id,
            ce.name,
            ce.weekly_capacity_hours,
            ce.is_team_lead,
            COALESCE(av.available_hours, ce.weekly_capacity_hours) AS remaining_hours,
            COALESCE(av.is_on_leave, FALSE) AS is_on_leave
        FROM company_employees ce
        LEFT JOIN availability av
            ON av.resource_id = ce.employee_id
            AND av.resource_type = 'employee'
            AND av.week_start_date = date_trunc('week', CURRENT_DATE)::date
        WHERE NOT EXISTS (
            SELECT 1 FROM allocations a
            WHERE a.resource_id = ce.employee_id
            AND a.status IN ('proposed', 'assigned')
        )
    """
    params = {}
    if domain:
        query += " AND ce.department = :domain"
        params["domain"] = domain

    query += " AND COALESCE(av.is_on_leave, FALSE) = FALSE"
    query += " AND COALESCE(av.available_hours, ce.weekly_capacity_hours) > 0"

    with engine.connect() as conn:
        rows = conn.execute(text(query), params).mappings().fetchall()
    return [dict(r) for r in rows]


def get_available_interns(domain: str = None) -> list[dict]:
    """
    Available means: current_status = 'AVAILABLE', verified, not already
    tied to an active allocation. No longer using a hardcoded time window
    — admin will manage TERMINATED status directly instead.
    """
    query = """
        SELECT intern_id AS id, name, role, current_status
        FROM interns_and_students i
        WHERE current_status = 'AVAILABLE'
          AND review_status = 'verified'
          AND NOT EXISTS (
              SELECT 1 FROM allocations a
              WHERE a.resource_id = i.intern_id
              AND a.status IN ('proposed', 'assigned')
          )
    """
    params = {}
    if domain:
        query += " AND department = :domain"
        params["domain"] = domain

    with engine.connect() as conn:
        rows = conn.execute(text(query), params).mappings().fetchall()
    return [dict(r) for r in rows]


def get_person_skills(person_id: str, person_type: str) -> list[dict]:
    table = "employee_skills" if person_type == "employee" else "intern_skills"
    id_column = "employee_id" if person_type == "employee" else "intern_id"

    with engine.connect() as conn:
        rows = conn.execute(
            text(f"""
                SELECT ps.skill_id, ps.proficiency_level, s.skill_embedding
                FROM {table} ps
                JOIN skills s ON ps.skill_id = s.skill_id
                WHERE ps.{id_column} = :pid
            """),
            {"pid": person_id},
        ).mappings().fetchall()

    return [
        {
            "skill_id": r["skill_id"],
            "embedding": _parse_embedding(r["skill_embedding"]),
            "proficiency_level": r["proficiency_level"],
        }
        for r in rows
    ]


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


def get_batch(batch_id: str) -> dict:
    with engine.connect() as conn:
        row = conn.execute(
            text("SELECT * FROM student_batches WHERE batch_id = :bid"),
            {"bid": batch_id},
        ).mappings().fetchone()
    return dict(row) if row else None


def get_training_engagement(engagement_id: str) -> dict:
    with engine.connect() as conn:
        row = conn.execute(
            text("SELECT * FROM training_engagements WHERE engagement_id = :eid"),
            {"eid": engagement_id},
        ).mappings().fetchone()
    return dict(row) if row else None


def get_allocation_target(allocation: dict) -> dict:
    """
    Given an allocation row, fetches the actual project/batch/training
    engagement it points to — dispatches based on reference_type since
    reference_id alone doesn't tell you which table to check.
    """
    ref_type = allocation.get("reference_type")
    ref_id = allocation.get("reference_id")

    if ref_type == "project":
        return get_project(ref_id)
    elif ref_type == "batch":
        return get_batch(ref_id)
    elif ref_type == "training":
        return get_training_engagement(ref_id)
    else:
        raise ValueError(f"Unknown reference_type: {ref_type}")