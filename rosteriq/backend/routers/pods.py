from typing import Optional
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, Query, status
from supabase import Client
from app.auth import get_db, get_current_user, AuthenticatedUser
from database import handle_supabase_error
from models.schemas import (
    PodCreate,
    PodUpdate,
    PodResponse,
    MessageResponse
)

router = APIRouter(prefix="/pods", tags=["Pods"])

@router.get("", response_model=list[PodResponse], summary="List authorized pods")
def list_pods(
    process_id: Optional[UUID] = Query(None, description="Filter pods by process ID"),
    db: Client = Depends(get_db),
    user: AuthenticatedUser = Depends(get_current_user)
):
    """Retrieve all pods accessible to the manager, optionally filtered by process."""
    try:
        query = db.table("pods").select("*")
        if process_id:
            query = query.eq("process_id", str(process_id))
        res = query.order("created_at").execute()
        return res.data or []
    except Exception as e:
        handle_supabase_error(e, "Pod")

@router.get("/{id}", response_model=PodResponse, summary="Get pod by ID")
def get_pod(
    id: UUID,
    db: Client = Depends(get_db),
    user: AuthenticatedUser = Depends(get_current_user)
):
    """Retrieve a specific pod by ID."""
    try:
        res = db.table("pods").select("*").eq("id", str(id)).execute()
        if not res.data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Pod {id} not found or access denied."
            )
        return res.data[0]
    except Exception as e:
        handle_supabase_error(e, "Pod")

@router.post("", response_model=PodResponse, status_code=status.HTTP_201_CREATED, summary="Create pod")
def create_pod(
    payload: PodCreate,
    db: Client = Depends(get_db),
    user: AuthenticatedUser = Depends(get_current_user)
):
    """Create a new pod under an authorized process."""
    # Verify process belongs to authorized brand/org
    process_check = db.table("processes").select("id").eq("id", str(payload.process_id)).execute()
    if not process_check.data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Process {payload.process_id} not found or you do not have permission."
        )

    insert_data = {
        "process_id": str(payload.process_id),
        "name": payload.name,
        "description": payload.description
    }
    try:
        res = db.table("pods").insert(insert_data).execute()
        if not res.data:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Failed to create pod."
            )
        return res.data[0]
    except Exception as e:
        handle_supabase_error(e, "Pod")

@router.patch("/{id}", response_model=PodResponse, summary="Update pod")
@router.put("/{id}", response_model=PodResponse, summary="Update pod")
def update_pod(
    id: UUID,
    payload: PodUpdate,
    db: Client = Depends(get_db),
    user: AuthenticatedUser = Depends(get_current_user)
):
    """Update pod information."""
    update_data = payload.model_dump(exclude_unset=True)
    if not update_data:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No fields provided for update."
        )
    try:
        res = db.table("pods").update(update_data).eq("id", str(id)).execute()
        if not res.data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Pod {id} not found or access denied."
            )
        return res.data[0]
    except Exception as e:
        handle_supabase_error(e, "Pod")

@router.delete("/{id}", response_model=MessageResponse, summary="Delete pod")
def delete_pod(
    id: UUID,
    db: Client = Depends(get_db),
    user: AuthenticatedUser = Depends(get_current_user)
):
    """Delete a pod and its shifts."""
    try:
        res = db.table("pods").delete().eq("id", str(id)).execute()
        if not res.data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Pod {id} not found or access denied."
            )
        return MessageResponse(
            message=f"Pod {id} deleted successfully.",
            id=id
        )
    except Exception as e:
        handle_supabase_error(e, "Pod")
