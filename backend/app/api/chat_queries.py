# app/api/chat_queries.py
from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session
from typing import List, Optional
from uuid import UUID

from app.api.deps import get_db
from app.models import ChatQuery
from app.schemas.chat_query import ChatQueryResponse, ChatQueryCreate

router = APIRouter()

@router.get("/", response_model=List[ChatQueryResponse])
def get_chat_history(
    user_id: Optional[UUID] = None,
    limit: int = 50,
    db: Session = Depends(get_db)
):
    """Retrieve chat history logs."""
    query = db.query(ChatQuery)
    if user_id:
        query = query.filter(ChatQuery.user_id == user_id)
    return query.order_by(ChatQuery.created_at.desc()).limit(limit).all()

@router.post("/", response_model=ChatQueryResponse, status_code=status.HTTP_201_CREATED)
def log_chat_query(query_in: ChatQueryCreate, db: Session = Depends(get_db)):
    """Save a user query and system response for audit/telemetry."""
    chat_log = ChatQuery(**query_in.model_dump())
    db.add(chat_log)
    db.commit()
    db.refresh(chat_log)
    return chat_log