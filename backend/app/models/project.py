# app/models/project.py
import uuid
from datetime import date
from typing import Optional, List
from sqlalchemy import String, Integer, Text, Date, Boolean, ForeignKey, Enum as SQLEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import ARRAY, FLOAT
from app.database import Base
from app.models.enums import ProjectStatus
from app.models.allocation import Allocation

class Project(Base):
    __tablename__ = "projects"

    project_id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    title: Mapped[str] = mapped_column(String(150), nullable=False)
    project_type: Mapped[str] = mapped_column(String(30), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    start_date: Mapped[date] = mapped_column(Date, nullable=False)
    end_date: Mapped[date] = mapped_column(Date, nullable=False)
    required_hours_per_week: Mapped[int] = mapped_column(Integer, nullable=False)
    priority_level: Mapped[str] = mapped_column(String(20), default="Medium")
    
    status: Mapped[ProjectStatus] = mapped_column(
        SQLEnum(ProjectStatus, name="project_status_enum", native_enum=False),
        default=ProjectStatus.OPEN,
        nullable=False
    )

    # Relationships
    allocations: Mapped[List["Allocation"]] = relationship("Allocation", back_populates="project", cascade="all, delete-orphan")
    requirements: Mapped[List["ProjectRequirement"]] = relationship("ProjectRequirement", back_populates="project", cascade="all, delete-orphan")


class ProjectRequirement(Base):
    __tablename__ = "project_requirements"

    requirement_id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    project_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("projects.project_id", ondelete="CASCADE"), nullable=False)
    skill_id: Mapped[uuid.UUID] = mapped_column(nullable=False)
    min_proficiency: Mapped[int] = mapped_column(Integer, default=1)
    is_mandatory: Mapped[bool] = mapped_column(Boolean, default=True)
    requirement_embedding: Mapped[Optional[List[float]]] = mapped_column(ARRAY(FLOAT), nullable=True)

    # Relationship
    project: Mapped["Project"] = relationship("Project", back_populates="requirements")