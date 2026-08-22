# app/models/taxonomy.py
from typing import Optional, TYPE_CHECKING, List
from uuid import UUID, uuid4
from pgvector.sqlalchemy import Vector
from sqlalchemy import Column, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database import Base



class Skill(Base):
    __tablename__ = "skills"

    skill_id = Column(String(20), primary_key=True)
    name: Mapped[str] = mapped_column("skill_name", String(100), unique=True, nullable=False)
    category: Mapped[Optional[str]] = mapped_column("category", String(50), nullable=True, default=None)
    skill_embedding = mapped_column(Vector(768), nullable=True)



class Designation(Base):
    __tablename__ = "designations"

    designation_id = Column(String(20), primary_key=True)
    title: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    department: Mapped[str] = mapped_column(String(50), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text)


