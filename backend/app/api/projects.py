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
from app.models.allocation import Allocation
from app.models.enums import ProjectStatus
from app.models.employee import CompanyEmployee, EmployeeCompletedProject
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

def get_designation_titles_map(db : Session) -> dict:
    """Fetches designation_id -> title mapping from the designations table."""
    title_map = {}
    try:
        
            query = text("""
                SELECT 
                    designation_id, title 
                FROM designations
            """)
            rows = db.execute(query).fetchall()
            for row in rows:
               if row[0] is not None and row[1] is not None:
                   title_map[str(row[0])] = str(row[1])

            
    except Exception as e:
        print(f"[DEBUG] Failed to fetch designations map: {e}")
    return title_map


@router.post("/{project_id}/recommendations")
async def fetch_recommendations(
    project_id: str, 
    payload: RecommendationRequest,
    db: Session = Depends(get_db)
):
    try:
        result_dict = recommend_candidates_for_project(project_id) or {}
        req_type = payload.type.lower().strip() if payload.type else "mentors"
        is_student_req = req_type in ["students", "interns", "intern", "student"]

        # 1. Flexible key lookup for result_dict
        if is_student_req:
            candidates = result_dict.get("interns") or result_dict.get("students") or []
        elif req_type in ["team_leads", "team_lead", "lead"]:
            candidates = result_dict.get("eligible_team_leads") or result_dict.get("team_leads") or []
        else:
            candidates= (
                 result_dict.get("mentors") 
                or result_dict.get("recommended_mentors") 
                or result_dict.get("eligible_mentors")
                or result_dict.get("candidates")
                or []
            )

        designation_map = get_designation_titles_map(db) if not is_student_req else {}
        cleaned_candidates = []

        for c in candidates:
            # 2. Convert SQLAlchemy / Pydantic objects to dict if needed
            if hasattr(c, "__dict__"):
                c = {k: v for k, v in c.__dict__.items() if not k.startswith("_")}
            elif hasattr(c, "dict") and callable(c.dict):
                c = c.dict()

            if isinstance(c, dict):
                raw_skills = c.get("skills")
                skills_list = [str(s) for s in raw_skills] if isinstance(raw_skills, list) else []

                if is_student_req:
                    role_val = "Intern"
                    univ_val = str(c.get("university") or c.get("college_institution") or "Intern")
                else:
                    desig_id = str(c.get("designation_id") or "")
                    role_val = designation_map.get(desig_id) or c.get("role") or c.get("designation") or "Mentor"
                    univ_val = "N/A"

                cleaned_candidates.append({
                    "id": str(c.get("id") or c.get("employee_id") or c.get("_id") or "unknown"),
                    "name": str(c.get("name") or c.get("full_name") or "Unnamed Candidate"),
                    "matchScore": float(c.get("suitability_score") or c.get("score") or c.get("match_score") or 0),
                    "skills": skills_list,
                    "role": str(role_val),
                    "university": univ_val,
                })

        print(f"DEBUG: req_type={req_type}, candidates_count={len(candidates)}, candidates={candidates}")
        print(f"DEBUG: cleaned_candidates_count={len(cleaned_candidates)}")
        return JSONResponse(content=cleaned_candidates)

    except ValueError as ve:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(ve))
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Engine execution error: {str(e)}"
        )

def get_or_create_skill(db: Session, skill_name: str, default_category: str = "General") -> Skill:
    clean_name = skill_name.strip()

    # 1. Check if skill already exists (case-insensitive)
    existing_skill = (
        db.query(Skill)
        .filter(func.lower(Skill.skill_name) == clean_name.lower())
        .first()
    )
    if existing_skill:
        return existing_skill

    # 2. Generate Skill Embedding (if embedding function exists)
    embedding = None
    if generate_embedding:
        try:
            embedding = generate_embedding(clean_name)
        except Exception as e:
            logger.warning(f"Failed to generate embedding for skill '{clean_name}': {e}")

    # 3. Auto-generate skills_id (Format: rp2-skl-0001)
    total_skills = db.query(func.count(Skill.skill_id)).scalar() or 0
    next_id = f"rp2-skl-{(total_skills + 1):04d}"

    # 4. Create and insert new Skill record
    new_skill = Skill(
        skill_id=next_id,
        skill_name=clean_name,
        skill_embedding=embedding,
        category=default_category
    )
    db.add(new_skill)
    db.flush()  # Flushes to obtain skills_id without committing transaction

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
                p.category,
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
            LEFT JOIN allocations a ON p.project_id = a.reference_id
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
                    "status": row["project_status"] or "open",
                    "start_date": str(row["start_date"]) if row["start_date"] else "TBD",
                    "category": row["category"] or "General",
                    "project_type": row["project_type"] or "internal_project",
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
                "project_type": proj["project_type"],
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


