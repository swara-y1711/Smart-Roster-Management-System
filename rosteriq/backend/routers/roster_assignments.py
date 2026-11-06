from datetime import date
from typing import Optional
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, Query, status
from supabase import Client
from app.auth import get_db, get_current_user, AuthenticatedUser
from database import handle_supabase_error
from models.schemas import (
    RosterAssignmentCreate,
    RosterAssignmentUpdate,
    RosterAssignmentResponse,
    MessageResponse
)

router = APIRouter(prefix="/roster-assignments", tags=["Roster Assignments"])

@router.get("", response_model=list[RosterAssignmentResponse], summary="List roster assignments")
def list_roster_assignments(
    employee_id: Optional[UUID] = Query(None, description="Filter by employee ID"),
    shift_id: Optional[UUID] = Query(None, description="Filter by shift ID"),
    assignment_date: Optional[date] = Query(None, description="Filter by assignment date (YYYY-MM-DD)"),
    db: Client = Depends(get_db),
    user: AuthenticatedUser = Depends(get_current_user)
):
    """Retrieve roster assignments accessible to the manager with optional filters."""
    try:
        query = db.table("roster_assignments").select("*")
        if employee_id:
            query = query.eq("employee_id", str(employee_id))
        if shift_id:
            query = query.eq("shift_id", str(shift_id))
        if assignment_date:
            query = query.eq("assignment_date", assignment_date.isoformat())
        res = query.order("assignment_date").execute()
        return res.data or []
    except Exception as e:
        handle_supabase_error(e, "Roster Assignment")

@router.get("/{id}", response_model=RosterAssignmentResponse, summary="Get roster assignment by ID")
def get_roster_assignment(
    id: UUID,
    db: Client = Depends(get_db),
    user: AuthenticatedUser = Depends(get_current_user)
):
    """Retrieve a specific roster assignment by ID."""
    try:
        res = db.table("roster_assignments").select("*").eq("id", str(id)).execute()
        if not res.data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Roster assignment {id} not found or access denied."
            )
        return res.data[0]
    except Exception as e:
        handle_supabase_error(e, "Roster Assignment")

@router.post("", response_model=RosterAssignmentResponse, status_code=status.HTTP_201_CREATED, summary="Create roster assignment")
def create_roster_assignment(
    payload: RosterAssignmentCreate,
    db: Client = Depends(get_db),
    user: AuthenticatedUser = Depends(get_current_user)
):
    """Assign an employee to a shift for a specific date."""
    # 1. Verify employee exists and is accessible
    emp_check = db.table("employees").select("id").eq("id", str(payload.employee_id)).execute()
    if not emp_check.data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Employee {payload.employee_id} not found or you do not have permission."
        )

    # 2. Verify shift exists and is accessible
    shift_check = db.table("shifts").select("id").eq("id", str(payload.shift_id)).execute()
    if not shift_check.data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Shift {payload.shift_id} not found or you do not have permission."
        )

    insert_data = {
        "employee_id": str(payload.employee_id),
        "shift_id": str(payload.shift_id),
        "assignment_date": payload.assignment_date.isoformat(),
        "status": payload.status or "scheduled"
    }
    try:
        res = db.table("roster_assignments").insert(insert_data).execute()
        if not res.data:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Failed to create roster assignment."
            )
        return res.data[0]
    except Exception as e:
        handle_supabase_error(e, "Roster Assignment")

@router.patch("/{id}", response_model=RosterAssignmentResponse, summary="Update roster assignment")
@router.put("/{id}", response_model=RosterAssignmentResponse, summary="Update roster assignment")
def update_roster_assignment(
    id: UUID,
    payload: RosterAssignmentUpdate,
    db: Client = Depends(get_db),
    user: AuthenticatedUser = Depends(get_current_user)
):
    """Update a roster assignment."""
    update_data = payload.model_dump(exclude_unset=True)
    if not update_data:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No fields provided for update."
        )
    # Convert dates or UUIDs to string for Supabase payload
    if "assignment_date" in update_data and isinstance(update_data["assignment_date"], date):
        update_data["assignment_date"] = update_data["assignment_date"].isoformat()
    if "employee_id" in update_data and update_data["employee_id"]:
        update_data["employee_id"] = str(update_data["employee_id"])
    if "shift_id" in update_data and update_data["shift_id"]:
        update_data["shift_id"] = str(update_data["shift_id"])

    try:
        res = db.table("roster_assignments").update(update_data).eq("id", str(id)).execute()
        if not res.data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Roster assignment {id} not found or access denied."
            )
        return res.data[0]
    except Exception as e:
        handle_supabase_error(e, "Roster Assignment")

@router.delete("/{id}", response_model=MessageResponse, summary="Delete roster assignment")
def delete_roster_assignment(
    id: UUID,
    db: Client = Depends(get_db),
    user: AuthenticatedUser = Depends(get_current_user)
):
    """Delete a roster assignment."""
    try:
        res = db.table("roster_assignments").delete().eq("id", str(id)).execute()
        if not res.data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Roster assignment {id} not found or access denied."
            )
        return MessageResponse(
            message=f"Roster assignment {id} deleted successfully.",
            id=id
        )
    except Exception as e:
        handle_supabase_error(e, "Roster Assignment")
