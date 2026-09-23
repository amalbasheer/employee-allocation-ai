import logging
import re
from datetime import datetime, timezone, date, timedelta
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel
from sqlalchemy.orm import Session
from sqlalchemy import func, desc, or_, text, select, Integer

from app.api.deps import get_db
from app.models.webinar import TrainingEngagement, TrainingRequirement, StudentBatch
from app.models.allocation import Allocation, AllocationLog, Substitution
from app.models.employee import CompanyEmployee, Availability
from services.notifications import send_assignment_notification, send_proposed_notification
from ai_engine.extraction import extract_skills_from_text
from ai_engine.embedding import generate_embedding
from ai_engine.recommend import recommend_mentor_for_training
from ai_engine.db import get_next_mentor_for_batch
from skill_utils import get_or_create_skill

logger = logging.getLogger(__name__)

router = APIRouter()


# ==================== SCHEMAS ====================

class CreateEngagementSchema(BaseModel):
    title: str
    engagement_type: str  # "webinar", "workshop", "demo", "seminar"
    description: Optional[str] = None
    start_date: date
    end_date: Optional[date] = None
    required_hours: int = 2
    required_skill_ids: Optional[List[str]] = []
    institution_name: Optional[str] = None
    location: Optional[str] = None
    region: Optional[str] = None
    audience: Optional[str] = None
    domain: Optional[str] = None
    mode: Optional[str] = "online"  # "online" or "offline"
    session: Optional[str] = "Morining"

class ProposeMentorSchema(BaseModel):
    mentor_id: str
    suitability_score: float = 1.0
    session: Optional[str]

class EmployeeActionSchema(BaseModel):
    action: str  # "accept" or "reject"
    rejection_reason: Optional[str] = None

class CreateStudentBatchSchema(BaseModel):
    batch_name: str
    domain: str  # "Data Analytics" | "Data Science"
    start_date: date
    end_date: date
    delivery_mode: Optional[str] = "online"


# ==================== UTILITY FUNCTIONS ====================

def check_and_update_completed_engagements(db: Session):
    """Automatically updates engagements to 'completed' status if end_date has passed."""
    today = date.today()
    expired_engagements = db.query(TrainingEngagement).filter(
        TrainingEngagement.end_date < today,
        TrainingEngagement.status.in_(["open", "allocated", "accepted", "proposed"])
    ).all()

    for eng in expired_engagements:
        eng.status = "completed"
        alloc = db.query(Allocation).filter(
            Allocation.reference_id == eng.engagement_id,
            Allocation.reference_type.in_(["webinar", "training", "engagement"]),
            Allocation.status != "completed"
        ).first()
        if alloc:
            alloc.status = "completed"

    if expired_engagements:
        db.commit()



# ==================== API ENDPOINTS ====================

@router.get("/engagements")
def list_engagements(
    type_filter: Optional[str] = Query(None, description="webinar, workshop, demo, seminar"),
    db: Session = Depends(get_db)
):
    check_and_update_completed_engagements(db)
    query = db.query(TrainingEngagement)
    if type_filter and type_filter.lower() != "all":
        query = query.filter(TrainingEngagement.engagement_type == type_filter.lower())
    
    engagements = query.order_by(desc(TrainingEngagement.start_date)).all()

    # 1. Collect all unique non-null mentor_ids from the engagements
    mentor_ids = list({
        eng.mentor_id for eng in engagements 
        if getattr(eng, "mentor_id", None) is not None
    })

    # 2. Fetch mentor details from CompanyEmployee & designations table
    mentor_map = {}
    designation_map = {}
    if mentor_ids:
        employees = db.query(CompanyEmployee).filter(CompanyEmployee.employee_id.in_(mentor_ids)).all()
        mentor_map = {emp.employee_id: emp for emp in employees}

        # Extract designation IDs for these mentors
        desig_ids = list({
            getattr(emp, "designation_id") 
            for emp in employees 
            if getattr(emp, "designation_id", None) is not None
        })

        if desig_ids:
            try:
                desig_rows = db.execute(
                    text("SELECT designation_id, title FROM designations WHERE designation_id = ANY(:ids)"),
                    {"ids": desig_ids}
                ).fetchall()
                designation_map = {row[0]: row[1] for row in desig_rows}
            except Exception as e:
                logger.warning(f"Could not load designations: {e}")

    # 3. Build enriched response payload
    formatted_engagements = []
    for eng in engagements:
        # Convert SQLAlchemy object to dictionary
        eng_dict = {column.name: getattr(eng, column.name) for column in eng.__table__.columns}

        # Resolve mentor details
        mentor_id = getattr(eng, "mentor_id", None)
        emp_obj = mentor_map.get(mentor_id)

        mentor_name = (
            getattr(emp_obj, "full_name", None) or getattr(emp_obj, "name", None)
            if emp_obj else None
        )
        desig_id = getattr(emp_obj, "designation_id", None) if emp_obj else None
        mentor_designation = designation_map.get(desig_id)

        # Attach fields for the frontend
        eng_dict["mentor_name"] = mentor_name or "Unassigned"
        eng_dict["mentor_designation"] = mentor_designation or "N/A"

        formatted_engagements.append(eng_dict)

    return formatted_engagements

