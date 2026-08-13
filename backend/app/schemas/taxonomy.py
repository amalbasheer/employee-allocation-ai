# backend/app/schemas/taxonomy.py
from pydantic import BaseModel
from typing import Optional
from uuid import UUID

class SkillResponse(BaseModel):
    skill_id: UUID
    skill_name: str
    category: Optional[str]

    class Config:
        from_attributes = True

class DesignationResponse(BaseModel):
    designation_id: UUID
    title: str
    department: str

    class Config:
        from_attributes = True