@router.post("", response_model=ProjectResponse, status_code=status.HTTP_201_CREATED)
def create_project(
    project_in: ProjectCreate, 
    db: Session = Depends(get_db),
    admin_user: UserProfile = Depends(require_admin)
):
    """
    Create a new project with auto-generated ID (rp2-proj-XXXX),
    deduplicated skills, auto-populated skills table, vector embeddings,
    and returns requirement details including skill_name.
    """
    raw_skills_input = getattr(project_in, "raw_skills", []) or []
    project_data = project_in.model_dump(exclude={"requirements", "raw_skills"})

    try:
        # -------------------------------------------------------------
        # 1. AUTO PROJECT ID GENERATION
        # -------------------------------------------------------------
        if not project_data.get("project_id"):
            total_count = db.query(func.count(Project.project_id)).scalar() or 0
            project_data["project_id"] = f"rp2-proj-{(total_count + 1):04d}"

        new_project = Project(**project_data, status="open")
        db.add(new_project)
        db.flush()

        # -------------------------------------------------------------
        # 2. PROCESS & DEDUPLICATE REQUIREMENTS
        # -------------------------------------------------------------
        raw_requirements: List[Dict[str, Any]] = []

        # Case A: Explicit requirements
        explicit_reqs = getattr(project_in, "requirements", None)
        if explicit_reqs:
            for req in explicit_reqs:
                s_name = getattr(req, "skill_name", None) or getattr(req, "skill_id", "General")
                raw_requirements.append({
                    "skill_name": str(s_name),
                    "min_proficiency": getattr(req, "min_proficiency", 3),
                    "is_mandatory": getattr(req, "is_mandatory", True)
                })

        # Case B: AI Skill Extraction
        if not raw_requirements and extract_skills_from_text:
            if new_project.description or raw_skills_input:
                try:
                    extracted = extract_skills_from_text(
                        new_project.description or "",
                        raw_skills_input
                    )
                    for item in extracted:
                        s_name = getattr(item, "skill_name", str(item))
                        raw_requirements.append({
                            "skill_name": str(s_name),
                            "min_proficiency": getattr(item, "min_proficiency", 3),
                            "is_mandatory": getattr(item, "is_mandatory", True)
                        })
                except Exception as e:
                    logger.warning(f"AI skill extraction failed: {e}. Falling back to raw skills.")

        # Case C: Fallback raw skills list
        if not raw_requirements and raw_skills_input:
            for sk_name in raw_skills_input:
                raw_requirements.append({
                    "skill_name": str(sk_name),
                    "min_proficiency": 3,
                    "is_mandatory": True
                })

        # Case-insensitive deduplication
        seen_skills = set()
        deduped_requirements = []
        for req in raw_requirements:
            normalized_name = req["skill_name"].strip().lower()
            if normalized_name and normalized_name not in seen_skills:
                seen_skills.add(normalized_name)
                deduped_requirements.append(req)

        # -------------------------------------------------------------
        # 3. POPULATE SKILLS & REQUIREMENTS TABLE
        # -------------------------------------------------------------
        project_category = getattr(new_project, "category", "General") or "General"
        total_req_count = db.query(func.count(ProjectRequirement.requirement_id)).scalar() or 0

        # List to hold response structure with skill_name included
        formatted_requirements_output = []

        for idx, req_data in enumerate(deduped_requirements, start=1):
            clean_skill_name = req_data["skill_name"].strip()

            # Ensure skill exists in DB
            skill_obj = get_or_create_skill(db, clean_skill_name, default_category=project_category)

            # Resolve skill ID safely
            resolved_skill_id = (
                getattr(skill_obj, "skills_id", None) 
                or getattr(skill_obj, "skill_id", None)
            )

            # Resolve embedding safely
            req_embedding = getattr(skill_obj, "skill_embedding", None)
            if not req_embedding and generate_embedding:
                try:
                    req_embedding = generate_embedding(clean_skill_name)
                except Exception as e:
                    logger.warning(f"Embedding generation failed for '{clean_skill_name}': {e}")

            # Generate unique requirement ID
            req_id = f"rp2-req-{(total_req_count + idx):04d}"

            db_req = ProjectRequirement(
                requirement_id=req_id,
                project_id=new_project.project_id,
                skill_id=resolved_skill_id,
                min_proficiency=req_data["min_proficiency"],
                is_mandatory=req_data["is_mandatory"],
                requirement_embedding=req_embedding
            )
            db.add(db_req)

            # Collect formatted dict including skill_name for frontend
            formatted_requirements_output.append({
                "skill_id": resolved_skill_id,
                "skill_name": skill_obj.skill_name,  # <-- Added skill_name
                "min_proficiency": req_data["min_proficiency"],
                "is_mandatory": req_data["is_mandatory"],
            })

        db.commit()
        db.refresh(new_project)

        return {
            "project_id": new_project.project_id,
            "title": new_project.title,
            "description": new_project.description or "",
            "category": project_category,
            "project_type": getattr(new_project, "project_type", "internal_project"),
            "status": str(new_project.status.value if hasattr(new_project.status, 'value') else new_project.status),
            "start_date": str(new_project.start_date) if new_project.start_date else None,
            "end_date": str(new_project.end_date) if new_project.end_date else None,
            "required_hours_per_week": new_project.required_hours_per_week,
            "priority_level": new_project.priority_level,
            "requiredSkills": [req["skill_name"] for req in formatted_requirements_output], # <-- String array of names for frontend direct rendering
            "requirements": formatted_requirements_output  # <-- Returns list with skill_name
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

VALID_PROJECT_STATUSES = ["open", "in_progress", "completed", "cancelled"]

def calculate_progress(status: str) -> int:
    status_lower = str(status).lower()
    if status_lower in ["completed", "done", "finished"]:
        return 100
    elif status_lower in ["in_progress", "active", "started", "assigned"]:
        return 50
    elif status_lower in ["accepted", "proposed", "pending"]:
        return 10
    return 0
@router.patch("/{project_id}/status", response_model=ProjectResponse)
def update_project_status(
    project_id: str,
    status_in: StatusUpdateRequest,
    db: Session = Depends(get_db),
    current_user: UserProfile = Depends(get_current_user)
):
    """Update project status and cascade completion to all assigned allocations (employees and interns)."""
    
    # 1. Fetch Project
    project = db.query(Project).filter(Project.project_id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    # 2. Authorization Check (Must be Admin or Assigned Employee/Mentor)
    user_role = str(getattr(current_user, "role", "")).lower().strip()

    if user_role != "admin":
        employee = db.query(CompanyEmployee).filter(
            func.lower(CompanyEmployee.email) == func.lower(current_user.email)
        ).first()

        if not employee:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Employee record associated with your email could not be found."
            )

        employee_id = str(getattr(employee, "employee_id", getattr(employee, "id", "")))

        is_assigned_mentor = db.query(Allocation).filter(
            Allocation.reference_id == project_id,
            Allocation.resource_id == employee_id,
            func.lower(Allocation.resource_type).in_(["employee", "mentor"]),
            func.lower(Allocation.status).in_(["assigned", "in_progress", "accepted", "active"])
        ).first()

        if not is_assigned_mentor:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You do not have permission to update the status of this project."
            )

    # 3. Validate Status Input
    target_status = status_in.status.lower().strip()
    if target_status not in VALID_PROJECT_STATUSES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid project status '{status_in.status}'. Valid states: {VALID_PROJECT_STATUSES}"
        )

    # 4. Update Project Status & Progress Percentage
    project.status = target_status
    computed_progress = calculate_progress(target_status)

    if hasattr(project, "progress_percentage"):
        project.progress_percentage = computed_progress
    elif hasattr(project, "progress"):
        project.progress = computed_progress

    # 5. Cascade Status to ALL Allocations (Updates both Employee and Intern records)
    if target_status in ["completed", "cancelled"]:
        db.query(Allocation).filter(
            Allocation.reference_id == project_id
        ).update({"status": target_status}, synchronize_session=False)

    db.commit()
    db.refresh(project)

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


