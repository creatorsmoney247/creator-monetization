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
# INIT PAYMENT
# -------------------------------------------------
@router.post("/init")
def init_payment(payload: Dict[str, Any]):
    """
    Initialize Paystack PRO subscription payment.
    """

    email = payload.get("email")
    amount = payload.get("amount")
    telegram_id = payload.get("telegram_id")

    if not email or not isinstance(email, str):
        raise HTTPException(400, "Missing or invalid email")

    if amount is None:
        raise HTTPException(400, "Missing amount")

    if telegram_id is None:
        raise HTTPException(400, "Missing telegram_id")

    try:
        amount = int(amount)
    except:
        raise HTTPException(400, "Invalid amount")

    reference = str(uuid.uuid4())

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
                "telegram_id": str(telegram_id),
                "plan": "PRO"  # <---- important
            },
        },
        timeout=15,
    )

    if not resp.ok:
        logger.error("Paystack init failed: %s", resp.text)
        raise HTTPException(400, "Paystack init failed")

    # Store pending payment
    conn = get_db()
    try:
        cur = conn.cursor()
        cur.execute(
            """
            INSERT INTO payments (reference, telegram_id, amount, plan, status)
            VALUES (%s, %s, %s, %s, 'pending')
            """,
            (reference, str(telegram_id), amount, "PRO"),
        )
        conn.commit()
    finally:
        conn.close()

    return resp.json().get("data", {})


# -------------------------------------------------
# PAYSTACK WEBHOOK
# -------------------------------------------------
@router.post("/webhook")
async def paystack_webhook(request: Request):
    """
    Handle Paystack charge.success webhook for PRO monthly.
    """

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

        # Mark as success
        cur.execute(
            "UPDATE payments SET status='success', paid_at=CURRENT_TIMESTAMP WHERE reference=%s",
            (reference,),
        )

        if plan == "PRO":
            # 30-day subscription
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
                (str(telegram_id),)
            )

        conn.commit()

    except Exception as e:
        logger.error(f"Webhook DB error: {e}")
        conn.rollback()
        raise HTTPException(500, "Internal Error")

    finally:
        conn.close()

    return {"status": "subscription_active", "plan": plan}
