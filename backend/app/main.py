# -------------------------------------------------
# STANDARD IMPORTS
# -------------------------------------------------
import os
import json
import hmac
import hashlib
import logging
import uuid
from typing import Dict

import requests
import psycopg2
from fastapi import FastAPI, Request, HTTPException

# -------------------------------------------------
# ROUTERS
# -------------------------------------------------
from app.routes.telegram_webhook import router as telegram_router
# -------------------------------------------------
# LOGGING
# -------------------------------------------------
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("creator-backend")

# -------------------------------------------------
# ENV HELPERS (RENDER-SAFE)
# -------------------------------------------------
def get_required_env(name: str) -> str:
    value = os.getenv(name)
    if not value or not value.strip():
        raise RuntimeError(f"❌ Missing required env var: {name}")
    return value

# -------------------------------------------------
# REQUIRED ENV VARS (NO .env)
# -------------------------------------------------
DATABASE_URL = get_required_env("DATABASE_URL")
PAYSTACK_SECRET_KEY = get_required_env("PAYSTACK_SECRET_KEY")

# -------------------------------------------------
# DATABASE (LAZY — NO STARTUP CONNECTION)
# -------------------------------------------------
def get_db():
    return psycopg2.connect(
        DATABASE_URL,
        connect_timeout=5,
    )

# -------------------------------------------------
# FASTAPI APP
# -------------------------------------------------
app = FastAPI(
    title="Creator Monetization API",
    version="1.0.0",
)

# Telegram webhook router
app.include_router(telegram_router, prefix="/telegram")

# -------------------------------------------------
# HEALTH CHECK (NO DB)
# -------------------------------------------------
@app.get("/health")
def health():
    return {"status": "ok"}

# -------------------------------------------------
# PRICING API (NO DB)
# -------------------------------------------------
@app.post("/pricing/calculate")
def calculate_pricing(payload: Dict):
    try:
        avg_views = int(payload["avg_views"])
        engagement = float(payload["engagement_rate"])
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid payload")

    recommended = int((avg_views * engagement) * 2)
    minimum = int(recommended * 0.7)

    return {
        "recommended_price": recommended,
        "minimum_price": minimum,
    }

# -------------------------------------------------
# PAYSTACK INIT (DB USED HERE — SAFE)
# -------------------------------------------------
@app.post("/paystack/init")
def paystack_init(payload: Dict):
    try:
        email = payload["email"]
        amount = int(payload["amount"])
        telegram_id = str(payload["metadata"]["telegram_id"])
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid payload")

    reference = str(uuid.uuid4())

    response = requests.post(
        "https://api.paystack.co/transaction/initialize",
        headers={
            "Authorization": f"Bearer {PAYSTACK_SECRET_KEY}",
            "Content-Type": "application/json",
        },
        json={
            "email": email,
            "amount": amount,
            "reference": reference,
            "metadata": {"telegram_id": telegram_id},
        },
        timeout=15,
    )

    if not response.ok:
        logger.error("Paystack init failed: %s", response.text)
        raise HTTPException(status_code=400, detail="Paystack init failed")

    conn = get_db()
    cur = conn.cursor()
    cur.execute(
        """
        INSERT INTO payments (reference, telegram_id, amount, status)
        VALUES (%s, %s, %s, 'pending')
        """,
        (reference, telegram_id, amount),
    )
    conn.commit()
    conn.close()

    return response.json()["data"]

# -------------------------------------------------
# PAYSTACK WEBHOOK (SECURE)
# -------------------------------------------------
@app.post("/paystack/webhook")
async def paystack_webhook(request: Request):
    raw = await request.body()
    signature = request.headers.get("x-paystack-signature")

    expected = hmac.new(
        PAYSTACK_SECRET_KEY.encode(),
        raw,
        hashlib.sha512,
    ).hexdigest()

    if not hmac.compare_digest(signature or "", expected):
        raise HTTPException(status_code=400, detail="Invalid signature")

    event = json.loads(raw)

    if event.get("event") != "charge.success":
        return {"status": "ignored"}

    data = event["data"]
    reference = data["reference"]
    telegram_id = str(data["metadata"]["telegram_id"])

    conn = get_db()
    cur = conn.cursor()

    cur.execute(
        "UPDATE payments SET status='success' WHERE reference=%s",
        (reference,),
    )

    cur.execute(
        """
        INSERT INTO creators (telegram_id, is_pro, pro_activated_at)
        VALUES (%s, 1, CURRENT_TIMESTAMP)
        ON CONFLICT (telegram_id)
        DO UPDATE SET
            is_pro = 1,
            pro_activated_at = CURRENT_TIMESTAMP
        """,
        (telegram_id,),
    )

    conn.commit()
    conn.close()

    return {"status": "upgraded"}
