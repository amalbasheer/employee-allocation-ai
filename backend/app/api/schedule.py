from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import text
from datetime import datetime, timedelta, timezone
from typing import Optional
from pydantic import BaseModel, validator

from app.database import get_db
from app.models import Allocation, TrainingEngagement, StudentBatch, AllocationLog
from app.api.deps import require_admin
from app.schemas.project import UserProfile

router = APIRouter()

DAYS_OF_WEEK = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"]

class ShiftUpdateRequest(BaseModel):
    item_id: str
    entity_type: str  # 'project', 'training_engagement', or 'student_batch'
    session: str      # 'morning' or 'evening'

    @validator("session")
    def validate_session(cls, v):
        v = str(v).lower().strip()
        if v not in ["morning", "evening"]:
            raise ValueError("Session must be either 'morning' or 'evening'")
        return v

    @validator("entity_type")
    def validate_entity_type(cls, v):
        v = str(v).lower().strip()
        if v not in ["project", "training_engagement", "student_batch"]:
            raise ValueError("Entity type must be 'project', 'training_engagement', or 'student_batch'")
        return v


@router.get("/calendar")
def get_weekly_calendar_schedule(
    week_start: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """
    Retrieves weekly schedules across:
    1. Projects (allocations + projects + company_employees)
    2. Training Engagements (training_engagements + company_employees)
    3. Student Batches (student_batches + company_employees)
    """
    if not week_start:
        today = datetime.now(timezone.utc).date()
        monday = today - timedelta(days=today.weekday())
        week_start = monday.strftime("%Y-%m-%d")

    # UNION ALL combining all three sources
    query = text("""
        -- 1. PROJECTS SCHEDULE (allocations + projects + company_employees)
        SELECT 
            a.reference_id AS item_id,
            'project' AS entity_type,
            a.resource_id,
            COALESCE(ce.name, 'Unknown Employee') AS employee_name,
            COALESCE(p.title, a.reference_id) AS title,
            LOWER(COALESCE(a.session, 'morning')) AS session,
            p.start_date,
            p.end_date
        FROM allocations a
        JOIN company_employees ce ON a.resource_id = ce.employee_id
        JOIN projects p ON a.reference_id = p.project_id
        WHERE LOWER(p.status) IN ('in_progress') and LOWER(a.status) IN ('assigned')
        UNION ALL

        -- 2. TRAINING ENGAGEMENT SCHEDULE (training_engagements + company_employees)
        SELECT 
            te.engagement_id AS item_id,
            'training_engagement' AS entity_type,
            te.mentor_id AS resource_id,
            COALESCE(ce.name, 'Unknown Employee') AS employee_name,
            COALESCE(te.title, te.engagement_id) AS title,
            LOWER(COALESCE(te.session, 'morning')) AS session,
            te.start_date,
            te.end_date 
        FROM training_engagements te
        JOIN company_employees ce ON te.mentor_id = ce.employee_id
        WHERE LOWER(COALESCE(te.status, 'active')) IN ('allocated', 'in_progress', 'assigned')

        UNION ALL

        -- 3. STUDENT BATCH SCHEDULE (student_batches + company_employees)
        SELECT 
            sb.batch_id AS item_id,
            'student_batch' AS entity_type,
            sb.mentor_id AS resource_id,
            COALESCE(ce.name, 'Unknown Employee') AS employee_name,
            COALESCE(sb.batch_name, sb.batch_id) AS title,
            LOWER(COALESCE(sb.session, 'morning')) AS session,
            sb.start_date,
            sb.end_date
        FROM student_batches sb
        JOIN company_employees ce ON sb.mentor_id = ce.employee_id
        WHERE LOWER(COALESCE(sb.status, 'active')) IN ('in_progress')

        ORDER BY employee_name ASC
    """)

    rows = db.execute(query).fetchall()
    employee_map = {}

    for row in rows:
        item_id, entity_type, res_id, emp_name, title, session_val, start_date, end_date = row

        if res_id not in employee_map:
            employee_map[res_id] = {
                "resource_id": res_id,
                "employee_name": emp_name,
                "days": {
                    day: {"morning": [], "evening": []} for day in DAYS_OF_WEEK
                }
            }

        schedule_item = {
            "item_id": item_id,
            "entity_type": entity_type,
            "title": title,
            "session": session_val if session_val in ["morning", "evening"] else "morning"
        }

        # Populate allocation across Monday - Friday
        sess_key = schedule_item["session"]
        for day in DAYS_OF_WEEK:
            employee_map[res_id]["days"][day][sess_key].append(schedule_item)

    return {
        "week_start_date": week_start,
        "days": DAYS_OF_WEEK,
        "schedules": list(employee_map.values())
    }


@router.patch("/shift")
def update_schedule_shift(
    payload: ShiftUpdateRequest,
    db: Session = Depends(get_db),
    current_user: UserProfile = Depends(require_admin)
):
    """
    Updates the session ('morning' or 'evening') in the respective table 
    (allocations, training_engagements, or student_batches).
    """
    entity_type = payload.entity_type.lower()
    item_id = payload.item_id
    new_session = payload.session

    if entity_type == "project":
        record = db.query(Allocation).filter(Allocation.reference_id == item_id and Allocation.status == 'assigned')
        if not record:
            raise HTTPException(status_code=404, detail=f"Allocation '{item_id}' not found.")
        old_session = record.session
        record.session = new_session

    elif entity_type == "training_engagement":
        record = db.query(TrainingEngagement).filter(TrainingEngagement.engagement_id == item_id).first()
        if not record:
            raise HTTPException(status_code=404, detail=f"Training Engagement '{item_id}' not found.")
        old_session = record.session
        record.session = new_session

    elif entity_type == "student_batch":
        record = db.query(StudentBatch).filter(StudentBatch.batch_id == item_id).first()
        if not record:
            raise HTTPException(status_code=404, detail=f"Student Batch '{item_id}' not found.")
        old_session = record.session
        record.session = new_session

    # Record Audit Log Entry
    audit_log = AllocationLog(
        log_id=f"log-{int(datetime.now(timezone.utc).timestamp() * 1000)}",
        allocation_id=item_id,
        action=f"SHIFT_CHANGE [{entity_type.upper()}]: {old_session} -> {new_session}",
        changed_by=current_user.name,
        timestamp=datetime.now(timezone.utc)
    )
    db.add(audit_log)

    db.commit()

    return {
        "message": f"Shift updated successfully in {entity_type} table.",
        "item_id": item_id,
        "entity_type": entity_type,
        "session": new_session
    }