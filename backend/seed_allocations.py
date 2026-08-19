# backend/seed_allocations.py
"""
Seeds the allocations, substitutions, and allocation_logs tables.
Includes realistic project assignments for employees and students,
along with substitution records and audit history.
"""

import sys
import os
import enum
from datetime import datetime, timezone, timedelta
from dotenv import load_dotenv
from sqlalchemy import text
load_dotenv()

# 2. Add ai_engine to Python path using absolute path
ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if ROOT_DIR not in sys.path:
    sys.path.append(ROOT_DIR)

from ai_engine.db import engine



class AllocationStatus(str, enum.Enum):
    PROPOSED = "proposed"
    ACCEPTED = "accepted"
    REJECTED = "rejected"
    ASSIGNED = "assigned"
    SUBSTITUTED = "substituted"
    CANCELLED = "cancelled"


# Sample Allocation Data
ALLOCATIONS_DATA = [
    {
        "allocation_id": "rp2-alloc-0001",
        "resource_type": "employee",
        "resource_id": "rp2-emp-0001",
        "project_id": "rp2-proj-0001",
        "role_on_project": "Lead Data Analyst",
        "allocated_hours": 20,
        "suitability_score": 0.94,
        "status": AllocationStatus.ASSIGNED.value,
        "assigned_by": "AI_Engine",
        "logs": [
            {"action": "PROPOSED", "changed_by": "AI_Engine", "hours_ago": 72},
            {"action": "ASSIGNED", "changed_by": "Resource_Manager", "hours_ago": 24},
        ],
    },
    {
        "allocation_id": "rp2-alloc-0002",
        "resource_type": "student",
        "resource_id": "rp2-int-0001",
        "project_id": "rp2-proj-0001",
        "role_on_project": "Data Analyst Intern",
        "allocated_hours": 20,
        "suitability_score": 0.82,
        "status": AllocationStatus.ACCEPTED.value,
        "assigned_by": "AI_Engine",
        "logs": [
            {"action": "PROPOSED", "changed_by": "AI_Engine", "hours_ago": 48},
            {"action": "ACCEPTED", "changed_by": "stu-0001", "hours_ago": 12},
        ],
    },
    {
        "allocation_id": "rp2-alloc-0003",
        "resource_type": "employee",
        "resource_id": "rp2-emp-0002",
        "project_id": "rp2-proj-0003",
        "role_on_project": "Senior Supply Chain Analyst",
        "allocated_hours": 35,
        "suitability_score": 0.88,
        "status": AllocationStatus.SUBSTITUTED.value,
        "assigned_by": "AI_Engine",
        "substitution": {
            "substitution_id": "rp2-sub-0001",
            "substitute_resource_type": "employee",
            "substitute_resource_id": "emp-0005",
            "reason": "Original resource reallocated to critical high-priority initiative.",
        },
        "logs": [
            {"action": "PROPOSED", "changed_by": "AI_Engine", "hours_ago": 120},
            {"action": "ASSIGNED", "changed_by": "Resource_Manager", "hours_ago": 96},
            {"action": "SUBSTITUTED", "changed_by": "Project_Lead", "hours_ago": 10},
        ],
    },
    {
        "allocation_id": "rp2-alloc-0004",
        "resource_type": "employee",
        "resource_id": "rp2-emp-0003",
        "project_id": "rp2-proj-0004",
        "role_on_project": "Lead ML Engineer",
        "allocated_hours": 40,
        "suitability_score": 0.96,
        "status": AllocationStatus.ASSIGNED.value,
        "assigned_by": "AI_Engine",
        "logs": [
            {"action": "PROPOSED", "changed_by": "AI_Engine", "hours_ago": 36},
            {"action": "ASSIGNED", "changed_by": "Resource_Manager", "hours_ago": 18},
        ],
    },
    {
        "allocation_id": "rp2-alloc-0005",
        "resource_type": "employee",
        "resource_id": "rp2-emp-0004",
        "project_id": "rp2-proj-0005",
        "role_on_project": "Computer Vision Specialist",
        "allocated_hours": 40,
        "suitability_score": 0.91,
        "status": AllocationStatus.PROPOSED.value,
        "assigned_by": "AI_Engine",
        "logs": [
            {"action": "PROPOSED", "changed_by": "AI_Engine", "hours_ago": 6},
        ],
    },
    {
        "allocation_id": "rp2-alloc-0006",
        "resource_type": "student",
        "resource_id": "rp2-int-0002",
        "project_id": "rp2-proj-0006",
        "role_on_project": "NLP Research Assistant",
        "allocated_hours": 20,
        "suitability_score": 0.75,
        "status": AllocationStatus.REJECTED.value,
        "assigned_by": "AI_Engine",
        "logs": [
            {"action": "PROPOSED", "changed_by": "AI_Engine", "hours_ago": 60},
            {"action": "REJECTED", "changed_by": "stu-0002", "hours_ago": 30},
        ],
    },
]


