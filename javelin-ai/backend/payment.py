"""
routes/payment.py
─────────────────
Razorpay integration using direct httpx calls.
No razorpay SDK — avoids the pkg_resources / Python 3.12 breakage.
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
    "free":    9900,    # ₹99 in paise
    "premium": 199900,  # ₹1999 in paise
}


def _auth_header() -> dict:
    """Basic auth header for Razorpay API."""
    if not RZP_KEY_ID or not RZP_KEY_SECRET:
        raise HTTPException(503, "Payment gateway not configured.")
    token = base64.b64encode(f"{RZP_KEY_ID}:{RZP_KEY_SECRET}".encode()).decode()
    return {"Authorization": f"Basic {token}", "Content-Type": "application/json"}


class CreateOrderRequest(BaseModel):
    video_id: str
    tier: str     # "free" | "premium"


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
    """Create a Razorpay order via direct REST call."""
    if req.tier not in PRICES:
        raise HTTPException(400, f"Invalid tier: {req.tier}")

    amount = PRICES[req.tier]

    payload = {
        "amount":   amount,
        "currency": "INR",
        "receipt":  req.video_id[:40],
        "notes": {
            "video_id": req.video_id,
            "user_id":  current_user["uid"],
            "tier":     req.tier,
        },
    }

    try:
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.post(
                f"{RZP_BASE_URL}/orders",
                json=payload,
                headers=_auth_header(),
            )
            resp.raise_for_status()
            order = resp.json()
    except httpx.HTTPStatusError as e:
        logger.error("Razorpay order creation failed: %s – %s", e.response.status_code, e.response.text)
        raise HTTPException(502, "Payment gateway error.")
    except Exception as e:
        logger.error("Razorpay request error: %s", e)
        raise HTTPException(502, "Payment gateway unreachable.")

    logger.info("Created order %s for %s (₹%.2f)", order["id"], req.video_id, amount / 100)

    return {
        "order_id": order["id"],
        "amount":   amount,
        "currency": "INR",
        "key_id":   RZP_KEY_ID,
        "tier":     req.tier,
    }


@router.post("/verify")
async def verify_payment(
    req: VerifyPaymentRequest,
    current_user: dict = Depends(get_current_user),
):
    """Verify Razorpay HMAC-SHA256 signature and unlock the analysis tier."""
    expected = hmac.new(
        RZP_KEY_SECRET.encode(),
        f"{req.razorpay_order_id}|{req.razorpay_payment_id}".encode(),
        hashlib.sha256,
    ).hexdigest()

    if not hmac.compare_digest(expected, req.razorpay_signature):
        logger.warning("Invalid payment signature for video %s", req.video_id)
        raise HTTPException(400, "Payment verification failed – invalid signature.")

    # Mark as paid
    await update_doc("analyses", req.video_id, {
        "paid":       True,
        "payment_id": req.razorpay_payment_id,
        "order_id":   req.razorpay_order_id,
    })

    # Fetch tier from order notes via REST
    tier = "free"
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.get(
                f"{RZP_BASE_URL}/orders/{req.razorpay_order_id}",
                headers=_auth_header(),
            )
            resp.raise_for_status()
            tier = resp.json().get("notes", {}).get("tier", "free")
    except Exception as e:
        logger.warning("Could not fetch order tier, defaulting to free: %s", e)

    await update_doc("analyses", req.video_id, {"tier": tier})

    logger.info("Payment verified for video %s  tier=%s", req.video_id, tier)
    return {"success": True, "tier": tier, "video_id": req.video_id}


@router.post("/webhook")
async def razorpay_webhook(payload: dict):
    """Razorpay webhook — handles payment.captured event."""
    event = payload.get("event")
    logger.info("Webhook received: %s", event)

    if event == "payment.captured":
        payment = payload.get("payload", {}).get("payment", {}).get("entity", {})
        notes   = payment.get("notes", {})
        vid     = notes.get("video_id")
        tier    = notes.get("tier", "free")

        if vid:
            await update_doc("analyses", vid, {
                "paid":               True,
                "tier":               tier,
                "webhook_confirmed":  True,
            })
            logger.info("Webhook: payment confirmed for video %s", vid)

    return {"status": "ok"}
