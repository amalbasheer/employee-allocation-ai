"""
db.py
All the raw database reads live here — one place, so if TM renames a
column later, you only fix it in this file, not scattered across
extraction/matching/recommend code.
"""

import os
from dotenv import load_dotenv
from sqlalchemy import create_engine, text

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    raise EnvironmentError("DATABASE_URL not set in .env")

engine = create_engine(DATABASE_URL)


def get_project(project_id: str) -> dict:
    """Fetch one project's core fields (title, type, status, etc.)."""
    with engine.connect() as conn:
        row = conn.execute(
            text("SELECT * FROM projects WHERE project_id = :pid"),
            {"pid": project_id},
        ).mappings().fetchone()
    return dict(row) if row else None


def get_project_requirements(project_id: str) -> list[dict]:
    """
    Fetch a project's required skills, joined with the shared skills
    table to get each skill's embedding.
    """
    with engine.connect() as conn:
        rows = conn.execute(
            text("""
                SELECT pr.skill_id, pr.min_proficiency, pr.is_mandatory,
                       s.skill_name, s.skill_embedding
                FROM project_requirements pr
                JOIN skills s ON pr.skill_id = s.skill_id
                WHERE pr.project_id = :pid
            """),
            {"pid": project_id},
        ).mappings().fetchall()
    return [
        {
            "skill_id": r["skill_id"],
            "embedding": r["skill_embedding"],
            "min_proficiency": r["min_proficiency"],
            "is_mandatory": r["is_mandatory"],
        }
        for r in rows
    ]


def get_available_mentors() -> list[dict]:
    """
    Fetch mentors/employees. is_team_lead lives directly on
    company_employees — no join needed.
    """
    with engine.connect() as conn:
        rows = conn.execute(
            text("""
                SELECT employee_id AS id, name, weekly_capacity_hours, is_team_lead
                FROM company_employees
            """)
        ).mappings().fetchall()
    return [dict(r) for r in rows]


def get_available_interns() -> list[dict]:
    """
    Fetch interns/students who are currently free — one project at a
    time, so this is a simple status check, not hours math.
    """
    with engine.connect() as conn:
        rows = conn.execute(
            text("""
                SELECT intern_id AS id, name, role, current_status
                FROM interns_and_students
                WHERE current_status = 'AVAILABLE'
                  AND review_status = 'verified'
            """)
        ).mappings().fetchall()
    return [dict(r) for r in rows]


def get_person_skills(person_id: str, person_type: str) -> list[dict]:
    """
    Fetch one person's skills + embeddings, joined through the shared
    skills table. Works for either an employee or an intern — same
    shape either way, so matching.py doesn't need to know which.
    """
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
            "embedding": r["skill_embedding"],
            "proficiency_level": r["proficiency_level"],
        }
        for r in rows
    ]