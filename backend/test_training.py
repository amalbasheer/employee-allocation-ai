# backend/test_training.py
"""
Runs recommend_mentor_for_training() against every seeded training
engagement and prints the full ranked list — proves whether DA team
leads are genuinely missing from results, or just ranking low.
"""

import sys, os
from sqlalchemy import text

ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.append(ROOT_DIR)

from ai_engine.db import engine
from ai_engine.recommend import recommend_mentor_for_training


def get_all_training_ids():
    with engine.connect() as conn:
        rows = conn.execute(
            text("SELECT engagement_id, title FROM training_engagements ORDER BY engagement_id")
        ).fetchall()
    return [(r[0], r[1]) for r in rows]


def run_test():
    engagements = get_all_training_ids()
    print(f"Testing training recommendations against {len(engagements)} engagements...\n")
    print("=" * 60)

    for engagement_id, title in engagements:
        print(f"\nTRAINING: {title}  [{engagement_id}]")
        try:
            results = recommend_mentor_for_training(engagement_id)
        except Exception as e:
            print(f"    ❌ ERROR: {e}")
            continue

        if not results:
            print("    (no candidates returned)")
        else:
            for rank, r in enumerate(results, start=1):
                print(f"    {rank}. {r['name']}  —  score: {r['suitability_score']}")

        print("-" * 60)

    print("\n✅ Test complete.")


if __name__ == "__main__":
    run_test()