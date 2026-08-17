# app/schemas/chat_query.py
from pydantic import BaseModel
from typing import Optional
from uuid import UUID
from datetime import datetime

class ChatQueryBase(BaseModel):
    user_query: str
    processed_intent: Optional[str] = None
    response_payload: Optional[dict] = None
    user_id: Optional[str] = None

class ChatQueryCreate(ChatQueryBase):
    pass

class ChatQueryResponse(ChatQueryBase):
    query_id: str
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True