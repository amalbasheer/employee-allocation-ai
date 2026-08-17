# backend/seed_dummy_users.py
"""
Creates test accounts with REAL Supabase Auth logins:
- 1 admin
- 18 employees (9 per domain: 3 team leads + 6 regular mentors, DA + DS)
- 8 interns (4 DA + 4 DS)

Safe to re-run — reuses existing accounts/rows instead of duplicating.
Password for all accounts: Password123!
"""

import sys
import os
import random
from uuid import uuid4
from dotenv import load_dotenv
from supabase import create_client, Client
from sqlalchemy import text

sys.path.append(os.path.join(os.path.dirname(__file__), "..", "ai_engine"))
from db import engine
from skill_utils import get_or_create_skill

load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_SERVICE_KEY = os.getenv("SUPABASE_KEY")

if not SUPABASE_URL or not SUPABASE_SERVICE_KEY:
    raise ValueError("Missing SUPABASE_URL or SUPABASE_KEY in .env")

supabase: Client = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)

PASSWORD = "Password123!"

DA_SKILLS = ["Python", "SQL", "Data Analytics", "Power BI", "Tableau", "Statistics"]
DS_SKILLS = ["Python", "Machine Learning", "Deep Learning", "PyTorch", "TensorFlow", "Computer Vision"]

DEPT_CODES = {"Data Analytics": "da", "Data Science": "ds"}

DA_EMP_NAMES = ["Aravind", "Nithya", "Sanjay", "Lakshmi", "Vivek", "Pooja", "Karthik", "Deepa", "Rohan"]
DS_EMP_NAMES = ["Rajesh", "Anitha", "Suresh", "Meenakshi", "Manoj", "Latha", "Prasad", "Swathi", "Anand"]

DA_INTERN_NAMES = ["Amal", "Priya", "Rahul", "Sneha"]
DS_INTERN_NAMES = ["Athira", "Sandeep", "Nisha", "Gokul"]


def create_auth_user(email: str, name: str, role: str) -> str:
    try:
        res = supabase.auth.admin.create_user({
            "email": email, "password": PASSWORD, "email_confirm": True,
            "user_metadata": {"name": name, "role": role},
        })
        return res.user.id
    except Exception:
        users = supabase.auth.admin.list_users()
        for u in users:
            if u.email == email:
                return u.id
        raise RuntimeError(f"Could not create or find auth user for {email}")


def get_designation_id(title: str) -> str:
    with engine.connect() as conn:
        row = conn.execute(
            text("SELECT designation_id FROM designations WHERE title = :title"),
            {"title": title},
        ).fetchone()
    if not row:
        raise ValueError(f"Designation '{title}' not found — run backend/seed.py first")
    return row[0]


def person_already_has_skills(person_id: str, person_type: str) -> bool:
    """Checks if this person already has skills recorded — avoids
    re-inserting duplicate skill rows on re-runs."""
    table = "employee_skills" if person_type == "employee" else "intern_skills"
    id_col = "employee_id" if person_type == "employee" else "intern_id"
    with engine.connect() as conn:
        row = conn.execute(
            text(f"SELECT 1 FROM {table} WHERE {id_col} = :pid LIMIT 1"),
            {"pid": person_id},
        ).fetchone()
    return row is not None


def assign_skills(person_id: str, skill_pool: list[str], person_type: str, gap_test: bool = False):
    if person_already_has_skills(person_id, person_type):
        print(f"    (skills already recorded, skipping)")
        return

    table = "employee_skills" if person_type == "employee" else "intern_skills"
    id_col = "employee_id" if person_type == "employee" else "intern_id"
    chosen = random.sample(skill_pool, 2 if gap_test else random.randint(3, 5))

    with engine.begin() as conn:
        for skill_name in chosen:
            skill_id = get_or_create_skill(skill_name)
            if person_type == "employee":
                conn.execute(
                    text(f"""
                        INSERT INTO {table} ({id_col}, skill_id, proficiency_level)
                        VALUES (:pid, :skill_id, :prof)
                        ON CONFLICT DO NOTHING
                    """),
                    {"pid": person_id, "skill_id": skill_id, "prof": random.randint(2, 5)},
                )
            else:
                conn.execute(
                    text(f"""
                        INSERT INTO {table} ({id_col}, skill_id, proficiency_level, extraction_confidence)
                        VALUES (:pid, :skill_id, :prof, :conf)
                        ON CONFLICT DO NOTHING
                    """),
                    {
                        "pid": person_id, "skill_id": skill_id,
                        "prof": round(random.uniform(2.0, 5.0), 1),
                        "conf": round(random.uniform(0.7, 0.98), 2),
                    },
                )


