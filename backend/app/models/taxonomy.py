# app/models/taxonomy.py
from typing import Optional, TYPE_CHECKING, List
from uuid import UUID, uuid4
from pgvector.sqlalchemy import Vector
from sqlalchemy import Column, ForeignKey, Integer, String, Text, DateTime, Date
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database import Base
from datetime import datetime, date, timezone


class Skill(Base):
    __tablename__ = "skills"

    skill_id = Column(String(20), primary_key=True)
    skill_name: Mapped[str] = mapped_column("skill_name", String(100), unique=True, nullable=False)
    category: Mapped[Optional[str]] = mapped_column("category", String(50), nullable=True, default=None)
    skill_embedding = mapped_column(Vector(768), nullable=True)



class Designation(Base):
    __tablename__ = "designations"

    designation_id = Column(String(20), primary_key=True)
    title: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    department: Mapped[str] = mapped_column(String(50), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text)


class ScheduleOverride(Base):
    __tablename__ = "schedule_overrides"

    override_id = Column(String, primary_key=True)  # e.g., "ovr-1001"
    
    # Target Entity
    entity_type = Column(String, nullable=False)    # 'project', 'student_batch', 'training_engagement'
    entity_id = Column(String, nullable=False)      # project_id, batch_id, engagement_id
    
    # Override Scope & Target Dates
    scope = Column(String, nullable=False, default="single_day")  # 'single_day' or 'full_week'
    override_date = Column(Date, nullable=True)                 # E.g., 2026-09-21 (for single_day)
    week_start_date = Column(Date, nullable=True)               # E.g., 2026-09-21 (Monday, for full_week)
    
    # Shift Values
    original_session = Column(String, nullable=True)            # E.g., 'morning'
    new_session = Column(String, nullable=False)               # E.g., 'evening'
    
    # Metadata & Tracking
    reason = Column(Text, nullable=True)                        # Optional note/reason
    created_by_user_id = Column(String, nullable=False)        # ID of employee or admin making the change
    created_by_role = Column(String, nullable=False)           # 'employee' or 'admin'
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    status = Column(String(50), nullable=True)