@router.post("/engagements", status_code=status.HTTP_201_CREATED)
def schedule_engagement(payload: CreateEngagementSchema, db: Session = Depends(get_db)):
    # 1. Safe ID Generation
    last_id = db.query(TrainingEngagement.engagement_id).order_by(TrainingEngagement.engagement_id.desc()).limit(1).scalar()
    if last_id and '-' in last_id:
        try:
            prefix, num_str = last_id.rsplit('-', 1)
            next_num = int(num_str) + 1
            new_id = f"{prefix}-{next_num:04d}"
        except ValueError:
            new_id = f"rp2-train-0001"
    else:
        new_id = "rp2-train-0001"

    new_engagement = TrainingEngagement(
        engagement_id=new_id,
        title=payload.title,
        engagement_type=payload.engagement_type.lower(),
        description=payload.description,
        start_date=payload.start_date,
        end_date=payload.end_date or payload.start_date,
        required_hours=payload.required_hours,
        status="open",
        institution_name=payload.institution_name,
        location=payload.location,
        region=payload.region,
        audience=payload.audience,
        domain=payload.domain,
        mode=payload.mode,
        session=payload.session,
    )

    db.add(new_engagement)
    db.flush()

    req_text = f"{payload.title} {payload.description or ''}".strip()

    # 2. Flexible Skill Extraction (Handles both dicts and plain strings)
    final_skill_names = []
    if extract_skills_from_text and callable(extract_skills_from_text):
        try:
            raw_extracted = extract_skills_from_text(req_text, source_type="training")
            skill_list = raw_extracted.get("skills", []) if isinstance(raw_extracted, dict) else raw_extracted
            
            for item in skill_list:
                if isinstance(item, dict) and item.get("name"):
                    final_skill_names.append(item.get("name"))
                elif isinstance(item, str) and item.strip():
                    final_skill_names.append(item.strip())
            
            # Deduplicate extracted skills preserving order
            final_skill_names = list(dict.fromkeys(final_skill_names))
        except Exception as e:
            logger.warning(f"Skill extraction failed: {e}")

    # 3. Generate Skill Embedding
    req_embedding = None
    if generate_embedding and callable(generate_embedding):
        try:
            embedding_input = ", ".join(final_skill_names) if final_skill_names else req_text
            req_embedding = generate_embedding(embedding_input)
        except Exception as e:
            logger.warning(f"Embedding generation failed: {e}")

    # 4. Save Training Requirements Safely
    for skill_name in final_skill_names:
        try:
            # Pass db session to get_or_create_skill helper
            skill_id = get_or_create_skill(db, skill_name) if 'db' in get_or_create_skill.__code__.co_varnames else get_or_create_skill(skill_name)
            
            training_req = TrainingRequirement(
                engagement_id=new_engagement.engagement_id,
                skill_id=skill_id,
                min_proficiency=1,
                is_mandatory=True,
                requirement_embedding=req_embedding
            )
            db.add(training_req)
        except Exception as e:
            logger.warning(f"Failed to save requirement for skill '{skill_name}': {e}")

    try:
        db.commit()
        db.refresh(new_engagement)
    except Exception as e:
        db.rollback()
        logger.error(f"Database commit failed: {e}")
        raise HTTPException(status_code=500, detail="Failed to schedule engagement.")

    return new_engagement



def parse_skill_label(skill_item, skill_map: dict) -> str | None:
    """Extracts and maps skill representations (string, dict, or object) to display names."""
    if isinstance(skill_item, str):
        # If it's a skill ID, replace with skill_name from DB map if present
        return skill_map.get(skill_item, skill_item)

    if isinstance(skill_item, dict):
        s_id = skill_item.get("skill_id") or skill_item.get("id")
        s_name = skill_item.get("skill_name") or skill_item.get("name") or skill_item.get("title")
        
        # Prefer mapped name by ID first, fallback to explicit name or raw ID
        if s_id in skill_map:
            return skill_map[s_id]
        return s_name or (skill_map.get(s_id, s_id) if s_id else None)

    # Object handling
    s_id = getattr(skill_item, "skill_id", None)
    s_name = getattr(skill_item, "skill_name", None) or getattr(skill_item, "name", None)
    if s_id in skill_map:
        return skill_map[s_id]
    return s_name or s_id

