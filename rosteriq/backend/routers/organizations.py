from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status
from supabase import Client
from app.auth import get_db, get_current_user, AuthenticatedUser
from database import handle_supabase_error
from models.schemas import OrganizationResponse

router = APIRouter(prefix="/organizations", tags=["Organizations"])

@router.get("", response_model=list[OrganizationResponse], summary="List authorized organizations")
def list_organizations(
    db: Client = Depends(get_db),
    user: AuthenticatedUser = Depends(get_current_user)
):
    """Return the manager's authorized workforce datasets for internal API use."""
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
