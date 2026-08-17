# app/api/projects.py
from typing import List
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.project import Project, ProjectRequirement
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

router = APIRouter()


# ==========================================
# PROJECT ENDPOINTS
# ==========================================
@router.get("", response_model=List[ProjectResponse])
def get_projects(
    db: Session = Depends(get_db),
    current_user: UserProfile = Depends(get_current_user)
):
    """Fetch all projects."""
    return db.query(Project).all()


@router.post("", response_model=ProjectResponse, status_code=status.HTTP_201_CREATED)
def create_project(
    project_in: ProjectCreate, 
    db: Session = Depends(get_db),
    admin_user: UserProfile = Depends(require_admin)
):
    """Create a new project with optional requirements."""
    project_data = project_in.model_dump(exclude={"requirements"})
    new_project = Project(**project_data, status=ProjectStatus.OPEN)
    
    db.add(new_project)
    db.commit()
    db.refresh(new_project)

    if project_in.requirements:
        for req in project_in.requirements:
            db_req = ProjectRequirement(
                project_id=new_project.project_id,
                **req.model_dump(exclude={"project_id"})
            )
            db.add(db_req)
        db.commit()
        db.refresh(new_project)

    return new_project


@router.get("/{project_id}", response_model=ProjectResponse)
def get_project_by_id(
    project_id: str, 
    db: Session = Depends(get_db),
    current_user: UserProfile = Depends(get_current_user)
):
    """Fetch a single project by UUID."""
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
    """Update overall project lifecycle status (OPEN, IN_PROGRESS, COMPLETED, CANCELLED)."""
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
    """Delete a project."""
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
    """Add a skill requirement to a project."""
    project = db.query(Project).filter(Project.project_id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    req_data = req_in.model_dump(exclude={"project_id"})
    new_req = ProjectRequirement(project_id=project_id, **req_data)

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