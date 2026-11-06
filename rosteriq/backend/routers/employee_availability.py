from typing import Optional
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, Query, status
from supabase import Client
from app.auth import get_db, get_current_user, AuthenticatedUser
from database import handle_supabase_error
from models.schemas import (
    EmployeeAvailabilityCreate,
    EmployeeAvailabilityUpdate,
    EmployeeAvailabilityResponse,
    MessageResponse
)

router = APIRouter(prefix="/employee-availability", tags=["Employee Availability"])

@router.get("", response_model=list[EmployeeAvailabilityResponse], summary="List employee availability")
def list_employee_availability(
    employee_id: Optional[UUID] = Query(None, description="Filter availability by employee ID"),
    db: Client = Depends(get_db),
    user: AuthenticatedUser = Depends(get_current_user)
):
    """Retrieve employee availability records, optionally filtered by employee ID."""
    try:
        query = db.table("employee_availability").select("*")
        if employee_id:
            query = query.eq("employee_id", str(employee_id))
        res = query.order("day_of_week").execute()
        return res.data or []
    except Exception as e:
        handle_supabase_error(e, "Employee Availability")

@router.get("/{id}", response_model=EmployeeAvailabilityResponse, summary="Get availability by ID")
def get_employee_availability(
    id: UUID,
    db: Client = Depends(get_db),
    user: AuthenticatedUser = Depends(get_current_user)
):
    """Retrieve a specific employee availability record."""
    try:
        res = db.table("employee_availability").select("*").eq("id", str(id)).execute()
        if not res.data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Employee availability {id} not found or access denied."
            )
        return res.data[0]
    except Exception as e:
        handle_supabase_error(e, "Employee Availability")

@router.post("", response_model=EmployeeAvailabilityResponse, status_code=status.HTTP_201_CREATED, summary="Create availability record")
def create_employee_availability(
    payload: EmployeeAvailabilityCreate,
    db: Client = Depends(get_db),
    user: AuthenticatedUser = Depends(get_current_user)
):
    """Create an availability record for an employee."""
    # Verify employee exists and is in user's organization
    emp_check = db.table("employees").select("id").eq("id", str(payload.employee_id)).execute()
    if not emp_check.data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Employee {payload.employee_id} not found or you do not have permission."
        )

    insert_data = {
        "employee_id": str(payload.employee_id),
        "day_of_week": payload.day_of_week,
        "start_time": payload.start_time,
        "end_time": payload.end_time,
        "is_available": payload.is_available if payload.is_available is not None else True
    }
    try:
        res = db.table("employee_availability").insert(insert_data).execute()
        if not res.data:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Failed to create employee availability."
            )
        return res.data[0]
    except Exception as e:
        handle_supabase_error(e, "Employee Availability")

@router.patch("/{id}", response_model=EmployeeAvailabilityResponse, summary="Update availability record")
@router.put("/{id}", response_model=EmployeeAvailabilityResponse, summary="Update availability record")
def update_employee_availability(
    id: UUID,
    payload: EmployeeAvailabilityUpdate,
    db: Client = Depends(get_db),
    user: AuthenticatedUser = Depends(get_current_user)
):
    """Update an employee availability record."""
    update_data = payload.model_dump(exclude_unset=True)
    if not update_data:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No fields provided for update."
        )
    try:
        res = db.table("employee_availability").update(update_data).eq("id", str(id)).execute()
        if not res.data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Employee availability {id} not found or access denied."
            )
        return res.data[0]
    except Exception as e:
        handle_supabase_error(e, "Employee Availability")

@router.delete("/{id}", response_model=MessageResponse, summary="Delete availability record")
def delete_employee_availability(
    id: UUID,
    db: Client = Depends(get_db),
    user: AuthenticatedUser = Depends(get_current_user)
):
    """Delete an employee availability record."""
    try:
        res = db.table("employee_availability").delete().eq("id", str(id)).execute()
        if not res.data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Employee availability {id} not found or access denied."
            )
        return MessageResponse(
            message=f"Employee availability {id} deleted successfully.",
            id=id
        )
    except Exception as e:
        handle_supabase_error(e, "Employee Availability")
