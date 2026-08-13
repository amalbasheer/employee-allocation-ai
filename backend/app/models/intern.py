import uuid
from datetime import datetime
from typing import Optional
from sqlalchemy import String, Integer, Float, Text, DateTime, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.dialects.postgresql import JSONB
from pgvector.sqlalchemy import Vector
from app.database import Base

class InternAndStudent(Base):
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
    weekly_capacity_hours: Mapped[int] = mapped_column(Integer, default=20)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

class InternSkill(Base):
    __tablename__ = "intern_skills"

    intern_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("interns_and_students.intern_id", ondelete="CASCADE"), primary_key=True)
    skill_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("skills.skill_id", ondelete="CASCADE"), primary_key=True)
    proficiency_level: Mapped[int] = mapped_column(Integer, default=1)
    skill_embedding = mapped_column(Vector(768), nullable=True)  # 768-dim for Gemini
    extraction_confidence: Mapped[float] = mapped_column(Float, default=0.85)