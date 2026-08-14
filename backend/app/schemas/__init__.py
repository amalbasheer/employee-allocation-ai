# app/schemas/__init__.py
from app.schemas.taxonomy import (
    SkillBase, SkillCreate, SkillResponse,
    DesignationBase, DesignationCreate, DesignationResponse
)
from app.schemas.employee import (
    EmployeeBase, EmployeeCreate, EmployeeUpdate, EmployeeResponse,
    EmployeeSkillCreate, EmployeeSkillResponse, AvailabilityResponse
)
from app.schemas.intern import (
    InternBase, InternCreate, InternRegisterWithUrl, InternResponse,
    InternSkillCreate, InternSkillResponse
)
from app.schemas.project import (
    SkillReqInput, ProjectBase, ProjectCreate, CreateProjectSchema, ProjectResponse
)
from app.schemas.allocation_log import (
    AllocationBase, AllocationCreate, AllocationUpdate, AllocationResponse,
    AllocationLogBase, AllocationLogCreate, AllocationLogResponse
)

__all__ = [
    "SkillBase", "SkillCreate", "SkillResponse",
    "DesignationBase", "DesignationCreate", "DesignationResponse",
    "EmployeeBase", "EmployeeCreate", "EmployeeUpdate", "EmployeeResponse",
    "EmployeeSkillCreate", "EmployeeSkillResponse", "AvailabilityResponse",
    "InternBase", "InternCreate", "InternRegisterWithUrl", "InternResponse",
    "InternSkillCreate", "InternSkillResponse",
    "SkillReqInput", "ProjectBase", "ProjectCreate", "CreateProjectSchema", "ProjectResponse",
    "AllocationBase", "AllocationCreate", "AllocationUpdate", "AllocationResponse",
    "AllocationLogBase", "AllocationLogCreate", "AllocationLogResponse",
]