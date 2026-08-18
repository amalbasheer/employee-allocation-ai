# backend/seed_skills.py
import os
import sys
from dotenv import load_dotenv
from sqlalchemy import create_engine, text
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parent.parent / "ai_engine"))
from embedding import generate_embeddings_batch, generate_embedding

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    raise EnvironmentError("DATABASE_URL not set in .env")

engine = create_engine(DATABASE_URL)

STARTER_SKILLS = [
    ("Python", "tech_stack"), ("React.js", "tech_stack"), ("FastAPI", "tech_stack"),
    ("SQL", "tech_stack"), ("PostgreSQL", "tech_stack"), ("Docker", "tech_stack"),
    ("Git", "tech_stack"), ("PyTorch", "tech_stack"), ("TensorFlow", "tech_stack"),
    ("LangChain", "tech_stack"), ("Machine Learning", "domain"), ("Deep Learning", "domain"),
    ("Data Analytics", "domain"), ("Natural Language Processing", "domain"),
    ("Computer Vision", "domain"), ("Power BI", "tech_stack"), ("Tableau", "tech_stack"),
    ("Statistics", "domain"), ("Communication", "soft_skill"),
    ("Public Speaking", "soft_skill"), ("Mentoring", "soft_skill"),
]

STARTER_DESIGNATIONS = [
    ("Data Analytics Mentor", "Data Analytics", "Mentors student batches and trainees in data analytics"),
    ("Senior Data Analytics Mentor", "Data Analytics", "Team lead for data analytics projects and mentor batches"),
    ("Data Science Mentor", "Data Science", "Mentors student batches and trainees in data science"),
    ("Senior Data Science Mentor", "Data Science", "Team lead for data science projects and mentor batches"),
]


def seed_skills():
    names = [name for name, _ in STARTER_SKILLS]
    print(f"Checking which of {len(names)} skills already exist...")
    with engine.connect() as conn:
        existing = conn.execute(
            text("SELECT skill_name FROM skills WHERE skill_name = ANY(:names)"),
            {"names": names},
        ).fetchall()
    existing_names = {row[0] for row in existing}
    to_add = [(name, cat) for name, cat in STARTER_SKILLS if name not in existing_names]

    if not to_add:
        print("All starter skills already exist — nothing to do.")
        return

    print(f"Generating embeddings for {len(to_add)} new skills...")
    vectors = generate_embeddings_batch([name for name, _ in to_add])

    print("Inserting into skills table (letting Postgres generate IDs)...")
    with engine.begin() as conn:
        for (name, category), vector in zip(to_add, vectors):
            conn.execute(
                text("""
                    INSERT INTO skills (skill_name, category, skill_embedding)
                    VALUES (:name, :category, :embedding)
                """),
                {"name": name, "category": category, "embedding": vector},
            )
    print(f"Done — added {len(to_add)} skills.")


def seed_designations():
    print("Checking designations...")
    with engine.connect() as conn:
        existing = conn.execute(text("SELECT title FROM designations")).fetchall()
    existing_titles = {row[0] for row in existing}
    to_add = [d for d in STARTER_DESIGNATIONS if d[0] not in existing_titles]

    if not to_add:
        print("All starter designations already exist — nothing to do.")
        return

    with engine.begin() as conn:
        for title, department, description in to_add:
            conn.execute(
                text("""
                    INSERT INTO designations (title, department, description)
                    VALUES (:title, :dept, :desc)
                """),
                {"title": title, "dept": department, "desc": description},
            )
    print(f"Done — added {len(to_add)} designations.")


def get_or_create_skill(skill_name: str, category: str = "tech_stack") -> str:
    with engine.connect() as conn:
        row = conn.execute(
            text("SELECT skill_id FROM skills WHERE LOWER(skill_name) = LOWER(:name)"),
            {"name": skill_name},
        ).fetchone()
    if row:
        return row[0]

    embedding = generate_embedding(skill_name)
    with engine.begin() as conn:
        result = conn.execute(
            text("""
                INSERT INTO skills (skill_name, category, skill_embedding)
                VALUES (:name, :category, :embedding)
                RETURNING skill_id
            """),
            {"name": skill_name, "category": category, "embedding": embedding},
        )
        return result.fetchone()[0]


if __name__ == "__main__":
    seed_skills()
    seed_designations()