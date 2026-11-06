from typing import Optional
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, Query, status
from supabase import Client
from app.auth import get_db, get_current_user, AuthenticatedUser
from database import handle_supabase_error
from models.schemas import (
    EmployeePodCreate,
    EmployeePodResponse,
    MessageResponse
)

router = APIRouter(prefix="/employee-pods", tags=["Employee Pods"])

@router.get("", response_model=list[EmployeePodResponse], summary="List employee pod associations")
def list_employee_pods(
    employee_id: Optional[UUID] = Query(None, description="Filter by employee ID"),
    pod_id: Optional[UUID] = Query(None, description="Filter by pod ID"),
    db: Client = Depends(get_db),
    user: AuthenticatedUser = Depends(get_current_user)
):
    """Retrieve employee-pod memberships."""
    try:
        query = db.table("employee_pods").select("*")
        if employee_id:
            query = query.eq("employee_id", str(employee_id))
        if pod_id:
            query = query.eq("pod_id", str(pod_id))
        res = query.execute()
        return res.data or []
    except Exception as e:
        handle_supabase_error(e, "Employee Pod")

@router.post("", response_model=EmployeePodResponse, status_code=status.HTTP_201_CREATED, summary="Assign employee to pod")
def create_employee_pod(
    payload: EmployeePodCreate,
    db: Client = Depends(get_db),
    user: AuthenticatedUser = Depends(get_current_user)
):
    """Assign an employee to a pod."""
    # Verify employee
    emp_check = db.table("employees").select("id").eq("id", str(payload.employee_id)).execute()
    if not emp_check.data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Employee {payload.employee_id} not found or access denied."
        )

    # Verify pod
    pod_check = db.table("pods").select("id").eq("id", str(payload.pod_id)).execute()
    if not pod_check.data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Pod {payload.pod_id} not found or access denied."
        )

    insert_data = {
        "employee_id": str(payload.employee_id),
        "pod_id": str(payload.pod_id),
        "is_primary": payload.is_primary if payload.is_primary is not None else False
    }
    try:
        res = db.table("employee_pods").insert(insert_data).execute()
        if not res.data:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Failed to assign employee to pod."
            )
        return res.data[0]
    except Exception as e:
        handle_supabase_error(e, "Employee Pod")

@router.delete("", response_model=MessageResponse, summary="Remove employee from pod")
def delete_employee_pod(
    employee_id: UUID = Query(..., description="Employee ID"),
    pod_id: UUID = Query(..., description="Pod ID"),
    db: Client = Depends(get_db),
    user: AuthenticatedUser = Depends(get_current_user)
):
    """Remove an employee assignment from a pod."""
    try:
        res = db.table("employee_pods").delete().eq("employee_id", str(employee_id)).eq("pod_id", str(pod_id)).execute()
        if not res.data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Employee pod assignment not found or access denied."
            )
        return MessageResponse(
            message=f"Employee {employee_id} removed from pod {pod_id}."
        )
    except Exception as e:
        handle_supabase_error(e, "Employee Pod")
