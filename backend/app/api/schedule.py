from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import text
from datetime import datetime, timedelta, timezone, date
from typing import Optional, Literal, Any
from pydantic import BaseModel, validator

from app.database import get_db
from app.models import Allocation, TrainingEngagement, StudentBatch, AllocationLog, Project
from app.models.taxonomy import ScheduleOverride
from app.api.deps import require_admin, get_current_user
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

def to_date_obj(val: any) -> Optional[date]:
    """Helper to safely convert string, datetime, or date into a date object."""
    if not val:
        return None
    if isinstance(val, datetime):
        return val.date()
    if isinstance(val, date):
        return val
    if isinstance(val, str):
        try:
            return datetime.strptime(val[:10], "%Y-%m-%d").date()
        except ValueError:
            return None
    return None


def get_active_days(day_of_week_str: Optional[str], item_start_date: Optional[date], days_of_week_list: list) -> list:
    """
    Resolves matching days in days_of_week_list based on:
    1. Comma-separated day strings (e.g., 'Mon, Wed, Fri')
    2. Start date calculation (for Training Engagements)
    """
    # Build lookup map for flexible matching (e.g. 'mon' -> 'Mon'/'Monday')
    day_lookup = {}
    for d in days_of_week_list:
        d_clean = str(d).strip().lower()
        day_lookup[d_clean] = d
        day_lookup[d_clean[:3]] = d  # handle 3-letter abbreviation

    matched_days = []

    # Case 1: Stored string day of week (Projects & Batches)
    if day_of_week_str:
        tokens = [t.strip().lower() for t in day_of_week_str.replace(";", ",").split(",") if t.strip()]
        for token in tokens:
            if token in day_lookup:
                matched_days.append(day_lookup[token])
            elif token[:3] in day_lookup:
                matched_days.append(day_lookup[token[:3]])

    # Case 2: Calculated from start_date (Training Engagements)
    elif item_start_date:
        full_day = item_start_date.strftime("%A").lower()  # e.g., 'monday'
        short_day = item_start_date.strftime("%a").lower()  # e.g., 'mon'
        if full_day in day_lookup:
            matched_days.append(day_lookup[full_day])
        elif short_day in day_lookup:
            matched_days.append(day_lookup[short_day])

    return list(set(matched_days))

# Flexible lookup supporting both short ('Wed') and full ('Wednesday') day names
DAY_OFFSET_MAP = {
    "monday": 0, "mon": 0,
    "tuesday": 1, "tue": 1,
    "wednesday": 2, "wed": 2,
    "thursday": 3, "thu": 3,
    "friday": 4, "fri": 4,
    "saturday": 5, "sat": 5,
    "sunday": 6, "sun": 6,
}

def get_day_offset(day_name: str) -> int:
    """Safely converts any day name string to its Monday-relative index (0-6)."""
    clean_name = str(day_name).strip().lower()
    return DAY_OFFSET_MAP.get(clean_name, 0)


