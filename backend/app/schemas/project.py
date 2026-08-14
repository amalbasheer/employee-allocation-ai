# app/schemas/project.py
from pydantic import BaseModel
from typing import Optional, List
from uuid import UUID
from datetime import date

class SkillReqInput(BaseModel):
    skill_id: UUID
    min_proficiency: float = 1.0
    required_experience_years: float = 0.0
    is_mandatory: bool = True

class ProjectBase(BaseModel):
    title: str
    description: Optional[str] = None
    client_name: Optional[str] = None
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    status: Optional[str] = "PLANNED"
    required_hours: Optional[int] = 0

class ProjectCreate(ProjectBase):
    pass

class CreateProjectSchema(ProjectBase):
    skills: Optional[List[SkillReqInput]] = []

class ProjectResponse(ProjectBase):
    project_id: UUID

    class Config:
        from_attributes = True