@router.post("/sync-completed-projects")
def sync_completed_projects(db: Session = Depends(get_db)):
    try:
        # 1. Fetch aggregated completed projects joining allocation, companyemployee, and projects
        # For PostgreSQL (use STRING_AGG):
        sync_sql = text("""
            SELECT 
                ce.name AS employee_name,
                STRING_AGG(p.title, ', ') AS title,
                COUNT(p.project_id) AS count
            FROM allocations a
            JOIN company_employees ce ON a.resource_id = ce.reference_id
            JOIN projects p ON a.project_id = p.project_id
            WHERE p.status = 'completed' 
              AND a.status = 'assigned'
            GROUP BY ce.reference_id, ce.name
        """)
        
        # Note: If using MySQL, replace STRING_AGG(p.title, ', ') with GROUP_CONCAT(p.title SEPARATOR ', ')
        
        aggregated_rows = db.execute(sync_sql).mappings().all()

        # 2. Clear old sync records
        db.execute(text("TRUNCATE TABLE employee_completed_projects;"))

        # 3. Bulk insert newly aggregated data
        new_records = [
            EmployeeCompletedProject(
                employee_name=row["employee_name"],
                title=row["title"],
                count=row["count"]
            )
            for row in aggregated_rows
        ]
        
        db.add_all(new_records)
        db.commit()

        return {
            "success": True,
            "message": f"Successfully synced completed projects for {len(new_records)} employees.",
            "count": len(new_records)
        }

    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to sync completed projects: {str(e)}"
        )
