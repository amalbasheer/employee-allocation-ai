# app/models/taxonomy.py
from sqlalchemy import String, Float, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column
from uuid import uuid4, UUID
from app.database import Base
from typing import Optional

class Skill(Base):
    __tablename__ = "skills"

    skill_id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    name: Mapped[str] = mapped_column("skill_name", String(100), unique=True, nullable=False)
    category: Mapped[Optional[str]] = mapped_column("category", String(50), nullable=True, default=None)


class Designation(Base):
    __tablename__ = "designations"

    designation_id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    title: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)

class DesignationSkill(Base):
    __tablename__ = "designation_skills"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    designation_id: Mapped[UUID] = mapped_column(ForeignKey("designations.designation_id"), nullable=False)
    skill_id: Mapped[UUID] = mapped_column(ForeignKey("skills.skill_id"), nullable=False)
    min_proficiency: Mapped[float] = mapped_column(Float, default=1.0)