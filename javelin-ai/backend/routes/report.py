"""
routes/report.py
────────────────
Report retrieval, PDF download, and dashboard history.
"""

from fastapi import APIRouter, HTTPException, Depends
from fastapi.responses import FileResponse
import os

from utils.auth import get_current_user
from utils.firebase import get_doc, query_collection

router = APIRouter()


@router.get("/{video_id}")
async def get_report(
    video_id: str,
    current_user: dict = Depends(get_current_user),
):
    """Return the full report JSON for a completed analysis."""
    report = await get_doc("reports", video_id)
    if not report:
        raise HTTPException(404, "Report not found. Analysis may still be in progress.")

    if report.get("user_id") != current_user["uid"]:
        raise HTTPException(403, "Access denied.")

    return report


@router.get("/{video_id}/pdf")
async def download_pdf(
    video_id: str,
    current_user: dict = Depends(get_current_user),
):
    """
    Stream the PDF report.
    Falls back to regenerating from local tmp if cloud URL unavailable.
    """
    report = await get_doc("reports", video_id)
    if not report:
        raise HTTPException(404, "Report not found.")
    if report.get("user_id") != current_user["uid"]:
        raise HTTPException(403, "Access denied.")

    # Try local tmp first (fast path for same-instance requests)
    local_pdf = f"tmp/pdfs/{video_id}_report.pdf"
    if os.path.exists(local_pdf):
        return FileResponse(
            local_pdf,
            media_type="application/pdf",
            filename=f"amentum_report_{video_id[:8]}.pdf",
        )

    # Return cloud URL redirect
    pdf_url = report.get("pdf_url")
    if pdf_url:
        from fastapi.responses import RedirectResponse
        return RedirectResponse(pdf_url)

    raise HTTPException(503, "PDF not yet available. Retry in a moment.")


@router.get("/user/history")
async def get_user_history(
    current_user: dict = Depends(get_current_user),
):
    """Return all reports for the authenticated user (newest first)."""
    user_id = current_user["uid"]
    docs = await query_collection(
        "reports",
        filters=[("user_id", "==", user_id)],
        order_by="created_at",
        limit=50,
    )
    # Strip heavy fields (timeseries, full landmarks) for list view
    slim = []
    for d in docs:
        slim.append({
            "video_id":      d.get("video_id"),
            "created_at":    d.get("created_at"),
            "overall_score": d.get("overall_score"),
            "grade":         d.get("grade"),
            "release_angle": d.get("release_angle"),
            "tier":          d.get("tier"),
            "status":        d.get("status"),
            "pdf_url":       d.get("pdf_url"),
            "overlay_url":   d.get("overlay_url"),
            "keyframe_urls": d.get("keyframe_urls"),
        })
    return {"history": slim, "count": len(slim)}
