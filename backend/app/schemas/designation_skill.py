# app/schemas/designation_skill.py
from pydantic import BaseModel, Field
from typing import Optional
from uuid import UUID

class DesignationSkillBase(BaseModel):
    designation_id: UUID
    skill_id: UUID
    min_proficiency: float = Field(default=1.0, ge=0.0, le=5.0)

class DesignationSkillCreate(DesignationSkillBase):
    pass

class DesignationSkillResponse(DesignationSkillBase):
    id: UUID

    class Config:
        from_attributes = True