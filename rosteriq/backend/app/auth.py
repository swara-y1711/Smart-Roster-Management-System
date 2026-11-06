import logging
from uuid import UUID
from typing import Optional, Tuple
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel
from supabase import Client
from database import get_supabase_client, get_user_supabase_client

logger = logging.getLogger(__name__)

security = HTTPBearer(
    scheme_name="BearerAuth",
    description="Pass Supabase access token (JWT) as 'Bearer <token>'",
    auto_error=True
)

class AuthenticatedUser(BaseModel):
    id: UUID
    email: Optional[str] = None
    role: Optional[str] = "authenticated"

def get_token(credentials: HTTPAuthorizationCredentials = Depends(security)) -> str:
    if not credentials or not credentials.credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing Bearer authentication token."
        )
    return credentials.credentials

def get_current_user(token: str = Depends(get_token)) -> AuthenticatedUser:
    """Validates the JWT token against Supabase Auth and returns user identity."""
    client = get_supabase_client()
    try:
        user_response = client.auth.get_user(token)
        if not user_response or not user_response.user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid or expired authentication credentials."
            )
        user = user_response.user
        return AuthenticatedUser(
            id=UUID(user.id),
            email=user.email,
            role=getattr(user, "role", "authenticated")
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.warning(f"Auth verification failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Authentication failed: {str(e)}"
        )

def get_db(token: str = Depends(get_token)) -> Client:
    """Returns a Supabase client scoped to the authenticated user's JWT to enforce RLS."""
    return get_user_supabase_client(token)

def get_current_user_and_db(
    user: AuthenticatedUser = Depends(get_current_user),
    db: Client = Depends(get_db)
) -> Tuple[AuthenticatedUser, Client]:
    """Convenience dependency returning both user identity and RLS-scoped db client."""
    return user, db
