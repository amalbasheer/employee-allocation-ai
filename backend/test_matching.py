# backend/test_matching.py
"""
Runs the REAL matching engine against real seeded projects and people,
and just PRINTS the rankings — doesn't write anything to the database.
Pure verification: does the AI/ML pipeline actually work end to end.
"""

import sys
import os

ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.append(ROOT_DIR)
sys.path.append(os.path.join(ROOT_DIR, "ai_engine"))

from dotenv import load_dotenv
from sqlalchemy import text
from ai_engine.db import engine
from ai_engine.recommend import recommend_candidates_for_project

load_dotenv()


def get_all_project_ids() -> list[str]:
    with engine.connect() as conn:
        rows = conn.execute(text("SELECT project_id, title FROM projects ORDER BY project_id")).fetchall()
    return [(r[0], r[1]) for r in rows]


def print_ranking(label: str, candidates: list[dict]):
    if not candidates:
        print(f"    {label}: (none found)")
        return
    print(f"    {label}:")
    for rank, c in enumerate(candidates, start=1):
        print(f"      {rank}. {c.get('name', c['id'])}  —  score: {c['suitability_score']}")


def run_test():
    projects = get_all_project_ids()
    print(f"Testing matching engine against {len(projects)} seeded projects...\n")
    print("=" * 60)

    for project_id, title in projects:
        print(f"\nPROJECT: {title}  [{project_id}]")
        try:
            result = recommend_candidates_for_project(project_id)
        except Exception as e:
            print(f"    ❌ ERROR: {e}")
            continue

        roles_needed = result["roles_needed"]
        print(f"  Roles needed: {roles_needed}")

        if "team_lead" in roles_needed:
            # Work engagement — interns only pair with a team lead,
            # so the plain mentor pool is irrelevant here
            print_ranking("Eligible Team Leads", result.get("eligible_team_leads", []))
            print_ranking("Interns", result.get("interns", []))
        else:
            # Training engagement — mentor only, no interns involved
            print_ranking("Mentors", result.get("mentors", []))

        print("-" * 60)

    print("\n✅ Test complete.")


if __name__ == "__main__":
    run_test()