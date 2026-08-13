import uuid
from datetime import datetime, date
from typing import Optional
from sqlalchemy import String, Integer, Float, Boolean, Date, DateTime, ForeignKey, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column
from pgvector.sqlalchemy import Vector
from app.database import Base

class CompanyEmployee(Base):
    __tablename__ = "company_employees"

    employee_id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    email: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    designation_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("designations.designation_id"))
    department: Mapped[str] = mapped_column(String(50), nullable=False)
    experience_years: Mapped[float] = mapped_column(Float, default=0.0)
    weekly_capacity_hours: Mapped[int] = mapped_column(Integer, default=40)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

class EmployeeSkill(Base):
    __tablename__ = "employee_skills"

    employee_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("company_employees.employee_id", ondelete="CASCADE"), primary_key=True)
    skill_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("skills.skill_id", ondelete="CASCADE"), primary_key=True)
    proficiency_level: Mapped[int] = mapped_column(Integer, default=1)
    skill_embedding = mapped_column(Vector(768), nullable=True)  # 768-dim for Gemini
    is_custom_override: Mapped[bool] = mapped_column(Boolean, default=False)

class Availability(Base):
    __tablename__ = "availability"

    availability_id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    resource_type: Mapped[str] = mapped_column(String(20), nullable=False)  # employee / intern
    resource_id: Mapped[uuid.UUID] = mapped_column(nullable=False)
    week_start_date: Mapped[date] = mapped_column(Date, nullable=False)
    available_hours: Mapped[int] = mapped_column(Integer, nullable=False)
    is_on_leave: Mapped[bool] = mapped_column(Boolean, default=False)

    __table_args__ = (UniqueConstraint('resource_id', 'week_start_date', name='uq_resource_week'),)