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
from app.models.project import Project, ProjectRequirement
from app.models.taxonomy import Skill
from app.models.enums import ProjectStatus
from app.schemas.project import (
    ProjectCreate,
    ProjectResponse,
    ProjectUpdate,
    ProjectRequirementCreate,
    ProjectRequirementResponse,
    StatusUpdateRequest,
    UserProfile,
)
from app.api.deps import get_current_user, require_admin

ROOT_DIR = Path(__file__).resolve().parents[3]  # Adjust depth based on app location
if str(ROOT_DIR) not in sys.path:
    sys.path.append(str(ROOT_DIR))

# Import AI Engine services with resilient fallbacks
try:
    from ai_engine.extraction import extract_skills_from_text
except ImportError:
    extract_skills_from_text = None

try:
    from ai_engine.embedding import generate_embedding
except ImportError:
    generate_embedding = None

logger = logging.getLogger(__name__)


# Add project root to sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../../..")))

try:
    from ai_engine.recommend import recommend_candidates_for_project
except ImportError:
    def recommend_candidates_for_project(project_id: str) -> dict:
        return {"project_title": "", "roles_needed": [], "mentors": [], "interns": []}

router = APIRouter()

class RecommendationRequest(BaseModel):
    skills: Optional[List[str]] = []
    type: str = "mentors"  # 'mentors' or 'students'/'interns'

# Append this function to the bottom of your existing projects.py
@router.post("/projects/{project_id}/recommendations")
async def fetch_recommendations(project_id: str, payload: RecommendationRequest):
    try:
        result_dict = recommend_candidates_for_project(project_id)
        req_type = payload.type.lower() if payload.type else "mentors"

        if req_type in ["students", "interns", "intern"]:
            candidates = result_dict.get("interns") or []
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

        # JSONResponse avoids triggering response_model validation errors
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
# PROJECT ENDPOINTS
# ==========================================
@router.get("/details")
async def get_all_projects(db: Session = Depends(get_db)):
    try:
        # SQL query joining projects, requirements, skills, allocations, employees, and interns
        query = text("""
            SELECT 
                p.project_id,
                p.title,
                p.description,
                p.status AS project_status,
                p.start_date,
                p.project_type,
                s.skill_name,
                a.allocation_id,
                a.resource_id,
                a.status AS allocation_status,
                COALESCE(e.name, i.name, 'Unknown') AS resource_name,
                CASE 
                    WHEN e.employee_id IS NOT NULL THEN 'employee'
                    WHEN i.intern_id IS NOT NULL THEN 'intern'
                    ELSE 'unknown'
                END AS resource_type
            FROM projects p
            LEFT JOIN project_requirements pr ON p.project_id = pr.project_id
            LEFT JOIN skills s ON pr.skill_id = s.skill_id
            LEFT JOIN allocations a ON p.project_id = a.project_id
            LEFT JOIN company_employees e ON a.resource_id = e.employee_id
            LEFT JOIN interns_and_students i ON a.resource_id = i.intern_id
            ORDER BY p.project_id
        """)

        rows = db.execute(query).mappings().all()

        # Aggregate flat SQL rows into structured JSON objects
        projects_map: Dict[Any, Dict[str, Any]] = {}

        for row in rows:
            pid = row["project_id"]

            if pid not in projects_map:
                projects_map[pid] = {
                    "project_id": str(pid),
                    "title": row["title"] or "",
                    "description": row["description"] or "",
                    "status": row["project_status"] or "OPEN",
                    "start_date": str(row["start_date"]) if row["start_date"] else "TBD",
                    "category": row["project_type"] or "General",
                    "skills": set(),
                    "allocations": {}
                }

            # Map unique skills
            if row["skill_name"]:
                projects_map[pid]["skills"].add(row["skill_name"])

            # Map unique resource allocations
            if row["allocation_id"]:
                alloc_id = row["allocation_id"]
                if alloc_id not in projects_map[pid]["allocations"]:
                    projects_map[pid]["allocations"][alloc_id] = {
                        "resource_id": str(row["resource_id"]),
                        "resource_name": row["resource_name"],
                        "resource_type": row["resource_type"],
                        "allocation_status": row["allocation_status"] or "PENDING"
                    }

        # Format aggregated map into JSON response list
        formatted_projects: List[Dict[str, Any]] = []
        for proj in projects_map.values():
            formatted_projects.append({
                "project_id": proj["project_id"],
                "title": proj["title"],
                "description": proj["description"],
                "status": proj["status"],
                "start_date": proj["start_date"],
                "category": proj["category"],
                "skills": list(proj["skills"]),
                "allocations": list(proj["allocations"].values())
            })

        return JSONResponse(content=formatted_projects)

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch projects from database: {str(e)}"
        )

