# app/schemas/allocation.py
import uuid
from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, ConfigDict
from app.models.enums import AllocationStatus

class ProposeAllocationRequest(BaseModel):
    project_id: uuid.UUID
    resource_type: str  # "employee" or "student"
    resource_id: uuid.UUID
    role_on_project: str = "lead_mentor"
    allocated_hours: int
    suitability_score: float = 1.0

class AllocationStatusUpdateRequest(BaseModel):
    status: AllocationStatus

class SubstituteRequest(BaseModel):
    substitute_resource_type: str
    substitute_resource_id: uuid.UUID
    reason: str

class AllocationLogResponse(BaseModel):
    log_id: uuid.UUID
    allocation_id: uuid.UUID
    action: str
    changed_by: str
    timestamp: datetime

    model_config = ConfigDict(from_attributes=True)

class SubstitutionResponse(BaseModel):
    substitution_id: uuid.UUID
    original_allocation_id: uuid.UUID
    substitute_resource_type: str
    substitute_resource_id: uuid.UUID
    reason: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)

class AllocationResponse(BaseModel):
    allocation_id: uuid.UUID
    resource_type: str
    resource_id: uuid.UUID
    project_id: uuid.UUID
    role_on_project: str
    allocated_hours: int
    suitability_score: float
    status: AllocationStatus
    assigned_at: datetime
    assigned_by: str

    model_config = ConfigDict(from_attributes=True)