@router.get("/engagements/{engagement_id}/recommendations")
def get_recommendations(engagement_id: str, db: Session = Depends(get_db)):
    engagement = db.query(TrainingEngagement).filter(TrainingEngagement.engagement_id == engagement_id).first()
    if not engagement:
        raise HTTPException(status_code=404, detail=f"No training engagement found with id {engagement_id}")

    raw_recommendations = []
    try:
        raw_recommendations = recommend_mentor_for_training(engagement_id=engagement_id)
    except Exception as e:
        import traceback
        print(f"FULL ERROR TRACEBACK:\n{traceback.format_exc()}")
        logger.warning(f"AI Mentor Recommendation failed: {e}")

    # 1. Collect all recommended employee IDs
    emp_ids = [
        item.get("employee_id") or item.get("id")
        for item in raw_recommendations
        if item.get("employee_id") or item.get("id")
    ]

    # 2. Fetch CompanyEmployee records & lookup Designation table by designation_id
    emp_map = {}
    designation_map = {}
    if emp_ids:
        emp_records = db.query(CompanyEmployee).filter(CompanyEmployee.employee_id.in_(emp_ids)).all()
        emp_map = {emp.employee_id: emp for emp in emp_records}
        
        # Extract unique non-null designation_ids
        desig_ids = list({
            getattr(emp, "designation_id") 
            for emp in emp_records 
            if getattr(emp, "designation_id", None) is not None
        })
        
        # Load designation names from designations table
        if desig_ids:
            try:
                desig_rows = db.execute(
                    text("SELECT designation_id, title FROM designations WHERE designation_id = ANY(:ids)"),
                    {"ids": desig_ids}
                ).fetchall()
                designation_map = {row[0]: row[1] for row in desig_rows}
            except Exception as e:
                logger.warning(f"Could not load designations from DB: {e}")

    # 3. Build skill_id -> skill_name lookup dictionary from DB
    skill_map = {}
    try:
        skill_rows = db.execute(text("SELECT skill_id, skill_name FROM skills")).fetchall()
        skill_map = {row[0]: row[1] for row in skill_rows}
    except Exception as e:
        logger.warning(f"Could not load skill mapping from DB: {e}")

    formatted_recommendations = []
    for idx, item in enumerate(raw_recommendations):
        emp_id = item.get("employee_id") or item.get("id")
        emp_obj = emp_map.get(emp_id)

        raw_skills = item.get("skills", [])
        
        # Translate skill IDs to skill names
        extracted_skills = [
            label for label in (parse_skill_label(s, skill_map) for s in raw_skills) if label is not None
        ]

        score = item.get("suitability_score") or item.get("score") or item.get("match_score") or 0.0

        # Retrieve employee full name from CompanyEmployee table
        emp_name = (
            getattr(emp_obj, "full_name", None) or getattr(emp_obj, "name", None) 
            or item.get("name") or item.get("full_name") or f"Mentor {idx+1}"
        )

        # Map designation_id from CompanyEmployee to designation_name in designations table
        desig_id = getattr(emp_obj, "designation_id", None) if emp_obj else None
        emp_designation = (
            designation_map.get(desig_id)
            or item.get("designation") 
            or item.get("role") 
            or "Technical Specialist"
        )

        formatted_recommendations.append({
            "employee_id": emp_id,
            "name": emp_name,
            "designation": emp_designation,
            "match_score": round(float(score) * 100 if float(score) <= 1.0 else float(score), 1),
            "skills": extracted_skills
        })

    # Fallback if recommendations list is empty
    if not formatted_recommendations:
        employees = db.query(CompanyEmployee).limit(5).all()
        
        fallback_desig_ids = list({
            getattr(e, "designation_id") 
            for e in employees 
            if getattr(e, "designation_id", None) is not None
        })
        fallback_desig_map = {}
        if fallback_desig_ids:
            try:
                desig_rows = db.execute(
                    text("SELECT designation_id, designation_name FROM designations WHERE designation_id = ANY(:ids)"),
                    {"ids": fallback_desig_ids}
                ).fetchall()
                fallback_desig_map = {row[0]: row[1] for row in desig_rows}
            except Exception:
                pass

        formatted_recommendations = [
            {
                "employee_id": getattr(e, "employee_id", f"emp-10{idx}"),
                "name": getattr(e, "full_name", getattr(e, "name", f"Mentor {idx+1}")),
                "designation": fallback_desig_map.get(getattr(e, "designation_id", None), "Technical Specialist"),
                "match_score": round(95.0 - (idx * 4), 1),
                "skills": ["Python", "Machine Learning", "System Design"]
            }
            for idx, e in enumerate(employees)
        ]

    return formatted_recommendations


