import os
import uuid
import hmac
import hashlib
import logging
from typing import Dict

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
    return psycopg2.connect(DATABASE_URL)


# -------------------------------------------------
# INIT PAYMENT
# -------------------------------------------------
from app.services.paystack_service import init_paystack_payment

@router.post("/init")
def init_payment(payload: Dict):
    try:
        email = payload["email"]
        amount = int(payload["amount"])
        telegram_id = str(payload["metadata"]["telegram_id"])
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid payload")

    url = init_paystack_payment(email, amount, telegram_id)
    return {"authorization_url": url}


# -------------------------------------------------
# PAYSTACK WEBHOOK
# -------------------------------------------------
@router.post("/webhook")
async def paystack_webhook(request: Request):
    raw_body = await request.body()
    signature = request.headers.get("x-paystack-signature")

    expected = hmac.new(
        PAYSTACK_SECRET_KEY.encode(),
        raw_body,
        hashlib.sha512,
    ).hexdigest()

    if not hmac.compare_digest(signature or "", expected):
        raise HTTPException(status_code=400, detail="Invalid Paystack signature")

    payload = await request.json()

    if payload.get("event") != "charge.success":
        return {"status": "ignored"}

    data = payload.get("data", {})
    reference = data.get("reference")
    telegram_id = str(data.get("metadata", {}).get("telegram_id"))

    if not reference or not telegram_id:
        return {"status": "invalid"}

    conn = get_db()
    cur = conn.cursor()

    # Mark payment as successful
    cur.execute(
        "UPDATE payments SET status='success' WHERE reference=%s",
        (reference,),
    )

    # 🔓 UNLOCK PRO
    cur.execute("""
        INSERT INTO creators (telegram_id, is_pro, pro_activated_at)
        VALUES (%s, 1, CURRENT_TIMESTAMP)
        ON CONFLICT (telegram_id)
        DO UPDATE SET
            is_pro=1,
            pro_activated_at=CURRENT_TIMESTAMP
    """, (telegram_id,))

    conn.commit()
    conn.close()

    return {"status": "upgraded"}