def reset_allocations_tables():
    """Wipes allocations, substitutions, and logs for a clean seed run."""
    print("Cleaning allocation tables...")
    with engine.begin() as conn:
        conn.execute(text("TRUNCATE TABLE allocation_logs CASCADE"))
        conn.execute(text("TRUNCATE TABLE substitutions CASCADE"))
        conn.execute(text("TRUNCATE TABLE allocations CASCADE"))
    print("✅ Allocation tables cleared.\n")


def seed_allocations():
    print("Seeding allocations, substitutions, and logs...")
    log_counter = 1

    now = datetime.now(timezone.utc)

    with engine.begin() as conn:
        for alloc in ALLOCATIONS_DATA:
            assigned_at_time = now - timedelta(hours=24)

            # 1. Insert Allocation Record
            conn.execute(
                text("""
                    INSERT INTO allocations (
                        allocation_id, resource_type, resource_id, project_id,
                        role_on_project, allocated_hours, suitability_score,
                        status, assigned_at, assigned_by
                    )
                    VALUES (
                        :allocation_id, :resource_type, :resource_id, :project_id,
                        :role_on_project, :allocated_hours, :suitability_score,
                        :status, :assigned_at, :assigned_by
                    )
                    ON CONFLICT (allocation_id) DO NOTHING
                """),
                {
                    "allocation_id": alloc["allocation_id"],
                    "resource_type": alloc["resource_type"],
                    "resource_id": alloc["resource_id"],
                    "project_id": alloc["project_id"],
                    "role_on_project": alloc["role_on_project"],
                    "allocated_hours": alloc["allocated_hours"],
                    "suitability_score": alloc["suitability_score"],
                    "status": alloc["status"],
                    "assigned_at": assigned_at_time,
                    "assigned_by": alloc["assigned_by"],
                },
            )
            print(
                f"  Added Allocation: [{alloc['allocation_id']}] "
                f"{alloc['resource_type'].title()} {alloc['resource_id']} -> {alloc['project_id']} ({alloc['status']})"
            )

            # 2. Insert Substitution Record (if applicable)
            if "substitution" in alloc:
                sub = alloc["substitution"]
                conn.execute(
                    text("""
                        INSERT INTO substitutions (
                            substitution_id, original_allocation_id, 
                            substitute_resource_type, substitute_resource_id, 
                            reason, created_at
                        )
                        VALUES (
                            :substitution_id, :original_allocation_id,
                            :substitute_resource_type, :substitute_resource_id,
                            :reason, :created_at
                        )
                        ON CONFLICT (substitution_id) DO NOTHING
                    """),
                    {
                        "substitution_id": sub["substitution_id"],
                        "original_allocation_id": alloc["allocation_id"],
                        "substitute_resource_type": sub["substitute_resource_type"],
                        "substitute_resource_id": sub["substitute_resource_id"],
                        "reason": sub["reason"],
                        "created_at": now - timedelta(hours=10),
                    },
                )
                print(
                    f"    -> Substitution Added: [{sub['substitution_id']}] "
                    f"Replaced with {sub['substitute_resource_type']} {sub['substitute_resource_id']}"
                )

            # 3. Insert Allocation Log Entries
            for log_entry in alloc.get("logs", []):
                log_id = f"rp2-log-{log_counter:04d}"
                log_counter += 1
                log_timestamp = now - timedelta(hours=log_entry["hours_ago"])

                conn.execute(
                    text("""
                        INSERT INTO allocation_logs (
                            log_id, allocation_id, action, changed_by, timestamp
                        )
                        VALUES (:log_id, :allocation_id, :action, :changed_by, :timestamp)
                        ON CONFLICT (log_id) DO NOTHING
                    """),
                    {
                        "log_id": log_id,
                        "allocation_id": alloc["allocation_id"],
                        "action": log_entry["action"],
                        "changed_by": log_entry["changed_by"],
                        "timestamp": log_timestamp,
                    },
                )
                print(f"    -> Log [{log_id}]: Action '{log_entry['action']}' by {log_entry['changed_by']}")

    print("\n✅ Allocations, substitutions, and logs successfully seeded!")


if __name__ == "__main__":
    reset_allocations_tables()
    seed_allocations()