@router.get("", response_model=List[ProjectResponse])
def get_projects(
    db: Session = Depends(get_db),
    current_user: UserProfile = Depends(get_current_user)
):
    """Fetch all projects from database."""
    return db.query(Project).all()


 # create a new project with auto-generated ID, deduplicated skills, and AI-driven vector embeddings

@router.post("", response_model=ProjectResponse, status_code=status.HTTP_201_CREATED)
def create_project(
    project_in: ProjectCreate, 
    db: Session = Depends(get_db),
    admin_user: UserProfile = Depends(require_admin)
):
    """
    Create a new project with auto-generated ID (rp2-proj-XXXX),
    deduplicated skills, and AI-driven vector embeddings.
    """
    raw_skills_input = getattr(project_in, "raw_skills", []) or []
    project_data = project_in.model_dump(exclude={"requirements", "raw_skills"})

    try:
        # -------------------------------------------------------------
        # 1. AUTO ID GENERATION (Format: rp2-proj-0001)
        # -------------------------------------------------------------
        if not project_data.get("project_id"):
            total_count = db.query(func.count(Project.project_id)).scalar() or 0
            project_data["project_id"] = f"rp2-proj-{(total_count + 1):04d}"

        new_project = Project(**project_data, status=ProjectStatus.OPEN)
        db.add(new_project)
        db.flush()  # Ensures project_id is bound for requirements

        # -------------------------------------------------------------
        # 2. PROCESS REQUIREMENTS
        # -------------------------------------------------------------
        raw_requirements: List[Dict[str, Any]] = []

        # Case A: Explicit requirements passed in payload
        explicit_reqs = getattr(project_in, "requirements", None)
        if explicit_reqs:
            for req in explicit_reqs:
                s_name = getattr(req, "skill_name", None) or getattr(req, "skill_id", "General")
                raw_requirements.append({
                    "skill_name": s_name,
                    "min_proficiency": getattr(req, "min_proficiency", 3),
                    "is_mandatory": getattr(req, "is_mandatory", True)
                })

        # Case B: AI Skill Extraction from description + raw_skills
        if not raw_requirements and extract_skills_from_text:
            if new_project.description or raw_skills_input:
                try:
                    extracted = extract_skills_from_text(
                        description=new_project.description or "",
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

        # Case C: Fallback to raw_skills list
        if not raw_requirements and raw_skills_input:
            for sk_name in raw_skills_input:
                raw_requirements.append({
                    "skill_name": sk_name,
                    "min_proficiency": 3,
                    "is_mandatory": True
                })

        # -------------------------------------------------------------
        # 3. DEDUPLICATION BY SKILL NAME
        # -------------------------------------------------------------
        seen_skills = set()
        deduped_requirements = []

        for req in raw_requirements:
            normalized_name = req["skill_name"].strip().lower()
            if normalized_name not in seen_skills:
                seen_skills.add(normalized_name)
                deduped_requirements.append(req)

        # -------------------------------------------------------------
        # 4. RESOLVE SKILL IDs, EMBEDDINGS & SAVE REQUIREMENTS
        # -------------------------------------------------------------
        for req_data in deduped_requirements:
            skill_name = req_data["skill_name"].strip()
            skill_obj = get_or_create_skill(db, skill_name)

            embedding_vector = None
            if generate_embedding:
                try:
                    embedding_vector = generate_embedding(skill_name)
                except Exception as e:
                    logger.warning(f"Embedding generation failed for skill '{skill_name}': {e}")

            db_req = ProjectRequirement(
                project_id=new_project.project_id,
                skill_id=skill_obj.skill_id,
                min_proficiency=req_data["min_proficiency"],
                is_mandatory=req_data["is_mandatory"],
                requirement_embedding=embedding_vector
            )
            db.add(db_req)

        db.commit()
        db.refresh(new_project)
        # Safely fetch requirements relationship regardless of ORM property name
        req_list = getattr(new_project, "requirements", None) or getattr(new_project, "project_requirements", None) or []

        return {
            "project_id": new_project.project_id,
            "title": new_project.title,
            "description": new_project.description or "",
            "category": new_project.category or "General",
            "project_type": getattr(new_project, "project_type", "Internal"),
            "status": str(new_project.status.value if hasattr(new_project.status, 'value') else new_project.status),
            "start_date": str(new_project.start_date) if new_project.start_date else None,
            "end_date": str(new_project.end_date) if new_project.end_date else None,
            "required_hours_per_week": new_project.required_hours_per_week,
            "priority_level": new_project.priority_level,
            "requirements": [
                {
                    "skill_id": req.skill_id,
                    "min_proficiency": req.min_proficiency,
                    "is_mandatory": req.is_mandatory,
                }
                for req in req_list
            ],
        }

    except Exception as e:
        db.rollback()
        logger.error(f"Error creating project: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create project: {str(e)}"
        )

@router.get("/{project_id}", response_model=ProjectResponse)
def get_project_by_id(
    project_id: str, 
    db: Session = Depends(get_db),
    current_user: UserProfile = Depends(get_current_user)
):
    """Fetch a single project by ID."""
    project = db.query(Project).filter(Project.project_id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    return project


@router.patch("/{project_id}", response_model=ProjectResponse)
def update_project(
    project_id: str, 
    project_in: ProjectUpdate, 
    db: Session = Depends(get_db),
    admin_user: UserProfile = Depends(require_admin)
):
    """Update general project details."""
    project = db.query(Project).filter(Project.project_id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    update_data = project_in.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(project, field, value)

    db.commit()
    db.refresh(project)
    return project


@router.patch("/{project_id}/status", response_model=ProjectResponse)
def update_project_status(
    project_id: str,
    status_in: StatusUpdateRequest,
    db: Session = Depends(get_db),
    admin_user: UserProfile = Depends(require_admin)
):
    """Update overall project lifecycle status (open, in_progress, completed, cancelled)."""
    project = db.query(Project).filter(Project.project_id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    try:
        new_status = ProjectStatus(status_in.status.lower())
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid project status '{status_in.status}'. Valid states: {[e.value for e in ProjectStatus]}"
        )

    project.status = new_status
    db.commit()
    db.refresh(project)
    return project


@router.delete("/{project_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_project(
    project_id: str, 
    db: Session = Depends(get_db),
    admin_user: UserProfile = Depends(require_admin)
):
    """Delete a project and its associated requirements."""
    project = db.query(Project).filter(Project.project_id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    db.delete(project)
    db.commit()
    return None


# ==========================================
# PROJECT REQUIREMENTS ENDPOINTS
# ==========================================
@router.post("/{project_id}/requirements", response_model=ProjectRequirementResponse, status_code=status.HTTP_201_CREATED)
def add_project_requirement(
    project_id: str, 
    req_in: ProjectRequirementCreate, 
    db: Session = Depends(get_db),
    admin_user: UserProfile = Depends(require_admin)
):
    """Manually add a skill requirement to an existing project."""
    project = db.query(Project).filter(Project.project_id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    # Resolve skill_id from skill name or ID
    skill_identifier = getattr(req_in, "skill_name", None) or getattr(req_in, "skill_id")
    skill_obj = get_or_create_skill(db, skill_identifier)

    embedding_vector = None
    if generate_embedding:
        try:
            embedding_vector = generate_embedding(skill_obj.skill_name)
        except Exception as e:
            logger.warning(f"Embedding generation failed: {e}")

    new_req = ProjectRequirement(
        project_id=project_id,
        skill_id=skill_obj.skill_id,
        min_proficiency=req_in.min_proficiency,
        is_mandatory=req_in.is_mandatory,
        requirement_embedding=embedding_vector
    )

    db.add(new_req)
    db.commit()
    db.refresh(new_req)
    return new_req


@router.delete("/{project_id}/requirements/{requirement_id}", status_code=status.HTTP_204_NO_CONTENT)
def remove_project_requirement(
    project_id: str, 
    requirement_id: str, 
    db: Session = Depends(get_db),
    admin_user: UserProfile = Depends(require_admin)
):
    """Remove a skill requirement from a project."""
    req = db.query(ProjectRequirement).filter(
        ProjectRequirement.requirement_id == requirement_id,
        ProjectRequirement.project_id == project_id
    ).first()

    if not req:
        raise HTTPException(status_code=404, detail="Project requirement not found")

    db.delete(req)
    db.commit()
    return None