@router.get("/calendar")
def get_weekly_calendar_schedule(
    week_start: Optional[str] = None,
    db: Session = Depends(get_db)
):
    if not week_start:
        today = datetime.now(timezone.utc).date()
        monday = today - timedelta(days=today.weekday())
        target_week_start = monday
    else:
        target_week_start = datetime.strptime(week_start, "%Y-%m-%d").date()

    target_week_end = target_week_start + timedelta(days=6)

    # -------------------------------------------------------------------
    # 1. FETCH ALL SCHEDULE OVERRIDES FOR THE WEEK
    # -------------------------------------------------------------------
    overrides_query = text("""
        SELECT 
            LOWER(TRIM(entity_type)) AS entity_type,
            LOWER(TRIM(entity_id)) AS entity_id,
            override_date,
            LOWER(TRIM(original_session)) AS original_session,
            LOWER(TRIM(new_session)) AS new_session,
            scope, reason
        FROM schedule_overrides
        WHERE override_date BETWEEN :w_start AND :w_end
           OR week_start_date = :w_start
    """)
    override_rows = db.execute(
        overrides_query, 
        {"w_start": target_week_start, "w_end": target_week_end}
    ).fetchall()

    # Map overrides: (entity_type, entity_id, date_str) -> override detail
    overrides_map = {}
    for row in override_rows:
        e_type, e_id, o_date, orig_sess, new_sess, scope, reason = row
        o_date_str = o_date.strftime("%Y-%m-%d") if isinstance(o_date, (date, datetime)) else str(o_date)
        
        lookup_key = (e_type, e_id, o_date_str)
        overrides_map[lookup_key] = {
            "new_session": new_sess,
            "original_session": orig_sess,
            "scope": scope,
            "reason": reason,
        }

    # -------------------------------------------------------------------
    # 2. FETCH BASE SCHEDULES
    # -------------------------------------------------------------------
    query = text("""
        -- 1. PROJECTS SCHEDULE
        SELECT 
            a.reference_id AS item_id,
            'project' AS entity_type,
            a.resource_id,
            COALESCE(ce.name, 'Unknown Employee') AS employee_name,
            COALESCE(p.title, a.reference_id) AS title,
            LOWER(COALESCE(p.session, 'morning')) AS session,
            p.start_date,
            p.end_date,
            p.day_of_week AS day_of_week
        FROM allocations a
        JOIN company_employees ce ON a.resource_id = ce.employee_id
        JOIN projects p ON a.reference_id = p.project_id
        WHERE LOWER(p.status) IN ('in_progress') AND LOWER(a.status) IN ('assigned')

        UNION ALL

        -- 2. TRAINING ENGAGEMENT SCHEDULE
        SELECT 
            te.engagement_id AS item_id,
            'training_engagement' AS entity_type,
            te.mentor_id AS resource_id,
            COALESCE(ce.name, 'Unknown Employee') AS employee_name,
            COALESCE(te.title, te.engagement_id) AS title,
            LOWER(COALESCE(te.session, 'morning')) AS session,
            te.start_date,
            te.end_date,
            NULL AS day_of_week
        FROM training_engagements te
        JOIN company_employees ce ON te.mentor_id = ce.employee_id
        WHERE LOWER(COALESCE(te.status, 'active')) IN ('allocated', 'in_progress', 'assigned')

        UNION ALL

        -- 3. STUDENT BATCH SCHEDULE
        SELECT 
            sb.batch_id AS item_id,
            'student_batch' AS entity_type,
            sb.mentor_id AS resource_id,
            COALESCE(ce.name, 'Unknown Employee') AS employee_name,
            COALESCE(sb.batch_name, sb.batch_id) AS title,
            LOWER(COALESCE(sb.session, 'morning')) AS session,
            sb.start_date,
            sb.end_date,
            sb.day_of_week AS day_of_week
        FROM student_batches sb
        JOIN company_employees ce ON sb.mentor_id = ce.employee_id
        WHERE LOWER(COALESCE(sb.status, 'active')) IN ('in_progress')

        ORDER BY employee_name ASC
    """)

    rows = db.execute(query).fetchall()
    employee_map = {}

    for row in rows:
        item_id, entity_type, res_id, emp_name, title, base_session, start_date_val, end_date_val, raw_day_of_week = row

        item_start = to_date_obj(start_date_val)
        item_end = to_date_obj(end_date_val)

        # Date range filtering
        if item_start and item_start > target_week_end:
            continue
        if item_end and item_end < target_week_start:
            continue

        if res_id not in employee_map:
            employee_map[res_id] = {
                "resource_id": res_id,
                "employee_name": emp_name,
                "days": {
                    day: {"morning": [], "evening": []} for day in DAYS_OF_WEEK
                }
            }

        # Resolve matching days for this schedule item
        active_days = get_active_days(raw_day_of_week, item_start, DAYS_OF_WEEK)

        for day in active_days:
            # Standardize day key to match employee_map keys
            matched_day_key = next((d for d in DAYS_OF_WEEK if d.lower().startswith(day.lower()[:3])), None)
            
            if matched_day_key and matched_day_key in employee_map[res_id]["days"]:
                # 1. Calculate actual YYYY-MM-DD date for this day
                day_offset = get_day_offset(matched_day_key)
                actual_date = target_week_start + timedelta(days=day_offset)
                date_str = actual_date.strftime("%Y-%m-%d")

                # 2. Check for single-day or weekly override
                clean_entity_type = str(entity_type).strip().lower()
                clean_item_id = str(item_id).strip().lower()
                override_key = (clean_entity_type, clean_item_id, date_str)

                clean_base_session = str(base_session).lower() if base_session else "morning"
                final_session = clean_base_session if clean_base_session in ["morning", "evening"] else "morning"
                is_overridden = False

                if override_key in overrides_map:
                    final_session = overrides_map[override_key]["new_session"]
                    is_overridden = True

                schedule_item = {
                    "item_id": item_id,
                    "entity_type": entity_type,
                    "title": title,
                    "session": final_session,
                    "date": date_str,
                    "is_overridden": is_overridden,
                    "reason": overrides_map[override_key]["reason"] if is_overridden else None,
                }

                # 3. Assign item to the correct session slot (morning / evening)
                target_slot = final_session if final_session in ["morning", "evening"] else "morning"
                employee_map[res_id]["days"][matched_day_key][target_slot].append(schedule_item)

    return {
        "week_start_date": target_week_start.strftime("%Y-%m-%d"),
        "days": DAYS_OF_WEEK,
        "schedules": list(employee_map.values())
    }

