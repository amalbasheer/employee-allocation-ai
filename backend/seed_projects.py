# backend/seed_projects.py
"""
Seeds the projects and project_requirements tables.
Uses ProjectStatus enum string values ('open', 'in_progress').
Uses ai_engine/embeddings.py to compute requirement_embedding vectors.
"""

import sys
import os
import enum
from datetime import date, timedelta
from dotenv import load_dotenv, find_dotenv
from sqlalchemy import text

load_dotenv(find_dotenv())

# 2. Add ai_engine to Python path using absolute path
ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if ROOT_DIR not in sys.path:
    sys.path.append(ROOT_DIR)

from ai_engine.db import engine
from skill_utils import get_or_create_skill
from ai_engine.embedding import generate_embedding



class ProjectStatus(str, enum.Enum):
    OPEN = "open"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


load_dotenv()

PROJECTS_DATA = [
    # --- Data Analytics Projects ---
    {
        "project_id": "rp2-proj-0001",
        "title": "E-Commerce Customer Churn & Sentiment Dashboard",
        "project_type": "Data Analytics",
        "description": "Analyze customer transaction history and feedback to build an interactive dashboard tracking churn rate and sentiment metrics.",
        "start_date": date.today(),
        "end_date": date.today() + timedelta(days=90),
        "required_hours_per_week": 40,
        "priority_level": "High",
        "status": ProjectStatus.OPEN.value,
        "required_skills": [
            {"name": "SQL", "min_proficiency": 3, "is_mandatory": True},
            {"name": "Power BI", "min_proficiency": 4, "is_mandatory": True},
            {"name": "Python", "min_proficiency": 2, "is_mandatory": False},
            {"name": "Data Analytics", "min_proficiency": 3, "is_mandatory": True},
        ],
    },
    {
        "project_id": "rp2-proj-0002",
        "title": "Healthcare Operations & Patient Flow Analytics",
        "project_type": "Data Analytics",
        "description": "Optimize hospital bed capacity and emergency room wait times using historical admission datasets.",
        "start_date": date.today() + timedelta(days=7),
        "end_date": date.today() + timedelta(days=60),
        "required_hours_per_week": 30,
        "priority_level": "Medium",
        "status": ProjectStatus.OPEN.value,
        "required_skills": [
            {"name": "Tableau", "min_proficiency": 3, "is_mandatory": True},
            {"name": "SQL", "min_proficiency": 3, "is_mandatory": True},
            {"name": "Statistics", "min_proficiency": 2, "is_mandatory": False},
        ],
    },
    {
        "project_id": "rp2-proj-0003",
        "title": "Supply Chain Inventory Forecasting Analytics",
        "project_type": "Data Analytics",
        "description": "Develop automated reports to highlight stockout risks and reorder thresholds across retail distribution centers.",
        "start_date": date.today() - timedelta(days=15),
        "end_date": date.today() + timedelta(days=45),
        "required_hours_per_week": 35,
        "priority_level": "High",
        "status": ProjectStatus.IN_PROGRESS.value,
        "required_skills": [
            {"name": "Python", "min_proficiency": 3, "is_mandatory": True},
            {"name": "Power BI", "min_proficiency": 3, "is_mandatory": True},
            {"name": "Statistics", "min_proficiency": 3, "is_mandatory": False},
        ],
    },

    # --- Data Science Projects ---
    {
        "project_id": "rp2-proj-0004",
        "title": "Predictive Financial Fraud Detection Pipeline",
        "project_type": "Data Science",
        "description": "Train and deploy machine learning models (XGBoost/LightGBM) to detect anomalous transactions in real-time.",
        "start_date": date.today(),
        "end_date": date.today() + timedelta(days=120),
        "required_hours_per_week": 40,
        "priority_level": "High",
        "status": ProjectStatus.OPEN.value,
        "required_skills": [
            {"name": "Python", "min_proficiency": 4, "is_mandatory": True},
            {"name": "Machine Learning", "min_proficiency": 4, "is_mandatory": True},
            {"name": "PyTorch", "min_proficiency": 3, "is_mandatory": False},
        ],
    },
    {
        "project_id": "rp2-proj-0005",
        "title": "Automated Medical Image Defect Detection",
        "project_type": "Data Science",
        "description": "Construct a Computer Vision CNN pipeline to analyze radiology scans for automated lesion identification.",
        "start_date": date.today() + timedelta(days=14),
        "end_date": date.today() + timedelta(days=150),
        "required_hours_per_week": 40,
        "priority_level": "High",
        "status": ProjectStatus.OPEN.value,
        "required_skills": [
            {"name": "Python", "min_proficiency": 4, "is_mandatory": True},
            {"name": "Computer Vision", "min_proficiency": 4, "is_mandatory": True},
            {"name": "TensorFlow", "min_proficiency": 3, "is_mandatory": True},
            {"name": "Deep Learning", "min_proficiency": 4, "is_mandatory": True},
        ],
    },
    {
        "project_id": "rp2-proj-0006",
        "title": "NLP Customer Support Ticket Classifier",
        "project_type": "Data Science",
        "description": "Fine-tune an LLM/Transformer model to auto-categorize and route high-priority customer support tickets.",
        "start_date": date.today() - timedelta(days=30),
        "end_date": date.today() + timedelta(days=30),
        "required_hours_per_week": 20,
        "priority_level": "Low",
        "status": ProjectStatus.IN_PROGRESS.value,
        "required_skills": [
            {"name": "Python", "min_proficiency": 3, "is_mandatory": True},
            {"name": "Deep Learning", "min_proficiency": 3, "is_mandatory": True},
            {"name": "PyTorch", "min_proficiency": 3, "is_mandatory": False},
        ],
    },
]


