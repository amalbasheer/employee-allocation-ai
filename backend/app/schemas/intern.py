# app/schemas/intern.py
from pydantic import BaseModel, EmailStr
from typing import Optional, Literal
from uuid import UUID

class InternBase(BaseModel):
    name: str
    email: EmailStr
    college_institution: str
    degree_program: Optional[str] = None
    role: Literal["intern", "student"] = "intern"
    resume_document_url: str
    current_status: Optional[str] = "AVAILABLE"

class InternCreate(InternBase):
    pass

class InternRegisterWithUrl(BaseModel):
    name: str
    email: EmailStr
    resume_url: str

class InternResponse(InternBase):
    intern_id: UUID
    name: str
    email: EmailStr
    college_institution: str
    resume_document_url: str
    review_status: str

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