def generate_next_allocation_id(db: Session) -> str:
    # Fetch all allocation IDs matching the prefix
    alloc_ids = db.scalars(
        select(Allocation.allocation_id).filter(Allocation.allocation_id.like("rp2-alloc-%"))
    ).all()
    
    max_num = 0
    for alloc_id in alloc_ids:
        parts = alloc_id.split("-")
        if parts[-1].isdigit():
            max_num = max(max_num, int(parts[-1]))
            
    return f"rp2-alloc-{max_num + 1:04d}"

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
@router.post("/engagements/{engagement_id}/propose")
def propose_mentor(
    engagement_id: str, 
    payload: ProposeMentorSchema, 
    db: Session = Depends(get_db)
):
    # 1. Fetch Training Engagement
    engagement = (
        db.query(TrainingEngagement)
        .filter(TrainingEngagement.engagement_id == engagement_id)
        .first()
    )
    if not engagement:
        raise HTTPException(status_code=404, detail="Engagement not found")

    engagement.status = "proposed"
    engagement.mentor_id = payload.mentor_id

    # 2. Find or Create Allocation record
    alloc = (
        db.query(Allocation)
        .filter(
            Allocation.reference_id == engagement_id,
            Allocation.reference_type.in_(["webinar", "training", "engagement"])
        )
        .first()
    )

    if not alloc:
        alloc = Allocation(
            allocation_id=generate_next_allocation_id(db),
            reference_type="training",
            reference_id=engagement_id,
            resource_id=payload.mentor_id,
            resource_type="employee",
            status="proposed",
            suitability_score=payload.suitability_score,
            role_on_project="trainer",
            assigned_at=datetime.now(timezone.utc),
            assigned_by="admin",
            allocated_hours=2,
            session=engagement.session,
        )
        db.add(alloc)
    else:
        alloc.resource_id = payload.mentor_id
        alloc.status = "proposed"

    # 3. Create Audit Log Entry
    log_entry = AllocationLog(
        log_id=generate_next_log_id(db),
        allocation_id=alloc.allocation_id,
        action="PROPOSED",
        changed_by="admin",
        timestamp=datetime.now(timezone.utc)
    )
    db.add(log_entry)

    # 4. Commit Database Transaction
    db.commit()

    # -------------------------------------------------------------------
    # 5. SEND EMAIL NOTIFICATION TO PROPOSED MENTOR
    # -------------------------------------------------------------------
    if payload.mentor_id:
        mentor = (
            db.query(CompanyEmployee)
            .filter(CompanyEmployee.employee_id == payload.mentor_id)
            .first()
        )

        if mentor and mentor.email:
            try:
                training_title = (
                    getattr(engagement, "title", None) 
                    or getattr(engagement, "name", None) 
                    or f"Training Engagement {engagement_id}"
                )

                base_desc = getattr(engagement, "description", "") or ""
                session_str = f"Session: {engagement.session}" if getattr(engagement, "session", None) else ""
                req_hours = (
                    getattr(engagement, "required_hours", None) 
                    or getattr(engagement, "duration_hours", None)
                )
                hours_str = f"Required Hours: {req_hours}" if req_hours else ""
                extra_details = " | ".join(filter(None, [session_str, hours_str]))

                full_description = (
                    f"A new training engagement mentor proposal has been submitted for your review.\n"
                    f"{extra_details}\n\n"
                    f"Details: {base_desc}"
                ).strip()

                start_date_str = str(
                    getattr(engagement, "start_date", None) 
                    or getattr(engagement, "date", "TBD")
                )
                end_date_str = str(getattr(engagement, "end_date", "TBD"))
                priority_str = getattr(engagement, "priority_level", "Medium") or "Medium"

                send_proposed_notification(
                    recipient_email=mentor.email,
                    recipient_name=mentor.name,
                    project_title=f"[Proposal] {training_title}",
                    description=full_description,
                    start_date=start_date_str,
                    end_date=end_date_str,
                    priority=priority_str,
                )
            except Exception as e:
                logger.warning(f"Failed to send mentor proposal notification email: {e}")

    return {"message": "Proposal sent successfully", "status": engagement.status}

def get_week_start(d: date) -> date:
    """Returns the Monday of the week for a given date."""
    return d - timedelta(days=d.weekday())

def generate_next_availability_id(db: Session) -> str:
    """
    Generates sequential availability IDs based on the highest existing ID.
    """
    # Fetch the lexicographically highest availability_id
    max_id = db.query(func.max(Availability.availability_id)).scalar()
    
    if not max_id:
        next_num = 1
    else:
        # Extract trailing numbers (e.g., 'rp2-avail-0005' -> 5)
        try:
            next_num = int(max_id.split("-")[-1]) + 1
        except (ValueError, IndexError):
            next_num = 1

    return f"rp2-avail-{next_num:04d}"  

def update_mentor_availability_for_training(
    db: Session,
    mentor_id: str,
    training_start_date: date | datetime,
    session_name: str,
    required_hours: float,
    default_session_capacity: float = 15.0
):
    """
    Deducts the required training hours from the mentor's availability 
    for the week containing the training start date.
    Creates a new availability record if one does not exist for that week.
    """
    if not training_start_date:
        return

    # Convert datetime to date if necessary
    t_date = training_start_date.date() if isinstance(training_start_date, datetime) else training_start_date
    week_start = get_week_start(t_date)
    
    target_session = (session_name or "morning").strip().lower()
    deduct_hours = float(required_hours or 0.0)

    # 1. Search for existing availability record for this week and session
    availability_record = (
        db.query(Availability)
        .filter(
            Availability.employee_id == mentor_id,
            Availability.week_start_date == week_start,
            func.lower(Availability.session) == target_session
        )
        .first()
    )

    if availability_record:
        # UPDATE: Deduct required hours from existing availability
        current_hours = float(availability_record.available_hours or 0.0)
        availability_record.available_hours = max(0.0, current_hours - deduct_hours)
    else:
        # CREATE: Generate new record with new primary key ID
        new_avail_id = generate_next_availability_id(db)
        new_hours = max(0.0, default_session_capacity - deduct_hours)

        new_availability = Availability(
            availability_id=new_avail_id,
            employee_id=mentor_id,
            week_start_date=week_start,
            session=target_session,
            available_hours=new_hours
        )
        db.add(new_availability)
