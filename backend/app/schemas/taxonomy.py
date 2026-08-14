# app/schemas/taxonomy.py
from pydantic import BaseModel, ConfigDict
from typing import Optional, List
from uuid import UUID


# ==========================================
# SKILL SCHEMAS
# ==========================================
class SkillBase(BaseModel):
    name: str
    category: Optional[str] = None


class SkillCreate(SkillBase):
    skill_embedding: Optional[List[float]] = None  # Optional 768-dim float list


class SkillUpdate(BaseModel):
    name: Optional[str] = None
    category: Optional[str] = None
    skill_embedding: Optional[List[float]] = None


class SkillResponse(SkillBase):
    model_config = ConfigDict(from_attributes=True)

    skill_id: UUID
    skill_embedding: Optional[List[float]] = None


# ==========================================
# DESIGNATION SCHEMAS
# ==========================================
class DesignationBase(BaseModel):
    title: str
    department: str
    description: Optional[str] = None


class DesignationCreate(DesignationBase):
    pass


class DesignationUpdate(BaseModel):
    title: Optional[str] = None
    department: Optional[str] = None
    description: Optional[str] = None


class DesignationResponse(DesignationBase):
    model_config = ConfigDict(from_attributes=True)

    designation_id: UUID


# ==========================================
# DESIGNATION SKILL SCHEMAS (Composite Primary Key)
# ==========================================
class DesignationSkillBase(BaseModel):
    designation_id: UUID
    skill_id: UUID
    default_proficiency: int = 3


class DesignationSkillCreate(DesignationSkillBase):
    pass


class DesignationSkillResponse(DesignationSkillBase):
    model_config = ConfigDict(from_attributes=True)