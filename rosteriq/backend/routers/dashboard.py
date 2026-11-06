from typing import Any

from fastapi import APIRouter, Depends
from supabase import Client

from app.auth import AuthenticatedUser, get_current_user, get_db
from database import handle_supabase_error

router = APIRouter(prefix="/dashboard", tags=["Dashboard"])

DASHBOARD_TABLES = {
    "organizations": "organizations",
    "brands": "brands",
    "processes": "processes",
    "pods": "pods",
    "employees": "employees",
    "employeePods": "employee_pods",
    "employeeSkills": "employee_skills",
    "availability": "employee_availability",
    "shifts": "shifts",
    "assignments": "roster_assignments",
}


@router.get("", summary="Get all workforce records available to the manager")
def get_dashboard_data(
    db: Client = Depends(get_db),
    user: AuthenticatedUser = Depends(get_current_user),
) -> dict[str, list[dict[str, Any]]]:
    """Return records visible through the authenticated manager's existing RLS policies."""
    try:
        return {
            response_key: db.table(table).select("*").execute().data or []
            for response_key, table in DASHBOARD_TABLES.items()
        }
    except Exception as error:
        handle_supabase_error(error, "Dashboard")
