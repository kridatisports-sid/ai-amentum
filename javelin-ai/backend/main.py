"""
Amentum Sports – Javelin AI Analysis Backend
FastAPI application with async video processing pipeline.
"""

import os
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from routes.upload import router as upload_router
from routes.analyze import router as analyze_router
from routes.report import router as report_router
from routes.payment import router as payment_router
from routes.auth import router as auth_router

# ── Logging ──────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(name)s – %(message)s",
)
logger = logging.getLogger("amentum")

# ── Lifespan (startup / shutdown) ────────────────────────────────────────────
@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("🚀  Amentum AI backend starting …")
    # Ensure local temp dirs exist
    os.makedirs("tmp/uploads", exist_ok=True)
    os.makedirs("tmp/frames",  exist_ok=True)
    os.makedirs("tmp/outputs", exist_ok=True)
    os.makedirs("tmp/pdfs",    exist_ok=True)
    yield
    logger.info("⏹  Amentum AI backend shutting down …")

# ── App ───────────────────────────────────────────────────────────────────────
app = FastAPI(
    title="Amentum Sports – Javelin AI API",
    version="1.0.0",
    description="AI-powered javelin throw biomechanical analysis engine.",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=os.getenv("ALLOWED_ORIGINS", "http://localhost:5173").split(","),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Serve generated PDFs / overlay videos as static assets
app.mount("/static", StaticFiles(directory="tmp"), name="static")

# ── Routers ───────────────────────────────────────────────────────────────────
app.include_router(auth_router,    prefix="/api/auth",    tags=["Auth"])
app.include_router(upload_router,  prefix="/api/upload",  tags=["Upload"])
app.include_router(analyze_router, prefix="/api/analyze", tags=["Analyze"])
app.include_router(report_router,  prefix="/api/report",  tags=["Report"])
app.include_router(payment_router, prefix="/api/payment", tags=["Payment"])

@app.get("/health")
async def health():
    return {"status": "ok", "service": "amentum-javelin-ai"}
