# backend/create_auth_for_new_employees.py
"""
Creates real Supabase Auth accounts for the 6 employees added directly
via SQL tonight — needed for them to actually be able to log in, since
raw SQL inserts into company_employees never touch Supabase Auth.
"""

import sys, os

ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.append(ROOT_DIR)

from seed_dummy_users import create_auth_user  # reuse the existing function

NEW_EMPLOYEES = [
    ("divya.da@rp2.com", "Divya", "employee"),
    ("arjun.da@rp2.com", "Arjun", "employee"),
    ("sneha.da@rp2.com", "Sneha", "employee"),
    ("kiran.ds@rp2.com", "Kiran", "employee"),
    ("meera.ds@rp2.com", "Meera", "employee"),
    ("rahul.ds@rp2.com", "Rahul", "employee"),
]

if __name__ == "__main__":
    print("Creating Supabase Auth accounts for 6 new employees...\n")
    for email, name, role in NEW_EMPLOYEES:
        user_id = create_auth_user(email, name, role)
        print(f"  {email} -> auth user_id: {user_id}")
    print("\n✅ Done. All 6 can now log in with password: Password123!")