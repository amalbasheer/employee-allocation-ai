# app/models/allocation.py
import uuid
from typing import TYPE_CHECKING
from datetime import datetime
from typing import Optional, List
from sqlalchemy import Column, String, Integer, func, Float, Text, DateTime, ForeignKey, Enum as SQLEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database import Base
from app.models.enums import AllocationStatus
if TYPE_CHECKING:
    from app.models.project import Project

class Allocation(Base):
    __tablename__ = "allocations"

    allocation_id = Column(String(20), primary_key=True)
    resource_type: Mapped[str] = mapped_column(String(20), nullable=False)  # "employee" or "student"
    resource_id = Column(String(20), nullable=False)
    project_id = Column(String(20), ForeignKey("projects.project_id"), nullable=False)
    role_on_project: Mapped[str] = mapped_column(String(50), default="lead_mentor")
    allocated_hours: Mapped[int] = mapped_column(Integer, nullable=False)
    suitability_score: Mapped[float] = mapped_column(Float, nullable=False)
    
    status: Mapped[AllocationStatus] = mapped_column(
        SQLEnum(AllocationStatus, name="allocation_status_enum", native_enum=False),
        default=AllocationStatus.PROPOSED,
        nullable=False
    )
    
    assigned_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    assigned_by: Mapped[str] = mapped_column(String(100), default="AI_Engine")

    # Relationships
    project: Mapped["Project"] = relationship("Project", back_populates="allocations")
    substitutions: Mapped[List["Substitution"]] = relationship("Substitution", back_populates="original_allocation")
    logs: Mapped[List["AllocationLog"]] = relationship("AllocationLog", back_populates="allocation", cascade="all, delete-orphan")


class Substitution(Base):
    __tablename__ = "substitutions"

    substitution_id = Column(String(20), primary_key=True)
    original_allocation_id = Column(String(20), ForeignKey("allocations.allocation_id"), nullable=False)
    substitute_resource_type: Mapped[str] = mapped_column(String(20), nullable=False)
    substitute_resource_id = Column(String(20), nullable=False)
    reason: Mapped[str] = mapped_column(Text, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    # Relationship
    original_allocation: Mapped["Allocation"] = relationship("Allocation", back_populates="substitutions")


class AllocationLog(Base):
    __tablename__ = "allocation_logs"

    log_id = Column(String(20), primary_key=True)
    allocation_id = Column(String(20), ForeignKey("allocations.allocation_id"), nullable=False)
    action: Mapped[str] = mapped_column(String(100), nullable=False)
    changed_by: Mapped[str] = mapped_column(String(100), nullable=False)
    timestamp = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    # Relationship
    allocation: Mapped["Allocation"] = relationship("Allocation", back_populates="logs")