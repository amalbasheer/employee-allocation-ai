# app/api/router.py
from fastapi import APIRouter
from app.api import (
    taxonomy, employees, interns, projects, allocations,
    allocation_logs, substitutions, chat_queries, designation_skills
)

api_router = APIRouter()

api_router.include_router(taxonomy.router, prefix="/taxonomy", tags=["Master Taxonomy"])
api_router.include_router(employees.router, prefix="/employees", tags=["Company Employees"])
api_router.include_router(interns.router, prefix="/interns", tags=["Interns & Students"])
api_router.include_router(projects.router, prefix="/projects", tags=["Projects"])
api_router.include_router(allocations.router, prefix="/allocations", tags=["Allocations"])
api_router.include_router(allocation_logs.router, prefix="/logs", tags=["Allocation History Logs"])
api_router.include_router(substitutions.router, prefix="/substitutions", tags=["Resource Substitutions"])
api_router.include_router(chat_queries.router, prefix="/chat-queries", tags=["Chat & Audit Queries"])
api_router.include_router(designation_skills.router, prefix="/designation-skills", tags=["Designation Skills Mapping"])