from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status
from supabase import Client
from app.auth import get_db, get_current_user, AuthenticatedUser
from database import handle_supabase_error
from models.schemas import (
    OrganizationCreate,
    OrganizationUpdate,
    OrganizationResponse,
    MessageResponse
)

router = APIRouter(prefix="/organizations", tags=["Organizations"])

@router.get("", response_model=list[OrganizationResponse], summary="List authorized organizations")
def list_organizations(
    db: Client = Depends(get_db),
    user: AuthenticatedUser = Depends(get_current_user)
):
    """Retrieve all organizations that the authenticated manager belongs to."""
    try:
        res = db.table("organizations").select("*").order("created_at").execute()
        return res.data or []
    except Exception as e:
        handle_supabase_error(e, "Organization")

@router.get("/{id}", response_model=OrganizationResponse, summary="Get organization by ID")
def get_organization(
    id: UUID,
    db: Client = Depends(get_db),
    user: AuthenticatedUser = Depends(get_current_user)
):
    """Retrieve a specific organization by ID."""
    try:
        res = db.table("organizations").select("*").eq("id", str(id)).execute()
        if not res.data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Organization {id} not found or access denied."
            )
        return res.data[0]
    except Exception as e:
        handle_supabase_error(e, "Organization")

@router.post("", response_model=OrganizationResponse, status_code=status.HTTP_201_CREATED, summary="Create new organization")
def create_organization(
    payload: OrganizationCreate,
    db: Client = Depends(get_db),
    user: AuthenticatedUser = Depends(get_current_user)
):
    """Create a new organization. The calling manager is automatically registered as a member."""
    try:
        # Try calling the custom RPC first
        rpc_res = db.rpc("create_organization", {"organization_name": payload.name}).execute()
        if rpc_res.data and len(rpc_res.data) > 0:
            return rpc_res.data[0]
    except Exception:
        # Fallback to direct insert (the DB trigger will add membership)
        pass

    try:
        res = db.table("organizations").insert({"name": payload.name}).execute()
        if not res.data:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Failed to create organization."
            )
        return res.data[0]
    except Exception as e:
        handle_supabase_error(e, "Organization")

@router.patch("/{id}", response_model=OrganizationResponse, summary="Update organization")
@router.put("/{id}", response_model=OrganizationResponse, summary="Update organization")
def update_organization(
    id: UUID,
    payload: OrganizationUpdate,
    db: Client = Depends(get_db),
    user: AuthenticatedUser = Depends(get_current_user)
):
    """Update organization details."""
    update_data = payload.model_dump(exclude_unset=True)
    if not update_data:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No fields provided for update."
        )
    try:
        res = db.table("organizations").update(update_data).eq("id", str(id)).execute()
        if not res.data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Organization {id} not found or access denied."
            )
        return res.data[0]
    except Exception as e:
        handle_supabase_error(e, "Organization")

@router.delete("/{id}", response_model=MessageResponse, summary="Delete organization")
def delete_organization(
    id: UUID,
    db: Client = Depends(get_db),
    user: AuthenticatedUser = Depends(get_current_user)
):
    """Delete an organization and all its cascade-dependent entities."""
    try:
        res = db.table("organizations").delete().eq("id", str(id)).execute()
        if not res.data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Organization {id} not found or access denied."
            )
        return MessageResponse(
            message=f"Organization {id} deleted successfully.",
            id=id
        )
    except Exception as e:
        handle_supabase_error(e, "Organization")
