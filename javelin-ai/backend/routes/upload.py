"""
routes/upload.py
────────────────
Handles video upload, stores to Firebase Storage, enqueues analysis.
"""

import os
import uuid
import logging
import asyncio
import aiofiles
from fastapi import APIRouter, UploadFile, File, HTTPException, Depends, BackgroundTasks
from fastapi.responses import JSONResponse
from typing import Optional

from utils.auth import get_current_user
from utils.firebase import upload_to_storage, save_doc, update_doc
from services.pose_analyzer import analyze_video
from services.scorer import score_throw
from services.report_generator import build_full_report

router = APIRouter()
logger = logging.getLogger("amentum.upload")

ALLOWED_TYPES = {"video/mp4", "video/quicktime", "video/x-msvideo"}
MAX_BYTES     = 200 * 1024 * 1024   # 200 MB


async def _run_analysis_pipeline(
    video_id: str,
    local_path: str,
    storage_url: str,
    user_id: str,
    tier: str,
):
    """
    Background task: pose analysis → scoring → report → Firestore update.
    Runs entirely async-friendly (CPU-heavy parts in thread executor).
    """
    loop = asyncio.get_event_loop()
    try:
        logger.info("[%s] Analysis pipeline starting", video_id)

        # ── 1. Pose analysis (CPU heavy – run in thread pool) ─────────────
        await update_doc("analyses", video_id, {"status": "analysing"})
        throw_analysis = await loop.run_in_executor(
            None, analyze_video, local_path, video_id
        )

        # ── 2. Scoring ────────────────────────────────────────────────────
        await update_doc("analyses", video_id, {"status": "scoring"})
        scored = await loop.run_in_executor(None, score_throw, throw_analysis)

        # ── 3. AI narrative + report doc ──────────────────────────────────
        await update_doc("analyses", video_id, {"status": "generating_report"})
        report_doc = await build_full_report(scored, user_id, tier)

        # ── 4. Upload overlay video to storage ────────────────────────────
        overlay_url: Optional[str] = None
        if throw_analysis.overlay_video_path and os.path.exists(
            throw_analysis.overlay_video_path
        ):
            overlay_url = await loop.run_in_executor(
                None,
                upload_to_storage,
                throw_analysis.overlay_video_path,
                f"overlays/{video_id}_overlay.mp4",
            )

        # ── 5. Upload key-frame images ────────────────────────────────────
        keyframe_urls: dict = {}
        for phase, kf_path in throw_analysis.keyframe_paths.items():
            if os.path.exists(kf_path):
                kf_url = await loop.run_in_executor(
                    None,
                    upload_to_storage,
                    kf_path,
                    f"keyframes/{video_id}_{phase}.jpg",
                )
                keyframe_urls[phase] = kf_url

        # ── 6. Generate PDF ───────────────────────────────────────────────
        from services.pdf_export import generate_pdf
        pdf_path = f"tmp/pdfs/{video_id}_report.pdf"
        await loop.run_in_executor(None, generate_pdf, report_doc, pdf_path)
        pdf_url: Optional[str] = None
        if os.path.exists(pdf_path):
            pdf_url = await loop.run_in_executor(
                None,
                upload_to_storage,
                pdf_path,
                f"reports/{video_id}_report.pdf",
            )

        # ── 7. Save report to Firestore ───────────────────────────────────
        report_doc.update({
            "overlay_url":   overlay_url,
            "keyframe_urls": keyframe_urls,
            "pdf_url":       pdf_url,
            "status":        "complete",
        })
        await save_doc("reports", video_id, report_doc)
        await update_doc("analyses", video_id, {
            "status":     "complete",
            "report_ref": video_id,
        })

        logger.info("[%s] Pipeline complete. Score=%.1f", video_id, scored.overall_score)

    except Exception as exc:
        logger.error("[%s] Pipeline failed: %s", video_id, exc, exc_info=True)
        await update_doc("analyses", video_id, {
            "status": "failed",
            "error":  str(exc),
        })
    finally:
        # Clean up local temp files
        for path in [local_path]:
            if path and os.path.exists(path):
                try:
                    os.remove(path)
                except OSError:
                    pass


@router.post("/")
async def upload_video(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    tier: str = "free",             # "free" | "premium" – validated by payment check
    current_user: dict = Depends(get_current_user),
):
    """
    1. Validates file type & size.
    2. Saves to temp disk.
    3. Uploads original to Firebase Storage.
    4. Creates a Firestore analysis record (status=queued).
    5. Enqueues background analysis pipeline.
    6. Returns video_id immediately (client polls /analyze/{video_id}).
    """
    # Validate content type
    if file.content_type not in ALLOWED_TYPES:
        raise HTTPException(
            status_code=415,
            detail=f"Unsupported file type: {file.content_type}. Use MP4 or MOV.",
        )

    video_id   = str(uuid.uuid4())
    user_id    = current_user["uid"]
    local_path = f"tmp/uploads/{video_id}_{file.filename}"

    # Stream to disk while checking size
    written = 0
    try:
        async with aiofiles.open(local_path, "wb") as f:
            while chunk := await file.read(1024 * 1024):   # 1 MB chunks
                written += len(chunk)
                if written > MAX_BYTES:
                    raise HTTPException(
                        status_code=413,
                        detail="File exceeds 200 MB limit.",
                    )
                await f.write(chunk)
    except HTTPException:
        if os.path.exists(local_path):
            os.remove(local_path)
        raise

    logger.info("[%s] Uploaded %d bytes for user %s", video_id, written, user_id)

    # Upload original to Firebase Storage
    storage_url = upload_to_storage(local_path, f"videos/{video_id}_{file.filename}")

    # Create Firestore analysis stub
    await save_doc("analyses", video_id, {
        "video_id":    video_id,
        "user_id":     user_id,
        "filename":    file.filename,
        "size_bytes":  written,
        "storage_url": storage_url,
        "tier":        tier,
        "status":      "queued",
    })

    # Kick off background pipeline
    background_tasks.add_task(
        _run_analysis_pipeline,
        video_id, local_path, storage_url, user_id, tier,
    )

    return JSONResponse(
        status_code=202,
        content={
            "video_id":    video_id,
            "status":      "queued",
            "message":     "Video received. Analysis started.",
            "poll_url":    f"/api/analyze/{video_id}",
        },
    )
