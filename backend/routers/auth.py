# backend/routers/auth.py

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, EmailStr
from dependencies import supabase

# APIRouter groups related endpoints together
# prefix="/auth" means all routes here start with /auth
# tags=["Authentication"] groups them in Swagger UI
router = APIRouter(prefix="/auth", tags=["Authentication"])


# ── Request body models ──────────────────────────────────────
# Pydantic validates these automatically before your function runs
# If email isn't a valid email format, FastAPI returns 422 automatically

class SignupRequest(BaseModel):
    email: EmailStr      # validates email format automatically
    password: str


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


# ── Routes ───────────────────────────────────────────────────

@router.post("/signup")
async def signup(body: SignupRequest):
    """
    Create a new user account.
    Supabase handles password hashing — we never see the plain password.
    """
    try:
        response = supabase.auth.sign_up({
            "email": body.email,
            "password": body.password
        })

        if response.user is None:
            raise HTTPException(
                status_code=400,
                detail="Signup failed. Email may already be registered."
            )

        return {
            "message": "Account created successfully",
            "user_id": str(response.user.id),
            "email": response.user.email
        }

    except HTTPException:
        raise  # re-raise our own exceptions unchanged
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/login")
async def login(body: LoginRequest):
    """
    Log in with email and password.
    Returns a JWT access token — frontend stores this and sends it
    with every subsequent request in the Authorization header.
    """
    try:
        response = supabase.auth.sign_in_with_password({
            "email": body.email,
            "password": body.password
        })

        return {
            "access_token": response.session.access_token,
            "token_type": "bearer",
            "user_id": str(response.user.id),
            "email": response.user.email,
            "message": "Login successful"
        }

    except Exception:
        # Always return a generic message for failed logins
        # Never say "email not found" vs "wrong password" — security reason below
        raise HTTPException(
            status_code=401,
            detail="Invalid email or password"
        )