@router.post("/engagements/{engagement_id}/confirm")
def confirm_allocation(engagement_id: str, db: Session = Depends(get_db)):
    # 1. Fetch Training Engagement
    engagement = (
        db.query(TrainingEngagement)
        .filter(TrainingEngagement.engagement_id == engagement_id)
        .first()
    )
    if not engagement:
        raise HTTPException(status_code=404, detail="Engagement not found")

    if engagement.status != "accepted":
        raise HTTPException(
            status_code=400, 
            detail="Engagement status must be accepted to confirm"
        )

    # Update engagement status
    engagement.status = "allocated"

    # 2. Fetch associated Allocation
    alloc = (
        db.query(Allocation)
        .filter(
            Allocation.reference_id == engagement_id,
            Allocation.reference_type.in_(["webinar", "training", "engagement"])
        )
        .first()
    )

    mentor_id = None
    if alloc:
        alloc.status = "assigned"

        # 3. UPDATE / CREATE MENTOR AVAILABILITY
        # Extracts mentor resource ID, session, required hours, and training start date
        mentor_id = alloc.resource_id
        session_type = (
            getattr(alloc, "session", None) 
            or getattr(engagement, "session", None) 
            or "morning"
        )
        req_hours = (
            getattr(engagement, "required_hours", None) 
            or getattr(engagement, "duration_hours", None) 
            or getattr(alloc, "allocated_hours", 0.0)
            or 0.0
        )
        start_date = getattr(engagement, "start_date", None) or getattr(engagement, "date", None)

        if mentor_id and start_date:
            update_mentor_availability_for_training(
                db=db,
                mentor_id=str(mentor_id),
                training_start_date=start_date,
                session_name=session_type,
                required_hours=req_hours
            )

    # 4. Create Audit Log Entry
    log_entry = AllocationLog(
        log_id=generate_next_log_id(db),
        allocation_id=alloc.allocation_id if alloc else f"ENG_{engagement_id}",
        action="TRAINER_ASSIGNED",
        changed_by="admin",
        timestamp=datetime.now(timezone.utc)
    )
    db.add(log_entry)
    db.commit()

    # -------------------------------------------------------------------
    # 5. SEND EMAIL NOTIFICATION TO CONFIRMED MENTOR / TRAINER
    # -------------------------------------------------------------------
    target_mentor_id = mentor_id or getattr(engagement, "mentor_id", None)
    if target_mentor_id:
        mentor = (
            db.query(CompanyEmployee)
            .filter(CompanyEmployee.employee_id == target_mentor_id)
            .first()
        )

        if mentor and mentor.email:
            try:
                training_title = (
                    getattr(engagement, "title", None) 
                    or getattr(engagement, "name", None) 
                    or f"Training Engagement {engagement_id}"
                )

                base_desc = getattr(engagement, "description", "") or ""
                session_str = f"Session: {engagement.session}" if getattr(engagement, "session", None) else ""
                req_hours = (
                    getattr(engagement, "required_hours", None) 
                    or getattr(engagement, "duration_hours", None)
                )
                hours_str = f"Required Hours: {req_hours}" if req_hours else ""
                extra_details = " | ".join(filter(None, [session_str, hours_str]))

                full_description = (
                    f"Your trainer allocation for '{training_title}' has been officially confirmed.\n"
                    f"{extra_details}\n\n"
                    f"Details: {base_desc}"
                ).strip()

                start_date_str = str(
                    getattr(engagement, "start_date", None) 
                    or getattr(engagement, "date", "TBD")
                )
                end_date_str = str(getattr(engagement, "end_date", "TBD"))
                priority_str = getattr(engagement, "priority_level", "Medium") or "Medium"

                send_assignment_notification(
                    recipient_email=mentor.email,
                    recipient_name=mentor.name,
                    project_title=training_title,
                    description=full_description,
                    start_date=start_date_str,
                    end_date=end_date_str,
                    priority=priority_str,
                )
            except Exception as e:
                logger.warning(f"Failed to send confirmation notification email: {e}")

    return {
        "message": "Engagement allocation confirmed and availability updated",
        "status": engagement.status
    }
# ==================== EMPLOYEE RESPONSES ====================

@router.post("/engagements/{engagement_id}/employee-action")
def employee_action(engagement_id: str, employee_id: str, payload: EmployeeActionSchema, db: Session = Depends(get_db)):
    engagement = db.query(TrainingEngagement).filter(TrainingEngagement.engagement_id == engagement_id).first()
    if not engagement:
        raise HTTPException(status_code=404, detail="Engagement not found")

    action_clean = payload.action.lower()
    if action_clean == "accept":
        engagement.status = "accepted"
        alloc_status = "accepted"
    elif action_clean == "reject":
        engagement.status = "rejected"
        alloc_status = "rejected"

        sub_record = Substitution(
            reference_type="engagement",
            reference_id=engagement_id,
            previous_employee_id=employee_id,
            reason=payload.rejection_reason or "Declined by speaker",
            created_at=datetime.now(timezone.utc)
        )
        db.add(sub_record)
    else:
        raise HTTPException(status_code=400, detail="Action must be accept or reject")

    alloc = db.query(Allocation).filter(
        Allocation.reference_id == engagement_id,
        Allocation.reference_type.in_(["webinar", "training", "engagement"])
    ).first()
    if alloc:
        alloc.status = alloc_status

    log_entry = AllocationLog(
        reference_id=engagement_id,
        employee_id=employee_id,
        action=f"employee_{action_clean}",
        timestamp=datetime.now(timezone.utc)
    )
    db.add(log_entry)
    db.commit()

    return {"message": f"Engagement status updated to {engagement.status}"}


