# app/routers/dashboard.py
from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session
from app.database import get_db

router = APIRouter()

@router.get("/overview")
def get_dashboard_overview(db: Session = Depends(get_db)):
    # Replace mock counts with actual SQL queries (e.g., db.query(Allocation)...)
    return {
        "allocations_trend": {
            "categories": ["Jan", "Feb", "Mar", "Apr", "May", "Jun"],
            "series": [
                {"name": "Assigned", "data": [12, 19, 15, 25, 22, 30]},
                {"name": "Proposed", "data": [5, 8, 12, 6, 9, 4]}
            ]
        },
        "project_status": {
            "labels": ["In Progress", "Open", "Completed", "Cancelled"],
            "series": [14, 8, 22, 3]
        }
    }