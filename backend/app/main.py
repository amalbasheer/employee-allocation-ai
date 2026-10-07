# app/main.py
from fastapi.concurrency import asynccontextmanager

import app.models
from importlib import import_module
import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[2]
if str(ROOT_DIR) not in sys.path:
    sys.path.append(str(ROOT_DIR))

from app.api.router import api_router
from app.api.training_sync import sync_completed_trainings_and_allocations
from app.database import SessionLocal
from dotenv import load_dotenv
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from apscheduler.schedulers.background import BackgroundScheduler


load_dotenv()

# 1. Initialize Scheduler
scheduler = BackgroundScheduler()

# 2. Define Helper Job
def run_training_sync_job():
    """Background wrapper that opens/closes its own DB session."""
    db = SessionLocal()
    try:
        res = sync_completed_trainings_and_allocations(db)
        print(f"[Cron Job] Sync complete: {res}")
    except Exception as e:
        db.rollback()
        print(f"[Cron Job Error] Sync failed: {e}")
    finally:
        db.close()

# 3. Define Lifespan Manager
@asynccontextmanager
async def lifespan(app: FastAPI):
    # --- Startup ---
    run_training_sync_job()  # Run sync on startup
    scheduler.add_job(run_training_sync_job, "interval", minutes=1)  # Run every minute (for testing)
    scheduler.start()
    app.state.scheduler = scheduler  # Store scheduler in app state for potential future use
    
    yield  # Application runs
    
    # --- Shutdown ---
    app.state.scheduler.shutdown()
    
app = FastAPI(
    title="Employee & Intern Allocation AI Platform",
    description="Backend API for managing skill taxonomies, employee resources, intern parsing, and allocation engines.",
    version="1.0.0",
    lifespan=lifespan
)


# Enable CORS for frontend integration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*", "https://main.d12rtouuvuicy7.amplifyapp.com", 
                   "https://employee-allocation-ai.onrender.com",
                   "http://localhost:3000",
                   "http://localhost:5173",
                   "http://localhost:8000", 
                   "http://localhost:5174"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    print(f"CRITICAL BACKEND ERROR ON {request.url}: {exc}")

    # Let CORSMiddleware handle headers automatically
    return JSONResponse(
        status_code=500,
        content={
            "detail": "Internal Server Error",
            "error_type": str(type(exc).__name__),
        },
    )


@app.get("/")
def root():
    return {"message": "Employee Allocation AI API is running on AWS Lambda!"}


@app.get("/test-json")
def test_json():
    return {"status": "success", "message": "Connection working"}


# Register central API router under /api
app.include_router(api_router, prefix="/api")



