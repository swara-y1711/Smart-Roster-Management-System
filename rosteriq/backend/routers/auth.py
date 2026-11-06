from fastapi import APIRouter, Depends, HTTPException, status
from supabase import Client
from app.auth import get_db, get_current_user, AuthenticatedUser
from database import handle_supabase_error
from models.schemas import ManagerProfileResponse

router = APIRouter(prefix="/auth", tags=["Authentication & Profile"])

@router.get("/me", response_model=ManagerProfileResponse, summary="Get current manager profile")
def get_current_profile(
    user: AuthenticatedUser = Depends(get_current_user),
    db: Client = Depends(get_db)
):
    """Retrieve the manager profile of the currently authenticated user."""
    try:
        res = db.table("manager_profiles").select("*").eq("id", str(user.id)).execute()
        if not res.data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Manager profile not found for the authenticated user."
            )
        return res.data[0]
    except Exception as e:
        handle_supabase_error(e, "ManagerProfile")
