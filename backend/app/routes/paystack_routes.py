# backend/app/routes/paystack_routes.py

import requests
import sqlite3
import os
import uuid
from fastapi import APIRouter, HTTPException, Request
from dotenv import load_dotenv

load_dotenv()

router = APIRouter()

PAYSTACK_SECRET = os.getenv("PAYSTACK_SECRET_KEY")
CALLBACK_URL = os.getenv("PAYSTACK_CALLBACK_URL")

DB_PATH = "backend/app/bot_users.db"

# -----------------------------
# INIT PAYMENT
# -----------------------------
@router.post("/paystack/init")
def init_payment(payload: dict):
    if not PAYSTACK_SECRET:
        raise HTTPException(status_code=500, detail="Paystack secret not set")

    reference = str(uuid.uuid4())
    telegram_id = payload.get("metadata", {}).get("telegram_id")

    if not telegram_id:
        raise HTTPException(status_code=400, detail="telegram_id missing")

    headers = {
        "Authorization": f"Bearer {PAYSTACK_SECRET}",
        "Content-Type": "application/json",
    }

    data = {
        "email": payload["email"],
        "amount": payload["amount"],
        "reference": reference,
        "callback_url": CALLBACK_URL,
        "metadata": {
            "telegram_id": telegram_id
        },
    }

    res = requests.post(
        "https://api.paystack.co/transaction/initialize",
        json=data,
        headers=headers,
        timeout=10,
    )

    if not res.ok:
        raise HTTPException(status_code=400, detail="Paystack init failed")

    # Save pending payment
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    cur.execute(
        """
        INSERT INTO payments (reference, telegram_id, amount, status)
        VALUES (?, ?, ?, ?)
        """,
        (reference, str(telegram_id), payload["amount"], "pending"),
    )

    conn.commit()
    conn.close()

    return res.json()["data"]


# -----------------------------
# PAYSTACK WEBHOOK
# -----------------------------
@router.post("/paystack/webhook")
async def paystack_webhook(request: Request):
    payload = await request.json()

    if payload.get("event") != "charge.success":
        return {"status": "ignored"}

    data = payload.get("data", {})
    reference = data.get("reference")
    metadata = data.get("metadata", {})
    telegram_id = metadata.get("telegram_id")

    if not reference or not telegram_id:
        return {"status": "invalid"}

    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    # Mark payment as successful
    cur.execute(
        "UPDATE payments SET status = ? WHERE reference = ?",
        ("success", reference),
    )

    # 🔓 UNLOCK PRO
    cur.execute(
        "UPDATE creators SET is_pro = 1 WHERE telegram_id = ?",
        (str(telegram_id),),
    )

    conn.commit()
    conn.close()

    return {"status": "ok"}
