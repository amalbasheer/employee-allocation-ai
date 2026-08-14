# app/schemas/intern.py
from pydantic import BaseModel, EmailStr
from typing import Optional
from uuid import UUID

class InternBase(BaseModel):
    name: str
    email: EmailStr
    college_university: Optional[str] = None
    resume_url: Optional[str] = None

class InternCreate(InternBase):
    pass

class InternRegisterWithUrl(BaseModel):
    name: str
    email: EmailStr
    resume_url: str

class InternResponse(InternBase):
    intern_id: UUID

    class Config:
        from_attributes = True

class InternSkillBase(BaseModel):
    skill_id: UUID
    proficiency_level: float = 1.0

class InternSkillCreate(InternSkillBase):
    pass

class InternSkillResponse(InternSkillBase):
    id: UUID
    intern_id: UUID

    class Config:
        from_attributes = True