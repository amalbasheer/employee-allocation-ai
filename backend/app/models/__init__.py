# app/models/__init__.py
from app.models.taxonomy import Skill, Designation, DesignationSkill
from app.models.employee import CompanyEmployee, EmployeeSkill, Availability
from app.models.intern import InternsAndStudents, InternSkill
from app.models.project import Project, ProjectRequirement
from app.models.allocation import Allocation, AllocationLog, Substitution
from app.models.chat_query import ChatQuery

__all__ = [
    "Skill",
    "Designation",
    "DesignationSkill",
    "CompanyEmployee",
    "EmployeeSkill",
    "Availability",
    "InternsAndStudents",
    "InternSkill",
    "Project",
    "ProjectRequirement",
    "Allocation",
    "AllocationLog",
    "Substitution",
    "ChatQuery",
]