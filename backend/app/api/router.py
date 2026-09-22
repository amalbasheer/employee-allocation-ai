# app/api/router.py
from fastapi import APIRouter
from app.api import (
    auth, taxonomy, employees, interns, projects, allocations, optimizer, schedule,
    chat_queries, dashboard, training, ai_project_helper, batches, ai_event_helper,
    leave_requests,
)

api_router = APIRouter()

api_router.include_router(auth.router, prefix="/auth", tags=["Authentication"])
api_router.include_router(taxonomy.router, prefix="/taxonomy", tags=["Master Taxonomy"])
api_router.include_router(employees.router, prefix="/employees", tags=["Company Employees"])
api_router.include_router(interns.router, prefix="/interns", tags=["Interns & Students"])
api_router.include_router(projects.router, prefix="/projects", tags=["Projects"])
api_router.include_router(allocations.router, prefix="/allocations", tags=["Allocations"])
api_router.include_router(chat_queries.router, prefix="/chat-queries", tags=["Chat & Audit Queries"])
api_router.include_router(dashboard.router, prefix="/dashboard", tags=["Dashboard"])
api_router.include_router(training.router, prefix="/training", tags=["Training Management"])
api_router.include_router(ai_project_helper.router, prefix="/ai-projects", tags=["AI Project Generator"])
api_router.include_router(batches.router, prefix="/batches", tags=["Batches"])
api_router.include_router(ai_event_helper.router,prefix="/ai_events", tags=["Webinars & Workshops"])
api_router.include_router(optimizer.router, prefix="/optimize", tags=["Allocation Optimizer"])
api_router.include_router(schedule.router, prefix="/schedule", tags=["Weekly Schedule"])
api_router.include_router(leave_requests.router, prefix="/leave", tags=["Leave Requests"])