# ==================== STUDENT BATCH APIS ====================

@router.get("/student-batches")
def list_student_batches(db: Session = Depends(get_db)):
    batches = db.query(StudentBatch).order_by(desc(StudentBatch.start_date)).all()
    if not batches:
        return []

    # 1. Collect all non-null trainer / instructor / mentor IDs across batches
    trainer_ids = list({
        getattr(b, "mentor_id", None) or getattr(b, "instructor_id", None) or getattr(b, "trainer_id", None)
        for b in batches
        if (getattr(b, "mentor_id", None) or getattr(b, "instructor_id", None) or getattr(b, "trainer_id", None)) is not None
    })

    # 2. Bulk fetch trainer details from CompanyEmployee & designations
    trainer_map = {}
    designation_map = {}
    if trainer_ids:
        employees = db.query(CompanyEmployee).filter(CompanyEmployee.employee_id.in_(trainer_ids)).all()
        trainer_map = {emp.employee_id: emp for emp in employees}

        desig_ids = list({
            getattr(emp, "designation_id") 
            for emp in employees 
            if getattr(emp, "designation_id", None) is not None
        })

        if desig_ids:
            try:
                desig_rows = db.execute(
                    text("SELECT designation_id, title FROM designations WHERE designation_id = ANY(:ids)"),
                    {"ids": desig_ids}
                ).fetchall()
                designation_map = {row[0]: row[1] for row in desig_rows}
            except Exception as e:
                logger.warning(f"Could not load designations for batch trainers: {e}")

    # 3. Format batch records into front-end friendly payload
    formatted_batches = []
    for b in batches:
        # Convert SQLAlchemy object to dictionary
        batch_dict = {column.name: getattr(b, column.name) for column in b.__table__.columns}

        # Resolve primary trainer / mentor ID
        t_id = getattr(b, "trainer_id", None) or getattr(b, "instructor_id", None) or getattr(b, "mentor_id", None)
        emp_obj = trainer_map.get(t_id)

        trainer_name = (
            getattr(emp_obj, "full_name", None) or getattr(emp_obj, "name", None)
            if emp_obj else None
        )
        desig_id = getattr(emp_obj, "designation_id", None) if emp_obj else None
        trainer_designation = designation_map.get(desig_id)

        # Attach computed/mapped metadata for frontend consumption
        batch_dict["trainer_name"] = trainer_name or "Unassigned"
        batch_dict["trainer_designation"] = trainer_designation or "N/A"
        
        # Ensure fallback defaults for standard UI cards/tables
        batch_dict["student_count"] = getattr(b, "student_count", None) or getattr(b, "total_students", 0)

        formatted_batches.append(batch_dict)

    return formatted_batches


@router.post("/student-batches", status_code=status.HTTP_201_CREATED)
def create_student_batch(payload: CreateStudentBatchSchema, db: Session = Depends(get_db)):
    assigned_mentor = get_next_mentor_for_batch(
        domain=payload.domain,
        month_num=payload.start_date.month,
        year=payload.start_date.year
    )
    mentor_id = assigned_mentor.get("employee_id") if assigned_mentor else None

    new_batch = StudentBatch(
        batch_name=payload.batch_name,
        domain=payload.domain,
        start_date=payload.start_date,
        end_date=payload.end_date,
        delivery_mode=payload.delivery_mode,
        mentor_id=mentor_id,
        status="open"
    )
    db.add(new_batch)
    db.commit()
    db.refresh(new_batch)
    return new_batch


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

