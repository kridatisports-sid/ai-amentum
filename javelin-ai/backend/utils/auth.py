"""
utils/auth.py
─────────────
FastAPI dependency that verifies Firebase Auth ID tokens.
"""

import logging
from fastapi import HTTPException, Header
from typing import Optional
import firebase_admin
from firebase_admin import auth as fb_auth
from utils.firebase import _init

logger = logging.getLogger("amentum.auth")


async def get_current_user(authorization: Optional[str] = Header(None)) -> dict:
    """
    Extracts and verifies the Firebase ID token from the Authorization header.
    Returns the decoded token dict with uid, email, etc.
    """
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(401, "Missing or invalid Authorization header.")

    id_token = authorization.split(" ", 1)[1]

    try:
        _init()   # Ensure Firebase is initialised
        decoded = fb_auth.verify_id_token(id_token)
        return decoded
    except fb_auth.ExpiredIdTokenError:
        raise HTTPException(401, "Token expired. Please re-authenticate.")
    except fb_auth.InvalidIdTokenError:
        raise HTTPException(401, "Invalid token.")
    except Exception as e:
        logger.error("Auth error: %s", e)
        raise HTTPException(401, "Authentication failed.")
