"""
routes/payment.py
─────────────────
Razorpay order creation and webhook verification.

Flow:
  1. Frontend calls POST /api/payment/create-order with { tier, video_id }
  2. Backend creates Razorpay order, returns { order_id, amount, key_id }
  3. Frontend opens Razorpay modal, user pays
  4. Frontend sends payment_id + signature to POST /api/payment/verify
  5. Backend verifies HMAC, marks video as paid in Firestore
  6. Analysis pipeline respects tier on the analysis doc
"""

import os
import hmac
import hashlib
import logging
import razorpay
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel

from utils.auth import get_current_user
from utils.firebase import update_doc, get_doc

router = APIRouter()
logger = logging.getLogger("amentum.payment")

RZP_KEY_ID     = os.getenv("RAZORPAY_KEY_ID", "")
RZP_KEY_SECRET = os.getenv("RAZORPAY_KEY_SECRET", "")

PRICES = {
    "free":    9900,    # ₹99 in paise
    "premium": 199900,  # ₹1999 in paise
}


def _rzp_client() -> razorpay.Client:
    if not RZP_KEY_ID or not RZP_KEY_SECRET:
        raise HTTPException(503, "Payment gateway not configured.")
    return razorpay.Client(auth=(RZP_KEY_ID, RZP_KEY_SECRET))


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
    """Create a Razorpay order for the given tier."""
    if req.tier not in PRICES:
        raise HTTPException(400, f"Invalid tier: {req.tier}")

    amount = PRICES[req.tier]
    client = _rzp_client()

    try:
        order = client.order.create({
            "amount":   amount,
            "currency": "INR",
            "receipt":  req.video_id[:40],
            "notes": {
                "video_id": req.video_id,
                "user_id":  current_user["uid"],
                "tier":     req.tier,
            },
        })
    except Exception as e:
        logger.error("Razorpay order creation failed: %s", e)
        raise HTTPException(502, "Payment gateway error.")

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
    """
    Verify Razorpay HMAC signature and unlock the analysis tier.
    """
    # HMAC-SHA256 signature check
    expected = hmac.new(
        RZP_KEY_SECRET.encode(),
        f"{req.razorpay_order_id}|{req.razorpay_payment_id}".encode(),
        hashlib.sha256,
    ).hexdigest()

    if not hmac.compare_digest(expected, req.razorpay_signature):
        logger.warning("Invalid payment signature for video %s", req.video_id)
        raise HTTPException(400, "Payment verification failed – invalid signature.")

    # Mark analysis doc as paid
    await update_doc("analyses", req.video_id, {
        "paid":       True,
        "payment_id": req.razorpay_payment_id,
        "order_id":   req.razorpay_order_id,
    })

    # Fetch tier from order notes (re-query to determine which tier was paid)
    client = _rzp_client()
    try:
        order = client.order.fetch(req.razorpay_order_id)
        tier  = order.get("notes", {}).get("tier", "free")
    except Exception:
        tier = "free"

    await update_doc("analyses", req.video_id, {"tier": tier})

    logger.info("Payment verified for video %s  tier=%s", req.video_id, tier)
    return {"success": True, "tier": tier, "video_id": req.video_id}


@router.post("/webhook")
async def razorpay_webhook(payload: dict):
    """
    Razorpay webhook endpoint (configure in Razorpay dashboard).
    Handles payment.captured event as a secondary confirmation path.
    """
    event = payload.get("event")
    logger.info("Webhook received: %s", event)

    if event == "payment.captured":
        payment = payload.get("payload", {}).get("payment", {}).get("entity", {})
        notes   = payment.get("notes", {})
        vid     = notes.get("video_id")
        tier    = notes.get("tier", "free")

        if vid:
            await update_doc("analyses", vid, {
                "paid": True,
                "tier": tier,
                "webhook_confirmed": True,
            })
            logger.info("Webhook: payment confirmed for video %s", vid)

    return {"status": "ok"}
