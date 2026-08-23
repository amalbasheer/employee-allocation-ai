# backend/seed_availability.py
"""
Seeds the availability table for all employees for the current week.
Most people get full capacity (available_hours = weekly_capacity_hours);
a couple are deliberately given reduced hours to test that the
optimizer/matching correctly accounts for people who are partly busy.
"""

import sys, os
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
        rows = conn.execute(
            text("SELECT employee_id, name, weekly_capacity_hours FROM company_employees")
        ).mappings().fetchall()
    return [dict(r) for r in rows]


def seed_availability():
    week_start = get_this_weeks_monday()
    employees = get_all_employees()

    reduced_hours_ids = {employees[3]["employee_id"], employees[12]["employee_id"]} if len(employees) > 12 else set()

    with engine.begin() as conn:
        for emp in employees:
            is_reduced = emp["employee_id"] in reduced_hours_ids
            available_hours = 5 if is_reduced else emp["weekly_capacity_hours"]

            conn.execute(
                text("""
                    INSERT INTO availability
                    (resource_type, resource_id, week_start_date, available_hours, is_on_leave)
                    VALUES ('employee', :emp_id, :week_start, :hours, FALSE)
                """),
                {
                    "emp_id": emp["employee_id"],
                    "week_start": week_start,
                    "hours": available_hours,
                },
            )
            tag = " (reduced/near-capacity)" if is_reduced else ""
            print(f"  {emp['name']} ({emp['employee_id']}) -> {available_hours} hrs{tag}")

    print(f"\n✅ Availability seeded for {len(employees)} employees, week starting {week_start}.")


if __name__ == "__main__":
    reset()
    seed_availability()