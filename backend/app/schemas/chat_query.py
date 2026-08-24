from typing import Optional, List, Any
from datetime import datetime
from pydantic import BaseModel, Field

class RecommendationItem(BaseModel):
    resource_id: Optional[str] = None
    name: str
    resource_type: str
    suitability_score: float
    reason: Optional[str] = None

class ChatQueryCreate(BaseModel):
    query: str
    user_id: Optional[str] = None

class ChatQueryResponse(BaseModel):
    id: str = Field(..., validation_alias="query_id")
    user_id: str
    query: str = Field(..., validation_alias="query_text", serialization_alias="query")
    response_text: str
    recommendations: Optional[List[RecommendationItem]] = []
    created_at: Optional[datetime] = Field(None, validation_alias="timestamp")

    class Config:
        from_attributes = True
        populate_by_name = True