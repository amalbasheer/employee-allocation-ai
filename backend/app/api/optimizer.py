from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field
from typing import List

from ai_engine.optimizer_integration import (
    optimize_multiple_projects,
    optimize_multiple_trainings,
)

router = APIRouter()


# --- Request Schemas ---
class ProjectOptimizeRequest(BaseModel):
    project_ids: List[str] = Field(
        ..., 
        example=["proj-101", "proj-102"], 
        description="List of project IDs to optimize concurrently"
    )

class TrainingOptimizeRequest(BaseModel):
    engagement_ids: List[str] = Field(
        ..., 
        example=["rp2-train-0001", "rp2-train-0002"], 
        description="List of training engagement IDs to optimize concurrently"
    )


# --- API 1: Project Allocation Optimization ---
@router.post("/projects", summary="Optimize Project Team Lead & Intern Allocations")
async def api_optimize_projects(payload: ProjectOptimizeRequest):
    """
    Solves global assignment for team leads across multiple projects 
    simultaneously while attaching top intern suggestions.
    """
    if not payload.project_ids:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="project_ids list cannot be empty."
        )

    try:
        result = optimize_multiple_projects(payload.project_ids)
        return result
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Project optimization error: {str(e)}"
        )


# --- API 2: Training Engagement Speaker Optimization ---
@router.post("/trainings", summary="Optimize Speaker/Mentor Allocations for Training")
async def api_optimize_trainings(payload: TrainingOptimizeRequest):
    """
    Solves global assignment for training speakers/mentors across 
    multiple engagements simultaneously to prevent over-allocation.
    """
    if not payload.engagement_ids:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="engagement_ids list cannot be empty."
        )

    try:
        result = optimize_multiple_trainings(payload.engagement_ids)
        return result
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Training optimization error: {str(e)}"
        )