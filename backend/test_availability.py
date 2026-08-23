# backend/test_availability.py
"""
Proves the availability filter actually works:
1. Rank candidates for a project, take the #1 team lead
2. Write a REAL allocation for them (status='confirmed')
3. Re-run the ranking for a DIFFERENT project
4. Confirm that person no longer shows up as available
"""

import sys, os
from uuid import uuid4
from sqlalchemy import text

ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.append(ROOT_DIR)
sys.path.append(os.path.join(ROOT_DIR, "ai_engine"))

from ai_engine.db import engine
from ai_engine.recommend import recommend_candidates_for_project


def get_two_open_project_ids():
    with engine.connect() as conn:
        rows = conn.execute(
            text("SELECT project_id, title FROM projects WHERE status = 'open' ORDER BY project_id LIMIT 2")
        ).fetchall()
    return rows


def write_allocation(project_id: str, resource_id: str, resource_type: str, role: str, score: float):
    with engine.begin() as conn:
        conn.execute(
            text("""
              INSERT INTO allocations
              (allocation_id, resource_type, resource_id, reference_type, reference_id,
              role_on_project, allocated_hours, suitability_score, status, assigned_by, assigned_at)
              VALUES (:aid, :rtype, :rid, 'project', :pid, :role, 20, :score, 'assigned', 'AI_Engine_Test', NOW())
            """),
            {
              "aid": f"rp2-alloc-{str(uuid4())[:8]}", "rtype": resource_type, "rid": resource_id,
              "pid": project_id, "role": role, "score": score,
            },
        )
        if resource_type == "intern":
            conn.execute(
                text("UPDATE interns_and_students SET current_status = 'ASSIGNED' WHERE intern_id = :iid"),
                {"iid": resource_id},
            )
    print(f"  Wrote allocation: {resource_id} -> {project_id} ({role}, confirmed)")

def run():
    projects = get_two_open_project_ids()
    if len(projects) < 2:
        print("Need at least 2 open projects to run this test.")
        return

    proj_a_id, proj_a_title = projects[0]
    proj_b_id, proj_b_title = projects[1]

    print(f"BEFORE — ranking for Project B ({proj_b_title}):")
    result_before = recommend_candidates_for_project(proj_b_id)
    top_before = (result_before.get("eligible_team_leads") or result_before.get("mentors"))[0]
    print(f"  Top candidate: {top_before['name']} — score {top_before['suitability_score']}\n")

    print(f"Confirming {top_before['name']} to Project A ({proj_a_title})...")
    write_allocation(proj_a_id, top_before["id"], "employee", "team_lead", top_before["suitability_score"])

    print(f"\nAFTER — re-ranking for Project B ({proj_b_title}):")
    result_after = recommend_candidates_for_project(proj_b_id)
    candidates_after = result_after.get("eligible_team_leads") or result_after.get("mentors")
    names_after = [c["name"] for c in candidates_after]

    print(f"  Candidates now: {names_after}")

    if top_before["name"] not in names_after:
        print(f"\n✅ PASS: {top_before['name']} correctly excluded — availability filter works.")
    else:
        print(f"\n❌ FAIL: {top_before['name']} still shows up — filter is NOT working.")


if __name__ == "__main__":
    run()