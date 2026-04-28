"""
routes/auth.py
──────────────
Auth management endpoints (profile, token refresh hint).
Firebase Auth handles actual sign-in on the frontend;
this backend only needs to verify tokens.
"""

from fastapi import APIRouter, Depends
from utils.auth import get_current_user

router = APIRouter()


@router.get("/me")
async def get_profile(current_user: dict = Depends(get_current_user)):
    """Return the authenticated user's profile from the decoded token."""
    return {
        "uid":   current_user.get("uid"),
        "email": current_user.get("email"),
        "name":  current_user.get("name"),
    }
