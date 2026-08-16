# backend/seed.py
"""
seed_skills.py
Populates the `skills` table with a starter list of skills, each with
its embedding generated ONCE. Also provides get_or_create_skill() —
used during resume/project parsing (and by the dummy data scripts) to
reuse an existing skill's embedding instead of regenerating it.
"""

import os
import sys
from dotenv import load_dotenv
from sqlalchemy import create_engine, text
from pathlib import Path

# Add project root (one level up) to sys.path
sys.path.append(str(Path(__file__).resolve().parent.parent))

from ai_engine.embedding import generate_embeddings_batch, generate_embedding

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    raise EnvironmentError("DATABASE_URL not set in .env")

engine = create_engine(DATABASE_URL)

STARTER_SKILLS = [
    ("Python", "tech_stack"),
    ("React.js", "tech_stack"),
    ("FastAPI", "tech_stack"),
    ("SQL", "tech_stack"),
    ("PostgreSQL", "tech_stack"),
    ("Docker", "tech_stack"),
    ("Git", "tech_stack"),
    ("PyTorch", "tech_stack"),
    ("TensorFlow", "tech_stack"),
    ("LangChain", "tech_stack"),
    ("Machine Learning", "domain"),
    ("Deep Learning", "domain"),
    ("Data Analytics", "domain"),
    ("Natural Language Processing", "domain"),
    ("Computer Vision", "domain"),
    ("Power BI", "tech_stack"),
    ("Tableau", "tech_stack"),
    ("Statistics", "domain"),
    ("Communication", "soft_skill"),
    ("Public Speaking", "soft_skill"),
    ("Mentoring", "soft_skill"),
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

    print(f"Generating embeddings for {len(to_add)} new skills (one batch API call)...")
    texts = [name for name, _ in to_add]
    vectors = generate_embeddings_batch(texts)

    print("Inserting into skills table...")
    with engine.begin() as conn:
        for (name, category), vector in zip(to_add, vectors):
            conn.execute(
                text("""
                    INSERT INTO skills (skill_id, skill_name, category, skill_embedding)
                    VALUES (gen_random_uuid(), :name, :category, :embedding)
                """),
                {"name": name, "category": category, "embedding": vector},
            )

    print(f"Done — added {len(to_add)} skills with embeddings.")


def get_or_create_skill(skill_name: str, category: str = "tech_stack") -> str:
    """
    Call this whenever you need a skill_id for a given skill name.
    Returns the skill_id — reusing an existing embedding if the skill
    already exists, generating exactly one new embedding if it doesn't.
    """
    with engine.connect() as conn:
        row = conn.execute(
            text("SELECT skill_id FROM skills WHERE LOWER(skill_name) = LOWER(:name)"),
            {"name": skill_name},
        ).fetchone()

    if row:
        return row[0]  # existing skill_id, no new API call

    # New skill — one embedding call, one insert
    sys.path.append(os.path.join(os.path.dirname(__file__), "..", "ai_engine"))
    embedding = generate_embedding(skill_name)
    with engine.begin() as conn:
        result = conn.execute(
            text("""
                INSERT INTO skills (skill_id, skill_name, category, skill_embedding)
                VALUES (gen_random_uuid(), :name, :category, :embedding)
                RETURNING skill_id
            """),
            {"name": skill_name, "category": category, "embedding": embedding},
        )
        new_id = result.fetchone()[0]

    return new_id
