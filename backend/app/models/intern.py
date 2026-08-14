# app/models/intern.py
from sqlalchemy import String, Float, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column
from uuid import uuid4, UUID
from app.database import Base

class InternsAndStudents(Base):
    __tablename__ = "interns_and_students"

    intern_id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    email: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    college_university: Mapped[str] = mapped_column(String(150), nullable=True)
    resume_url: Mapped[str] = mapped_column(String(255), nullable=True)

class InternSkill(Base):
    __tablename__ = "intern_skills"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    intern_id: Mapped[UUID] = mapped_column(ForeignKey("interns_and_students.intern_id"), nullable=False)
    skill_id: Mapped[UUID] = mapped_column(ForeignKey("skills.skill_id"), nullable=False)
    proficiency_level: Mapped[float] = mapped_column(Float, default=1.0)