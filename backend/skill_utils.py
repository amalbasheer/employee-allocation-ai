# backend/skill_utils.py
import sys
import os

sys.path.append(os.path.join(os.path.dirname(__file__), "..", "ai_engine"))

from db import engine
from sqlalchemy import text
from embedding import generate_embedding


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