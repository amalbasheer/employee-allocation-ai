# routers/batches.py
from fastapi import APIRouter, HTTPException, Depends, status
import re
from pydantic import BaseModel
from typing import List, Optional, Union
from sqlalchemy import text, func
from sqlalchemy.orm import Session

from sqlalchemy import func, Integer
from datetime import timedelta, datetime, date
from app.models.webinar import StudentBatch  # adjust path if different
from app.models.employee import CompanyEmployee, Availability  # adjust path if different
# Import your database session dependency
from app.database import get_db
from services.notifications import send_assignment_notification
# Import your AI engine function
from ai_engine.db import recommend_batch_replacement, get_next_mentor_for_batch

import logging
logger = logging.getLogger(__name__)

router = APIRouter()


# --- Pydantic Schemas ---
class AssignMentorRequest(BaseModel):
    mentor_id: str
    session: Optional[str] = None
    day_of_week: Optional[Union [str, List[str]]] = None


class MentorResponse(BaseModel):
    id: str
    name: str
    designation: Optional[str] = "Mentor"
    match_score: Optional[float] = 90.0
    is_team_lead: Optional[bool] = False
    batch_count: Optional[int] = 0
    session: Optional[str]
    day_of_week: Optional[str]


class BatchResponse(BaseModel):
    batch_id: str
    batch_name: str
    domain: Optional[str]
    status: Optional[str]
    start_date: Optional[str]
    end_date: Optional[str]
    delivery_mode: Optional[str]
    mentor_id: Optional[str]
    trainer_name: Optional[str]
    session: Optional[str]
    day: Optional[str]


# -------------------------------------------------------------------------
# 1. GET ALL BATCHES
# -------------------------------------------------------------------------
@router.get("", response_model=List[BatchResponse])
def get_student_batches(db: Session = Depends(get_db)):
    """
    Fetches student batches joining 'company_employees' table to return employee name instead of ID.
    """
    query = text("""
        SELECT 
            b.batch_id, b.batch_name, b.domain, b.status, b.session, b.day_of_week as day
            b.start_date, b.end_date, b.delivery_mode, b.mentor_id,
            e.name AS trainer_name
        FROM student_batches b
        LEFT JOIN company_employees e ON b.mentor_id = e.employee_id
    """)
    results = db.execute(query).mappings().fetchall()
    return [dict(r) for r in results]




# -------------------------------------------------------------------------
# 3. ASSIGN / CHANGE MENTOR FOR A BATCH
# -------------------------------------------------------------------------
def parse_days_count(day_of_week_input) -> int:
    """
    Parses day_of_week whether provided as a string or list/iterable.
    Example:
      - "Tuesday, Thursday" -> 2
      - "Mon, Wed, Fri" -> 3
      - ["Tuesday", "Thursday"] -> 2
    """
    if not day_of_week_input:
        return 0

    if isinstance(day_of_week_input, list):
        return len([d for d in day_of_week_input if str(d).strip()])

    if isinstance(day_of_week_input, str):
        # Split by commas, slashes, or pipes
        days = [d.strip() for d in re.split(r'[,/|]+', day_of_week_input) if d.strip()]
        return len(days)

    return 0

def get_week_start(d: date) -> date:
    """Returns the Monday of the week for a given date."""
    return d - timedelta(days=d.weekday())

def get_week_starts_in_range(start_date: date | datetime, end_date: date | datetime) -> list[date]:
    """
    Generates a list of all week start dates (Mondays) falling between 
    start_date and end_date (inclusive of start and end weeks).
    Accepts both `datetime.date` and `datetime.datetime` objects.
    """
    # Normalize inputs to date objects
    s_date = start_date.date() if isinstance(start_date, datetime) else start_date
    e_date = end_date.date() if isinstance(end_date, datetime) else end_date

    weeks = []
    current_week = get_week_start(s_date)
    last_week = get_week_start(e_date)

    while current_week <= last_week:
        weeks.append(current_week)
        current_week += timedelta(days=7)

    return weeks

def generate_next_availability_id(db: Session) -> str:
    """
    Generates sequential availability IDs by extracting and incrementing
    the integer trailing digits using SQL casting.
    """
    # Extract trailing numbers and find numeric MAX directly in SQL
    max_num = db.query(
        func.max(
            func.cast(
                func.substring(Availability.availability_id, r'(\d+)$'),
                Integer
            )
        )
    ).scalar() or 0

    next_num = max_num + 1
    return f"rp2-avail-{next_num:04d}"

