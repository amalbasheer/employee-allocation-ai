# app/schemas/__init__.py

# 1. Taxonomy Schemas
from app.schemas.taxonomy import (
    SkillBase,
    SkillCreate,
    SkillUpdate,
    SkillResponse,
    DesignationBase,
    DesignationCreate,
    DesignationUpdate,
    DesignationResponse,
)

# 2. Employee & Availability Schemas
from app.schemas.employee import (
    CompanyEmployeeBase,
    CompanyEmployeeCreate,
    CompanyEmployeeUpdate,
    CompanyEmployeeResponse,
    # Aliases if referenced as Employee* in other modules
    CompanyEmployeeBase as EmployeeBase,
    CompanyEmployeeCreate as EmployeeCreate,
    CompanyEmployeeUpdate as EmployeeUpdate,
    CompanyEmployeeResponse as EmployeeResponse,
    EmployeeSkillBase,
    EmployeeSkillCreate,
    EmployeeSkillUpdate,
    EmployeeSkillResponse,
    AvailabilityBase,
    AvailabilityCreate,
    AvailabilityUpdate,
    AvailabilityResponse,
)

# 3. Intern Schemas
from app.schemas.intern import (
    InternBase,
    InternCreate,
    InternUpdate,
    InternResponse,
    InternSkillBase,
    InternSkillCreate,
    InternSkillUpdate,
    InternSkillResponse,
)

# 4. Project Schemas
from app.schemas.project import (
    UserProfile,
    StatusUpdateRequest,
    ProjectBase,
    ProjectCreate,
    ProjectUpdate,
    ProjectResponse,
    ProjectRequirementBase,
    ProjectRequirementCreate,
    ProjectRequirementUpdate,
    ProjectRequirementResponse,
)

# 5. Allocation, Substitution & Log Schemas
from app.schemas.allocation import (
    ProposeAllocationRequest,
    AllocationResponse,
    AllocationStatusUpdateRequest,
    SubstitutionResponse,
    SubstituteRequest,
    AllocationLogResponse,
)

# 6. Chat Query & Recommendation Schemas
from app.schemas.chat_query import (
    ChatQueryCreate,
    ChatQueryResponse,
)

__all__ = [
    # Taxonomy
    "SkillBase",
    "SkillCreate",
    "SkillUpdate",
    "SkillResponse",
    "DesignationBase",
    "DesignationCreate",
    "DesignationUpdate",
    "DesignationResponse",
    # Employee
    "CompanyEmployeeBase",
    "CompanyEmployeeCreate",
    "CompanyEmployeeUpdate",
    "CompanyEmployeeResponse",
    "EmployeeBase",
    "EmployeeCreate",
    "EmployeeUpdate",
    "EmployeeResponse",
    "EmployeeSkillBase",
    "EmployeeSkillCreate",
    "EmployeeSkillUpdate",
    "EmployeeSkillResponse",
    "AvailabilityBase",
    "AvailabilityCreate",
    "AvailabilityUpdate",
    "AvailabilityResponse",
    # Intern
    "InternBase",
    "InternCreate",
    "InternUpdate",
    "InternResponse",
    "InternSkillBase",
    "InternSkillCreate",
    "InternSkillUpdate",
    "InternSkillResponse",
    # Project
    "ProjectBase",
    "ProjectCreate",
    "ProjectUpdate",
    "ProjectResponse",
    "UserProfile",
    "StatusUpdateRequest",
    "ProjectRequirementBase",
    "ProjectRequirementCreate",
    "ProjectRequirementUpdate",
    "ProjectRequirementResponse", 
    # Allocation & Substitution
    "ProposeAllocationRequest",
    "AllocationStatusUpdateRequest",
    "AllocationResponse",
    "SubstituteRequest",
    "SubstitutionResponse",
    # Allocation Logs
    "AllocationLogResponse",
    # Chat / AI Queries
    "ChatQueryCreate",
    "ChatQueryResponse",
]