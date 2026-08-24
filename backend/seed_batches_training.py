# backend/seed_batches_training.py
"""
Seeds student_batches (no mentor pre-assigned — admin assigns manually
via frontend) and training_engagements + training_requirements
(skill-matched, team leads only, with deliberate date-overlap test
cases for both DA and DS domains).
"""

import sys, os
from datetime import date, timedelta
from sqlalchemy import text

ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.append(ROOT_DIR)
sys.path.append(os.path.join(ROOT_DIR, "ai_engine"))

from ai_engine.db import engine
from skill_utils import get_or_create_skill
from ai_engine.embedding import generate_embedding

DOMAINS = [("Data Analytics", "DA"), ("Data Science", "DS")]
DELIVERY_MODES = ["Offline", "Online"]


def reset():
    with engine.begin() as conn:
        conn.execute(text("TRUNCATE TABLE student_batches CASCADE"))
        conn.execute(text("TRUNCATE TABLE training_requirements CASCADE"))
        conn.execute(text("TRUNCATE TABLE training_engagements CASCADE"))
        conn.execute(text("ALTER SEQUENCE training_id_seq RESTART WITH 1"))
        conn.execute(text("ALTER SEQUENCE batch_id_seq RESTART WITH 1"))
    print("Cleared batches/training tables, sequences reset.\n")


def seed_batches():
    for month_num, month_name in [(7, "Jul"), (8, "Aug")]:
        start = date(2026, month_num, 15)
        end_month = month_num + 4
        end_year = 2026
        if end_month > 12:
            end_month -= 12
            end_year += 1
        end = date(end_year, end_month, 15)

        for domain, short in DOMAINS:
            for mode in DELIVERY_MODES:
                batch_name = f"{month_name} {short} {mode}"

                with engine.begin() as conn:
                    result = conn.execute(
                        text("""
                            INSERT INTO student_batches
                            (batch_name, domain, start_date, end_date, status, delivery_mode)
                            VALUES (:name, :domain, :start, :end, 'open', :mode)
                            RETURNING batch_id
                        """),
                        {
                            "name": batch_name, "domain": domain,
                            "start": start, "end": end, "mode": mode.lower(),
                        },
                    )
                    batch_id = result.fetchone()[0]

                print(f"  [{batch_id}] {batch_name} ({start} to {end}) — mentor to be assigned manually")


def seed_training():
    base = date.today() + timedelta(days=10)
    engagements = [
        {"title": "Intro to Machine Learning Webinar", "engagement_type": "webinar",
         "description": "Overview webinar introducing machine learning concepts, model training, and PyTorch basics.",
         "start_offset": 0, "duration_days": 1, "skills": [("Machine Learning", 4, True), ("PyTorch", 3, False)]},
        {"title": "Data Visualization Best Practices Demo", "engagement_type": "demo",
         "description": "Live demo showcasing effective dashboard design using Power BI and Tableau.",
         "start_offset": 3, "duration_days": 1, "skills": [("Power BI", 3, True), ("Tableau", 3, False)]},
        {"title": "SQL Query Optimization Webinar", "engagement_type": "webinar",
         "description": "Session covering indexing strategies and query performance tuning in SQL.",
         "start_offset": 5, "duration_days": 1, "skills": [("SQL", 3, True)]},
        {"title": "Git & Version Control Basics Demo", "engagement_type": "demo",
         "description": "Live walkthrough of Git branching, merging, and collaborative workflows.",
         "start_offset": 8, "duration_days": 1, "skills": [("Git", 2, True)]},
        {"title": "Deep Learning Model Deployment Webinar", "engagement_type": "webinar",
         "description": "Overview of deploying trained deep learning models into production pipelines.",
         "start_offset": 8, "duration_days": 1, "skills": [("Deep Learning", 4, True), ("Python", 3, True)]},

        {"title": "Cloud Security Fundamentals Workshop", "engagement_type": "workshop",
         "description": "Hands-on sessions covering AWS security basics, IAM, and encryption for beginners.",
         "start_offset": 12, "duration_days": 2, "skills": [("Python", 2, False), ("SQL", 2, False)]},
        {"title": "Computer Vision Applications Workshop", "engagement_type": "workshop",
         "description": "Hands-on workshop building basic image classification and object detection pipelines.",
         "start_offset": 13, "duration_days": 2,  # DS-side overlap with Cloud Security
         "skills": [("Computer Vision", 3, True), ("Python", 3, True)]},

        {"title": "Power BI Dashboard Design Workshop", "engagement_type": "workshop",
         "description": "Hands-on sessions building interactive dashboards with Power BI, focused on business reporting.",
         "start_offset": 16, "duration_days": 2, "skills": [("Power BI", 3, True), ("Data Analytics", 2, False)]},
        {"title": "Statistical Analysis for Business Webinar", "engagement_type": "webinar",
         "description": "Session covering descriptive and inferential statistics for business decision-making.",
         "start_offset": 17, "duration_days": 1,  # DA-side overlap with Power BI Workshop
         "skills": [("Statistics", 3, True), ("Data Analytics", 2, False)]},

        {"title": "Full-Stack Data Analytics Bootcamp Workshop", "engagement_type": "workshop",
         "description": "Intensive multi-day workshop covering the full data analytics pipeline — SQL, Python, Power BI dashboards, and statistical analysis.",
         "start_offset": 22, "duration_days": 3, "skills": [("Python", 3, True), ("SQL", 3, True), ("Power BI", 3, True), ("Statistics", 2, False)]},
    ]

    for eng in engagements:
        start = base + timedelta(days=eng["start_offset"])
        end = start + timedelta(days=eng["duration_days"] - 1)

        with engine.begin() as conn:
            result = conn.execute(
                text("""
                    INSERT INTO training_engagements (title, engagement_type, description, start_date, end_date, required_hours, status)
                    VALUES (:title, :etype, :desc, :start, :end, :hours, 'open')
                    RETURNING engagement_id
                """),
                {
                    "title": eng["title"], "etype": eng["engagement_type"],
                    "desc": eng["description"], "start": start, "end": end,
                    "hours": eng["duration_days"] * 4,
                },
            )
            engagement_id = result.fetchone()[0]

        for skill_name, min_prof, mandatory in eng["skills"]:
            skill_id = get_or_create_skill(skill_name)
            text_context = f"{skill_name} skill required for: {eng['title']} - {eng['description']}"
            embedding = generate_embedding(text_context)
            with engine.begin() as conn:
                conn.execute(
                    text("""
                        INSERT INTO training_requirements (engagement_id, skill_id, min_proficiency, is_mandatory, requirement_embedding)
                        VALUES (:eid, :sid, :prof, :mand, :emb)
                    """),
                    {"eid": engagement_id, "sid": skill_id, "prof": min_prof, "mand": mandatory, "emb": embedding},
                )
        print(f"  [{engagement_id}] {eng['title']} ({start} to {end})")


if __name__ == "__main__":
    reset()
    print("Seeding batches (Jul + Aug, no mentor pre-assigned)...")
    seed_batches()
    print("\nSeeding training engagements (with DA + DS overlap test cases)...")
    seed_training()
    print("\n✅ Done.")