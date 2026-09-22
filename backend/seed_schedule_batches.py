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
    def get_mentor(name):
        with engine.connect() as conn:
            row = conn.execute(
                text("SELECT employee_id, name FROM company_employees WHERE name = :name LIMIT 1"),
                {"name": name},
            ).mappings().fetchone()
        return row

    def insert_batch(batch_name, domain, start, end, mentor_row, mode, day, session,):
        with engine.begin() as conn:
            result = conn.execute(
                text("""
                    INSERT INTO student_batches
                    (batch_name, domain, start_date, end_date, mentor_id, status, delivery_mode, session, day_of_week)
                    VALUES (:name, :domain, :start, :end, :mentor_id, 'open', :mode, :session, :day_of_week)
                    RETURNING batch_id
                """),
                {
                    "name": batch_name, "domain": domain,
                    "start": start, "end": end,
                    "mentor_id": mentor_row["employee_id"] if mentor_row else None,
                    "mode": mode, "session": session, "day_of_week": day,
                },
            )
            batch_id = result.fetchone()[0]
        mentor_name = mentor_row["name"] if mentor_row else "unassigned"
        print(f"  [{batch_id}] {batch_name} -> {mentor_name} ({session})")

    ajmal = get_mentor("Ajmal")
    sneha = get_mentor("Sneha")
    asif = get_mentor("Asif")
    mubashira = get_mentor("Mubashira")
    amina = get_mentor("Amina")

    # --- DS: Suresh — April/May ---
    insert_batch("Jun DS Offline", "Data Science", date(2026, 6, 15), date(2026, 9, 14), ajmal, "offline", "Tue, Thur", "Morning")
    insert_batch("Jul DS Offline", "Data Science", date(2026, 7, 15), date(2026, 10, 14), ajmal, "offline", "Tue, Thur", "Evening")
    # --- Agentic AI: Suresh — June/July ---
    insert_batch("Sep Agentic AI Offline", "Agentic AI", date(2026, 9, 15), date(2026, 10, 14), ajmal, "offline", "Mon, Wed, Fri" , "Morning")
    
    # --- DS: Anitha — June/July ---
    insert_batch("Aug DS Offline", "Data Science", date(2026, 8, 15), date(2026, 11, 14), sneha, "offline", "Mon, Wed" , "Morning")
    insert_batch("Sep DS Offline", "Data Science", date(2026, 9, 15), date(2026, 12, 14), sneha, "offline", "Tue, Thur",  "Morning")

    # --- DA: Nithya — April/July ---
    insert_batch("Jun DA Offline", "Data Analytics", date(2026, 6, 15), date(2026, 9, 14), asif, "offline", "Mon, Wed",  "Morning")
    insert_batch("Jul DA Offline", "Data Analytics", date(2026, 7, 15), date(2026, 10, 14), asif, "offline", "Tue, Thur" , "Evening")

    # --- DA: Aravind — May/June ---
    insert_batch("Aug DA Offline", "Data Analytics", date(2026, 8, 15), date(2026, 11, 14), mubashira, "offline", "Tue, Thur" , "Morning")
    insert_batch("Sep DA Offline", "Data Analytics", date(2026, 9, 15), date(2026, 12, 14), mubashira, "offline", "Mon, Wed" , "Evening")

    # --- Soft Skills: Fathima — Feb/May, DA + DS (both online) ---
    insert_batch("Aug Soft Skills DS", "Soft Skill", date(2026, 8, 1), date(2026, 11, 28), amina, "offline", "Mon" , "Morning")
    insert_batch("Sep Soft Skills DS", "Soft Skill", date(2026, 9, 1), date(2026, 12, 31), amina, "offline", "Tue",  "Morning")
    insert_batch("Aug Soft Skills DA", "Soft Skill", date(2026, 8, 1), date(2026, 11, 28), amina, "offline", "Mon", "Evening")
    insert_batch("Sep Soft Skills DA", "Soft Skill", date(2026, 9, 1), date(2026, 12, 31), amina, "offline", "Tue", "Evening")
    insert_batch("Combined", "Soft Skill", date(2026, 8, 1), date(2026, 12, 31), amina, "offline", "Fri", "Morning")
        

    # --- Bridge Course: Anitha — recurring, days 1-14 each month, Mon/Wed/Fri afternoon ---
    for month_num, month_name in [(8, "Aug"), (9, "Sep")]:
        insert_batch(
            f"{month_name} Bridge Course",
            "Data Science",
            date(2026, month_num, 15),
            date(2026, month_num, 30),
            sneha,
            "offline",
            "Evening", "Tue, Thur",
        )

if __name__ == "__main__":
    seed_batches()