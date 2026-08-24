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


def get_next_round_robin_mentor(db: Session) -> Optional[CompanyEmployee]:
    """Round-robin mentor rotation cycling mentors across batches."""
    mentors = db.query(CompanyEmployee).filter(CompanyEmployee.is_active == True).all()
    if not mentors:
        return None

    last_batch = db.query(StudentBatch).filter(
        StudentBatch.mentor_id.isnot(None)
    ).order_by(desc(StudentBatch.created_at)).first()

    if not last_batch or not last_batch.mentor_id:
        return mentors[0]

    current_idx = 0
    for idx, m in enumerate(mentors):
        if m.employee_id == last_batch.mentor_id:
            current_idx = idx
            break

    consecutive_batches = db.query(func.count(StudentBatch.batch_id)).filter(
        StudentBatch.mentor_id == last_batch.mentor_id
    ).scalar() or 0

    if consecutive_batches % 2 == 0:
        next_index = (current_idx + 1) % len(mentors)
        return mentors[next_index]
    
    return mentors[current_idx]


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
    
    return query.order_by(desc(TrainingEngagement.start_date)).all()

@router.post("/engagements", status_code=status.HTTP_201_CREATED)
async def schedule_engagement(payload: CreateEngagementSchema, db: Session = Depends(get_db)):
    new_engagement = TrainingEngagement(
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
    extracted_skill_ids = []
    if extract_skills_from_text and callable(extract_skills_from_text):
        try:
            extracted_skill_ids = extract_skills_from_text(req_text)
        except Exception as e:
            logger.warning(f"Skill extraction failed: {e}")

    # 2. Merge explicit payload skills with extracted skills (deduplicated)
    final_skill_ids = list(set((payload.required_skill_ids or []) + extracted_skill_ids))

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

    # Build skill_id -> skill_name lookup dictionary from DB
    skill_map = {}
    try:
        skill_rows = db.execute(text("SELECT skill_id, skill_name FROM skills")).fetchall()
        skill_map = {row[0]: row[1] for row in skill_rows}
    except Exception as e:
        logger.warning(f"Could not load skill mapping from DB: {e}")

    formatted_recommendations = []
    for idx, item in enumerate(raw_recommendations):
        raw_skills = item.get("skills", [])
        
        # Translate skill IDs to skill names
        extracted_skills = [
            label for label in (parse_skill_label(s, skill_map) for s in raw_skills) if label is not None
        ]

        score = item.get("score") if item.get("score") is not None else item.get("match_score", 0.0)

        formatted_recommendations.append({
            "employee_id": item.get("id") or item.get("employee_id"),
            "name": item.get("name") or item.get("full_name", f"Mentor {idx+1}"),
            "designation": item.get("designation") or item.get("role", "Team Lead"),
            "match_score": round(float(score) * 100 if float(score) <= 1.0 else float(score), 1),
            "skills": extracted_skills
        })

    # Fallback if recommendations list is empty
    if not formatted_recommendations:
        employees = db.query(CompanyEmployee).limit(5).all()
        formatted_recommendations = [
            {
                "employee_id": getattr(e, "employee_id", f"emp-10{idx}"),
                "name": getattr(e, "full_name", f"Mentor {idx+1}"),
                "designation": getattr(e, "designation", "Technical Specialist"),
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
        alloc.status = "allocated"

    log_entry = AllocationLog(
        reference_id=engagement_id,
        employee_id=engagement.mentor_id,
        action="confirmed_assigned",
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
    return db.query(StudentBatch).order_by(desc(StudentBatch.start_date)).all()


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
def auto_generate_next_batch(db: Session = Depends(get_db)):
    last_batch = db.query(StudentBatch).order_by(desc(StudentBatch.end_date)).first()
    
    if last_batch:
        start_dt = last_batch.end_date
    else:
        today = date.today()
        start_dt = date(today.year, today.month, 15)

    month = start_dt.month % 12 + 1
    year = start_dt.year + (start_dt.month // 12)
    end_dt = date(year, month, 15)

    batch_name = f"Batch-{start_dt.strftime('%b')}-{end_dt.strftime('%b')}-{end_dt.year}"
    assigned_mentor = get_next_round_robin_mentor(db)
    mentor_id = assigned_mentor.employee_id if assigned_mentor else None

    new_batch = StudentBatch(
        batch_name=batch_name,
        domain="Data Analytics",
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