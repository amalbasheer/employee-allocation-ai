"""
seed_dummy_employees.py
Generates 10 DA employees + 10 DS employees, including deliberate
edge cases: 4 team leads per domain (for optimizer contention testing),
one nearly-at-capacity, one with a skill gap.
"""

import random
from uuid import uuid4
from sqlalchemy import text
from app.database import engine
from seed_skills import get_or_create_skill

DA_SKILLS = ["Python", "SQL", "Data Analytics", "Power BI", "Tableau", "Statistics"]
DS_SKILLS = ["Python", "Machine Learning", "Deep Learning", "PyTorch", "TensorFlow", "Computer Vision"]

FIRST_NAMES = ["Aravind", "Nithya", "Sanjay", "Lakshmi", "Vivek", "Pooja", "Karthik", "Deepa", "Rohan", "Fathima"]


def make_employee(name: str, department: str, is_team_lead: bool, near_capacity: bool = False) -> str:
    employee_id = str(uuid4())
    capacity = 40
    with engine.begin() as conn:
        conn.execute(
            text("""
                INSERT INTO company_employees
                (employee_id, name, email, department, experience_years,
                 weekly_capacity_hours, is_team_lead)
                VALUES (:id, :name, :email, :dept, :exp, :cap, :lead)
            """),
            {
                "id": employee_id, "name": name,
                "email": f"{name.lower()}.{department.lower()}@rp2.test",
                "dept": department,
                "exp": round(random.uniform(1.0, 8.0), 1),
                "cap": capacity,
                "lead": is_team_lead,
            },
        )

    if near_capacity:
        # Simulate them already having 35 of 40 hours booked via availability
        with engine.begin() as conn:
            conn.execute(
                text("""
                    INSERT INTO availability
                    (availability_id, resource_type, resource_id, week_start_date, available_hours, is_on_leave)
                    VALUES (:id, 'employee', :emp_id, CURRENT_DATE, 5, FALSE)
                """),
                {"id": str(uuid4()), "emp_id": employee_id},
            )

    return employee_id


def assign_skills(employee_id: str, skill_pool: list[str], gap_test: bool = False):
    chosen = random.sample(skill_pool, 2 if gap_test else random.randint(3, 5))
    with engine.begin() as conn:
        for skill_name in chosen:
            skill_id = get_or_create_skill(skill_name)
            conn.execute(
                text("""
                    INSERT INTO employee_skills (employee_id, skill_id, proficiency_level, is_custom_override)
                    VALUES (:emp_id, :skill_id, :prof, FALSE)
                """),
                {
                    "emp_id": employee_id, "skill_id": skill_id,
                    "prof": random.randint(2, 5),
                },
            )


def seed_dummy_employees():
    for domain, skills in [("Data Analytics", DA_SKILLS), ("Data Science", DS_SKILLS)]:
        print(f"Creating 10 {domain} employees (4 team leads)...")
        for i, name in enumerate(FIRST_NAMES):
            is_lead = i < 4          # first 4 per domain are team leads
            near_cap = (i == 4)      # one deliberately near capacity
            gap = (i == 5)           # one deliberately skill-weak

            emp_id = make_employee(f"{name}_{domain[:2]}", domain, is_lead, near_capacity=near_cap)
            assign_skills(emp_id, skills, gap_test=gap)

    print("✅ 20 employees created (10 DA, 10 DS) — 4 team leads each, 1 near-capacity, 1 skill-gap per domain.")

