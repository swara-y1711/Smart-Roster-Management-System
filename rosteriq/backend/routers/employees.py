from typing import Optional
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, Query, status
from supabase import Client
from app.auth import get_db, get_current_user, AuthenticatedUser
from database import handle_supabase_error
from models.schemas import (
    EmployeeCreate,
    EmployeeUpdate,
    EmployeeResponse,
    MessageResponse
)

router = APIRouter(prefix="/employees", tags=["Employees"])

@router.get("", response_model=list[EmployeeResponse], summary="List authorized employees")
def list_employees(
    organization_id: Optional[UUID] = Query(None, description="Filter by organization ID"),
    status_filter: Optional[str] = Query(None, alias="status", description="Filter by status (e.g. active, inactive)"),
    db: Client = Depends(get_db),
    user: AuthenticatedUser = Depends(get_current_user)
):
    """Retrieve all employees accessible to the manager, optionally filtered by organization and status."""
    try:
        query = db.table("employees").select("*")
        if organization_id:
            query = query.eq("organization_id", str(organization_id))
        if status_filter:
            query = query.eq("status", status_filter)
        res = query.order("first_name").execute()
        return res.data or []
    except Exception as e:
        handle_supabase_error(e, "Employee")

@router.get("/{id}", response_model=EmployeeResponse, summary="Get employee by ID")
def get_employee(
    id: UUID,
    db: Client = Depends(get_db),
    user: AuthenticatedUser = Depends(get_current_user)
):
    """Retrieve an employee by ID."""
    try:
        res = db.table("employees").select("*").eq("id", str(id)).execute()
        if not res.data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Employee {id} not found or access denied."
            )
        return res.data[0]
    except Exception as e:
        handle_supabase_error(e, "Employee")

@router.post("", response_model=EmployeeResponse, status_code=status.HTTP_201_CREATED, summary="Create employee")
def create_employee(
    payload: EmployeeCreate,
    db: Client = Depends(get_db),
    user: AuthenticatedUser = Depends(get_current_user)
):
    """Create a new employee within an authorized organization."""
    # Verify organization exists and belongs to user
    org_check = db.table("organizations").select("id").eq("id", str(payload.organization_id)).execute()
    if not org_check.data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Organization {payload.organization_id} not found or you are not a member."
        )

    insert_data = {
        "organization_id": str(payload.organization_id),
        "employee_code": payload.employee_code,
        "first_name": payload.first_name,
        "last_name": payload.last_name,
        "email": payload.email,
        "phone": payload.phone,
        "employment_type": payload.employment_type or "full_time",
        "status": payload.status or "active",
        "max_hours_per_week": payload.max_hours_per_week if payload.max_hours_per_week is not None else 40.0,
        "designation": payload.designation
    }
    try:
        res = db.table("employees").insert(insert_data).execute()
        if not res.data:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Failed to create employee."
            )
        return res.data[0]
    except Exception as e:
        handle_supabase_error(e, "Employee")

@router.patch("/{id}", response_model=EmployeeResponse, summary="Update employee")
@router.put("/{id}", response_model=EmployeeResponse, summary="Update employee")
def update_employee(
    id: UUID,
    payload: EmployeeUpdate,
    db: Client = Depends(get_db),
    user: AuthenticatedUser = Depends(get_current_user)
):
    """Update employee details."""
    update_data = payload.model_dump(exclude_unset=True)
    if not update_data:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No fields provided for update."
        )
    try:
        res = db.table("employees").update(update_data).eq("id", str(id)).execute()
        if not res.data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Employee {id} not found or access denied."
            )
        return res.data[0]
    except Exception as e:
        handle_supabase_error(e, "Employee")

@router.delete("/{id}", response_model=MessageResponse, summary="Delete employee")
def delete_employee(
    id: UUID,
    db: Client = Depends(get_db),
    user: AuthenticatedUser = Depends(get_current_user)
):
    """Delete an employee and cascading associations."""
    try:
        res = db.table("employees").delete().eq("id", str(id)).execute()
        if not res.data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Employee {id} not found or access denied."
            )
        return MessageResponse(
            message=f"Employee {id} deleted successfully.",
            id=id
        )
    except Exception as e:
        handle_supabase_error(e, "Employee")