@router.get("/my-schedule")
def get_my_weekly_schedule(
    week_start: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)  # Resolves logged-in employee
):
    """
    Retrieves the weekly schedule specifically for the currently logged-in employee.
    Maps authenticated user email -> company_employees.employee_id.
    Includes active Projects, Training Engagements, Student Batches, and Schedule Overrides.
    """
    # 1. Safely extract email from authenticated user session
    user_email = (
        current_user.get("email") 
        if isinstance(current_user, dict) 
        else getattr(current_user, "email", None)
    )

    if not user_email:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, 
            detail="User session does not contain an email address."
        )

    # 2. Look up employee_id and employee_name in company_employees table using email
    emp_query = text("""
        SELECT employee_id, name 
        FROM company_employees 
        WHERE LOWER(TRIM(email)) = LOWER(TRIM(:email))
        LIMIT 1
    """)
    emp_row = db.execute(emp_query, {"email": user_email}).fetchone()

    if not emp_row:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, 
            detail=f"No matching employee record found for email: {user_email}"
        )

    employee_id, employee_name = emp_row

    # 3. Resolve Target Week Range
    if not week_start:
        today = datetime.now(timezone.utc).date()
        monday = today - timedelta(days=today.weekday())
        target_week_start = monday
    else:
        target_week_start = datetime.strptime(week_start, "%Y-%m-%d").date()

    target_week_end = target_week_start + timedelta(days=6)

    # 4. Fetch Overrides including status field
    overrides_query = text("""
        SELECT 
            LOWER(TRIM(entity_type)) AS entity_type,
            LOWER(TRIM(entity_id)) AS entity_id,
            override_date,
            LOWER(TRIM(original_session)) AS original_session,
            LOWER(TRIM(new_session)) AS new_session,
            scope,
            LOWER(TRIM(status)) AS status
        FROM schedule_overrides
        WHERE override_date BETWEEN :w_start AND :w_end
           OR week_start_date = :w_start
    """)
    override_rows = db.execute(
        overrides_query, 
        {"w_start": target_week_start, "w_end": target_week_end}
    ).fetchall()

    overrides_map = {}
    for row in override_rows:
        e_type, e_id, o_date, orig_sess, new_sess, scope, ovr_status = row
        o_date_str = o_date.strftime("%Y-%m-%d") if isinstance(o_date, (date, datetime)) else str(o_date)
        overrides_map[(e_type, e_id, o_date_str)] = {
            "new_session": new_sess,
            "original_session": orig_sess,
            "scope": scope,
            "status": ovr_status
        }

    # 5. Fetch Base Schedule FILTERED BY mapped employee_id
    query = text("""
        -- 1. PROJECTS SCHEDULE
        SELECT 
            a.reference_id AS item_id,
            'project' AS entity_type,
            a.resource_id,
            COALESCE(ce.name, 'Unknown Employee') AS employee_name,
            COALESCE(p.title, a.reference_id) AS title,
            LOWER(COALESCE(p.session, 'morning')) AS session,
            p.start_date,
            p.end_date,
            p.day_of_week AS day_of_week
        FROM allocations a
        JOIN company_employees ce ON a.resource_id = ce.employee_id
        JOIN projects p ON a.reference_id = p.project_id
        WHERE a.resource_id = :emp_id 
          AND LOWER(p.status) IN ('in_progress') 
          AND LOWER(a.status) IN ('assigned')

        UNION ALL

        -- 2. TRAINING ENGAGEMENT SCHEDULE
        SELECT 
            te.engagement_id AS item_id,
            'training_engagement' AS entity_type,
            te.mentor_id AS resource_id,
            COALESCE(ce.name, 'Unknown Employee') AS employee_name,
            COALESCE(te.title, te.engagement_id) AS title,
            LOWER(COALESCE(te.session, 'morning')) AS session,
            te.start_date,
            te.end_date,
            NULL AS day_of_week
        FROM training_engagements te
        JOIN company_employees ce ON te.mentor_id = ce.employee_id
        WHERE te.mentor_id = :emp_id 
          AND LOWER(COALESCE(te.status, 'active')) IN ('allocated', 'in_progress', 'assigned')

        UNION ALL

        -- 3. STUDENT BATCH SCHEDULE
        SELECT 
            sb.batch_id AS item_id,
            'student_batch' AS entity_type,
            sb.mentor_id AS resource_id,
            COALESCE(ce.name, 'Unknown Employee') AS employee_name,
            COALESCE(sb.batch_name, sb.batch_id) AS title,
            LOWER(COALESCE(sb.session, 'morning')) AS session,
            sb.start_date,
            sb.end_date,
            sb.day_of_week AS day_of_week
        FROM student_batches sb
        JOIN company_employees ce ON sb.mentor_id = ce.employee_id
        WHERE sb.mentor_id = :emp_id 
          AND LOWER(COALESCE(sb.status, 'active')) IN ('in_progress')
    """)

    rows = db.execute(query, {"emp_id": employee_id}).fetchall()

    employee_schedule = {
        "Monday": {"morning": [], "evening": []},
        "Tuesday": {"morning": [], "evening": []},
        "Wednesday": {"morning": [], "evening": []},
        "Thursday": {"morning": [], "evening": []},
        "Friday": {"morning": [], "evening": []},
    }

    DAYS_LIST = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"]

    for row in rows:
        item_id, entity_type, res_id, emp_name, title, base_session, start_date_val, end_date_val, raw_day_of_week = row

        item_start = to_date_obj(start_date_val)
        item_end = to_date_obj(end_date_val)

        if item_start and item_start > target_week_end:
            continue
        if item_end and item_end < target_week_start:
            continue

        active_days = get_active_days(raw_day_of_week, item_start, DAYS_LIST)

        for day in active_days:
            matched_day_key = next((d for d in DAYS_LIST if d.lower().startswith(day.lower()[:3])), None)

            if matched_day_key and matched_day_key in employee_schedule:
                day_offset = get_day_offset(matched_day_key)
                actual_date = target_week_start + timedelta(days=day_offset)
                date_str = actual_date.strftime("%Y-%m-%d")

                override_key = (str(entity_type).strip().lower(), str(item_id).strip().lower(), date_str)

                clean_base_session = str(base_session).lower() if base_session else "morning"
                final_session = clean_base_session if clean_base_session in ["morning", "evening"] else "morning"
                
                is_overridden = False
                pending_request = False

                # Check if an override exists for this key
                if override_key in overrides_map:
                    ovr = overrides_map[override_key]
                    ovr_status = ovr["status"]

                    if ovr_status == "approved":
                        # Only apply the session change if status is APPROVED
                        final_session = ovr["new_session"]
                        is_overridden = True
                    elif ovr_status == "pending":
                        # Keep original base session, but mark as pending
                        pending_request = True

                schedule_item = {
                    "item_id": item_id,
                    "entity_type": entity_type,
                    "title": title,
                    "session": final_session,
                    "date": date_str,
                    "is_overridden": is_overridden,
                    "pending_request": pending_request
                }

                target_slot = final_session if final_session in ["morning", "evening"] else "morning"
                employee_schedule[matched_day_key][target_slot].append(schedule_item)

    return {
        "week_start_date": target_week_start.strftime("%Y-%m-%d"),
        "employee_id": employee_id,
        "employee_name": employee_name,
        "days": employee_schedule
    }

