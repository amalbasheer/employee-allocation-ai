# backend/app/api/webinars.py

import sys
import os
import logging
from typing import List, Optional, Dict, Any
from pathlib import Path
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session
from sqlalchemy import text, func
from fastapi.responses import JSONResponse

from app.database import get_db
from app.models.webinar import TrainingEngagement, TrainingRequirement, StudentBatch
from app.models.taxonomy import Skill
from app.schemas.webinar import (
    TrainingEngagementCreate,
    TrainingEngagementResponse,
    TrainingEngagementUpdate,
    TrainingRequirementCreate,
    TrainingRequirementResponse,
    StudentBatchCreate,
    StudentBatchResponse,
    StudentBatchUpdate,
)
from app.schemas.project import UserProfile
from app.api.deps import get_current_user, require_admin

ROOT_DIR = Path(__file__).resolve().parents[3]
if str(ROOT_DIR) not in sys.path:
    sys.path.append(str(ROOT_DIR))

logger = logging.getLogger(__name__)

# Import AI Engine services with resilient fallbacks
try:
    from ai_engine.extraction import extract_skills_from_text
except ImportError:
    extract_skills_from_text = None

try:
    from ai_engine.embedding import generate_embedding
except ImportError:
    generate_embedding = None

try:
    from ai_engine.recommend import recommend_candidates_for_project
except ImportError:
    def recommend_candidates_for_project(engagement_id: str) -> dict:
        return {"project_title": "", "roles_needed": [], "mentors": [], "interns": []}

router = APIRouter()


class StatusUpdateRequest(BaseModel):
    status: str


class RecommendationRequest(BaseModel):
    skills: Optional[List[str]] = []
    type: str = "mentors"  # 'mentors' or 'students'/'interns'


@router.post("/{engagement_id}/recommendations")
async def fetch_recommendations(engagement_id: str, payload: RecommendationRequest):
    try:
        result_dict = recommend_candidates_for_project(engagement_id)
        req_type = payload.type.lower() if payload.type else "mentors"

        if req_type in ["students", "interns", "intern"]:
            candidates = result_dict.get("interns") or []
        elif req_type in ["team_leads", "team_lead"]:
            candidates = result_dict.get("eligible_team_leads") or []
        else:
            candidates = result_dict.get("mentors") or []

        cleaned_candidates = []
        for c in candidates:
            if isinstance(c, dict):
                raw_skills = c.get("skills")
                skills_list = [str(s) for s in raw_skills] if isinstance(raw_skills, list) else []

                cleaned_candidates.append({
                    "id": str(c.get("id") or c.get("_id") or "unknown"),
                    "name": str(c.get("name") or c.get("full_name") or "Unnamed Candidate"),
                    "matchScore": float(c.get("matchScore") or c.get("score") or c.get("match_score") or 0),
                    "skills": skills_list,
                    "role": str(c.get("role") or c.get("designation") or "Mentor"),
                    "university": str(c.get("university") or c.get("college") or "N/A"),
                })

        return JSONResponse(content=cleaned_candidates)

    except ValueError as ve:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(ve))
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Engine execution error: {str(e)}"
        )


def get_or_create_skill(db: Session, skill_name: str) -> Skill:
    """Look up skill in 'skills' table by name (case-insensitive) or insert a new entry."""
    normalized_name = skill_name.strip().title()
    existing_skill = db.query(Skill).filter(Skill.skill_name.ilike(normalized_name)).first()
    if existing_skill:
        return existing_skill

    new_skill = Skill(skill_name=normalized_name)
    db.add(new_skill)
    db.flush()
    return new_skill


# ==========================================
# TRAINING ENGAGEMENT ENDPOINTS
# ==========================================