def seed_admin():
    print("\nCreating admin account...")
    admin_id = create_auth_user("admin@rp2.test", "System Admin", "ADMIN")
    print("✅ Admin ready: admin@rp2.test / Password123! (auth-only, not a workforce record)")


def seed_employees():
    domain_configs = [
        ("Data Analytics", DA_SKILLS, DA_EMP_NAMES, "Fullstack Developer"),
        ("Data Science", DS_SKILLS, DS_EMP_NAMES, "Senior AI Engineer"),
    ]
    for domain, skills, names, designation_title in domain_configs:
        dept_code = DEPT_CODES[domain]
        designation_id = get_designation_id(designation_title)
        print(f"\nCreating 9 {domain} employees (3 team leads)...")
        for i, name in enumerate(names):
            email = f"{name.lower()}.{dept_code}@rp2.test"
            is_lead = i < 3          # first 3 per domain are team leads
            near_cap = (i == 3)      # one deliberately near capacity
            gap = (i == 4)           # one deliberately skill-weak

            print(f"  {email} [{'TEAM LEAD' if is_lead else 'mentor'}]")
            user_id = create_auth_user(email, f"{name} ({domain})", "EMPLOYEE")

            with engine.begin() as conn:
                conn.execute(
                    text("""
                        INSERT INTO company_employees
                        (employee_id, name, email, department, experience_years,
                         weekly_capacity_hours, is_team_lead, designation_id, created_at)
                        VALUES (:id, :name, :email, :dept, :exp, 40, :lead, :desig_id, NOW())
                        ON CONFLICT (employee_id) DO NOTHING
                    """),
                    {
                        "id": user_id, "name": f"{name} ({domain})", "email": email,
                        "dept": domain, "exp": round(random.uniform(1.0, 8.0), 1),
                        "lead": is_lead, "desig_id": designation_id,
                    },
                )
                if near_cap:
                    conn.execute(
                        text("""
                            INSERT INTO availability
                            (availability_id, resource_type, resource_id, week_start_date, available_hours, is_on_leave)
                            VALUES (:id, 'employee', :emp_id, CURRENT_DATE, 5, FALSE)
                            ON CONFLICT (resource_id, week_start_date) DO NOTHING
                        """),
                        {"id": str(uuid4()), "emp_id": user_id},
                    )

            assign_skills(user_id, skills, "employee", gap_test=gap)

    print("\n✅ 18 employees ready (9 per domain, 3 team leads each).")


def seed_interns():
    domain_configs = [
        ("DA", DA_SKILLS, DA_INTERN_NAMES),
        ("DS", DS_SKILLS, DS_INTERN_NAMES),
    ]
    for domain, skills, names in domain_configs:
        print(f"\nCreating 4 {domain} interns...")
        for i, name in enumerate(names):
            email = f"{name.lower()}.{domain.lower()}intern@rp2.test"
            status = "ASSIGNED" if i == 0 else "AVAILABLE"
            gap = (i == 1)

            print(f"  {email} [{status}]")
            user_id = create_auth_user(email, f"{name} ({domain} intern)", "STUDENT")

            with engine.begin() as conn:
                conn.execute(
                    text("""
                        INSERT INTO interns_and_students
                        (intern_id, name, email, college_institution, degree_program,
                         resume_document_url, review_status, role, current_status, created_at)
                        VALUES (:id, :name, :email, :college, :degree, :resume, 'verified', 'intern', :status, NOW())
                        ON CONFLICT (intern_id) DO NOTHING
                    """),
                    {
                        "id": user_id, "name": f"{name} ({domain} intern)", "email": email,
                        "college": "Rajagiri College of Social Sciences", "degree": "B.Tech CS",
                        "resume": f"https://fake-storage.test/{user_id}.pdf", "status": status,
                    },
                )

            assign_skills(user_id, skills, "intern", gap_test=gap)

    print("\n✅ 8 interns ready (4 per domain).")


if __name__ == "__main__":
    seed_admin()
    seed_employees()
    seed_interns()
    print("\n🎉 All 27 test accounts ready — password: Password123!")