class ShiftOverrideRequest(BaseModel):
    entity_type: str                  # 'project', 'student_batch', 'training_engagement'
    item_id: str                      # project_id, batch_id, etc.
    new_session: str                  # 'morning', 'afternoon', 'evening'
    scope: str = "single_day"         # 'single_day' or 'full_week'
    override_date: Optional[date] = None      # Required if scope == 'single_day'
    week_start_date: Optional[date] = None    # Required if scope == 'full_week'
    reason: Optional[str] = None
    status: Optional[str] 

class ReviewOverrideRequest(BaseModel):
    action: Literal["approve", "reject"]
    remarks: Optional[str] = None

def generate_next_log_id(db: Session) -> str:
    """Safely extracts the maximum numeric suffix from allocation_logs to generate rp2-log-XXXX."""
    records = db.query(AllocationLog.log_id).filter(
        AllocationLog.log_id.like("rp2-log-%")
    ).all()

    max_num = 0
    for (log_id,) in records:
        if log_id:
            parts = str(log_id).split("-")
            if parts[-1].isdigit():
                max_num = max(max_num, int(parts[-1]))

    return f"rp2-log-{max_num + 1:04d}"

def get_user_role(user: Any) -> str:
    """
    Safely extracts the user role, prioritizing 'user_metadata' 
    (whether user is a Dict, SQLAlchemy model, or Pydantic model).
    """
    if not user:
        return "employee"

    # Case 1: user is a dictionary
    if isinstance(user, dict):
        metadata = user.get("user_metadata") or user.get("usermetadata") or {}
        if isinstance(metadata, dict) and metadata.get("role"):
            return str(metadata["role"]).lower().strip()
        if user.get("role"):
            return str(user["role"]).lower().strip()

    # Case 2: user is an object/model instance
    metadata = getattr(user, "user_metadata", None) or getattr(user, "usermetadata", None)
    
    if isinstance(metadata, dict) and metadata.get("role"):
        return str(metadata["role"]).lower().strip()
    elif metadata and hasattr(metadata, "role"):
        return str(getattr(metadata, "role")).lower().strip()

    # Fallback: Top-level role attribute on user object
    direct_role = getattr(user, "role", "employee")
    return str(direct_role).lower().strip() if direct_role else "employee"


