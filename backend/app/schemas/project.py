# app/schemas/project.py
from datetime import date
from typing import List, Optional
from uuid import UUID
from pydantic import BaseModel, ConfigDict


# ==========================================
# PROJECT REQUIREMENT SCHEMAS
# ==========================================
class ProjectRequirementBase(BaseModel):
    skill_id: UUID
    min_proficiency: int = 1
    is_mandatory: bool = True


class ProjectRequirementCreate(ProjectRequirementBase):
    project_id: Optional[UUID] = None
    requirement_embedding: Optional[List[float]] = None  # 768-dim float list for Gemini


class ProjectRequirementUpdate(BaseModel):
    min_proficiency: Optional[int] = None
    is_mandatory: Optional[bool] = None
    requirement_embedding: Optional[List[float]] = None


class ProjectRequirementResponse(ProjectRequirementBase):
    model_config = ConfigDict(from_attributes=True)

    requirement_id: UUID
    project_id: UUID
    requirement_embedding: Optional[List[float]] = None


# ==========================================
# PROJECT SCHEMAS
# ==========================================
class ProjectBase(BaseModel):
    title: str
    project_type: str
    description: Optional[str] = None
    start_date: date
    end_date: date
    required_hours_per_week: int
    priority_level: str = "Medium"
    status: str = "open"


class ProjectCreate(ProjectBase):
    # Allows attaching initial skill requirements during project creation
    requirements: Optional[List[ProjectRequirementBase]] = None


class ProjectUpdate(BaseModel):
    title: Optional[str] = None
    project_type: Optional[str] = None
    description: Optional[str] = None
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    required_hours_per_week: Optional[int] = None
    priority_level: Optional[str] = None
    status: Optional[str] = None


class ProjectResponse(ProjectBase):
    model_config = ConfigDict(from_attributes=True)

    project_id: UUID
    requirements: List[ProjectRequirementResponse] = []