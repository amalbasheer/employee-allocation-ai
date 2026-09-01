import logging
from datetime import datetime, timezone, date
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel
from sqlalchemy.orm import Session
from sqlalchemy import func, desc, or_, text, select

from app.api.deps import get_db
from app.models.webinar import TrainingEngagement, TrainingRequirement, StudentBatch
from app.models.allocation import Allocation, AllocationLog, Substitution
from app.models.employee import CompanyEmployee
from ai_engine.extraction import extract_skills_from_text
from ai_engine.embedding import generate_embedding
from ai_engine.recommend import recommend_mentor_for_training
from ai_engine.db import get_next_mentor_for_batch

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

class ProposeMentorSchema(BaseModel):
    mentor_id: str
    suitability_score: float = 1.0

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
                    text("SELECT designation_id, designation_name FROM designations WHERE designation_id = ANY(:ids)"),
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
async def schedule_engagement(payload: CreateEngagementSchema, db: Session = Depends(get_db)):
    last_id = db.query(TrainingEngagement.engagement_id).order_by(TrainingEngagement.engagement_id.desc()).limit(1).scalar()
    if last_id:
      prefix, num_str = last_id.rsplit('-', 1)  # Splits 'rp2-train-0005' -> ['rp2-train', '0005']
      next_num = int(num_str) + 1
      new_id = f"{prefix}-{next_num:04d}"       # Formats back to 'rp2-train-0006'
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
        status="open"
    )
    db.add(new_engagement)
    db.flush()

    req_text = f"{payload.title} {payload.description or ''}"

    # 1. Extract skills automatically from text
    # 1. Extract skills automatically from text
    extracted_skill_ids = []
    if extract_skills_from_text and callable(extract_skills_from_text):
        try:
            raw_extracted = extract_skills_from_text(req_text)
            
            if isinstance(raw_extracted, dict):
                # Unpack list values from standard wrapper keys
                for key in ("skills", "skill_ids", "extracted_skills", "skill_id", "data"):
                    val = raw_extracted.get(key)
                    if isinstance(val, list):
                        extracted_skill_ids = val
                        break
                    elif isinstance(val, str):
                        extracted_skill_ids = [val]
                        break
                else:
                    # Fallback for key-value skill maps (e.g., {"sk-001": 0.95})
                    extracted_skill_ids = [
                        k for k in raw_extracted.keys() 
                        if k not in ("skills", "skill_ids", "skill_id", "status", "message")
                    ]
            elif isinstance(raw_extracted, list):
                extracted_skill_ids = raw_extracted
            elif isinstance(raw_extracted, str):
                extracted_skill_ids = [raw_extracted]

        except Exception as e:
            logger.warning(f"Skill extraction failed: {e}")

    # 2. Merge explicit payload skills with extracted skills (deduplicated)
    # 1. Combine raw payload and extracted skill items
    raw_skills = (payload.required_skill_ids or []) + extracted_skill_ids

    # 2. Extract string IDs safely (handles both raw strings and dict objects)
    clean_skill_ids = []
    for item in raw_skills:
        if isinstance(item, str):
            clean_skill_ids.append(item)
        elif isinstance(item, dict):
            # Unpack standard ID keys if the extractor returned dict objects
            sid = item.get("skill_id") or item.get("id") or item.get("code")
            if sid and isinstance(sid, str):
                clean_skill_ids.append(sid)

    # 3. Deduplicate clean string IDs
    final_skill_ids = list(set(clean_skill_ids))
    # 3. Generate embedding using clean, extracted skill keywords (fallback to raw text if empty)
    embedding_input = ", ".join(final_skill_ids) if final_skill_ids else req_text
    req_embedding = None
    if generate_embedding and callable(generate_embedding):
        try:
            req_embedding = generate_embedding(embedding_input)
        except Exception as e:
            logger.warning(f"Embedding generation failed: {e}")

    # 4. Save training requirements
    for skill_id in final_skill_ids:
        training_req = TrainingRequirement(
            engagement_id=new_engagement.engagement_id,
            skill_id=skill_id,
            min_proficiency=1,
            is_mandatory=True,
            requirement_embedding=req_embedding
        )
        db.add(training_req)

    db.commit()
    db.refresh(new_engagement)
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
def propose_mentor(engagement_id: str, payload: ProposeMentorSchema, db: Session = Depends(get_db)):
    engagement = db.query(TrainingEngagement).filter(TrainingEngagement.engagement_id == engagement_id).first()
    if not engagement:
        raise HTTPException(status_code=404, detail="Engagement not found")

    engagement.status = "proposed"
    engagement.mentor_id = payload.mentor_id

    alloc = db.query(Allocation).filter(
        Allocation.reference_id == engagement_id,
        Allocation.reference_type.in_(["webinar", "training", "engagement"])
    ).first()

    if not alloc:
        alloc = Allocation(
            allocation_id=generate_next_allocation_id(db),
            # FIX: Use engagement.engagement_type (instance value) instead of TrainingEngagement.engagement_type
            reference_type="training",
            reference_id=engagement_id,
            resource_id=payload.mentor_id,
            resource_type="employee",
            status="proposed",
            suitability_score=payload.suitability_score,
            role_on_project="trainer",
            assigned_at=datetime.now(timezone.utc),
            assigned_by="admin",
            allocated_hours=2


        )
        db.add(alloc)
    else:
        alloc.resource_id = payload.mentor_id
        alloc.status = "proposed"

    log_entry = AllocationLog(
        log_id=generate_next_log_id(db),
        allocation_id=alloc.allocation_id,
        action="PROPOSED",
        changed_by="admin",
        timestamp=datetime.now(timezone.utc)
    )
    db.add(log_entry)
    db.commit()

    return {"message": "Proposal sent successfully", "status": engagement.status}


