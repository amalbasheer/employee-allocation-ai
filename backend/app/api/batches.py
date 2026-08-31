# routers/batches.py
from fastapi import APIRouter, HTTPException, Depends, status
from pydantic import BaseModel
from typing import List, Optional
from sqlalchemy.orm import Session
# Import your database session/connection dependency
from app.database import get_db
# Import your AI engine function
from ai_engine.db import recommend_batch_replacement

router = APIRouter()

# --- Pydantic Schemas ---
class AssignMentorRequest(BaseModel):
    mentor_id: str

class MentorResponse(BaseModel):
    id: str
    name: str
    designation: Optional[str] = "Mentor"
    match_score: Optional[float] = None

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
# 1. GET ALL BATCHES (Joins with companyemployee to map mentor_id to name)
# -------------------------------------------------------------------------
@router.get("", response_model=List[BatchResponse])
def get_student_batches(db: Session = Depends(get_db)):
    """
    Fetches student batches joining 'companyemployee' table to return employee name instead of ID.
    SQL equivalent:
    SELECT b.*, e.name as trainer_name 
    FROM student_batches b 
    LEFT JOIN company_employees e ON b.mentor_id = e.employee_id
    """
    query = """
        SELECT 
            b.batch_id, b.batch_name, b.domain, b.status, 
            b.start_date, b.end_date, b.delivery_mode, b.mentor_id,
            e.name AS trainer_name
        FROM student_batches b
        LEFT JOIN companyemployee e ON b.mentor_id = e.employee_id
    """
    results = db.execute(query).fetchall()
    return [dict(r) for r in results]


# -------------------------------------------------------------------------
# 2. GET RECOMMENDED MENTORS FOR A BATCH
# -------------------------------------------------------------------------
@router.get("/{batch_id}/recommended-mentors", response_model=List[MentorResponse])
def get_recommended_mentors(batch_id: str, db: Session = Depends(get_db)):
    try:
        # Call AI Engine function to get recommended mentor IDs / data
        # Example output from AI Engine: [{"mentor_id": "EMP101", "score": 95.0}, ...]
        ai_recommendations = recommend_mentor_for_batch(batch_id)
        
        if not ai_recommendations:
            return []

        # Extract mentor IDs
        if isinstance(ai_recommendations[0], dict):
            recommended_ids = [m["mentor_id"] for m in ai_recommendations]
            scores_map = {m["mentor_id"]: m.get("score", 0) for m in ai_recommendations}
        else:
            recommended_ids = ai_recommendations
            scores_map = {}

        # Fetch names and designations from companyemployee table
        query = """
            SELECT employee_id, name as name, designation_id 
            FROM company_employees 
            WHERE employee_id IN :ids
        """
        employees = db.execute(query, {"ids": tuple(recommended_ids)}).fetchall()

        # Format final recommendation payload
        recommended_mentors = []
        for emp in employees:
            emp_dict = dict(emp)
            emp_dict["match_score"] = scores_map.get(emp_dict["employee_id"], 90.0)
            recommended_mentors.append(emp_dict)

        # Sort by highest score
        recommended_mentors.sort(key=lambda x: x["match_score"], reverse=True)
        return recommended_mentors

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
    try:
        # 1. Update mentor_id in student_batch / training engagement table
        update_query = """
            UPDATE student_batches
            SET mentor_id = :mentor_id 
            WHERE batch_id = :batch_id
        """
        db.execute(update_query, {"mentor_id": payload.mentor_id, "batch_id": batch_id})
        db.commit()

        # 2. Fetch updated mentor's name from companyemployee table
        emp_query = "SELECT name FROM company_employees WHERE employee_id = :id"
        emp = db.execute(emp_query, {"id": payload.mentor_id}).fetchone()
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