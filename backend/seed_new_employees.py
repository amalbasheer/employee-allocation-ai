# backend/seed_new_employees_skills.py
"""
Seeds skills (with real embeddings) and availability for the 6 new
employees added tonight — Divya, Arjun, Sneha (DA), Kiran, Meera, Rahul (DS).
"""

import sys, os
from datetime import date, timedelta
from sqlalchemy import text

ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.append(ROOT_DIR)
sys.path.append(os.path.join(ROOT_DIR, "ai_engine"))

from ai_engine.db import engine
from skill_utils import get_or_create_skill
from ai_engine.embedding import generate_embedding

NEW_EMPLOYEE_SKILLS = {
    "divya.da@rp2.com": [
        ("Python", 4), ("SQL", 5), ("Power BI", 4), ("Data Analytics", 4),
        ("Statistics", 4), ("Tableau", 3), ("Excel", 5)
    ],
    "arjun.da@rp2.com": [
        ("Python", 3), ("SQL", 4), ("Tableau", 5), ("Statistics", 4),
        ("Power BI", 4), ("Data Analytics", 3), ("R", 3)
    ],
    "sneha.da@rp2.com": [
        ("Python", 5), ("SQL", 4), ("Power BI", 3), ("Data Analytics", 5),
        ("Statistics", 5), ("Excel", 4), ("SPSS", 3)
    ],
    "kiran.ds@rp2.com": [
        ("Python", 4), ("Machine Learning", 5), ("PyTorch", 3),
        ("SQL", 3), ("Deep Learning", 3), ("Statistics", 4)
    ],
    "meera.ds@rp2.com": [
        ("Python", 5), ("Machine Learning", 4), ("Deep Learning", 5),
        ("Computer Vision", 4), ("PyTorch", 4), ("TensorFlow", 3), ("NLP", 4)
    ],
    "rahul.ds@rp2.com": [
        ("Python", 3), ("Machine Learning", 4), ("TensorFlow", 4),
        ("SQL", 4), ("Computer Vision", 3), ("Deep Learning", 3)
    ],
}


def get_employee_id_by_email(email: str) -> str:
    with engine.connect() as conn:
        row = conn.execute(
            text("SELECT employee_id FROM company_employees WHERE email = :email"),
            {"email": email},
        ).fetchone()
    return row[0] if row else None


def seed_skills():
    print("Seeding skills for 6 new employees...\n")
    for email, skills in NEW_EMPLOYEE_SKILLS.items():
        emp_id = get_employee_id_by_email(email)
        if not emp_id:
            print(f"  ⚠️ No employee found for {email}, skipping.")
            continue

        for skill_name, proficiency in skills:
            skill_id = get_or_create_skill(skill_name)
            with engine.begin() as conn:
                conn.execute(
                    text("""
                        INSERT INTO employee_skills (employee_id, skill_id, proficiency_level)
                        VALUES (:emp_id, :skill_id, :prof)
                        ON CONFLICT (employee_id, skill_id) DO UPDATE SET proficiency_level = :prof
                    """),
                    {"emp_id": emp_id, "skill_id": skill_id, "prof": proficiency},
                )
        print(f"  {email} -> {[s[0] for s in skills]}")


def seed_availability():
    print("\nSeeding availability for 6 new employees...\n")
    today = date.today()
    week_start = today - timedelta(days=today.weekday())

    for email in NEW_EMPLOYEE_SKILLS.keys():
        emp_id = get_employee_id_by_email(email)
        if not emp_id:
            continue
        with engine.begin() as conn:
            conn.execute(
                text("""
                    INSERT INTO availability (resource_type, resource_id, week_start_date, available_hours, is_on_leave)
                    VALUES ('employee', :emp_id, :week_start, 40, FALSE)
                """),
                {"emp_id": emp_id, "week_start": week_start},
            )
        print(f"  {email} -> 40 hrs available")


if __name__ == "__main__":
    seed_skills()
    seed_availability()
    print("\n✅ Done.")