def update_mentor_availability_for_batch(
    db: Session,
    mentor_id: str,
    batch: StudentBatch,
    session_name: str,
    day_of_week_input,
    hours_per_day: float = 2.0,
    default_session_capacity: float = 15.0
):
    """
    Calculates weekly hours based on session frequency (2 hrs/day * days in week)
    and updates/creates availability entries for each week between start_date and end_date.
    """
    if not batch.start_date or not batch.end_date:
        return

    proj_start = batch.start_date.date() if isinstance(batch.start_date, datetime) else batch.start_date
    proj_end = batch.end_date.date() if isinstance(batch.end_date, datetime) else batch.end_date

    week_starts = get_week_starts_in_range(proj_start, proj_end)
    target_session = (session_name or "morning").strip().lower()

    # Calculate weekly hours to reduce (2 hours * number of days)
    num_days = parse_days_count(day_of_week_input)
    weekly_hours_to_reduce = num_days * hours_per_day

    if weekly_hours_to_reduce <= 0:
        return

    for week_start in week_starts:
        # Check if record exists for this mentor, week start date, and session
        availability_record = (
            db.query(Availability)
            .filter(
                Availability.resource_id == mentor_id,
                Availability.week_start_date == week_start,
                func.lower(Availability.session) == target_session
            )
            .first()
        )

        if availability_record:
            # UPDATE: Reduce available hours
            current_hours = float(availability_record.available_hours or 0.0)
            availability_record.available_hours = max(0.0, current_hours - weekly_hours_to_reduce)
        else:
            # CREATE: Generate new record with custom primary key ID
            new_avail_id = generate_next_availability_id(db)
            new_hours = max(0.0, default_session_capacity - weekly_hours_to_reduce)

            new_availability = Availability(
                availability_id=new_avail_id,
                resource_id=mentor_id,
                resource_type="employee",
                week_start_date=week_start,
                session=target_session,
                available_hours=new_hours
            )
            db.add(new_availability)
            db.flush()

@router.put("/{batch_id}/assign-mentor")
def assign_mentor_to_batch(
    batch_id: str, 
    payload: AssignMentorRequest, 
    db: Session = Depends(get_db)
):
    batch = db.query(StudentBatch).filter(StudentBatch.batch_id == batch_id).first()
    if not batch:
        raise HTTPException(status_code=404, detail="Batch not found")

    # Fall back to existing batch schedule if payload fields are None/omitted
    session_val = payload.session or batch.session
    day_of_week_val = payload.day_of_week or batch.day_of_week

    # Update batch record
    batch.mentor_id = payload.mentor_id
    batch.session = session_val
    batch.day_of_week = day_of_week_val

    if payload.mentor_id:
        # 1. UPDATE / CREATE MENTOR AVAILABILITY
        update_mentor_availability_for_batch(
            db=db,
            mentor_id=str(payload.mentor_id),
            batch=batch,
            session_name=session_val,
            day_of_week_input=day_of_week_val,
            hours_per_day=2.0  # 2 hours per session day
        )

        # 2. SEND EMAIL NOTIFICATION TO ASSIGNED MENTOR
        mentor = (
            db.query(CompanyEmployee)
            .filter(CompanyEmployee.employee_id == payload.mentor_id)
            .first()
        )

        if mentor and mentor.email:
            try:
                # Format days string safely
                if isinstance(day_of_week_val, list):
                    days_str = ", ".join(day_of_week_val)
                elif day_of_week_val:
                    days_str = str(day_of_week_val)
                else:
                    days_str = "TBD"

                # Format session string safely
                session_str = session_val.capitalize() if session_val else "Scheduled"

                batch_title = (
                    getattr(batch, "batch_name", None) 
                    or getattr(batch, "title", None) 
                    or f"Batch {batch.batch_id}"
                )
                
                description = (
                    f"You have been assigned as the mentor for Student Batch '{batch_title}'. "
                    f"Schedule: {session_str} Session on {days_str}."
                )

                send_assignment_notification(
                    recipient_email=mentor.email,
                    recipient_name=mentor.name,
                    project_title=batch_title,
                    description=description,
                    start_date=str(batch.start_date) if getattr(batch, "start_date", None) else "TBD",
                    end_date=str(batch.end_date) if getattr(batch, "end_date", None) else "TBD",
                    priority="High",
                )
            except Exception as e:
                logger.warning(f"Failed to send batch mentor assignment notification email: {e}")

    db.commit()
    db.refresh(batch)
    return batch

# -------------------------------------------------------------------------
@router.get("/{batch_id}/recommended-mentors", response_model=List[MentorResponse])
def get_recommended_mentors(batch_id: str, db: Session = Depends(get_db)):
    """
    Fetches recommended replacement mentors for a batch — uses
    recommend_batch_replacement for the full ranked list, and
    get_next_mentor_for_batch to specifically flag the genuine top pick.
    """
    try:
        batch = db.query(StudentBatch).filter(StudentBatch.batch_id == batch_id).first()
        if not batch:
            raise ValueError(f"Batch {batch_id} not found")

        ai_recommendations = recommend_batch_replacement(batch_id)

        top_pick = get_next_mentor_for_batch(
            domain=batch.domain,
            month_num=batch.start_date.month,
            year=batch.start_date.year,
            sub_domain=batch.domain,
            engine=db.get_bind()
        )
        top_pick_id = top_pick.get("employee_id") if top_pick else None

        formatted_mentors = []
        for rec in ai_recommendations:
            batch_count = rec.get("batch_count", 0)
            calculated_score = max(0.0, 100.0 - (batch_count * 10))
            designation = "Team Lead" if rec.get("is_team_lead") else "Mentor"
            session = rec.get("session")
            day_of_week = rec.get("day_of_week")

            formatted_mentors.append({
                "id": rec["id"],
                "name": rec["name"],
                "designation": designation,
                "match_score": calculated_score,
                "is_team_lead": bool(rec.get("is_team_lead")),
                "batch_count": batch_count,
                "is_top_pick": rec["id"] == top_pick_id,
                "session": session,
                "day_of_week": day_of_week,
            })

        formatted_mentors.sort(key=lambda m: (not m["is_top_pick"], -m["match_score"]))

        return formatted_mentors

    except ValueError as ve:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(ve))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Failed to fetch recommended mentors: {str(e)}")

