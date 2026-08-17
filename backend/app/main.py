# app/main.py
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from . import models  # Ensures all SQLAlchemy models are registered in Base.metadata
from app.api.router import api_router
from app.database import init_db


# Modern lifespan handler replaces @app.on_event("startup")
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup actions
    init_db()
    yield
    # Shutdown actions (if any cleanup is needed in the future)


app = FastAPI(
    title="Employee & Intern Allocation AI Platform",
    description="Backend API for managing skill taxonomies, employee resources, intern parsing, and allocation engines.",
    version="1.0.0",
    lifespan=lifespan,
)

# Define allowed origins (Frontend URLs)
origins = [
    "http://localhost:5173",  # Vite default
    "http://127.0.0.1:5173",
    "http://localhost:3000",  # React / Next.js default
    "http://127.0.0.1:3000",
    "*"                       # Allow all origins for development
]

# Enable CORS for frontend integration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register central API router under /api
app.include_router(api_router, prefix="/api")


@app.get("/")
def root():
    return {"message": "Employee Allocation AI API is running!"}

@app.get("/test-json")
def test_json():
    return {"status": "success", "message": "Connection working"}