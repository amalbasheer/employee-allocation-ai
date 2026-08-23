# app/schemas/intern.py
from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import UUID
from pydantic import BaseModel, ConfigDict, EmailStr


# ==========================================
# INTERN SKILL SCHEMAS
# ==========================================
class InternSkillBase(BaseModel):
    skill_id: str
    proficiency_level: float = 1.0
    extraction_confidence: float = 0.85


class InternSkillCreate(InternSkillBase):
    intern_id: Optional[str] = None


class InternSkillUpdate(BaseModel):
    proficiency_level: Optional[float] = None
    extraction_confidence: Optional[float] = None


class InternSkillResponse(InternSkillBase):
    model_config = ConfigDict(from_attributes=True)

    intern_id: str


# ==========================================
# INTERNS & STUDENTS SCHEMAS
# ==========================================
class InternBase(BaseModel):
    name: str
    email: EmailStr
    college_institution: Optional[str]
    degree_program: Optional[str] = None
    resume_document_url: str
    extracted_skills_raw: Optional[Any] = None  # JSONB field payload
    review_status: str = "pending_review"
    reviewed_by: Optional[str] = None
    role: str = "intern"
    current_status: str = "AVAILABLE"
    department: str


class InternCreate(InternBase):
    # Allows attaching initial skills during intern onboarding/resume parsing
    skills: Optional[List[InternSkillBase]] = None


class InternUpdate(BaseModel):
    name: Optional[str] = None
    email: Optional[EmailStr] = None
    college_institution: Optional[str] = None
    degree_program: Optional[str] = None
    resume_document_url: Optional[str] = None
    extracted_skills_raw: Optional[Any] = None
    review_status: Optional[str] = None
    reviewed_by: Optional[str] = None
    role: Optional[str] = None
    current_status: Optional[str] = None  # e.g., 'AVAILABLE' or 'ASSIGNED'
    department: Optional[str] = None


class InternResponse(InternBase):
    model_config = ConfigDict(from_attributes=True)

    intern_id: str
    created_at: datetime
    skills: List[InternSkillResponse] = []