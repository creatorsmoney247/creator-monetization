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
# ENV (BACKEND ONLY)
# -------------------------------------------------
def get_required_env(name: str) -> str:
    value = os.getenv(name)
    if not value or not value.strip():
        raise RuntimeError(f"❌ Missing required env var: {name}")
    return value


PAYSTACK_SECRET_KEY = get_required_env("PAYSTACK_SECRET_KEY")
DATABASE_URL = get_required_env("DATABASE_URL")


# -------------------------------------------------
# DB (SUPABASE / POSTGRES)
# -------------------------------------------------
def get_db():
    return psycopg2.connect(
        DATABASE_URL,
        sslmode="require",
        connect_timeout=5,
    )


# -------------------------------------------------
# INIT PAYMENT
# -------------------------------------------------
from app.services.paystack_service import init_paystack_payment


@router.post("/init")
def init_payment(payload: Dict[str, Any]):
    """
    Initialize Paystack payment session.
    """

    # --- Extract fields safely ---
    email = payload.get("email")
    raw_amount = payload.get("amount")
    meta = payload.get("metadata", {}) or {}
    telegram_id = meta.get("telegram_id")

    # --- Validate required fields ---
    if email is None or not isinstance(email, str):
        raise HTTPException(status_code=400, detail="Invalid or missing email")

    if telegram_id is None:
        raise HTTPException(status_code=400, detail="Invalid or missing telegram_id")

    # --- Validate amount type ---
    if raw_amount is None:
        raise HTTPException(status_code=400, detail="Missing amount")

    try:
        amount = int(raw_amount)
    except (TypeError, ValueError):
        raise HTTPException(status_code=400, detail="Invalid amount")

    # --- Call paystack service ---
    try:
        url = init_paystack_payment(email, amount, str(telegram_id))
    except Exception as e:
        logger.error(f"Paystack init failed → {e}")
        raise HTTPException(status_code=503, detail="Payment init failed, try again later")

    return {"authorization_url": url}


# -------------------------------------------------
# PAYSTACK WEBHOOK
# -------------------------------------------------
@router.post("/webhook")
async def paystack_webhook(request: Request):
    """
    Handle Paystack charge.success webhook.
    """
    raw_body = await request.body()
    signature = request.headers.get("x-paystack-signature")

    if not signature:
        raise HTTPException(status_code=400, detail="Missing Paystack signature")

    expected = hmac.new(
        PAYSTACK_SECRET_KEY.encode(),
        raw_body,
        hashlib.sha512,
    ).hexdigest()

    if not hmac.compare_digest(signature, expected):
        raise HTTPException(status_code=400, detail="Invalid Paystack signature")

    try:
        payload = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid JSON payload")

    if payload.get("event") != "charge.success":
        return {"status": "ignored"}

    data = payload.get("data") or {}
    reference = data.get("reference")
    metadata = data.get("metadata", {}) or {}
    telegram_id = metadata.get("telegram_id")

    if not reference or not telegram_id:
        logger.warning("Webhook missing reference or telegram_id")
        return {"status": "invalid"}

    conn = None
    try:
        conn = get_db()
        cur = conn.cursor()

        # Mark payment as successful
        cur.execute(
            "UPDATE payments SET status='success' WHERE reference=%s",
            (reference,),
        )

        # Unlock PRO
        cur.execute("""
            INSERT INTO creators (telegram_id, is_pro, pro_activated_at)
            VALUES (%s, 1, CURRENT_TIMESTAMP)
            ON CONFLICT (telegram_id)
            DO UPDATE SET
                is_pro=1,
                pro_activated_at=CURRENT_TIMESTAMP
        """, (str(telegram_id),))

        conn.commit()

    except Exception as e:
        logger.error(f"Webhook DB error → {e}")
        if conn:
            conn.rollback()
        raise HTTPException(status_code=500, detail="Internal Error")
    finally:
        if conn:
            conn.close()

    return {"status": "upgraded"}