def reset_projects_table():
    """Wipes projects and requirements so seed script runs cleanly."""
    print("Cleaning project tables...")
    with engine.begin() as conn:
        conn.execute(text("TRUNCATE TABLE project_requirements CASCADE"))
        conn.execute(text("TRUNCATE TABLE allocations CASCADE"))
        conn.execute(text("TRUNCATE TABLE projects CASCADE"))
    print("✅ Project tables cleared.\n")


def seed_projects():
    print("Seeding projects and skill requirements with embeddings...")
    req_counter = 1

    with engine.begin() as conn:
        for proj in PROJECTS_DATA:
            # 1. Insert Project into projects table
            conn.execute(
                text("""
                    INSERT INTO projects (
                        project_id, title, project_type, description, 
                        start_date, end_date, required_hours_per_week, 
                        priority_level, status
                    )
                    VALUES (
                        :project_id, :title, :project_type, :description,
                        :start_date, :end_date, :required_hours_per_week,
                        :priority_level, :status
                    )
                    ON CONFLICT (project_id) DO UPDATE SET
                        title = EXCLUDED.title,
                        description = EXCLUDED.description,
                        status = EXCLUDED.status
                """),
                {
                    "project_id": proj["project_id"],
                    "title": proj["title"],
                    "project_type": proj["project_type"],
                    "description": proj["description"],
                    "start_date": proj["start_date"],
                    "end_date": proj["end_date"],
                    "required_hours_per_week": proj["required_hours_per_week"],
                    "priority_level": proj["priority_level"],
                    "status": proj["status"],
                },
            )
            print(f"\n  Added Project: [{proj['project_id']}] {proj['title']} (Status: {proj['status']})")

            # 2. Insert Requirements into project_requirements table
            for req in proj["required_skills"]:
                skill_id = get_or_create_skill(req["name"])
                req_id = f"rp2-req-{req_counter:04d}"
                req_counter += 1

                # Construct rich text context for embedding calculation
                req_text_context = (
                    f"{req['name']} skill required for project: "
                    f"{proj['title']} - {proj['description']}"
                )

                # Generate vector embedding using Gemini via embeddings.py
                embedding_vector = generate_embedding(req_text_context)

                conn.execute(
                    text("""
                        INSERT INTO project_requirements (
                            requirement_id, project_id, skill_id, min_proficiency, is_mandatory, requirement_embedding
                        )
                        VALUES (:req_id, :project_id, :skill_id, :min_prof, :is_mandatory, :embedding)
                        ON CONFLICT (requirement_id) DO NOTHING
                    """),
                    {
                        "req_id": req_id,
                        "project_id": proj["project_id"],
                        "skill_id": skill_id,
                        "min_prof": req["min_proficiency"],
                        "is_mandatory": req["is_mandatory"],
                        "embedding": embedding_vector,
                    },
                )
                print(
                    f"    -> Req ID [{req_id}]: {req['name']} (Vector dim: {len(embedding_vector)})"
                )

    print("\n✅ Projects and requirements with embeddings successfully seeded!")


if __name__ == "__main__":
    reset_projects_table()
    seed_projects()