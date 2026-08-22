# app/models/intern.py
from typing import TYPE_CHECKING, List, Optional
from datetime import datetime
import uuid

from pgvector.sqlalchemy import Vector
from sqlalchemy import Column, DateTime, String, Float, func, Text, ForeignKey, text, CheckConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import JSONB
from uuid import uuid4, UUID

from supabase_auth import Optional, datetime
from app.database import Base


class InternsAndStudents(Base):
    __tablename__ = "interns_and_students"

    intern_id = Column(String(20), primary_key=True, server_default=text("'rp2-int-' || lpad(nextval('employee_id_seq')::text, 4, '0')"))
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    email: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    college_institution: Mapped[str] = mapped_column(String(150), nullable=False)
    degree_program: Mapped[Optional[str]] = mapped_column(String(100))
    resume_document_url: Mapped[str] = mapped_column(Text, nullable=False)  # Stores direct or bucket URL
    extracted_skills_raw = mapped_column(JSONB, nullable=True)
    review_status: Mapped[str] = mapped_column(String(20), default="pending_review")
    reviewed_by: Mapped[Optional[str]] = mapped_column(String(100))
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    role: Mapped[str] = mapped_column(String(20), default="intern", nullable=False)
    current_status: Mapped[str] = mapped_column(String(20), default="AVAILABLE", nullable=False)

    __table_args__ = (CheckConstraint("intern_id ~ '^rp2-int-\\d{4}$'", name="check_employee_id_format"),)


class InternSkill(Base):
    __tablename__ = "intern_skills"

    intern_id = Column(String(20), ForeignKey("interns_and_students.intern_id"), primary_key=True)
    skill_id = Column(String(20), ForeignKey("skills.skill_id"), primary_key=True)
    proficiency_level: Mapped[float] = mapped_column(Float, default=1.0)
    extraction_confidence: Mapped[float] = mapped_column(Float, default=0.85)



