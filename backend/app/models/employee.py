# app/models/employee.py
from sqlalchemy import String, Float, Integer, Boolean, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column
from uuid import uuid4, UUID
from app.database import Base

class CompanyEmployee(Base):
    __tablename__ = "company_employees"

    employee_id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    email: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    designation_id: Mapped[UUID] = mapped_column(ForeignKey("designations.designation_id"), nullable=True)
    department: Mapped[str] = mapped_column(String(50), nullable=False)
    experience_years: Mapped[float] = mapped_column(Float, default=0.0)
    weekly_capacity_hours: Mapped[int] = mapped_column(Integer, default=40)
    is_team_lead: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

class EmployeeSkill(Base):
    __tablename__ = "employee_skills"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    employee_id: Mapped[UUID] = mapped_column(ForeignKey("company_employees.employee_id"), nullable=False)
    skill_id: Mapped[UUID] = mapped_column(ForeignKey("skills.skill_id"), nullable=False)
    proficiency_level: Mapped[float] = mapped_column(Float, default=1.0)
    years_experience: Mapped[float] = mapped_column(Float, default=0.0)

class Availability(Base):
    __tablename__ = "availability"

    availability_id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    resource_id: Mapped[UUID] = mapped_column(nullable=False)
    resource_type: Mapped[str] = mapped_column(String(20), nullable=False)  # 'employee' or 'intern'
    allocated_hours: Mapped[int] = mapped_column(Integer, default=0)
    available_hours: Mapped[int] = mapped_column(Integer, default=40)