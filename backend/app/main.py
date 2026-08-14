# app/main.py
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

import app.models
from app.api.router import api_router
from app.database import init_db


app = FastAPI(
    title="Employee & Intern Allocation AI Platform",
    description="Backend API for managing skill taxonomies, employee resources, intern parsing, and allocation engines.",
    version="1.0.0"
)

# Enable CORS for frontend integration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize database tables on startup
@app.on_event("startup")
def on_startup():
    init_db()

# Register central API router under /api
app.include_router(api_router, prefix="/api")

@app.get("/")
def root():
    return {"message": "Employee Allocation AI API is running!"}