@router.get("/details")
async def get_all_webinar_details(db: Session = Depends(get_db)):
    try:
        query = text("""
            SELECT 
                te.engagement_id,
                te.title,
                te.description,
                te.engagement_type,
                te.status AS engagement_status,
                te.start_date,
                te.end_date,
                te.required_hours,
                s.skill_name,
                a.allocation_id,
                a.employee_id AS resource_id,
                a.status AS allocation_status,
                COALESCE(e.name, i.name, 'Unknown') AS resource_name,
                CASE 
                    WHEN e.employee_id IS NOT NULL THEN 'employee'
                    WHEN i.intern_id IS NOT NULL THEN 'intern'
                    ELSE 'unknown'
                END AS resource_type
            FROM training_engagements te
            LEFT JOIN training_requirements tr ON te.engagement_id = tr.engagement_id
            LEFT JOIN skills s ON tr.skill_id = s.skill_id
            LEFT JOIN allocations a ON te.engagement_id = a.reference_id
            LEFT JOIN company_employees e ON a.employee_id = e.employee_id
            LEFT JOIN interns_and_students i ON a.employee_id = i.intern_id
            ORDER BY te.engagement_id
        """)

        rows = db.execute(query).mappings().all()

        engagements_map: Dict[Any, Dict[str, Any]] = {}

        for row in rows:
            eid = row["engagement_id"]

            if eid not in engagements_map:
                engagements_map[eid] = {
                    "engagement_id": str(eid),
                    "title": row["title"] or "",
                    "description": row["description"] or "",
                    "engagement_type": row["engagement_type"] or "webinar",
                    "status": row["engagement_status"] or "open",
                    "start_date": str(row["start_date"]) if row["start_date"] else "TBD",
                    "end_date": str(row["end_date"]) if row["end_date"] else None,
                    "required_hours": row["required_hours"] or 2,
                    "skills": set(),
                    "allocations": {}
                }

            if row["skill_name"]:
                engagements_map[eid]["skills"].add(row["skill_name"])

            if row["allocation_id"]:
                alloc_id = row["allocation_id"]
                if alloc_id not in engagements_map[eid]["allocations"]:
                    engagements_map[eid]["allocations"][alloc_id] = {
                        "resource_id": str(row["resource_id"]),
                        "resource_name": row["resource_name"],
                        "resource_type": row["resource_type"],
                        "allocation_status": row["allocation_status"] or "PENDING"
                    }

        formatted_engagements: List[Dict[str, Any]] = []
        for eng in engagements_map.values():
            formatted_engagements.append({
                "engagement_id": eng["engagement_id"],
                "title": eng["title"],
                "description": eng["description"],
                "engagement_type": eng["engagement_type"],
                "status": eng["status"],
                "start_date": eng["start_date"],
                "end_date": eng["end_date"],
                "required_hours": eng["required_hours"],
                "skills": list(eng["skills"]),
                "allocations": list(eng["allocations"].values())
            })

        return JSONResponse(content=formatted_engagements)

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch webinar details: {str(e)}"
        )


@router.get("", response_model=List[TrainingEngagementResponse])
def get_webinars(
    db: Session = Depends(get_db),
    current_user: UserProfile = Depends(get_current_user)
):
    """Fetch all training engagements (webinars/workshops/etc.)."""
    return db.query(TrainingEngagement).all()