@router.post("/student-batches/auto-generate-next")
def auto_generate_next_batch(db: Session = Depends(get_db)):
    """
    Generates the next batch pairs (Offline + Online) for:
    - Data Analytics (e.g., Jun DA Offline)
    - Data Science (e.g., Jun DS Offline)
    - Agentic AI (e.g., Jun AI Offline)
    - Bridge (e.g., Jun Bridge Offline)
    - Softskill DS & DA (e.g., Jun DS Softskill Offline, Jun DA Softskill Offline)
    
    Automatically assigns mentors, sessions, and day schedules.
    """
    all_created_batches = []

    # Domain configuration: (domain_name, sub_domain_for_softskill, label_code)
    domain_configs = [
        ("Data Analytics", None, "DA"),
        ("Data Science", None, "DS"),
        ("Agentic AI", None, "AI"),
        ("Bridge", None, "Bridge"),
        ("Softskill", "Data Science", "DS Softskill"),
        ("Softskill", "Data Analytics", "DA Softskill"),
    ]

    for department, sub_domain, short_label in domain_configs:
        query = db.query(StudentBatch).filter(func.lower(StudentBatch.domain) == department.lower())
        
        # Filter Softskill by specific sub-domain in batch_name to track start dates independently
        if department == "Softskill" and sub_domain:
            query = query.filter(StudentBatch.batch_name.ilike(f"%{short_label}%"))

        last_batch = query.order_by(desc(StudentBatch.start_date)).first()

        if last_batch:
            prev_start = last_batch.start_date
            next_month = prev_start.month + 1
            next_year = prev_start.year
            if next_month > 12:
                next_month -= 12
                next_year += 1
            start_dt = date(next_year, next_month, 15)
        else:
            today = date.today()
            start_dt = date(today.year, today.month, 15)

        end_month = start_dt.month + 4
        end_year = start_dt.year
        if end_month > 12:
            end_month -= 12
            end_year += 1
        end_dt = date(end_year, end_month, 14)

        # Gets next mentor + free session + free day_of_week list
        assigned_mentor = get_next_mentor_for_batch(
            domain=department,
            month_num=start_dt.month,
            year=start_dt.year,
            sub_domain=sub_domain or "Data Science",
            engine=db.get_bind()
        )
        
        mentor_id = assigned_mentor.get("employee_id") if assigned_mentor else None
        session = assigned_mentor.get("session") if assigned_mentor else None
        day_of_week = assigned_mentor.get("day_of_week") if assigned_mentor else None

        for mode in ["offline", "online"]:
            batch_name = f"{start_dt.strftime('%b')} {short_label} {mode.capitalize()}"
            new_batch = StudentBatch(
                batch_name=batch_name,
                domain=department,
                start_date=start_dt,
                end_date=end_dt,
                delivery_mode=mode,
                mentor_id=mentor_id,
                session=session,
                day_of_week=day_of_week,
                status="open"
            )
            db.add(new_batch)
            all_created_batches.append(new_batch)

    # 1. Commit new batches
    db.commit()
    for b in all_created_batches:
        db.refresh(b)

    # 2. Fetch mentor details for response and notifications
    mentor_ids = list({b.mentor_id for b in all_created_batches if b.mentor_id})
    mentor_map = {}
    employee_objects = {}
    if mentor_ids:
        employees = db.query(CompanyEmployee).filter(CompanyEmployee.employee_id.in_(mentor_ids)).all()
        mentor_map = {e.employee_id: e.name for e in employees}
        employee_objects = {e.employee_id: e for e in employees}

    # 3. Update Mentor Availability & Send Email Notifications
    for batch in all_created_batches:
        if batch.mentor_id:
            update_mentor_availability_for_batch(
                db=db,
                mentor_id=str(batch.mentor_id),
                batch=batch,
                session_name=batch.session,
                day_of_week_input=batch.day_of_week,
                hours_per_day=2.0
            )

            mentor = employee_objects.get(batch.mentor_id)
            if mentor and mentor.email:
                try:
                    days_str = (
                        ", ".join(batch.day_of_week) 
                        if isinstance(batch.day_of_week, list) 
                        else str(batch.day_of_week or "N/A")
                    )
                    batch_title = batch.batch_name or f"Batch {batch.batch_id}"
                    description = (
                        f"You have been automatically assigned as the mentor for Student Batch '{batch_title}'. "
                        f"Delivery Mode: {batch.delivery_mode.capitalize()} | "
                        f"Schedule: {str(batch.session).capitalize() if batch.session else 'N/A'} Session on {days_str}."
                    )

                    send_assignment_notification(
                        recipient_email=mentor.email,
                        recipient_name=mentor.name,
                        project_title=batch_title,
                        description=description,
                        start_date=str(batch.start_date) if batch.start_date else "TBD",
                        end_date=str(batch.end_date) if batch.end_date else "TBD",
                        priority="High",
                    )
                except Exception as e:
                    logger.warning(f"Failed to send batch mentor assignment notification email: {e}")

    db.commit()

    # 4. Response Payload
    response = []
    for b in all_created_batches:
        response.append({
            "batch_id": b.batch_id,
            "batch_name": b.batch_name,
            "domain": b.domain,
            "start_date": b.start_date,
            "end_date": b.end_date,
            "delivery_mode": b.delivery_mode,
            "mentor_id": b.mentor_id,
            "trainer_name": mentor_map.get(b.mentor_id, "Unassigned"),
            "status": b.status,
            "session": b.session,
            "day_of_week": getattr(b, "day_of_week", None)
        })

    return response


class UpdateEngagementSchema(BaseModel):
    title: Optional[str] = None
    engagement_type: Optional[str] = None
    description: Optional[str] = None
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    required_hours: Optional[int] = None
    status: Optional[str] = None
    institution_name: Optional[str] = None
    location: Optional[str] = None
    region: Optional[str] = None
    audience: Optional[str] = None
    domain: Optional[str] = None
    mode: Optional[str] = None
    session: Optional[str] = None

class BulkCancelSchema(BaseModel):
    engagement_ids: List[str]

