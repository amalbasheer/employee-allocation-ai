# app/models/enums.py
import enum

class ProjectStatus(str, enum.Enum):
    OPEN = "open"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    CANCELLED = "cancelled"

class AllocationStatus(str, enum.Enum):
    PROPOSED = "proposed"
    ACCEPTED = "accepted"
    REJECTED = "rejected"
    ASSIGNED = "assigned"
    SUBSTITUTED = "substituted"
    CANCELLED = "cancelled"

class UserRole(str, enum.Enum):
    ADMIN = "admin"
    SUPERADMIN = "superadmin"
    EMPLOYEE = "employee"
    STUDENT = "student"
    INTERN = "intern"