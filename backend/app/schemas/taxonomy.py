# app/schemas/taxonomy.py
from pydantic import BaseModel, ConfigDict
from typing import Optional
from uuid import UUID

class SkillBase(BaseModel):
    name: str
    category: Optional[str] = None

class SkillCreate(SkillBase):
    pass

class SkillResponse(SkillBase):
    skill_id: UUID

    class Config:
        from_attributes = True

class DesignationBase(BaseModel):
    title: str

class DesignationCreate(DesignationBase):
    pass

class DesignationResponse(DesignationBase):
    designation_id: UUID

    class Config:
        from_attributes = True