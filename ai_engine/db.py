"""
db.py
All the raw database reads live here — one place, so if TM renames a
column later, you only fix it in this file.

NOTE: column names below match what's been discussed so far
(college_institution, role, current_status, skill_embedding on the
skills table, can_lead_projects on designations). If her live schema
differs, update the SQL here — nothing else needs to change.
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
    with engine.connect() as conn:
        rows = conn.execute(
            text("""
                SELECT e.employee_id AS id, e.name, e.weekly_capacity_hours,
                       d.can_lead_projects
                FROM company_employees e
                JOIN designations d ON e.designation_id = d.designation_id
                WHERE e.is_active = TRUE
            """)
        ).mappings().fetchall()
    return [dict(r) for r in rows]


def get_available_interns() -> list[dict]:
    with engine.connect() as conn:
        rows = conn.execute(
            text("""
                SELECT intern_id AS id, name, role, current_status
                FROM interns_and_students
                WHERE current_status = 'available'
                  AND review_status = 'verified'
            """)
        ).mappings().fetchall()
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
            "embedding": r["skill_embedding"],
            "proficiency_level": r["proficiency_level"],
        }
        for r in rows
    ]
