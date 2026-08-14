# app/models/taxonomy.py
from typing import Optional
from uuid import UUID, uuid4
from pgvector.sqlalchemy import Vector
from sqlalchemy import ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column
from app.database import Base


class Skill(Base):
    __tablename__ = "skills"

    skill_id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    name: Mapped[str] = mapped_column("skill_name", String(100), unique=True, nullable=False)
    category: Mapped[Optional[str]] = mapped_column("category", String(50), nullable=True, default=None)
    skill_embedding = mapped_column(Vector(768), nullable=True)


class Designation(Base):
    __tablename__ = "designations"

    designation_id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    title: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    department: Mapped[str] = mapped_column(String(50), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text)


class DesignationSkill(Base):
    __tablename__ = "designation_skills"

    designation_id: Mapped[UUID] = mapped_column(
        ForeignKey("designations.designation_id", ondelete="CASCADE"), 
        primary_key=True
    )
    skill_id: Mapped[UUID] = mapped_column(
        ForeignKey("skills.skill_id", ondelete="CASCADE"), 
        primary_key=True
    )
    default_proficiency: Mapped[int] = mapped_column(Integer, default=3)