@router.post("/engagements/{engagement_id}/confirm")
def confirm_allocation(engagement_id: str, db: Session = Depends(get_db)):
    engagement = db.query(TrainingEngagement).filter(TrainingEngagement.engagement_id == engagement_id).first()
    if not engagement:
        raise HTTPException(status_code=404, detail="Engagement not found")

    if engagement.status != "accepted":
        raise HTTPException(status_code=400, detail="Engagement status must be accepted to confirm")

    engagement.status = "allocated"

    alloc = db.query(Allocation).filter(
        Allocation.reference_id == engagement_id,
        Allocation.reference_type.in_(["webinar", "training", "engagement"])
    ).first()
    if alloc:
        alloc.status = "assigned"

    log_entry = AllocationLog(
        log_id=generate_next_log_id(db),
        allocation_id=alloc.allocation_id,
        action="TRAINER_ASSIGNED",
        changed_by="admin",
        timestamp=datetime.now(timezone.utc)
    )
    db.add(log_entry)
    db.commit()

    return {"message": "Engagement allocation confirmed", "status": engagement.status}


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
                    text("SELECT designation_id, designation_name FROM designations WHERE designation_id = ANY(:ids)"),
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
    assigned_mentor = get_next_round_robin_mentor(db)
    mentor_id = assigned_mentor.employee_id if assigned_mentor else None

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
    db.flush()

    if mentor_id:
        alloc = Allocation(
            reference_type="batch",
            reference_id=new_batch.batch_id,
            employee_id=mentor_id,
            status="allocated"
        )
        db.add(alloc)

    db.commit()
    db.refresh(new_batch)
    return new_batch


@router.post("/student-batches/auto-generate-next")
def auto_generate_next_batch(
    department: str = Query(default="Data Analytics"), 
    db: Session = Depends(get_db)
):
    # 1. Fetch the last created batch for this domain to determine next dates
    last_batch = (
        db.query(StudentBatch)
        .filter(func.lower(StudentBatch.domain) == department.strip().lower())
        .order_by(desc(StudentBatch.end_date))
        .first()
    )
    
    if last_batch:
        start_dt = last_batch.end_date
    else:
        today = date.today()
        start_dt = date(today.year, today.month, 15)

    month = start_dt.month % 12 + 1
    year = start_dt.year + (start_dt.month // 12)
    end_dt = date(year, month, 15)

    batch_name = f"Batch-{start_dt.strftime('%b')}-{end_dt.strftime('%b')}-{end_dt.year}"
    
    # 2. Call get_next_mentor_for_batch with domain, starting month, and year
    assigned_mentor = get_next_mentor_for_batch(
        domain=department,
        month_num=start_dt.month,
        year=start_dt.year
    )
    
    # 3. Extract employee_id from returned dictionary safely
    mentor_id = assigned_mentor.get("employee_id") if assigned_mentor else None

    # 4. Create and save new batch
    new_batch = StudentBatch(
        batch_name=batch_name,
        domain=department,
        start_date=start_dt,
        end_date=end_dt,
        delivery_mode="online",
        mentor_id=mentor_id,
        status="open"
    )
    db.add(new_batch)
    db.commit()
    db.refresh(new_batch)

    return new_batch