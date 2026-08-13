from app.schemas.taxonomy import SkillResponse, DesignationResponse
from app.schemas.employee import (
    EmployeeCreate,
    EmployeeUpdate,
    EmployeeResponse,
    EmployeeDetailResponse,
    EmployeeSkillCreate,
    EmployeeSkillResponse,
    AvailabilityCreate,
    AvailabilityResponse,
)
from app.schemas.intern import InternRegisterWithUrl, InternResponse
from app.schemas.project import CreateProjectSchema, SkillReqInput

__all__ = [
    "SkillResponse",
    "DesignationResponse",
    "EmployeeCreate",
    "EmployeeUpdate",
    "EmployeeResponse",
    "EmployeeDetailResponse",
    "EmployeeSkillCreate",
    "EmployeeSkillResponse",
    "AvailabilityCreate",
    "AvailabilityResponse",
    "InternRegisterWithUrl",
    "InternResponse",
    "CreateProjectSchema",
    "SkillReqInput",
]