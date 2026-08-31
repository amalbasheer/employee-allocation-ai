# app/api/router.py
from fastapi import APIRouter
from app.api import (
    auth, taxonomy, employees, interns, projects, allocations,
    chat_queries, dashboard, training, ai_project_helper, batches
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