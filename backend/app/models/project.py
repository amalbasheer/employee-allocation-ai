# app/models/project.py
import uuid
from typing import TYPE_CHECKING
from datetime import date
from typing import Optional, List
from sqlalchemy import Column, String, Integer, Text, Date, Boolean, ForeignKey, Enum as SQLEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import ARRAY, FLOAT
from app.database import Base
from pgvector.sqlalchemy import Vector
from app.models.enums import ProjectStatus
if TYPE_CHECKING:
    from app.models.allocation import Allocation
from app.models.taxonomy import Skill

class Project(Base):
    __tablename__ = "projects"

    project_id = Column(String(20), primary_key=True) 
    title: Mapped[str] = mapped_column(String(150), nullable=False)
    project_type: Mapped[str] = mapped_column(String(30), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    start_date: Mapped[date] = mapped_column(Date, nullable=False)
    end_date: Mapped[date] = mapped_column(Date, nullable=False)
    required_hours_per_week: Mapped[int] = mapped_column(Integer, nullable=False)
    priority_level: Mapped[str] = mapped_column(String(20), default="Medium")
    category: Mapped[str] = mapped_column(String(30), default="General")
    status = Column(String(10), nullable=False)

    # Relationships
    allocations = relationship("Allocation", primaryjoin="and_("
                "Project.project_id == foreign(Allocation.reference_id), "
                "Allocation.reference_type == 'project'"
                ")", back_populates="project")
    requirements: Mapped[List["ProjectRequirement"]] = relationship("ProjectRequirement", back_populates="project", cascade="all, delete-orphan")


class ProjectRequirement(Base):
    __tablename__ = "project_requirements"

    requirement_id = Column(String(20), primary_key=True)
    project_id = Column(String(20), ForeignKey("projects.project_id", ondelete="CASCADE"), nullable=False)
    skill_id = Column(String(20), ForeignKey("skills.skill_id", ondelete="CASCADE"), nullable=False)
    min_proficiency: Mapped[int] = mapped_column(Integer, default=1)
    is_mandatory: Mapped[bool] = mapped_column(Boolean, default=True)
    requirement_embedding = Column(Vector(768), nullable=True)
    # Relationship
    project: Mapped["Project"] = relationship("Project", back_populates="requirements")
    skill: Mapped["Skill"] = relationship("Skill")