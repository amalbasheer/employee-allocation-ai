# backend/create_test_auth_2.py
import sys, os

ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.append(ROOT_DIR)

from seed_dummy_users import create_auth_user

NEW_TEST_ACCOUNTS = [
    ("santamarym04@gmail.com", "Aravind", "employee"),
    ("santamarym024@gmail.com", "Suresh", "employee"),
]

if __name__ == "__main__":
    for email, name, role in NEW_TEST_ACCOUNTS:
        user_id = create_auth_user(email, name, role)
        print(f"{email} -> {user_id}")