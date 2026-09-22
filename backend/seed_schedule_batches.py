import sys, os
from datetime import date, timedelta
from sqlalchemy import text

ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.append(ROOT_DIR)
sys.path.append(os.path.join(ROOT_DIR, "ai_engine"))

from ai_engine.db import engine
from skill_utils import get_or_create_skill
from ai_engine.embedding import generate_embedding

def seed_batches():
    print("DEBUG: Entered seed_batches()")

    def get_mentor(name):
        print(f"DEBUG: Looking up mentor '{name}'...")
        with engine.connect() as conn:
            row = conn.execute(
                text("SELECT employee_id, name FROM company_employees WHERE name = :name LIMIT 1"),
                {"name": name},
            ).mappings().fetchone()
        print(f"DEBUG: Result for '{name}': {dict(row) if row else 'NOT FOUND'}")
        return row

    def insert_batch(batch_name, domain, start, end, mentor_row, mode, day_of_week, session):
        with engine.begin() as conn:
            result = conn.execute(
                text("""
                    INSERT INTO student_batches
                    (batch_name, domain, start_date, end_date, mentor_id, status, delivery_mode, day_of_week, session)
                    VALUES (:name, :domain, :start, :end, :mentor_id, 'open', :mode, :day, :session)
                    RETURNING batch_id
                """),
                {
                    "name": batch_name, "domain": domain,
                    "start": start, "end": end,
                    "mentor_id": mentor_row["employee_id"] if mentor_row else None,
                    "mode": mode, "day": day_of_week, "session": session,
                },
            )
            batch_id = result.fetchone()[0]
        mentor_name = mentor_row["name"] if mentor_row else "unassigned"
        print(f"  [{batch_id}] {batch_name} -> {mentor_name} ({day_of_week}, {session})")

    suresh = get_mentor("Suresh")
    anitha = get_mentor("Anitha")
    aravind = get_mentor("Aravind")
    nithya = get_mentor("Nithya")
    fathima = get_mentor("Fathima")

    # --- DS: Suresh — April/May ---
    insert_batch("Apr DS Offline", "Data Science", date(2026, 4, 15), date(2026, 8, 14), suresh, "offline", "Tue & Thu", "Morning")
    insert_batch("May DS Offline", "Data Science", date(2026, 5, 15), date(2026, 9, 14), suresh, "offline", "Tue & Thu", "Evening")

    # --- Agentic AI: Suresh — June/July ---
    insert_batch("Jun Agentic AI Offline", "Agentic AI", date(2026, 6, 15), date(2026, 8, 14), suresh, "offline", "Mon & Wed", "Morning")
    insert_batch("Jul Agentic AI Offline", "Agentic AI", date(2026, 7, 15), date(2026, 9, 14), suresh, "offline", "Mon & Wed", "Afternoon")

    # --- DS: Anitha — June/July ---
    insert_batch("Jun DS Offline", "Data Science", date(2026, 6, 15), date(2026, 10, 14), anitha, "offline", "Mon & Wed", "Morning")
    insert_batch("Jul DS Offline", "Data Science", date(2026, 7, 15), date(2026, 11, 14), anitha, "offline", "Tue & Thu", "Afternoon")

    # --- DA: Nithya — April/July ---
    insert_batch("Apr DA Offline", "Data Analytics", date(2026, 4, 15), date(2026, 8, 14), nithya, "offline", "Mon & Wed", "Morning")
    insert_batch("Jul DA Offline", "Data Analytics", date(2026, 7, 15), date(2026, 11, 14), nithya, "offline", "Tue & Thu", "Afternoon")

    # --- DA: Aravind — May/June ---
    insert_batch("May DA Offline", "Data Analytics", date(2026, 5, 15), date(2026, 9, 14), aravind, "offline", "Tue & Thu", "Morning")
    insert_batch("Jun DA Offline", "Data Analytics", date(2026, 6, 15), date(2026, 10, 14), aravind, "offline", "Mon & Wed", "Afternoon")

    # --- Soft Skills: Fathima — Feb/May, DA + DS (both online) ---
    insert_batch("Feb Soft Skills DS", "Data Science", date(2026, 2, 1), date(2026, 2, 28), fathima, "online", "Mon", "Afternoon")
    insert_batch("May Soft Skills DS", "Data Science", date(2026, 5, 1), date(2026, 5, 31), fathima, "online", "Mon", "Morning")
    insert_batch("Feb Soft Skills DA", "Data Analytics", date(2026, 2, 1), date(2026, 2, 28), fathima, "online", "Tue", "Morning")
    insert_batch("May Soft Skills DA", "Data Analytics", date(2026, 5, 1), date(2026, 5, 31), fathima, "online", "Tue", "Afternoon")

    # --- Bridge Course: Anitha — recurring, days 1-14 each month, Mon/Wed/Fri afternoon ---
    for month_num, month_name in [(4, "Apr"), (5, "May"), (6, "Jun"), (7, "Jul")]:
        insert_batch(
            f"{month_name} Bridge Course",
            "Data Science",
            date(2026, month_num, 1),
            date(2026, month_num, 14),
            anitha,
            "offline",
            "Mon, Wed & Fri",
            "Afternoon"
        )
if __name__ == "__main__":
     print("Starting batch seeding...")
     seed_batches()
     print("✅ Done — all batches created successfully.")