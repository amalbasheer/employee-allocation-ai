# app/schemas/allocation_log.py
from pydantic import BaseModel
from typing import Optional
from uuid import UUID
from datetime import datetime

class AllocationBase(BaseModel):
    project_id: UUID
    resource_id: UUID
    resource_type: str = "EMPLOYEE"
    allocated_hours: int
    match_score: Optional[float] = None
    status: Optional[str] = "ALLOCATED"

class AllocationCreate(AllocationBase):
    pass

class AllocationUpdate(BaseModel):
    allocated_hours: Optional[int] = None
    match_score: Optional[float] = None
    status: Optional[str] = None

class AllocationResponse(AllocationBase):
    allocation_id: UUID
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True

# Aliases for backward compatibility
AllocationLogBase = AllocationBase
AllocationLogCreate = AllocationCreate
AllocationLogResponse = AllocationResponse