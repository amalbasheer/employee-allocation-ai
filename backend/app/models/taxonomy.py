import uuid
from typing import Optional
from sqlalchemy import String, Text, Integer, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column
from app.database import Base

class Designation(Base):
    __tablename__ = "designations"

    designation_id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    title: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    department: Mapped[str] = mapped_column(String(50), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text)

class Skill(Base):
    __tablename__ = "skills"

    skill_id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    skill_name: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    category: Mapped[Optional[str]] = mapped_column(String(50))

class DesignationSkill(Base):
    __tablename__ = "designation_skills"

    designation_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("designations.designation_id", ondelete="CASCADE"), primary_key=True)
    skill_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("skills.skill_id", ondelete="CASCADE"), primary_key=True)
    default_proficiency: Mapped[int] = mapped_column(Integer, default=3)