def is_admin_user(user: Any) -> bool:
    """Determines whether the current user has administrative permissions."""
    role = get_user_role(user)
    return role in ["ADMIN", "admin", "superadmin", "manager"]

@router.post("/override")
def create_or_request_schedule_override(
    payload: ShiftOverrideRequest,
    db: Session = Depends(get_db),
    current_user: Any = Depends(get_current_user)
):
    entity_type = payload.entity_type.lower().strip()
    user_role = get_user_role(current_user)
    user_is_admin = is_admin_user(current_user)
    
    # 1. Fetch current default session from base entity
    original_session = None
    if entity_type == "project":
        item = db.query(Project).filter(Project.project_id == payload.item_id).first()
        if not item:
            raise HTTPException(status_code=404, detail="Project not found")
        original_session = item.session
    elif entity_type in ["student_batch", "batch"]:
        item = db.query(StudentBatch).filter(StudentBatch.batch_id == payload.item_id).first()
        if not item:
            raise HTTPException(status_code=404, detail="Student Batch not found")
        original_session = item.session
    elif entity_type in ["training_engagement", "training"]:
        item = db.query(TrainingEngagement).filter(TrainingEngagement.engagement_id == payload.item_id).first()
        if not item:
            raise HTTPException(status_code=404, detail="Training Engagement not found")
        original_session = item.session

    # 2. Query for existing override
    existing_query = db.query(ScheduleOverride).filter(
        ScheduleOverride.entity_type == entity_type,
        ScheduleOverride.entity_id == payload.item_id,
        ScheduleOverride.scope == payload.scope
    )
    
    if payload.scope == "single_day":
        if not payload.override_date:
            raise HTTPException(status_code=400, detail="override_date is required for single_day scope")
        existing_override = existing_query.filter(ScheduleOverride.override_date == payload.override_date).first()
    else:
        if not payload.week_start_date:
            raise HTTPException(status_code=400, detail="week_start_date is required for full_week scope")
        existing_override = existing_query.filter(ScheduleOverride.week_start_date == payload.week_start_date).first()

    # Determine status based on extracted role
    override_status = "APPROVED" if user_is_admin else "PENDING"
    user_id_str = str(getattr(current_user, "id", None) or current_user.get("id") if isinstance(current_user, dict) else "")

    # 3. Upsert Override
    if existing_override:
        existing_override.new_session = payload.new_session
        existing_override.reason = payload.reason
        existing_override.status = override_status
        existing_override.created_by_user_id = user_id_str
        existing_override.created_by_role = user_role
        target_override = existing_override
    else:
        next_id = f"ovr-{int(datetime.now(timezone.utc).timestamp() * 1000)}"
        target_override = ScheduleOverride(
            override_id=next_id,
            entity_type=entity_type,
            entity_id=payload.item_id,
            scope=payload.scope,
            override_date=payload.override_date,
            week_start_date=payload.week_start_date,
            original_session=original_session,
            new_session=payload.new_session,
            reason=payload.reason,
            status=override_status,
            created_by_user_id=user_id_str,
            created_by_role=user_role
        )
        db.add(target_override)

    # 4. Immediate Audit Logging for Admins
    if user_is_admin:
        allocation_id = None
        if entity_type in ("project", "training"):
            alloc = db.query(Allocation).filter(
                Allocation.reference_id == payload.item_id
            ).first()
            if alloc:
                allocation_id = alloc.allocation_id

        user_name = (
            getattr(current_user, "name", None) or 
            getattr(current_user, "full_name", None) or 
            (current_user.get("name") if isinstance(current_user, dict) else "Admin")
        )

        log_id = generate_next_log_id(db)
        audit_log = AllocationLog(
            log_id=log_id,
            allocation_id=allocation_id,
            action=f"DIRECT_SHIFT_OVERRIDE [{payload.scope.upper()}]: {original_session or 'N/A'} -> {payload.new_session}",
            changed_by=user_name,
            timestamp=datetime.now(timezone.utc)
        )
        db.add(audit_log)

    db.commit()

    if user_is_admin:
        return {
            "message": "Shift schedule override applied immediately by Admin.",
            "status": "APPROVED",
            "override_id": target_override.override_id,
            "scope": target_override.scope,
            "new_session": target_override.new_session
        }
    
    return {
        "message": "Shift schedule override request submitted successfully. Pending Admin approval.",
        "status": "PENDING",
        "override_id": target_override.override_id,
        "scope": target_override.scope,
        "requested_session": target_override.new_session
    }


