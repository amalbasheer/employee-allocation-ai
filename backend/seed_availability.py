# backend/seed_availability.py
"""
Seeds the availability table for all employees for the current week.
Inserts separate rows for 'morning' and 'evening' sessions.
Includes varied test cases: full capacity, reduced hours, and employees on leave.
"""

import os
import sys
from datetime import date, timedelta
from sqlalchemy import text

ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.append(ROOT_DIR)
sys.path.append(os.path.join(ROOT_DIR, "ai_engine"))

from ai_engine.db import engine


def get_this_weeks_monday() -> date:
    today = date.today()
    return today - timedelta(days=today.weekday())


def reset():
    with engine.begin() as conn:
        conn.execute(text("TRUNCATE TABLE availability CASCADE"))
    print("Cleared availability table.\n")


def get_all_employees():
    with engine.connect() as conn:
        rows = (
            conn.execute(
                text(
                    "SELECT employee_id, name, weekly_capacity_hours FROM company_employees"
                )
            )
            .mappings()
            .fetchall()
        )
    return [dict(r) for r in rows]


def seed_availability():
    week_start = get_this_weeks_monday()
    employees = get_all_employees()

    if not employees:
        print("⚠️ No employees found in company_employees table.")
        return

    # Assign specific employee indices to test cases
    leave_emp_ids = (
        {employees[1]["employee_id"]} if len(employees) > 1 else set()
    )
    reduced_emp_ids = (
        {employees[3]["employee_id"], employees[12]["employee_id"]}
        if len(employees) > 12
        else set()
    )

    insert_query = text("""
        INSERT INTO availability
        (resource_type, resource_id, week_start_date, available_hours, is_on_leave, leave_reason, session)
        VALUES ('employee', :emp_id, :week_start, :hours, :is_on_leave, :leave_reason, :session)
    """)

    with engine.begin() as conn:
        for emp in employees:
            emp_id = emp["employee_id"]
            total_cap = float(emp["weekly_capacity_hours"] or 40.0)

            # --- CASE 1: Employee is On Leave ---
            if emp_id in leave_emp_ids:
                leave_reason = "Medical Leave / Sick"
                for session_name in ["morning", "evening"]:
                    conn.execute(
                        insert_query,
                        {
                            "emp_id": emp_id,
                            "week_start": week_start,
                            "hours": 0.0,
                            "is_on_leave": True,
                            "leave_reason": leave_reason,
                            "session": session_name,
                        },
                    )
                print(f" 🏖️ {emp['name']} ({emp_id}) -> ON LEAVE ({leave_reason})")

            # --- CASE 2: Employee has Reduced / Partial Availability ---
            elif emp_id in reduced_emp_ids:
                # Morning session gets 5 hours, Evening gets 0 hours
                sessions = [
                    {"name": "morning", "hours": 5.0},
                    {"name": "evening", "hours": 0.0},
                ]
                for s in sessions:
                    conn.execute(
                        insert_query,
                        {
                            "emp_id": emp_id,
                            "week_start": week_start,
                            "hours": s["hours"],
                            "is_on_leave": False,
                            "leave_reason": None,
                            "session": s["name"],
                        },
                    )
                print(
                    f" ⚠️ {emp['name']} ({emp_id}) -> REDUCED (Morning: 5 hrs, Evening: 0 hrs)"
                )

            # --- CASE 3: Standard Full Capacity ---
            else:
                session_hours = total_cap / 2.0  # Split 40 hrs into 20 Morning + 20 Evening
                for session_name in ["morning", "evening"]:
                    conn.execute(
                        insert_query,
                        {
                            "emp_id": emp_id,
                            "week_start": week_start,
                            "hours": session_hours,
                            "is_on_leave": False,
                            "leave_reason": None,
                            "session": session_name,
                        },
                    )
                print(
                    f" ✅ {emp['name']} ({emp_id}) -> FULL ({session_hours} hrs/session)"
                )

    print(
        f"\n✅ Availability seeded for {len(employees)} employees across 'morning' & 'evening' sessions for week starting {week_start}."
    )


if __name__ == "__main__":
    reset()
    seed_availability()