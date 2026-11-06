from datetime import datetime, timezone
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.config import CORS_ORIGINS
from database import check_db_connection
from routers.auth import router as auth_router
from routers.organizations import router as organizations_router
from routers.brands import router as brands_router
from routers.processes import router as processes_router
from routers.pods import router as pods_router
from routers.employees import router as employees_router
from routers.employee_skills import router as employee_skills_router
from routers.employee_availability import router as employee_availability_router
from routers.shifts import router as shifts_router
from routers.roster_assignments import router as roster_assignments_router
from routers.employee_pods import router as employee_pods_router
from routers.scheduling import router as scheduling_router
from routers.scheduling_config import router as scheduling_config_router
from routers.sample_workforce import router as sample_workforce_router
from routers.dashboard import router as dashboard_router

app = FastAPI(
    title="RosterIQ API",
    description=(
        "FastAPI Backend for RosterIQ Smart Roster Management System.\n\n"
        "Features:\n"
        "- Full CRUD endpoints for Organizations, Brands, Processes, Pods, Employees, "
        "Skills, Availability, Shifts, and Roster Assignments.\n"
        "- Constraint-based monthly roster proposals, validation, and impact analysis.\n"
        "- Multi-tenant data isolation respecting Supabase Row Level Security (RLS).\n"
        "- JWT-based Manager authentication via Supabase Auth.\n"
        "- Foreign-key integrity validation and clear error responses."
    ),
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json"
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include entity routers
app.include_router(auth_router)
app.include_router(organizations_router)
app.include_router(brands_router)
app.include_router(processes_router)
app.include_router(pods_router)
app.include_router(employees_router)
app.include_router(employee_skills_router)
app.include_router(employee_availability_router)
app.include_router(shifts_router)
app.include_router(roster_assignments_router)
app.include_router(employee_pods_router)
app.include_router(scheduling_router)
app.include_router(scheduling_config_router)
app.include_router(sample_workforce_router)
app.include_router(dashboard_router)

@app.get("/", tags=["System"], summary="API Root")
def root():
    """Welcome and API documentation link."""
    return {
        "name": "RosterIQ API",
        "version": "1.0.0",
        "status": "online",
        "documentation": "/docs",
        "redoc": "/redoc"
    }

@app.get("/health", tags=["System"], summary="Health Check")
def health_check():
    """Service and database health check."""
    db_status = check_db_connection()
    return {
        "status": "healthy" if db_status.get("status") == "connected" else "degraded",
        "database": db_status,
        "timestamp": datetime.now(timezone.utc).isoformat()
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)
