# app/services/training_sync.py
from datetime import date, datetime
from sqlalchemy.orm import Session
from app.models import TrainingEngagement, Allocation  # Adjust imports as needed

def sync_completed_trainings_and_allocations(db: Session) -> dict:
    today = date.today()
    print(f"\n--- [DEBUG SYNC START] Current Date: {today} ---")

    # 1. Inspect all training engagements currently in DB
    all_trainings = db.query(TrainingEngagement).all()
    print(f"[DEBUG] Total Training Records Found: {len(all_trainings)}")

    for t in all_trainings:
        # Get ID dynamically regardless of whether it's named 'id' or 'engagement_id'
        t_id = getattr(t, 'id', getattr(t, 'engagement_id', None))
        t_status = getattr(t, 'status', None)
        t_end = getattr(t, 'end_date', None)

        # Convert end_date if stored as datetime or string
        if isinstance(t_end, datetime):
            t_end_date = t_end.date()
        else:
            t_end_date = t_end

        print(f"  -> ID: {t_id} | Status: '{t_status}' | End Date: {t_end_date} | Expired?: {t_end_date < today if t_end_date else 'N/A'}")

    # 2. Query expired trainings matching criteria
    # Use func.lower or check for naive date comparison
    expired_trainings = (
        db.query(TrainingEngagement)
        .filter(
            TrainingEngagement.end_date < today,
            TrainingEngagement.status != "completed"
        )
        .all()
    )

    print(f"[DEBUG] Expired Trainings Found matching criteria: {len(expired_trainings)}")

    if not expired_trainings:
        print("--- [DEBUG SYNC END] No records updated. ---\n")
        return {"updated_trainings": 0, "updated_allocations": 0}

    # Extract primary keys
    expired_ids = [str(getattr(t, 'id', getattr(t, 'engagement_id', ''))) for t in expired_trainings]

    # 3. Perform Updates
    updated_trainings_count = db.query(TrainingEngagement).filter(
        TrainingEngagement.engagement_id.in_(expired_ids) if hasattr(TrainingEngagement, 'engagement_id') else TrainingEngagement.training_id.in_(expired_ids)
    ).update({"status": "completed"}, synchronize_session=False)

    updated_allocations_count = db.query(Allocation).filter(
        Allocation.reference_id.in_(expired_ids),
        Allocation.status != "completed"
    ).update({"status": "completed"}, synchronize_session=False)

    db.commit()
    print(f"[DEBUG SUCCESS] Updated {updated_trainings_count} trainings and {updated_allocations_count} allocations.")
    print("--- [DEBUG SYNC END] ---\n")

    return {
        "updated_trainings": updated_trainings_count,
        "updated_allocations": updated_allocations_count
    }