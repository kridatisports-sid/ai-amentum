"""
routes/payment.py - No razorpay SDK, uses httpx directly
"""

import os
import hmac
import hashlib
import base64
import logging
import httpx
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel

from utils.auth import get_current_user
from utils.firebase import update_doc

router = APIRouter()
logger = logging.getLogger("amentum.payment")

RZP_KEY_ID     = os.getenv("RAZORPAY_KEY_ID", "")
RZP_KEY_SECRET = os.getenv("RAZORPAY_KEY_SECRET", "")
RZP_BASE_URL   = "https://api.razorpay.com/v1"

PRICES = {
    "free":    9900,
    "premium": 199900,
}


def _auth_header() -> dict:
    if not RZP_KEY_ID or not RZP_KEY_SECRET:
        raise HTTPException(503, "Payment gateway not configured.")
    token = base64.b64encode(f"{RZP_KEY_ID}:{RZP_KEY_SECRET}".encode()).decode()
    return {"Authorization": f"Basic {token}", "Content-Type": "application/json"}


class CreateOrderRequest(BaseModel):
    video_id: str
    tier: str


class VerifyPaymentRequest(BaseModel):
    video_id: str
    razorpay_order_id:   str
    razorpay_payment_id: str
    razorpay_signature:  str


@router.post("/create-order")
async def create_order(
    req: CreateOrderRequest,
    current_user: dict = Depends(get_current_user),
):
    if req.tier not in PRICES:
        raise HTTPException(400, f"Invalid tier: {req.tier}")
    amount = PRICES[req.tier]
    try:
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.post(
                f"{RZP_BASE_URL}/orders",
                json={
                    "amount": amount, "currency": "INR",
                    "receipt": req.video_id[:40],
                    "notes": {"video_id": req.video_id,
                              "user_id": current_user["uid"],
                              "tier": req.tier},
                },
                headers=_auth_header(),
            )
            resp.raise_for_status()
            order = resp.json()
    except Exception as e:
        logger.error("Razorpay error: %s", e)
        raise HTTPException(502, "Payment gateway error.")
    return {"order_id": order["id"], "amount": amount,
            "currency": "INR", "key_id": RZP_KEY_ID, "tier": req.tier}


@router.post("/verify")
async def verify_payment(
    req: VerifyPaymentRequest,
    current_user: dict = Depends(get_current_user),
):
    expected = hmac.new(
        RZP_KEY_SECRET.encode(),
        f"{req.razorpay_order_id}|{req.razorpay_payment_id}".encode(),
        hashlib.sha256,
    ).hexdigest()
    if not hmac.compare_digest(expected, req.razorpay_signature):
        raise HTTPException(400, "Payment verification failed.")
    await update_doc("analyses", req.video_id, {
        "paid": True,
        "payment_id": req.razorpay_payment_id,
        "order_id": req.razorpay_order_id,
    })
    tier = "free"
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.get(
                f"{RZP_BASE_URL}/orders/{req.razorpay_order_id}",
                headers=_auth_header(),
            )
            tier = resp.json().get("notes", {}).get("tier", "free")
    except Exception:
        pass
    await update_doc("analyses", req.video_id, {"tier": tier})
    return {"success": True, "tier": tier, "video_id": req.video_id}


@router.post("/webhook")
async def razorpay_webhook(payload: dict):
    event = payload.get("event")
    if event == "payment.captured":
        payment = payload.get("payload", {}).get("payment", {}).get("entity", {})
        notes = payment.get("notes", {})
        vid = notes.get("video_id")
        if vid:
            await update_doc("analyses", vid, {
                "paid": True, "tier": notes.get("tier", "free"),
                "webhook_confirmed": True,
            })
    return {"status": "ok"}