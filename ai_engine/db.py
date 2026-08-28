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

CATEGORY_TO_DEPARTMENT = {
    "Machine Learning": "Data Science",
    "Data Science": "Data Science",
    "Data Analytics": "Data Analytics",
}

def category_to_department(category: str) -> str | None:
    """Maps a project's subject category to the department used for
    mentor/intern filtering. Returns None for unmapped categories,
    so recommendations fall back to showing everyone rather than
    coming back empty."""
    return CATEGORY_TO_DEPARTMENT.get(category)

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


def get_available_mentors(domain: str = None, check_project_conflicts: bool = True) -> list[dict]:
    """
    Excludes anyone with an active PROJECT allocation, unless
    check_project_conflicts=False (used for training recommendations,
    which track their own conflicts separately via date overlap).
    Returns BOTH team leads and regular mentors together — is_team_lead
    is just a field on each result, not a filter.

    Args:
        domain: Must be exactly "Data Analytics" or "Data Science" — the
                full department name as stored in the database. Do NOT
                use abbreviations like "DA" or "DS".
    """
    query = """
        SELECT employee_id AS id, name, weekly_capacity_hours, is_team_lead
        FROM company_employees
    """
    conditions = []
    params = {}

    if check_project_conflicts:
        conditions.append("""
            NOT EXISTS (
                SELECT 1 FROM allocations a
                WHERE a.resource_id = employee_id
                AND a.status IN ('proposed', 'assigned')
                AND a.reference_type = 'project'
            )
        """)
    if domain:
        conditions.append("department = :domain")
        params["domain"] = domain

    if conditions:
        query += " WHERE " + " AND ".join(conditions)

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


def get_next_mentor_for_batch(domain: str, month_num: int, year: int = 2026) -> dict:
    """
    Mentors are assigned in 2-month blocks (Jun-Jul, Aug-Sep, Oct-Nov...),
    covering both online and offline sessions for that block.

    Given a specific month, finds which 2-month block it belongs to.
    If a mentor is already assigned to another batch within that same
    block, reuse them (so both months share one mentor). Otherwise,
    round-robin picks whoever has covered the fewest blocks so far.
    """
    # Determine the block's start month (odd months start blocks: Jun, Aug, Oct...)
    block_start_month = month_num if month_num % 2 == 0 else month_num - 1
    block_end_month = block_start_month + 1

    with engine.connect() as conn:
        # Check if a mentor is already assigned within this block for this domain
        existing = conn.execute(
            text("""
                SELECT sb.mentor_id, ce.name
                FROM student_batches sb
                JOIN company_employees ce ON ce.employee_id = sb.mentor_id
                WHERE sb.domain = :domain
                  AND sb.mentor_id IS NOT NULL
                  AND EXTRACT(MONTH FROM sb.start_date) BETWEEN :block_start AND :block_end
                  AND EXTRACT(YEAR FROM sb.start_date) = :year
                LIMIT 1
            """),
            {"domain": domain, "block_start": block_start_month, "block_end": block_end_month, "year": year},
        ).mappings().fetchone()

        if existing:
            return {"employee_id": existing["mentor_id"], "name": existing["name"]}

        # No one assigned to this block yet — round-robin pick the least-used mentor
        row = conn.execute(
            text("""
                SELECT ce.employee_id, ce.name, COUNT(a.allocation_id) AS block_count
                FROM company_employees ce
                LEFT JOIN allocations a
                    ON a.resource_id = ce.employee_id
                    AND a.reference_type = 'batch'
                    AND a.status IN ('proposed', 'accepted', 'assigned')
                WHERE ce.department = :domain
                GROUP BY ce.employee_id, ce.name
                ORDER BY block_count ASC, ce.employee_id ASC
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

def search_project_by_title(title_keyword: str) -> list[dict]:
    """Finds projects whose title contains the given keyword — lets the
    chatbot resolve a project name into its actual project_id."""
    with engine.connect() as conn:
        rows = conn.execute(
            text("""
                SELECT project_id, title, project_type, status
                FROM projects
                WHERE title ILIKE :keyword
            """),
            {"keyword": f"%{title_keyword}%"},
        ).mappings().fetchall()
    return [dict(r) for r in rows]


def get_intern_details(intern_id: str) -> dict:
    """Full details for one intern, including basic profile info."""
    with engine.connect() as conn:
        row = conn.execute(
            text("""
                SELECT intern_id, name, email, college_institution, degree_program,
                       current_status, department, review_status
                FROM interns_and_students WHERE intern_id = :id
            """),
            {"id": intern_id},
        ).mappings().fetchone()
    return dict(row) if row else None


def get_employee_details(employee_id: str) -> dict:
    """Full details for one employee, including basic profile info."""
    with engine.connect() as conn:
        row = conn.execute(
            text("""
                SELECT employee_id, name, email, department, designation_id,
                       weekly_capacity_hours, is_team_lead
                FROM company_employees WHERE employee_id = :id
            """),
            {"id": employee_id},
        ).mappings().fetchone()
    return dict(row) if row else None

def search_training_by_title(title_keyword: str) -> list[dict]:
    """Finds training engagements whose title contains the given keyword —
    lets the chatbot resolve a training name into its actual engagement_id."""
    with engine.connect() as conn:
        rows = conn.execute(
            text("""
                SELECT engagement_id, title, engagement_type, status
                FROM training_engagements
                WHERE title ILIKE :keyword
            """),
            {"keyword": f"%{title_keyword}%"},
        ).mappings().fetchall()
    return [dict(r) for r in rows]

def get_best_mentor_for_domain(domain: str) -> list[dict]:
    """
    General 'who's the best mentor for X domain' — no specific project
    to score against, so this ranks team leads first (more senior/capable
    role), then by available capacity as a tiebreaker.
    """
    mentors = get_available_mentors(domain=domain)
    return sorted(
        mentors,
        key=lambda m: (not m.get("is_team_lead", False), -m.get("weekly_capacity_hours", 0))
    )[:5]

def get_mentor_workload_summary(domain: str = None) -> list[dict]:
    """
    Shows each mentor's current active commitment count across
    projects, batches, and trainings — lets the assistant reason
    about who's genuinely least busy, not just binary available/not.
    """
    query = """
        SELECT ce.employee_id, ce.name, ce.department, ce.is_team_lead,
               COUNT(a.allocation_id) AS active_commitments
        FROM company_employees ce
        LEFT JOIN allocations a ON a.resource_id = ce.employee_id
            AND a.status IN ('proposed', 'assigned')
        WHERE 1=1
    """
    params = {}
    if domain:
        query += " AND ce.department = :domain"
        params["domain"] = domain
    query += " GROUP BY ce.employee_id, ce.name, ce.department, ce.is_team_lead ORDER BY active_commitments ASC"

    with engine.connect() as conn:
        rows = conn.execute(text(query), params).mappings().fetchall()
    return [dict(r) for r in rows]