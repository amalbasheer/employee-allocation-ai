# app/models/intern.py
from datetime import datetime
import uuid

from pgvector.sqlalchemy import Vector
from sqlalchemy import DateTime, String, Float, ForeignKey, Text
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.dialects.postgresql import JSONB
from uuid import uuid4, UUID

from supabase_auth import Optional, datetime
from app.database import Base

class InternsAndStudents(Base):
    __tablename__ = "interns_and_students"

    intern_id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    email: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    college_institution: Mapped[str] = mapped_column(String(150), nullable=False)
    degree_program: Mapped[Optional[str]] = mapped_column(String(100))
    resume_document_url: Mapped[str] = mapped_column(Text, nullable=False)  # Stores direct or bucket URL
    extracted_skills_raw = mapped_column(JSONB, nullable=True)
    review_status: Mapped[str] = mapped_column(String(20), default="pending_review")
    reviewed_by: Mapped[Optional[str]] = mapped_column(String(100))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    role: Mapped[str] = mapped_column(String(20), default="intern", nullable=False)
    current_status: Mapped[str] = mapped_column(String(20), default="AVAILABLE", nullable=False)

class InternSkill(Base):
    __tablename__ = "intern_skills"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    intern_id: Mapped[UUID] = mapped_column(ForeignKey("interns_and_students.intern_id"), nullable=False)
    skill_id: Mapped[UUID] = mapped_column(ForeignKey("skills.skill_id"), nullable=False)
    proficiency_level: Mapped[float] = mapped_column(Float, default=1.0)
    extraction_confidence: Mapped[float] = mapped_column(Float, default=0.85)