@router.post("", response_model=TrainingEngagementResponse, status_code=status.HTTP_201_CREATED)
def create_webinar(
    engagement_in: TrainingEngagementCreate,
    db: Session = Depends(get_db),
    admin_user: UserProfile = Depends(require_admin)
):
    """
    Create a new training engagement with auto-generated ID (rp2-eng-XXXX),
    deduplicated skills, and AI-driven vector embeddings.
    """
    raw_skills_input = getattr(engagement_in, "raw_skills", []) or []
    engagement_data = engagement_in.model_dump(exclude={"requirements", "raw_skills"})

    try:
        # 1. AUTO ID GENERATION (Format: rp2-eng-0001)
        if not engagement_data.get("engagement_id"):
            total_count = db.query(func.count(TrainingEngagement.engagement_id)).scalar() or 0
            engagement_data["engagement_id"] = f"rp2-eng-{(total_count + 1):04d}"

        new_engagement = TrainingEngagement(**engagement_data, status="open")
        db.add(new_engagement)
        db.flush()

        # 2. PROCESS REQUIREMENTS
        raw_requirements: List[Dict[str, Any]] = []

        explicit_reqs = getattr(engagement_in, "requirements", None)
        if explicit_reqs:
            for req in explicit_reqs:
                s_name = getattr(req, "skill_name", None) or getattr(req, "skill_id", "General")
                raw_requirements.append({
                    "skill_name": s_name,
                    "min_proficiency": getattr(req, "min_proficiency", 3),
                    "is_mandatory": getattr(req, "is_mandatory", True)
                })

        if not raw_requirements and extract_skills_from_text:
            if new_engagement.description or raw_skills_input:
                try:
                    extracted = extract_skills_from_text(
                        description=new_engagement.description or "",
                        raw_skills=raw_skills_input
                    )
                    for item in extracted:
                        raw_requirements.append({
                            "skill_name": getattr(item, "skill_name", str(item)),
                            "min_proficiency": getattr(item, "min_proficiency", 3),
                            "is_mandatory": getattr(item, "is_mandatory", True)
                        })
                except Exception as e:
                    logger.warning(f"AI skill extraction failed: {e}. Falling back to raw skills.")

        if not raw_requirements and raw_skills_input:
            for sk_name in raw_skills_input:
                raw_requirements.append({
                    "skill_name": sk_name,
                    "min_proficiency": 3,
                    "is_mandatory": True
                })

        # 3. DEDUPLICATION
        seen_skills = set()
        deduped_requirements = []

        for req in raw_requirements:
            normalized_name = req["skill_name"].strip().lower()
            if normalized_name not in seen_skills:
                seen_skills.add(normalized_name)
                deduped_requirements.append(req)

        # 4. RESOLVE SKILLS & SAVE REQUIREMENTS
        for req_data in deduped_requirements:
            skill_name = req_data["skill_name"].strip()
            skill_obj = get_or_create_skill(db, skill_name)

            embedding_vector = None
            if generate_embedding:
                try:
                    embedding_vector = generate_embedding(skill_name)
                except Exception as e:
                    logger.warning(f"Embedding generation failed for skill '{skill_name}': {e}")

            db_req = TrainingRequirement(
                engagement_id=new_engagement.engagement_id,
                skill_id=skill_obj.skill_id,
                min_proficiency=req_data["min_proficiency"],
                is_mandatory=req_data["is_mandatory"],
                requirement_embedding=embedding_vector
            )
            db.add(db_req)

        db.commit()
        db.refresh(new_engagement)
        req_list = getattr(new_engagement, "requirements", []) or []

        return {
            "engagement_id": new_engagement.engagement_id,
            "title": new_engagement.title,
            "description": new_engagement.description or "",
            "engagement_type": new_engagement.engagement_type,
            "status": str(new_engagement.status),
            "start_date": str(new_engagement.start_date) if new_engagement.start_date else None,
            "end_date": str(new_engagement.end_date) if new_engagement.end_date else None,
            "required_hours": new_engagement.required_hours,
            "mentor_id": new_engagement.mentor_id,
            "created_at": new_engagement.created_at,
            "requirements": [
                {
                    "requirement_id": req.requirement_id,
                    "engagement_id": req.engagement_id,
                    "skill_id": req.skill_id,
                    "min_proficiency": req.min_proficiency,
                    "is_mandatory": req.is_mandatory,
                }
                for req in req_list
            ],
        }

    except Exception as e:
        db.rollback()
        logger.error(f"Error creating training engagement: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create training engagement: {str(e)}"
        )


@router.get("/{engagement_id}", response_model=TrainingEngagementResponse)
def get_webinar_by_id(
    engagement_id: str,
    db: Session = Depends(get_db),
    current_user: UserProfile = Depends(get_current_user)
):
    """Fetch a single training engagement by ID."""
    engagement = db.query(TrainingEngagement).filter(TrainingEngagement.engagement_id == engagement_id).first()
    if not engagement:
        raise HTTPException(status_code=404, detail="Training engagement not found")
    return engagement


