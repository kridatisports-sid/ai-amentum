"""
routes/analyze.py  +  routes/report.py
Combined: status polling, report fetch, PDF download.
"""

from fastapi import APIRouter, HTTPException, Depends
from fastapi.responses import FileResponse
import os

from utils.auth import get_current_user
from utils.firebase import get_doc

router = APIRouter()


@router.get("/{video_id}")
async def get_analysis_status(
    video_id: str,
    current_user: dict = Depends(get_current_user),
):
    """Poll the analysis status for a given video_id."""
    doc = await get_doc("analyses", video_id)
    if not doc:
        raise HTTPException(404, "Analysis not found.")

    # Ownership check
    if doc.get("user_id") != current_user["uid"]:
        raise HTTPException(403, "Access denied.")

    return doc