@router.put("/engagements/{engagement_id}")
def update_engagement(
    engagement_id: str, 
    payload: UpdateEngagementSchema, 
    db: Session = Depends(get_db)
):
    # 1. Fetch Existing Engagement
    engagement = db.query(TrainingEngagement).filter(TrainingEngagement.engagement_id == engagement_id).first()
    if not engagement:
        raise HTTPException(status_code=404, detail="Engagement not found.")

    # 2. Update Basic Fields
    update_data = payload.dict(exclude_unset=True)
    for field, value in update_data.items():
        if field == "engagement_type" and value:
            setattr(engagement, field, value.lower())
        else:
            setattr(engagement, field, value)

    db.flush()

    # 3. Clear existing requirements for re-syncing
    db.query(TrainingRequirement).filter(TrainingRequirement.engagement_id == engagement_id).delete(synchronize_session=False)

    # 4. Extract Skills from updated content
    req_text = f"{engagement.title} {engagement.description or ''}".strip()
    final_skill_names = []
    
    if extract_skills_from_text and callable(extract_skills_from_text):
        try:
            raw_extracted = extract_skills_from_text(req_text, source_type="training")
            skill_list = raw_extracted.get("skills", []) if isinstance(raw_extracted, dict) else raw_extracted
            
            for item in skill_list:
                if isinstance(item, dict) and item.get("name"):
                    final_skill_names.append(item.get("name"))
                elif isinstance(item, str) and item.strip():
                    final_skill_names.append(item.strip())
            
            final_skill_names = list(dict.fromkeys(final_skill_names))
        except Exception as e:
            logger.warning(f"Skill extraction failed during update: {e}")

    # 5. Generate Skill Embedding
    req_embedding = None
    if generate_embedding and callable(generate_embedding):
        try:
            embedding_input = ", ".join(final_skill_names) if final_skill_names else req_text
            req_embedding = generate_embedding(embedding_input)
        except Exception as e:
            logger.warning(f"Embedding generation failed during update: {e}")

    # 6. Save Updated Requirements
    for skill_name in final_skill_names:
        try:
            skill_id = get_or_create_skill(db, skill_name) if 'db' in get_or_create_skill.__code__.co_varnames else get_or_create_skill(skill_name)
            
            training_req = TrainingRequirement(
                engagement_id=engagement.engagement_id,
                skill_id=skill_id,
                min_proficiency=1,
                is_mandatory=True,
                requirement_embedding=req_embedding
            )
            db.add(training_req)
        except Exception as e:
            logger.warning(f"Failed to save requirement for skill '{skill_name}': {e}")

    try:
        db.commit()
        db.refresh(engagement)
    except Exception as e:
        db.rollback()
        logger.error(f"Database commit failed during update: {e}")
        raise HTTPException(status_code=500, detail="Failed to update engagement.")

    return engagement

@router.delete("/engagements/{engagement_id}", status_code=status.HTTP_200_OK)
def delete_engagement(engagement_id: str, db: Session = Depends(get_db)):
    engagement = db.query(TrainingEngagement).filter(TrainingEngagement.engagement_id == engagement_id).first()
    if not engagement:
        raise HTTPException(status_code=404, detail="Engagement not found.")

    try:
        # 1. Delete associated requirements in TrainingRequirement
        db.query(TrainingRequirement).filter(TrainingRequirement.engagement_id == engagement_id).delete(synchronize_session=False)

        # 2. Delete associated allocations in TrainingAllocation if model exists
        if 'TrainingAllocation' in globals():
            db.query(Allocation).filter(Allocation.reference_id == engagement_id).delete(synchronize_session=False)

        # 3. Hard Delete Engagement Record
        db.delete(engagement)
        db.commit()
    except Exception as e:
        db.rollback()
        logger.error(f"Failed to hard delete engagement '{engagement_id}': {e}")
        raise HTTPException(status_code=500, detail="Failed to delete engagement from database.")

    return {"message": f"Engagement '{engagement_id}' and associated requirements permanently deleted."}


@router.post("/engagements/bulk-cancel", status_code=status.HTTP_200_OK)
def bulk_cancel_engagements(payload: BulkCancelSchema, db: Session = Depends(get_db)):
    if not payload.engagement_ids:
        raise HTTPException(status_code=400, detail="No engagement IDs provided.")

    try:
        # 1. Update status to 'cancelled' in TrainingEngagement table
        engagements_cancelled = db.query(TrainingEngagement)\
            .filter(TrainingEngagement.engagement_id.in_(payload.engagement_ids))\
            .update({TrainingEngagement.status: "cancelled"}, synchronize_session=False)

        # 2. Update status to 'cancelled' in TrainingAllocation table
        allocations_cancelled = 0
        if 'TrainingAllocation' in globals():
            allocations_cancelled = db.query(Allocation)\
                .filter(Allocation.reference_id.in_(payload.engagement_ids))\
                .update({Allocation.status: "cancelled"}, synchronize_session=False)

        db.commit()
    except Exception as e:
        db.rollback()
        logger.error(f"Bulk cancel failed: {e}")
        raise HTTPException(status_code=500, detail="Failed to cancel engagements.")

    return {
        "message": f"Successfully cancelled {engagements_cancelled} engagement(s) and {allocations_cancelled} allocation(s).",
        "cancelled_ids": payload.engagement_ids
    }