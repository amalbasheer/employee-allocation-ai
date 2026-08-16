"""
seed_dummy_interns.py
Generates 10 DA interns + 10 DS interns with realistic skill spreads —
including deliberate edge cases (one already assigned, one with a
skill gap) to actually stress-test matching/optimization logic.
"""

import random
from uuid import uuid4
from sqlalchemy import text
from app.database import engine
from seed_skills import get_or_create_skill

DA_SKILLS = ["Python", "SQL", "Data Analytics", "Power BI", "Tableau", "Statistics"]
DS_SKILLS = ["Python", "Machine Learning", "Deep Learning", "PyTorch", "TensorFlow", "Computer Vision"]

FIRST_NAMES = ["Amal", "Priya", "Rahul", "Sneha", "Arjun", "Divya", "Kiran", "Meera", "Vishnu", "Anjali"]


def make_intern(name: str, domain: str, force_status: str = "AVAILABLE") -> str:
    intern_id = str(uuid4())
    with engine.begin() as conn:
        conn.execute(
            text("""
                INSERT INTO interns_and_students
                (intern_id, name, email, college_institution, degree_program,
                 resume_document_url, review_status, role, current_status)
                VALUES (:id, :name, :email, :college, :degree, :resume, 'verified', 'intern', :status)
            """),
            {
                "id": intern_id, "name": name,
                "email": f"{name.lower()}.{domain.lower()}@test.com",
                "college": "Rajagiri College of Social Sciences",
                "degree": "B.Tech CS",
                "resume": f"https://fake-storage.test/{intern_id}.pdf",
                "status": force_status,
            },
        )
    return intern_id


def assign_skills(intern_id: str, skill_pool: list[str], gap_test: bool = False):
    """gap_test=True gives them only 2 skills instead of a full spread —
    used to confirm the system correctly ranks a weak-skill intern low."""
    chosen = random.sample(skill_pool, 2 if gap_test else random.randint(3, 5))
    with engine.begin() as conn:
        for skill_name in chosen:
            skill_id = get_or_create_skill(skill_name)
            conn.execute(
                text("""
                    INSERT INTO intern_skills (id, intern_id, skill_id, proficiency_level, extraction_confidence)
                    VALUES (:id, :intern_id, :skill_id, :prof, :conf)
                """),
                {
                    "id": str(uuid4()), "intern_id": intern_id, "skill_id": skill_id,
                    "prof": round(random.uniform(2.0, 5.0), 1),
                    "conf": round(random.uniform(0.7, 0.98), 2),
                },
            )


def seed_dummy_interns():
    print("Creating 10 DA interns...")
    for i, name in enumerate(FIRST_NAMES):
        status = "ASSIGNED" if i == 0 else "AVAILABLE"   # one deliberately busy
        intern_id = make_intern(name, "DA", force_status=status)
        assign_skills(intern_id, DA_SKILLS, gap_test=(i == 1))  # one deliberately skill-weak

    print("Creating 10 DS interns...")
    for i, name in enumerate(FIRST_NAMES):
        status = "ASSIGNED" if i == 0 else "AVAILABLE"
        intern_id = make_intern(f"{name}2", "DS", force_status=status)
        assign_skills(intern_id, DS_SKILLS, gap_test=(i == 1))

    print("✅ 20 interns created (10 DA, 10 DS) — 2 marked busy, 2 given weak skill spreads.")