@router.get("/pending")
def get_pending_shift_requests(
    db: Session = Depends(get_db),
    current_user: UserProfile = Depends(get_current_user)
):
    """Admin-only: Retrieve all pending shift override requests."""
    if not is_admin_user(current_user):
        raise HTTPException(status_code=403, detail="Access denied. Admin rights required.")

    pending_requests = db.query(ScheduleOverride).filter(
        ScheduleOverride.status == "PENDING"
    ).order_by(ScheduleOverride.override_id.desc()).all()

    return pending_requests


@router.post("/review/{override_id}")
def review_shift_override_request(
    override_id: str,
    review: ReviewOverrideRequest,
    db: Session = Depends(get_db),
    current_user: UserProfile = Depends(get_current_user)
):
    """Admin-only: Approve or Reject a pending shift override request."""
    if not is_admin_user(current_user):
        raise HTTPException(status_code=403, detail="Access denied. Admin rights required.")

    override = db.query(ScheduleOverride).filter(
        ScheduleOverride.override_id == override_id
    ).first()

    if not override:
        raise HTTPException(status_code=404, detail="Shift override request not found")

    if override.status != "PENDING":
        raise HTTPException(
            status_code=400, 
            detail=f"Request has already been processed with status: {override.status}"
        )

    if review.action == "approve":
        override.status = "APPROVED"
        
        # Write Audit Log on Approval
        allocation_id = None
        if override.entity_type in ("project", "training"):
            alloc = db.query(Allocation).filter(
                Allocation.reference_id == override.entity_id
            ).first()
            if alloc:
                allocation_id = alloc.allocation_id

        log_id = generate_next_log_id(db)
        audit_log = AllocationLog(
            log_id=log_id,
            allocation_id=allocation_id,
            action=f"SHIFT_APPROVED [{override.scope.upper()}]: {override.original_session or 'N/A'} -> {override.new_session}",
            changed_by=getattr(current_user, "name", "Admin"),
            timestamp=datetime.now(timezone.utc)
        )
        db.add(audit_log)
        msg = "Shift override request approved successfully."

    else:
        override.status = "REJECTED"
        msg = "Shift override request rejected."

    db.commit()

    return {
        "message": msg,
        "override_id": override.override_id,
        "status": override.status,
        "reviewed_by": current_user.id
    }