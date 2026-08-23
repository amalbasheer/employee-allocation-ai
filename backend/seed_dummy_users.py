# backend/seed_dummy_users.py
"""
Creates test accounts with REAL Supabase Auth logins:
- 1 admin
- 18 employees (9 per domain: 3 team leads + 6 regular mentors, DA + DS)
- 8 interns (4 DA + 4 DS)

Resets employee/intern data and sequences on every run, so IDs always
start fresh from 0001. Skills and designations are NOT reset — those
stay as a stable master dictionary (run seed_skills.py separately for those).

Password for all accounts: Password123!
"""

import sys
import os
import random
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

DA_COLLEGE_PROGRAMS = [
    ("Rajagiri College of Social Sciences", "B.Com Finance"),
    ("St. Teresa's College", "B.Sc Statistics"),
    ("Rajagiri School of Engineering & Technology", "B.Tech CSE"),
    ("Loyola College of Social Sciences", "BBA"),
    ("St. Teresa's College", "B.Sc Economics"),
]

DS_COLLEGE_PROGRAMS = [
    ("Rajagiri School of Engineering & Technology", "B.Tech CSE"),
    ("Cochin University of Science and Technology", "MCA"),
    ("St. Joseph's College", "BCA"),
    ("Model Engineering College", "B.Tech AI & Data Science"),
    ("Rajagiri College of Social Sciences", "B.Sc Mathematics"),
]


def reset_for_fresh_run():
    """Wipes people-related data and resets ID sequences so this
    script always produces a clean, predictable dataset starting
    from 0001 — regardless of what existed before."""
    print("Resetting for a fresh run...\n")
    with engine.begin() as conn:
        conn.execute(text("TRUNCATE TABLE employee_skills CASCADE"))
        conn.execute(text("TRUNCATE TABLE intern_skills CASCADE"))
        conn.execute(text("TRUNCATE TABLE availability CASCADE"))
        conn.execute(text("TRUNCATE TABLE company_employees CASCADE"))
        conn.execute(text("TRUNCATE TABLE interns_and_students CASCADE"))
        conn.execute(text("ALTER SEQUENCE employee_id_seq RESTART WITH 1"))
        conn.execute(text("ALTER SEQUENCE intern_id_seq RESTART WITH 1"))
    print("✅ Tables cleared, sequences reset to 1.\n")


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
        raise ValueError(f"Designation '{title}' not found — run backend/seed_skills.py first")
    return row[0]


def get_employee_id_by_email(email: str) -> str | None:
    with engine.connect() as conn:
        row = conn.execute(
            text("SELECT employee_id FROM company_employees WHERE email = :email"),
            {"email": email},
        ).fetchone()
    return row[0] if row else None


def get_intern_id_by_email(email: str) -> str | None:
    with engine.connect() as conn:
        row = conn.execute(
            text("SELECT intern_id FROM interns_and_students WHERE email = :email"),
            {"email": email},
        ).fetchone()
    return row[0] if row else None


def person_already_has_skills(person_id: str, person_type: str) -> bool:
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
    print("Creating admin account...")
    create_auth_user("admin@rp2.com", "System Admin", "ADMIN")
    print("✅ Admin ready: admin@rp2.com / Password123! (auth-only, not a workforce record)")


def seed_employees():
    domain_configs = [
        ("Data Analytics", DA_SKILLS, DA_EMP_NAMES, "Senior Data Analytics Mentor", "Data Analytics Mentor"),
        ("Data Science", DS_SKILLS, DS_EMP_NAMES, "Senior Data Science Mentor", "Data Science Mentor"),
    ]
    for domain, skills, names, lead_title, mentor_title in domain_configs:
        dept_code = DEPT_CODES[domain]
        lead_designation_id = get_designation_id(lead_title)
        mentor_designation_id = get_designation_id(mentor_title)
        gap = None  # decided per person below
        print(f"\nCreating 9 {domain} employees (3 team leads)...")
        for i, name in enumerate(names):
            email = f"{name.lower()}.{dept_code}@rp2.com"
            is_lead = i < 3
            skill_gap = (i == 4)  # one person per domain with fewer skills, for ranking tests
            designation_id = lead_designation_id if is_lead else mentor_designation_id

            print(f"  {email} [{'TEAM LEAD' if is_lead else 'mentor'}]")
            create_auth_user(email, name, "EMPLOYEE")

            employee_id = get_employee_id_by_email(email)
            if not employee_id:
                with engine.begin() as conn:
                    result = conn.execute(
                        text("""
                            INSERT INTO company_employees
                            (name, email, department, experience_years,
                             weekly_capacity_hours, is_team_lead, designation_id, created_at)
                            VALUES (:name, :email, :dept, :exp, 40, :lead, :desig_id, NOW())
                            RETURNING employee_id
                        """),
                        {
                            "name": name, "email": email, "dept": domain,
                            "exp": round(random.uniform(1.0, 8.0), 1),
                            "lead": is_lead, "desig_id": designation_id,
                        },
                    )
                    employee_id = result.fetchone()[0]
                print(f"    -> {employee_id}")

            assign_skills(employee_id, skills, "employee", gap_test=skill_gap)

    print("\n✅ 18 employees ready (9 per domain, 3 team leads each). All fully available.")


def seed_interns():
    domain_configs = [
        ("DA", DA_SKILLS, DA_INTERN_NAMES, DA_COLLEGE_PROGRAMS),
        ("DS", DS_SKILLS, DS_INTERN_NAMES, DS_COLLEGE_PROGRAMS),
    ]
    for domain, skills, names, college_programs in domain_configs:
        print(f"\nCreating 4 {domain} interns...")
        for i, name in enumerate(names):
            email = f"{name.lower()}.{domain.lower()}intern@rp2.com"
            skill_gap = (i == 1)  # one intern per domain with fewer skills, for ranking tests
            college, degree = random.choice(college_programs)

            print(f"  {email} [AVAILABLE] — {college}, {degree}")
            create_auth_user(email, name, "STUDENT")

            intern_id = get_intern_id_by_email(email)
            if not intern_id:
                with engine.begin() as conn:
                    result = conn.execute(
                        text("""
                            INSERT INTO interns_and_students
                            (name, email, college_institution, degree_program,
                            resume_document_url, review_status, role, current_status, department, created_at)
                            VALUES (:name, :email, :college, :degree, :resume, 'verified', 'intern', 'AVAILABLE', :department, NOW())
                            RETURNING intern_id
                        """),
                        {
                            "name": name, "email": email,
                            "college": college, "degree": degree,
                            "resume": f"https://fake-storage.test/{email}.pdf",
                            "department": "Data Analytics" if domain == "DA" else "Data Science",
                        },
                    )
                    intern_id = result.fetchone()[0]
                print(f"    -> {intern_id}")

            assign_skills(intern_id, skills, "intern", gap_test=skill_gap)

    print("\n✅ 8 interns ready (4 per domain). All fully available.")


if __name__ == "__main__":
    reset_for_fresh_run()
    seed_admin()
    seed_employees()
    seed_interns()
    print("\n🎉 All 27 test accounts ready — password: Password123!")