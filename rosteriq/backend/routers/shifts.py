from typing import Optional
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, Query, status
from supabase import Client
from app.auth import get_db, get_current_user, AuthenticatedUser
from database import handle_supabase_error
from models.schemas import (
    ShiftCreate,
    ShiftUpdate,
    ShiftResponse,
    MessageResponse
)

router = APIRouter(prefix="/shifts", tags=["Shifts"])

@router.get("", response_model=list[ShiftResponse], summary="List authorized shifts")
def list_shifts(
    pod_id: Optional[UUID] = Query(None, description="Filter shifts by pod ID"),
    db: Client = Depends(get_db),
    user: AuthenticatedUser = Depends(get_current_user)
):
    """Retrieve all shifts accessible to the manager, optionally filtered by pod."""
    try:
        query = db.table("shifts").select("*")
        if pod_id:
            query = query.eq("pod_id", str(pod_id))
        res = query.order("start_time").execute()
        return res.data or []
    except Exception as e:
        handle_supabase_error(e, "Shift")

@router.get("/{id}", response_model=ShiftResponse, summary="Get shift by ID")
def get_shift(
    id: UUID,
    db: Client = Depends(get_db),
    user: AuthenticatedUser = Depends(get_current_user)
):
    """Retrieve a specific shift by ID."""
    try:
        res = db.table("shifts").select("*").eq("id", str(id)).execute()
        if not res.data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Shift {id} not found or access denied."
            )
        return res.data[0]
    except Exception as e:
        handle_supabase_error(e, "Shift")

@router.post("", response_model=ShiftResponse, status_code=status.HTTP_201_CREATED, summary="Create shift")
def create_shift(
    payload: ShiftCreate,
    db: Client = Depends(get_db),
    user: AuthenticatedUser = Depends(get_current_user)
):
    """Create a new shift under an authorized pod."""
    # Verify pod exists and belongs to user
    pod_check = db.table("pods").select("id").eq("id", str(payload.pod_id)).execute()
    if not pod_check.data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Pod {payload.pod_id} not found or you do not have permission."
        )

    insert_data = {
        "pod_id": str(payload.pod_id),
        "shift_name": payload.shift_name,
        "start_time": payload.start_time,
        "end_time": payload.end_time,
        "required_headcount": payload.required_headcount if payload.required_headcount is not None else 1
    }
    try:
        res = db.table("shifts").insert(insert_data).execute()
        if not res.data:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Failed to create shift."
            )
        return res.data[0]
    except Exception as e:
        handle_supabase_error(e, "Shift")

@router.patch("/{id}", response_model=ShiftResponse, summary="Update shift")
@router.put("/{id}", response_model=ShiftResponse, summary="Update shift")
def update_shift(
    id: UUID,
    payload: ShiftUpdate,
    db: Client = Depends(get_db),
    user: AuthenticatedUser = Depends(get_current_user)
):
    """Update shift details."""
    update_data = payload.model_dump(exclude_unset=True)
    if not update_data:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No fields provided for update."
        )
    try:
        res = db.table("shifts").update(update_data).eq("id", str(id)).execute()
        if not res.data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Shift {id} not found or access denied."
            )
        return res.data[0]
    except Exception as e:
        handle_supabase_error(e, "Shift")

@router.delete("/{id}", response_model=MessageResponse, summary="Delete shift")
def delete_shift(
    id: UUID,
    db: Client = Depends(get_db),
    user: AuthenticatedUser = Depends(get_current_user)
):
    """Delete a shift."""
    try:
        res = db.table("shifts").delete().eq("id", str(id)).execute()
        if not res.data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Shift {id} not found or access denied."
            )
        return MessageResponse(
            message=f"Shift {id} deleted successfully.",
            id=id
        )
    except Exception as e:
        handle_supabase_error(e, "Shift")
