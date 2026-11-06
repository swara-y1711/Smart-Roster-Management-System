import logging
from typing import Optional
from fastapi import HTTPException, status
import psycopg
from postgrest.exceptions import APIError
from supabase import create_client, Client

try:
    import truststore
    truststore.inject_into_ssl()
except Exception:
    pass

from app.config import DATABASE_URL, SUPABASE_URL, SUPABASE_ANON_KEY

logger = logging.getLogger(__name__)

def check_db_connection() -> dict:
    """Verifies direct PostgreSQL connectivity via DATABASE_URL."""
    if not DATABASE_URL:
        return {"status": "unavailable", "message": "DATABASE_URL not configured"}
    try:
        with psycopg.connect(DATABASE_URL, connect_timeout=5) as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT 1;")
                return {"status": "connected", "result": cur.fetchone()[0]}
    except Exception as e:
        logger.error(f"Database connection error: {e}")
        return {"status": "error", "message": str(e)}

def get_supabase_client() -> Client:
    """Returns an anonymous Supabase client."""
    if not SUPABASE_URL or not SUPABASE_ANON_KEY:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Supabase credentials (SUPABASE_URL and SUPABASE_ANON_KEY) are not configured."
        )
    return create_client(SUPABASE_URL, SUPABASE_ANON_KEY)

def get_user_supabase_client(token: str) -> Client:
    """Returns a Supabase client scoped to the authenticated user's JWT."""
    client = get_supabase_client()
    if token:
        client.postgrest.auth(token)
    return client

def handle_supabase_error(error: Exception, resource_name: str = "Resource") -> None:
    """Converts Supabase / PostgREST API errors to appropriate FastAPI HTTPExceptions."""
    if isinstance(error, APIError):
        code = getattr(error, "code", "")
        msg = getattr(error, "message", str(error))
        details = getattr(error, "details", None)
        hint = getattr(error, "hint", None)
        
        detail_msg = msg
        if details:
            detail_msg += f" Details: {details}"
        if hint:
            detail_msg += f" Hint: {hint}"

        logger.warning(f"Supabase APIError [{code}]: {detail_msg}")

        # Unique violation
        if code == "23505":
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Conflict: A {resource_name.lower()} with these unique attributes already exists. {msg}"
            )
        # Foreign key violation
        if code == "23503":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid relationship: The referenced parent entity does not exist or you do not have permission. {msg}"
            )
        # Not-null violation
        if code == "23502":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Missing required field: {msg}"
            )
        # Permission denied / RLS violation
        if code == "42501":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Access denied: You are not authorized to perform this operation on {resource_name.lower()}."
            )
        # No rows returned for single()
        if code == "PGRST116":
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"{resource_name} not found or you are not authorized to access it."
            )
        # Invalid input syntax (e.g. UUID, date)
        if code == "22P02":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid input format: {msg}"
            )
        # Generic bad request
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=detail_msg
        )
    elif isinstance(error, HTTPException):
        raise error
    else:
        logger.error(f"Unexpected database error: {error}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An unexpected error occurred while processing {resource_name.lower()}."
        )
