# app/models/project.py
import uuid
from typing import TYPE_CHECKING
from datetime import date
from typing import Optional, List
from sqlalchemy import Column, String, Integer, Text, Date, Boolean, ForeignKey, Enum as SQLEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import ARRAY, FLOAT
from app.database import Base
from app.models.enums import ProjectStatus
if TYPE_CHECKING:
    from app.models.allocation import Allocation

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
    
    status = Column(String(10), nullable=False)

    # Relationships
    allocations: Mapped["Allocation"] = relationship("Allocation", back_populates="project")
    requirements: Mapped[List["ProjectRequirement"]] = relationship("ProjectRequirement", back_populates="project", cascade="all, delete-orphan")


class ProjectRequirement(Base):
    __tablename__ = "project_requirements"

    requirement_id = Column(String(20), primary_key=True)
    project_id = Column(String(20), ForeignKey("projects.project_id", ondelete="CASCADE"), nullable=False)
    skill_id = Column(String(20), nullable=False)
    min_proficiency: Mapped[int] = mapped_column(Integer, default=1)
    is_mandatory: Mapped[bool] = mapped_column(Boolean, default=True)
    requirement_embedding: Mapped[Optional[List[float]]] = mapped_column(ARRAY(FLOAT), nullable=True)

    # Relationship
    project: Mapped["Project"] = relationship("Project", back_populates="requirements")