@router.patch("/{engagement_id}", response_model=TrainingEngagementResponse)
def update_webinar(
    engagement_id: str,
    engagement_in: TrainingEngagementUpdate,
    db: Session = Depends(get_db),
    admin_user: UserProfile = Depends(require_admin)
):
    """Update training engagement details."""
    engagement = db.query(TrainingEngagement).filter(TrainingEngagement.engagement_id == engagement_id).first()
    if not engagement:
        raise HTTPException(status_code=404, detail="Training engagement not found")

    update_data = engagement_in.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(engagement, field, value)

    db.commit()
    db.refresh(engagement)
    return engagement


@router.patch("/{engagement_id}/status", response_model=TrainingEngagementResponse)
def update_webinar_status(
    engagement_id: str,
    status_in: StatusUpdateRequest,
    db: Session = Depends(get_db),
    admin_user: UserProfile = Depends(require_admin)
):
    """Update overall engagement status (open, in_progress, completed, cancelled)."""
    engagement = db.query(TrainingEngagement).filter(TrainingEngagement.engagement_id == engagement_id).first()
    if not engagement:
        raise HTTPException(status_code=404, detail="Training engagement not found")

    engagement.status = status_in.status.lower()
    db.commit()
    db.refresh(engagement)
    return engagement


@router.delete("/{engagement_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_webinar(
    engagement_id: str,
    db: Session = Depends(get_db),
    admin_user: UserProfile = Depends(require_admin)
):
    """Delete a training engagement and its requirements."""
    engagement = db.query(TrainingEngagement).filter(TrainingEngagement.engagement_id == engagement_id).first()
    if not engagement:
        raise HTTPException(status_code=404, detail="Training engagement not found")

    db.delete(engagement)
    db.commit()
    return None


# ==========================================
# TRAINING REQUIREMENTS ENDPOINTS
# ==========================================

@router.post("/{engagement_id}/requirements", response_model=TrainingRequirementResponse, status_code=status.HTTP_201_CREATED)
def add_webinar_requirement(
    engagement_id: str,
    req_in: TrainingRequirementCreate,
    db: Session = Depends(get_db),
    admin_user: UserProfile = Depends(require_admin)
):
    """Manually add a skill requirement to an existing training engagement."""
    engagement = db.query(TrainingEngagement).filter(TrainingEngagement.engagement_id == engagement_id).first()
    if not engagement:
        raise HTTPException(status_code=404, detail="Training engagement not found")

    skill_identifier = getattr(req_in, "skill_name", None) or getattr(req_in, "skill_id")
    skill_obj = get_or_create_skill(db, skill_identifier)

    embedding_vector = None
    if generate_embedding:
        try:
            embedding_vector = generate_embedding(skill_obj.skill_name)
        except Exception as e:
            logger.warning(f"Embedding generation failed: {e}")

    new_req = TrainingRequirement(
        engagement_id=engagement_id,
        skill_id=skill_obj.skill_id,
        min_proficiency=req_in.min_proficiency,
        is_mandatory=req_in.is_mandatory,
        requirement_embedding=embedding_vector
    )

    db.add(new_req)
    db.commit()
    db.refresh(new_req)
    return new_req


@router.delete("/{engagement_id}/requirements/{requirement_id}", status_code=status.HTTP_204_NO_CONTENT)
def remove_webinar_requirement(
    engagement_id: str,
    requirement_id: str,
    db: Session = Depends(get_db),
    admin_user: UserProfile = Depends(require_admin)
):
    """Remove a skill requirement from a training engagement."""
    req = db.query(TrainingRequirement).filter(
        TrainingRequirement.requirement_id == requirement_id,
        TrainingRequirement.engagement_id == engagement_id
    ).first()

    if not req:
        raise HTTPException(status_code=404, detail="Training requirement not found")

    db.delete(req)
    db.commit()
    return None