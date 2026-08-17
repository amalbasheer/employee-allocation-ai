# backend/app/models/chat.py
import uuid
from datetime import datetime
from sqlalchemy import Column, String, Text, DateTime, func
from sqlalchemy.orm import Mapped, mapped_column
from app.database import Base

class ChatQuery(Base):
    __tablename__ = "chat_queries"

    query_id = Column(String(20), primary_key=True)
    user_id = Column(String(36), nullable=False)
    query_text: Mapped[str] = mapped_column(Text, nullable=False)
    response_text: Mapped[str] = mapped_column(Text, nullable=False)
    timestamp = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)