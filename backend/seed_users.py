import os
from dotenv import load_dotenv
from supabase import create_client, Client

load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_SERVICE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY")

if not SUPABASE_URL or not SUPABASE_SERVICE_KEY:
    raise ValueError("Missing SUPABASE_URL or SUPABASE_SERVICE_ROLE_KEY in environment.")

supabase: Client = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)

TEST_USERS = [
    {
        "email": "admin@company.com",
        "password": "Password123!",
        "name": "System Admin",
        "role": "ADMIN",
        "table": "company_employees",
        "payload": {
            "department": "Engineering",
            "experience_years": 10.0,
            "weekly_capacity_hours": 40,
            "is_team_lead": True,
            "designation_id": "e1074e58-7651-4091-81e8-9cddf9d5a08e",
            "created_at": "2024-01-01T00:00:00Z"
        },
    },
    {
        "email": "employee@company.com",
        "password": "Password123!",
        "name": "Alex Smith",
        "role": "EMPLOYEE",
        "table": "company_employees",
        "payload": {
            "department": "AI Labs",
            "experience_years": 3.5,
            "weekly_capacity_hours": 40,
            "is_team_lead": False,
            "designation_id": "2fa08a60-f1dd-40ec-8f26-3b134ec44b35",
            "created_at": "2024-01-01T00:00:00Z"
        },
    },
    {
        "email": "student@company.com",
        "password": "Password123!",
        "name": "Jordan Doe",
        "role": "STUDENT",
        "table": "interns_and_students",
        "payload": {
            "college_institution": "MIT",
            "degree_program": "B.S. Computer Science",
            "resume_document_url": "https://example.com/resumes/jordan.pdf",
            "role": "STUDENT",
            "current_status": "AVAILABLE",
            "review_status": "pending_review",
            "created_at": "2024-01-01T00:00:00Z"
        },
    },
]

def seed_database():
    print("Starting database seeding...\n")

    for user_data in TEST_USERS:
        email = user_data["email"]
        password = user_data["password"]
        role = user_data["role"]
        table_name = user_data["table"]

        print(f"Processing: {email} [{role}]")
        user_id = None

        # 1. Create or retrieve Supabase Auth user
        try:
            auth_res = supabase.auth.admin.create_user({
                "email": email,
                "password": password,
                "email_confirm": True,
                "user_metadata": {"name": user_data["name"], "role": role}
            })
            user_id = auth_res.user.id
            print(f"  ✓ Auth Account Created: {user_id}")
        except Exception:
            print("  ! Auth User exists, fetching existing user ID...")
            try:
                users_resp = supabase.auth.admin.list_users()
                # Handle both list and object response shapes
                users_list = users_resp.users if hasattr(users_resp, 'users') else users_resp
                for u in users_list:
                    if u.email == email:
                        user_id = u.id
                        break
            except Exception as fetch_err:
                print(f"  ✖ Failed to list users: {fetch_err}")

        if not user_id:
            print(f"  ✖ Failed to resolve User ID for {email}\n")
            continue

        # 2. Map payload to correct Primary Keys
        if table_name == "company_employees":
            db_record = {
                "employee_id": user_id,
                "name": user_data["name"],
                "email": email,
                **user_data["payload"]
            }
        else:
            db_record = {
                "intern_id": user_id,
                "name": user_data["name"],
                "email": email,
                **user_data["payload"]
            }

        # 3. Upsert into target table
        try:
            supabase.table(table_name).upsert(db_record).execute()
            print(f"  ✓ Linked record in '{table_name}' table\n")
        except Exception as e:
            print(f"  ✖ Database upsert failed: {e}\n")

    print("Seeding complete.")

if __name__ == "__main__":
    seed_database()