# backend/backfill_training_requirements.py
import sys, os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from ai_engine.db import engine
from ai_engine.extraction import extract_skills_from_text
from skill_utils import get_or_create_skill
from sqlalchemy import text
from ai_engine.embedding import generate_embedding

def backfill_training_requirements():
    with engine.connect() as conn:
        trainings = conn.execute(
            text("""
                SELECT te.engagement_id, te.title, te.description
                FROM training_engagements te
                LEFT JOIN training_requirements tr ON tr.engagement_id = te.engagement_id
                WHERE tr.requirement_id IS NULL
            """)
        ).mappings().fetchall()

    print(f"Found {len(trainings)} trainings missing requirements.\n")

    for t in trainings:
        engagement_id = t["engagement_id"]
        text_input = f"{t['title']} {t['description'] or ''}"

        try:
            extracted = extract_skills_from_text(text_input, source_type="training")
            skill_list = extracted.get("skills", []) if isinstance(extracted, dict) else extracted

            for item in skill_list:
                skill_name = item.get("name") if isinstance(item, dict) else str(item)
                skill_id = get_or_create_skill(skill_name)
                req_embedding = generate_embedding(skill_name)

                with engine.begin() as conn:
                    conn.execute(
                        text("""
                            INSERT INTO training_requirements 
                            (engagement_id, skill_id, min_proficiency, is_mandatory, requirement_embedding)
                            VALUES (:eid, :sid, :prof, :mand, :emb)
                        """),
                        {
                            "eid": engagement_id,
                            "sid": skill_id,
                            "prof": item.get("min_proficiency", 3) if isinstance(item, dict) else 3,
                            "mand": item.get("is_mandatory", True) if isinstance(item, dict) else True,
                            "emb": req_embedding,
                        },
                    )
            print(f"  [{engagement_id}] {t['title']} -> {[s.get('name') if isinstance(s, dict) else s for s in skill_list]}")

        except Exception as e:
            print(f"  [{engagement_id}] FAILED: {e}")

    print("\n✅ Backfill complete.")

if __name__ == "__main__":
    backfill_training_requirements()