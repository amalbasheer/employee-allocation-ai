# backend/app/schemas/project.py
from pydantic import BaseModel
from typing import List, Optional
from uuid import UUID
from datetime import date

class SkillReqInput(BaseModel):
    skill_id: UUID
    min_proficiency: int = 3
    is_mandatory: bool = True

class CreateProjectSchema(BaseModel):
    title: str
    project_type: str
    description: str
    start_date: date
    end_date: date
    required_hours_per_week: int
    priority_level: Optional[str] = "Medium"
    requirements: List[SkillReqInput]