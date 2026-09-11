# app/main.py
import app.models
from importlib import import_module
from app.api.router import api_router
from dotenv import load_dotenv
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

load_dotenv()

app = FastAPI(
    title="Employee & Intern Allocation AI Platform",
    description="Backend API for managing skill taxonomies, employee resources, intern parsing, and allocation engines.",
    version="1.0.0",
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

# AWS Lambda Handler with lifespan disabled for minimal cold-start times
handler = import_module("mangum").Mangum(app, lifespan="off")