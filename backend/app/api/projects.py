# app/api/projects.py
from typing import List
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.project import Project, ProjectRequirement
from app.schemas.project import (
    ProjectCreate,
    ProjectResponse,
    ProjectUpdate,
    ProjectRequirementCreate,
    ProjectRequirementResponse,
    ProjectRequirementUpdate,
)

router = APIRouter()


# ==========================================
# PROJECT ENDPOINTS
# ==========================================
@router.get("", response_model=List[ProjectResponse])
def get_projects(db: Session = Depends(get_db)):
    """Fetch all projects along with their required skills."""
    projects = db.query(Project).all()
    
    # Attach requirements list to each project
    for project in projects:
        project.requirements = (
            db.query(ProjectRequirement)
            .filter(ProjectRequirement.project_id == project.project_id)
            .all()
        )
    return projects


@router.post("", response_model=ProjectResponse, status_code=status.HTTP_201_CREATED)
def create_project(project_in: ProjectCreate, db: Session = Depends(get_db)):
    """Create a new project (optionally with skill requirements)."""
    project_data = project_in.model_dump(exclude={"requirements"})
    new_project = Project(**project_data)
    
    db.add(new_project)
    db.commit()
    db.refresh(new_project)

    # Process nested requirements if passed during creation
    created_requirements = []
    if project_in.requirements:
        for req in project_in.requirements:
            db_req = ProjectRequirement(
                project_id=new_project.project_id,
                **req.model_dump()
            )
            db.add(db_req)
            created_requirements.append(db_req)
        
        db.commit()
        for req in created_requirements:
            db.refresh(req)

    new_project.requirements = created_requirements
    return new_project


@router.get("/{project_id}", response_model=ProjectResponse)
def get_project_by_id(project_id: UUID, db: Session = Depends(get_db)):
    """Fetch a single project by UUID."""
    project = db.query(Project).filter(Project.project_id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    project.requirements = (
        db.query(ProjectRequirement)
        .filter(ProjectRequirement.project_id == project_id)
        .all()
    )
    return project


@router.patch("/{project_id}", response_model=ProjectResponse)
def update_project(project_id: UUID, project_in: ProjectUpdate, db: Session = Depends(get_db)):
    """Update project details."""
    project = db.query(Project).filter(Project.project_id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    update_data = project_in.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(project, field, value)

    db.commit()
    db.refresh(project)

    project.requirements = (
        db.query(ProjectRequirement)
        .filter(ProjectRequirement.project_id == project_id)
        .all()
    )
    return project


@router.delete("/{project_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_project(project_id: UUID, db: Session = Depends(get_db)):
    """Delete a project (Cascade drops associated requirements)."""
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
def add_project_requirement(project_id: UUID, req_in: ProjectRequirementCreate, db: Session = Depends(get_db)):
    """Add a skill requirement to an existing project."""
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
def remove_project_requirement(project_id: UUID, requirement_id: UUID, db: Session = Depends(get_db)):
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