# backend/dependencies.py

from fastapi import Header, HTTPException, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from supabase import create_client, Client
from dotenv import load_dotenv
import os

load_dotenv()

supabase: Client = create_client(
    os.getenv("SUPABASE_URL"),
    os.getenv("SUPABASE_KEY")
)

# This scheme makes the Authorize button appear on protected routes
bearer_scheme = HTTPBearer()


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme)
):
    """
    Extracts and verifies the JWT token from the Authorization header.
    FastAPI automatically reads the Bearer token via HTTPBearer.
    """
    token = credentials.credentials  # just the token, "Bearer" prefix already stripped

    try:
        user_response = supabase.auth.get_user(token)
        return user_response.user
    except Exception:
        raise HTTPException(
            status_code=401,
            detail="Invalid or expired token. Please log in again."
        )