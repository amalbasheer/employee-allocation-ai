# backend/skill_utils.py
"""
skill_utils.py
Shared helper used whenever any code (resume parsing, project parsing,
or dummy data scripts) needs a skill_id for a given skill name.
Not a "seed" script — this runs continuously, not just once.
"""

import sys
import os

# ai_engine/ is a sibling folder of backend/ — add it to the import path
sys.path.append(os.path.join(os.path.dirname(__file__), "..", "ai_engine"))

from db import engine
from sqlalchemy import text
from embedding import generate_embedding


def get_or_create_skill(skill_name: str, category: str = "tech_stack") -> str:
    """
    Returns the skill_id — reusing an existing embedding if the skill
    already exists, generating exactly one new embedding if it doesn't.
    """
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
                INSERT INTO skills (skill_id, skill_name, category, skill_embedding)
                VALUES (gen_random_uuid(), :name, :category, :embedding)
                RETURNING skill_id
            """),
            {"name": skill_name, "category": category, "embedding": embedding},
        )
        return result.fetchone()[0]