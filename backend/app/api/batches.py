# routers/batches.py
from fastapi import APIRouter, HTTPException, Depends, status
from pydantic import BaseModel
from typing import List, Optional
from sqlalchemy import text, func
from sqlalchemy.orm import Session

from sqlalchemy import func
from app.models.webinar import StudentBatch  # adjust path if different
from app.models.employee import CompanyEmployee  # adjust path if different
# Import your database session dependency
from app.database import get_db
# Import your AI engine function
from ai_engine.db import recommend_batch_replacement, get_next_mentor_for_batch

router = APIRouter()


# --- Pydantic Schemas ---
class AssignMentorRequest(BaseModel):
    mentor_id: str


class MentorResponse(BaseModel):
    id: str
    name: str
    designation: Optional[str] = "Mentor"
    match_score: Optional[float] = 90.0
    is_team_lead: Optional[bool] = False
    batch_count: Optional[int] = 0


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
            b.batch_id, b.batch_name, b.domain, b.status, 
            b.start_date, b.end_date, b.delivery_mode, b.mentor_id,
            e.name AS trainer_name
        FROM student_batches b
        LEFT JOIN company_employees e ON b.mentor_id = e.employee_id
    """)
    results = db.execute(query).mappings().fetchall()
    return [dict(r) for r in results]


# -------------------------------------------------------------------------
# 2. GET RECOMMENDED MENTORS FOR A BATCH
# -------------------------------------------------------------------------
@router.get("/{batch_id}/recommended-mentors", response_model=List[MentorResponse])
def get_recommended_mentors(batch_id: str):
    """
    Fetches recommended replacement mentors for a batch directly from the AI Engine.
    Leverages round-robin ranking (fewest active batch commitments first).
    """
    try:
        # Call AI Engine function (returns dict with keys: id, name, is_team_lead, batch_count)
        ai_recommendations = recommend_batch_replacement(batch_id)

        formatted_mentors = []
        for rec in ai_recommendations:
            # Map batch count to a friendly match score for the frontend (0 batches = 100%, 1 = 90%, etc.)
            batch_count = rec.get("batch_count", 0)
            calculated_score = max(50.0, 100.0 - (batch_count * 10))

            designation = "Team Lead" if rec.get("is_team_lead") else "Mentor"

            formatted_mentors.append({
                "id": rec["id"],
                "name": rec["name"],
                "designation": designation,
                "match_score": calculated_score,
                "is_team_lead": bool(rec.get("is_team_lead")),
                "batch_count": batch_count
            })

        return formatted_mentors

    except ValueError as ve:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(ve)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch recommended mentors: {str(e)}"
        )


# -------------------------------------------------------------------------
# 3. ASSIGN / CHANGE MENTOR FOR A BATCH
# -------------------------------------------------------------------------
@router.put("/{batch_id}/assign-mentor")
def assign_mentor(batch_id: str, payload: AssignMentorRequest, db: Session = Depends(get_db)):
    """
    Assigns or updates the mentor for a specific student batch.
    """
    try:
        # 1. Update mentor_id in student_batches table
        update_query = text("""
            UPDATE student_batches
            SET mentor_id = :mentor_id 
            WHERE batch_id = :batch_id
        """)
        db.execute(update_query, {"mentor_id": payload.mentor_id, "batch_id": batch_id})
        db.commit()

        # 2. Fetch updated mentor's name from company_employees table
        emp_query = text("SELECT name FROM company_employees WHERE employee_id = :id")
        emp = db.execute(emp_query, {"id": payload.mentor_id}).mappings().fetchone()
        trainer_name = emp["name"] if emp else payload.mentor_id

        return {
            "success": True,
            "message": "Mentor updated successfully",
            "batch_id": batch_id,
            "mentor_id": payload.mentor_id,
            "trainer_name": trainer_name
        }

    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to assign mentor: {str(e)}"
        )

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
            year=batch.start_date.year
        )
        top_pick_id = top_pick.get("employee_id") if top_pick else None

        formatted_mentors = []
        for rec in ai_recommendations:
            batch_count = rec.get("batch_count", 0)
            calculated_score = max(0.0, 100.0 - (batch_count * 10))
            designation = "Team Lead" if rec.get("is_team_lead") else "Mentor"

            formatted_mentors.append({
                "id": rec["id"],
                "name": rec["name"],
                "designation": designation,
                "match_score": calculated_score,
                "is_team_lead": bool(rec.get("is_team_lead")),
                "batch_count": batch_count,
                "is_top_pick": rec["id"] == top_pick_id,
            })

        formatted_mentors.sort(key=lambda m: (not m["is_top_pick"], -m["match_score"]))

        return formatted_mentors

    except ValueError as ve:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(ve))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Failed to fetch recommended mentors: {str(e)}")

