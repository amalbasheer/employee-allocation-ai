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
    AllocationBase,
    AllocationCreate,
    AllocationUpdate,
    AllocationResponse,
    SubstitutionBase,
    SubstitutionCreate,
    SubstitutionUpdate,
    SubstitutionResponse,
    AllocationLogBase,
    AllocationLogCreate,
    AllocationLogResponse,
)

# 6. Chat Query & Recommendation Schemas
from app.schemas.chat_query import (
    ChatQueryBase,
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
    "ProjectRequirementBase",
    "ProjectRequirementCreate",
    "ProjectRequirementUpdate",
    "ProjectRequirementResponse", 
    # Allocation & Substitution
    "AllocationBase",
    "AllocationCreate",
    "AllocationUpdate",
    "AllocationResponse",
    "SubstitutionBase",
    "SubstitutionCreate",
    "SubstitutionUpdate",
    "SubstitutionResponse",
    # Allocation Logs
    "AllocationLogBase",
    "AllocationLogCreate",
    "AllocationLogResponse",
    # Chat / AI Queries
    "ChatQueryBase",
    "ChatQueryCreate",
    "ChatQueryResponse",
]