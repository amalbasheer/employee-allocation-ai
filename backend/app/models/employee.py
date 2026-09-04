# app/models/employee.py
import uuid
from datetime import datetime
from typing import Optional, List
from sqlalchemy import Column, Text, DateTime, Date, text, String, Float, func, Integer, Boolean, ForeignKey, UniqueConstraint, CheckConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship
from uuid import uuid4, UUID
from app.database import Base
from datetime import datetime, date
from pgvector.sqlalchemy import Vector


class CompanyEmployee(Base):
    __tablename__ = "company_employees"

    employee_id = Column(String(20), primary_key=True, # Tells SQLAlchemy to let Postgres handle default generation
        server_default=text("'rp2-emp-' || lpad(nextval('employee_id_seq')::text, 4, '0')"))
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    email: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    designation_id = Column(String(20), ForeignKey("designations.designation_id"), nullable=True)
    department: Mapped[str] = mapped_column(String(50), nullable=False)
    experience_years: Mapped[float] = mapped_column(Float, default=0.0)
    weekly_capacity_hours: Mapped[int] = mapped_column(Integer, default=40)
    is_team_lead: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    location: Mapped[Optional[str]] = mapped_column(String(50))
    preferred_audience: Mapped[Optional[str]] = mapped_column(String(50))

    __table_args__ = (
            # Ensures employee_id must start with 'rp2-emp-' followed by exactly 4 digits
            CheckConstraint("employee_id ~ '^rp2-emp-\\d{4}$'", name="check_employee_id_format"),
        )

    

class EmployeeSkill(Base):
    __tablename__ = "employee_skills"

    employee_id = Column(String(20), ForeignKey("company_employees.employee_id", ondelete="CASCADE"), primary_key=True)
    skill_id = Column(String(20), ForeignKey("skills.skill_id", ondelete="CASCADE"), primary_key=True)
    proficiency_level: Mapped[int] = mapped_column(Integer, default=1)


    
class Availability(Base):
    __tablename__ = "availability"

    availability_id = Column(String(20), primary_key=True)
    resource_type: Mapped[str] = mapped_column(String(20), nullable=False)
    resource_id = Column(String(20), nullable=False)
    week_start_date: Mapped[date] = mapped_column(Date, nullable=False)
    available_hours: Mapped[int] = mapped_column(Integer, nullable=False)
    is_on_leave: Mapped[bool] = mapped_column(Boolean, default=False)

    __table_args__ = (UniqueConstraint('resource_id', 'week_start_date', name='uq_resource_week'),)


class EmployeeCompletedProject(Base):
    __tablename__ = 'employee_completed_projects'

    completed_id = Column(Integer, primary_key=True, autoincrement=True)
    employee_name = Column(String(255), nullable=False)
    title = Column(Text, nullable=True)  # Stores comma-separated project titles
    count = Column(Integer, default=0)
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())