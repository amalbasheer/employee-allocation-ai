# app/schemas/project.py
from datetime import date
from typing import List, Optional, Any, Dict
from uuid import UUID
from pydantic import BaseModel, ConfigDict
from app.models.enums import ProjectStatus

# ==========================================
# USER PROFILE SCHEMA
# ==========================================
class UserProfile(BaseModel):
    id: str
    email: str
    role: str
    name: Optional[str] = None


# ==========================================
# PROJECT REQUIREMENT SCHEMAS
# ==========================================
class ProjectRequirementBase(BaseModel):
    skill_id: str
    min_proficiency: int = 1
    is_mandatory: bool = True


class ProjectRequirementCreate(ProjectRequirementBase):
    project_id: Optional[str] = None
    requirement_embedding: Optional[List[float]] = None  # 768-dim vector


class ProjectRequirementUpdate(BaseModel):
    min_proficiency: Optional[int] = None
    is_mandatory: Optional[bool] = None
    requirement_embedding: Optional[List[float]] = None


class ProjectRequirementResponse(ProjectRequirementBase):
    requirement_id: Optional[str] = None
    project_id: Optional[str] = None
    requirement_embedding: Optional[List[float]] = None

    model_config = ConfigDict(from_attributes=True)


# ==========================================
# PROJECT SCHEMAS
# ==========================================
# Master dictionary defining weights (totaling 100%)
MILESTONE_WEIGHTS: Dict[str, int] = {
    "project_kickoff": 5,
    "architecture_design": 10,
    "repo_cicd_setup": 10,
    "core_development": 35,
    "testing_code_review": 10,
    "deployment": 15,
    "documentation": 10,
    "final_signoff": 5,
}

class UpdateMilestonesRequest(BaseModel):
    completed_milestones: List[str]

class ProjectBase(BaseModel):
    title: str
    project_type: str
    category: str
    description: Optional[str] = None
    start_date: date
    end_date: date
    required_hours_per_week: int
    priority_level: str = "Medium"

    


class ProjectCreate(ProjectBase):
    requirements: Optional[List[ProjectRequirementCreate]] = None


class ProjectUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    priority_level: Optional[str] = None
    status: Optional[ProjectStatus] = None


class StatusUpdateRequest(BaseModel):
    status: str


class ProjectResponse(ProjectBase):
    project_id: str
    status: Optional[Any] = None
    requirements: Optional[List[ProjectRequirementResponse]] = []
    completed_milestones: List[str] = []

    model_config = ConfigDict(from_attributes=True)