# test_full_training_flow.py
import sys, os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from ai_engine.db import engine, get_available_mentors, get_person_skills
from ai_engine.matching import rank_candidates
from ai_engine.recommend import calculate_daily_occupied_hours, _parse_embedding
from sqlalchemy import text

engagement_id = "rp2-train-0010"

with engine.connect() as conn:
    engagement = conn.execute(
        text("SELECT * FROM training_engagements WHERE engagement_id = :eid"),
        {"eid": engagement_id},
    ).mappings().fetchone()
    print("Engagement:", dict(engagement))

    requirements_rows = conn.execute(
        text("SELECT * FROM training_requirements WHERE engagement_id = :eid"),
        {"eid": engagement_id},
    ).mappings().fetchall()
    print("Requirements count:", len(requirements_rows))

    domain = engagement.get("domain", "")
    region_filter = None if engagement.get("mode") == "online" else engagement.get("region")
    mentors = get_available_mentors(domain=domain, region=region_filter, check_project_conflicts=False)
    team_leads = [m for m in mentors if m.get("is_team_lead")]
    print("Team leads:", [t["name"] for t in team_leads])

    available_team_leads = []
    for tl in team_leads:
        occupied_hrs = calculate_daily_occupied_hours(
            conn=conn, mentor_id=tl["id"], domain=domain,
            training_date=engagement["start_date"], training_session=engagement.get("session", "morning")
        )
        daily_available_hrs = max(0.0, 4.0 - occupied_hrs)
        required_hours = float(engagement.get("required_hours") or 1.0)
        print(f"{tl['name']}: occupied={occupied_hrs}, available={daily_available_hrs}, required={required_hours}, PASSES={daily_available_hrs >= required_hours}")
        if daily_available_hrs >= required_hours:
            tl["skills"] = get_person_skills(tl["id"], "employee")
            available_team_leads.append(tl)

    print("Available team leads after check:", [t["name"] for t in available_team_leads])

    requirements = [
        {
            "skill_id": r["skill_id"],
            "embedding": _parse_embedding(r["requirement_embedding"]),
            "min_proficiency": r["min_proficiency"],
            "is_mandatory": r["is_mandatory"],
        }
        for r in requirements_rows
    ]

    ranked = rank_candidates(available_team_leads, requirements)
    print("Ranked result:", ranked)