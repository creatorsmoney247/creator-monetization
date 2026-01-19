# backend/app/routes/paystack_routes.py

import os
import uuid
import hmac
import hashlib
import logging
from typing import Dict, Any

import requests
import psycopg2
from fastapi import APIRouter, HTTPException, Request

logger = logging.getLogger("creator-backend.paystack")

router = APIRouter(prefix="/paystack", tags=["paystack"])


# -------------------------------------------------
# ENV
# -------------------------------------------------
def get_required_env(name: str) -> str:
    value = os.getenv(name)
    if not value or not value.strip():
        raise RuntimeError(f"❌ Missing required env var: {name}")
    return value

PAYSTACK_SECRET_KEY = get_required_env("PAYSTACK_SECRET_KEY")
DATABASE_URL = get_required_env("DATABASE_URL")


# -------------------------------------------------
# DB HELPERS
# -------------------------------------------------
def get_db():
    return psycopg2.connect(
        DATABASE_URL,
        sslmode="require",
        connect_timeout=5,
    )


# -------------------------------------------------
# INIT PAYMENT (Supports Bot Payload)
# -------------------------------------------------
@router.post("/init")
def init_payment(payload: Dict[str, Any]):
    """
    Initialize Paystack PRO subscription payment.
    Supports:
        {email, amount, telegram_id}
        {email, amount, metadata: {telegram_id}}
    """

    # ------------------------------
    # Extract Email
    # ------------------------------
    email = payload.get("email")
    if not email or not isinstance(email, str):
        raise HTTPException(400, "Missing or invalid email")

    # ------------------------------
    # Extract Amount
    # ------------------------------
    amount = payload.get("amount")
    if amount is None:
        raise HTTPException(400, "Missing amount")

    try:
        amount = int(amount)
    except:
        raise HTTPException(400, "Invalid amount")

    # ------------------------------
    # Extract Telegram ID (2 compatible formats)
    # ------------------------------
    telegram_id = payload.get("telegram_id")

    if telegram_id is None:
        # fallback to metadata.telegram_id
        metadata = payload.get("metadata") or {}
        telegram_id = metadata.get("telegram_id")

    if telegram_id is None:
        raise HTTPException(400, "Missing telegram_id")

    telegram_id = str(telegram_id)

    # ------------------------------
    # Generate Unique Reference
    # ------------------------------
    reference = str(uuid.uuid4())

    # ------------------------------
    # Initialize Paystack
    # ------------------------------
    resp = requests.post(
        "https://api.paystack.co/transaction/initialize",
        headers={
            "Authorization": f"Bearer {PAYSTACK_SECRET_KEY}",
            "Content-Type": "application/json",
        },
        json={
            "email": email,
            "amount": amount,
            "reference": reference,
            "metadata": {
                "telegram_id": telegram_id,
                "plan": "PRO"
            },
        },
        timeout=15,
    )

    if not resp.ok:
        logger.error("❌ Paystack init failed: %s", resp.text)
        raise HTTPException(400, "Paystack init failed")

    body = resp.json()
    data = body.get("data") or {}

    # ------------------------------
    # Store Pending Payment in DB
    # ------------------------------
    conn = get_db()
    try:
        cur = conn.cursor()
        cur.execute(
            """
            INSERT INTO payments (reference, telegram_id, amount, plan, status)
            VALUES (%s, %s, %s, %s, 'pending')
            """,
            (reference, telegram_id, amount, "PRO"),
        )
        conn.commit()
    finally:
        conn.close()

    return {
        "authorization_url": data.get("authorization_url"),
        "reference": reference,
    }


# -------------------------------------------------
# PAYSTACK WEBHOOK (Handles charge.success)
# -------------------------------------------------
@router.post("/webhook")
async def paystack_webhook(request: Request):
    raw_body = await request.body()
    signature = request.headers.get("x-paystack-signature")

    if not signature:
        raise HTTPException(400, "Missing Paystack signature")

    expected = hmac.new(
        PAYSTACK_SECRET_KEY.encode(),
        raw_body,
        hashlib.sha512
    ).hexdigest()

    if not hmac.compare_digest(expected, signature):
        raise HTTPException(400, "Invalid Paystack signature")

    try:
        payload = await request.json()
    except:
        raise HTTPException(400, "Invalid JSON")

    if payload.get("event") != "charge.success":
        return {"status": "ignored"}

    data = payload.get("data") or {}
    metadata = data.get("metadata") or {}

    reference = data.get("reference")
    telegram_id = metadata.get("telegram_id")
    plan = metadata.get("plan")

    if not reference or not telegram_id:
        logger.warning("Webhook missing fields")
        return {"status": "ignored"}

    conn = get_db()
    try:
        cur = conn.cursor()

        # Mark payment as success
        cur.execute(
            "UPDATE payments SET status='success', paid_at=CURRENT_TIMESTAMP WHERE reference=%s",
            (reference,),
        )

        # Enable PRO for 30 days
        if plan == "PRO":
            cur.execute(
                """
                INSERT INTO creators (telegram_id, is_pro, pro_activated_at, pro_expires_at)
                VALUES (%s, TRUE, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP + INTERVAL '30 days')
                ON CONFLICT (telegram_id)
                DO UPDATE SET
                    is_pro = TRUE,
                    pro_activated_at = CURRENT_TIMESTAMP,
                    pro_expires_at = CURRENT_TIMESTAMP + INTERVAL '30 days'
                """,
                (telegram_id,)
            )

        conn.commit()

    except Exception as e:
        logger.error(f"Webhook DB error: {e}")
        conn.rollback()
        raise HTTPException(500, "Internal Error")

    finally:
        conn.close()

    return {"status": "subscription_active", "plan": plan}
