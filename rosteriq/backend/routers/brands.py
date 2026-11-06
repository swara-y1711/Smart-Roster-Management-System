from typing import Optional
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, Query, status
from supabase import Client
from app.auth import get_db, get_current_user, AuthenticatedUser
from database import handle_supabase_error
from models.schemas import (
    BrandCreate,
    BrandUpdate,
    BrandResponse,
    MessageResponse
)

router = APIRouter(prefix="/brands", tags=["Brands"])

@router.get("", response_model=list[BrandResponse], summary="List authorized brands")
def list_brands(
    organization_id: Optional[UUID] = Query(None, description="Filter brands by organization ID"),
    db: Client = Depends(get_db),
    user: AuthenticatedUser = Depends(get_current_user)
):
    """Retrieve all brands accessible to the authenticated manager, optionally filtered by organization."""
    try:
        query = db.table("brands").select("*")
        if organization_id:
            query = query.eq("organization_id", str(organization_id))
        res = query.order("created_at").execute()
        return res.data or []
    except Exception as e:
        handle_supabase_error(e, "Brand")

@router.get("/{id}", response_model=BrandResponse, summary="Get brand by ID")
def get_brand(
    id: UUID,
    db: Client = Depends(get_db),
    user: AuthenticatedUser = Depends(get_current_user)
):
    """Retrieve a specific brand by ID."""
    try:
        res = db.table("brands").select("*").eq("id", str(id)).execute()
        if not res.data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Brand {id} not found or access denied."
            )
        return res.data[0]
    except Exception as e:
        handle_supabase_error(e, "Brand")

@router.post("", response_model=BrandResponse, status_code=status.HTTP_201_CREATED, summary="Create brand")
def create_brand(
    payload: BrandCreate,
    db: Client = Depends(get_db),
    user: AuthenticatedUser = Depends(get_current_user)
):
    """Create a new brand within an authorized organization."""
    # Verify organization accessibility first for a clearer error message
    org_check = db.table("organizations").select("id").eq("id", str(payload.organization_id)).execute()
    if not org_check.data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Organization {payload.organization_id} not found or you are not a member."
        )

    insert_data = {
        "organization_id": str(payload.organization_id),
        "name": payload.name,
        "industry": payload.industry,
        "description": payload.description
    }
    try:
        res = db.table("brands").insert(insert_data).execute()
        if not res.data:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Failed to create brand."
            )
        return res.data[0]
    except Exception as e:
        handle_supabase_error(e, "Brand")

@router.patch("/{id}", response_model=BrandResponse, summary="Update brand")
@router.put("/{id}", response_model=BrandResponse, summary="Update brand")
def update_brand(
    id: UUID,
    payload: BrandUpdate,
    db: Client = Depends(get_db),
    user: AuthenticatedUser = Depends(get_current_user)
):
    """Update brand information."""
    update_data = payload.model_dump(exclude_unset=True)
    if not update_data:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No fields provided for update."
        )
    try:
        res = db.table("brands").update(update_data).eq("id", str(id)).execute()
        if not res.data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Brand {id} not found or access denied."
            )
        return res.data[0]
    except Exception as e:
        handle_supabase_error(e, "Brand")

@router.delete("/{id}", response_model=MessageResponse, summary="Delete brand")
def delete_brand(
    id: UUID,
    db: Client = Depends(get_db),
    user: AuthenticatedUser = Depends(get_current_user)
):
    """Delete a brand and cascading processes/pods."""
    try:
        res = db.table("brands").delete().eq("id", str(id)).execute()
        if not res.data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Brand {id} not found or access denied."
            )
        return MessageResponse(
            message=f"Brand {id} deleted successfully.",
            id=id
        )
    except Exception as e:
        handle_supabase_error(e, "Brand")
