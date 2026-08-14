# app/schemas/allocation.py
from datetime import datetime
from typing import List, Optional
from uuid import UUID
from pydantic import BaseModel, ConfigDict


# ==========================================
# SUBSTITUTION SCHEMAS
# ==========================================
class SubstitutionBase(BaseModel):
    original_allocation_id: UUID
    substitute_resource_type: str
    substitute_resource_id: UUID
    reason: str


class SubstitutionCreate(BaseModel):
    substitute_resource_type: str
    substitute_resource_id: UUID
    reason: str

class SubstitutionUpdate(BaseModel):
    """Schema for approving, rejecting, or updating a substitution request."""
    status: Optional[str] = None
    substitute_resource_type: Optional[str] = None
    substitute_resource_id: Optional[UUID] = None
    reason: Optional[str] = None

class SubstitutionResponse(SubstitutionBase):
    model_config = ConfigDict(from_attributes=True)

    substitution_id: UUID
    created_at: datetime


# ==========================================
# ALLOCATION LOG SCHEMAS
# ==========================================
class AllocationLogBase(BaseModel):
    allocation_id: UUID
    action: str
    changed_by: str


class AllocationLogCreate(BaseModel):
    action: str
    changed_by: str


class AllocationLogResponse(AllocationLogBase):
    model_config = ConfigDict(from_attributes=True)

    log_id: UUID
    timestamp: datetime


# ==========================================
# ALLOCATION SCHEMAS
# ==========================================
class AllocationBase(BaseModel):
    resource_type: str
    resource_id: UUID
    project_id: UUID
    role_on_project: str = "lead_mentor"
    allocated_hours: int
    suitability_score: float
    status: str = "proposed"
    assigned_by: str = "AI_Engine"


class AllocationCreate(AllocationBase):
    pass


class AllocationUpdate(BaseModel):
    resource_type: Optional[str] = None
    resource_id: Optional[UUID] = None
    project_id: Optional[UUID] = None
    role_on_project: Optional[str] = None
    allocated_hours: Optional[int] = None
    suitability_score: Optional[float] = None
    status: Optional[str] = None
    assigned_by: Optional[str] = None


class AllocationResponse(AllocationBase):
    model_config = ConfigDict(from_attributes=True)

    allocation_id: UUID
    assigned_at: datetime
    substitutions: List[SubstitutionResponse] = []
    logs: List[AllocationLogResponse] = []