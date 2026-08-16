# backend/seed_dummy_users.py
"""
Creates a full set of test accounts with REAL Supabase Auth logins:
- 1 admin
- 20 employees (10 Data Analytics + 10 Data Science, 4 team leads each)
- 20 interns (10 DA + 10 DS)

Every account shares the same password: Password123!

This replaces the old seed_users.py (3 accounts) and the old
seed_dummy_employees.py / seed_dummy_interns.py (no real login) —
delete those three files once this one is working.
"""

import sys
import os
import random
from uuid import uuid4
from dotenv import load_dotenv
from supabase import create_client, Client
from sqlalchemy import text

# ai_engine/ is a sibling folder of backend/ — add it to the import path
sys.path.append(os.path.join(os.path.dirname(__file__), "..", "ai_engine"))
from db import engine
from skill_utils import get_or_create_skill

load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_SERVICE_KEY = os.getenv("SUPABASE_KEY")

if not SUPABASE_URL or not SUPABASE_SERVICE_KEY:
    raise ValueError("Missing SUPABASE_URL or SUPABASE_SERVICE_ROLE_KEY in .env")

supabase: Client = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)

PASSWORD = "Password123!"

DA_SKILLS = ["Python", "SQL", "Data Analytics", "Power BI", "Tableau", "Statistics"]
DS_SKILLS = ["Python", "Machine Learning", "Deep Learning", "PyTorch", "TensorFlow", "Computer Vision"]

DEPT_CODES = {"Data Analytics": "da", "Data Science": "ds"}

DA_EMP_NAMES = ["Aravind", "Nithya", "Sanjay", "Lakshmi", "Vivek", "Pooja", "Karthik", "Deepa", "Rohan", "Fathima"]
DS_EMP_NAMES = ["Rajesh", "Anitha", "Suresh", "Meenakshi", "Manoj", "Latha", "Prasad", "Swathi", "Anand", "Revathi"]

DA_INTERN_NAMES = ["Amal", "Priya", "Rahul", "Sneha", "Arjun", "Divya", "Naveen", "Meera", "Vishnu", "Anjali"]
DS_INTERN_NAMES = ["Athira", "Sandeep", "Nisha", "Gokul", "Reshma", "Vignesh", "Haritha", "Sarath", "Devika", "Adarsh"]


def create_auth_user(email: str, name: str, role: str) -> str:
    """Creates a Supabase Auth login, or reuses it if it already exists."""
    try:
        res = supabase.auth.admin.create_user({
            "email": email,
            "password": PASSWORD,
            "email_confirm": True,
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

def assign_skills(person_id: str, skill_pool: list[str], person_type: str, gap_test: bool = False):
    table = "employee_skills" if person_type == "employee" else "intern_skills"
    id_col = "employee_id" if person_type == "employee" else "intern_id"
    chosen = random.sample(skill_pool, 2 if gap_test else random.randint(3, 5))

    with engine.begin() as conn:
        for skill_name in chosen:
            skill_id = get_or_create_skill(skill_name)
            if person_type == "employee":
                conn.execute(
                    text(f"""
                        INSERT INTO {table} ({id_col}, skill_id, proficiency_level, is_custom_override)
                        VALUES (:pid, :skill_id, :prof, FALSE)
                        ON CONFLICT DO NOTHING
                    """),
                    {"pid": person_id, "skill_id": skill_id, "prof": random.randint(2, 5)},
                )
            else:
                conn.execute(
                    text(f"""
                        INSERT INTO {table} (id, {id_col}, skill_id, proficiency_level, extraction_confidence)
                        VALUES (:id, :pid, :skill_id, :prof, :conf)
                    """),
                    {
                        "id": str(uuid4()), "pid": person_id, "skill_id": skill_id,
                        "prof": round(random.uniform(2.0, 5.0), 1),
                        "conf": round(random.uniform(0.7, 0.98), 2),
                    },
                )


def seed_admin():
    print("\nCreating admin account...")
    admin_id = create_auth_user("admin@rp2.test", "System Admin", "ADMIN")
    designation_id = get_designation_id("Senior AI Engineer")
    with engine.begin() as conn:
        conn.execute(
           text("""
             INSERT INTO company_employees
             (employee_id, name, email, department, experience_years, weekly_capacity_hours, is_team_lead, designation_id, created_at)
             VALUES (:id, 'System Admin', 'admin@rp2.test', 'Administration', 10.0, 40, TRUE, :desig_id, NOW())
             ON CONFLICT (employee_id) DO NOTHING
        """),
    {"id": admin_id, "desig_id": designation_id},
)
    print("✅ Admin ready: admin@rp2.test / Password123!")


def seed_employees():
    domain_configs = [
        ("Data Analytics", DA_SKILLS, DA_EMP_NAMES),
        ("Data Science", DS_SKILLS, DS_EMP_NAMES),
    ]
    for domain, skills, names in domain_configs:
        dept_code = DEPT_CODES[domain]
        designation_title = "Senior AI Engineer" if domain == "Data Science" else "Fullstack Developer"
        designation_id = get_designation_id(designation_title)
        print(f"\nCreating 10 {domain} employees (4 team leads)...")
        for i, name in enumerate(EMP_NAMES):
            email = f"{name.lower()}.{dept_code}@rp2.test"
            is_lead = i < 4
            near_cap = (i == 4)
            gap = (i == 5)

            print(f"  {email} [{'TEAM LEAD' if is_lead else 'employee'}]")
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
                    "dept": domain, "exp": round(random.uniform(1.0, 8.0), 1), "lead": is_lead,
                    "desig_id": designation_id,
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

    print("\n✅ 20 employees created with real logins.")

def seed_interns():
    domain_configs = [
        ("DA", DA_SKILLS, DA_INTERN_NAMES),
        ("DS", DS_SKILLS, DS_INTERN_NAMES),
    ]
    for domain, skills, names in domain_configs:
        print(f"\nCreating 10 {domain} interns...")
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
                     resume_document_url, review_status, role, current_status)
                    VALUES (:id, :name, :email, :college, :degree, :resume, 'verified', 'intern', :status)
                    ON CONFLICT (intern_id) DO NOTHING
                  """),

                    {
                        "id": user_id, "name": f"{name} ({domain} intern)", "email": email,
                        "college": "Rajagiri College of Social Sciences", "degree": "B.Tech CS",
                        "resume": f"https://fake-storage.test/{user_id}.pdf", "status": status,
                    },
                )

            assign_skills(user_id, skills, "intern", gap_test=gap)

    print("\n✅ 20 interns created with real logins.")


if __name__ == "__main__":
    seed_admin()
    seed_employees()
    seed_interns()
    print("\n🎉 All 41 test accounts ready — everyone shares password: Password123!")