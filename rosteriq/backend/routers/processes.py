from typing import Optional
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, Query, status
from supabase import Client
from app.auth import get_db, get_current_user, AuthenticatedUser
from database import handle_supabase_error
from models.schemas import (
    ProcessCreate,
    ProcessUpdate,
    ProcessResponse,
    MessageResponse
)

router = APIRouter(prefix="/processes", tags=["Processes"])

@router.get("", response_model=list[ProcessResponse], summary="List authorized processes")
def list_processes(
    brand_id: Optional[UUID] = Query(None, description="Filter processes by brand ID"),
    db: Client = Depends(get_db),
    user: AuthenticatedUser = Depends(get_current_user)
):
    """Retrieve all processes accessible to the manager, optionally filtered by brand."""
    try:
        query = db.table("processes").select("*")
        if brand_id:
            query = query.eq("brand_id", str(brand_id))
        res = query.order("created_at").execute()
        return res.data or []
    except Exception as e:
        handle_supabase_error(e, "Process")

@router.get("/{id}", response_model=ProcessResponse, summary="Get process by ID")
def get_process(
    id: UUID,
    db: Client = Depends(get_db),
    user: AuthenticatedUser = Depends(get_current_user)
):
    """Retrieve a specific process by ID."""
    try:
        res = db.table("processes").select("*").eq("id", str(id)).execute()
        if not res.data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Process {id} not found or access denied."
            )
        return res.data[0]
    except Exception as e:
        handle_supabase_error(e, "Process")

@router.post("", response_model=ProcessResponse, status_code=status.HTTP_201_CREATED, summary="Create process")
def create_process(
    payload: ProcessCreate,
    db: Client = Depends(get_db),
    user: AuthenticatedUser = Depends(get_current_user)
):
    """Create a new process under an authorized brand."""
    # Verify brand exists and belongs to the manager's authorized organization
    brand_check = db.table("brands").select("id").eq("id", str(payload.brand_id)).execute()
    if not brand_check.data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Brand {payload.brand_id} not found or you do not have permission."
        )

    insert_data = {
        "brand_id": str(payload.brand_id),
        "name": payload.name,
        "description": payload.description
    }
    try:
        res = db.table("processes").insert(insert_data).execute()
        if not res.data:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Failed to create process."
            )
        return res.data[0]
    except Exception as e:
        handle_supabase_error(e, "Process")

@router.patch("/{id}", response_model=ProcessResponse, summary="Update process")
@router.put("/{id}", response_model=ProcessResponse, summary="Update process")
def update_process(
    id: UUID,
    payload: ProcessUpdate,
    db: Client = Depends(get_db),
    user: AuthenticatedUser = Depends(get_current_user)
):
    """Update process information."""
    update_data = payload.model_dump(exclude_unset=True)
    if not update_data:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No fields provided for update."
        )
    try:
        res = db.table("processes").update(update_data).eq("id", str(id)).execute()
        if not res.data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Process {id} not found or access denied."
            )
        return res.data[0]
    except Exception as e:
        handle_supabase_error(e, "Process")

@router.delete("/{id}", response_model=MessageResponse, summary="Delete process")
def delete_process(
    id: UUID,
    db: Client = Depends(get_db),
    user: AuthenticatedUser = Depends(get_current_user)
):
    """Delete a process and its pods."""
    try:
        res = db.table("processes").delete().eq("id", str(id)).execute()
        if not res.data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Process {id} not found or access denied."
            )
        return MessageResponse(
            message=f"Process {id} deleted successfully.",
            id=id
        )
    except Exception as e:
        handle_supabase_error(e, "Process")
