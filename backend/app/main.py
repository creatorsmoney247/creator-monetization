import os
import json
import hmac
import hashlib
import logging
import uuid
from typing import Dict, Any

import requests
import psycopg2
from fastapi import FastAPI, Request, HTTPException, status
from telegram.constants import ParseMode

from .db_auto_migrate import run_migrations
from app.routes.telegram_webhook import router as telegram_router
from app.routes.telegram_webhook import telegram_app

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("creator-backend")

def get_required_env(name: str) -> str:
    value = os.getenv(name)
    if not value or not value.strip():
        raise RuntimeError(f"❌ Missing required env var: {name}")
    return value

DATABASE_URL = get_required_env("DATABASE_URL")
PAYSTACK_SECRET_KEY = get_required_env("PAYSTACK_SECRET_KEY")

def get_db():
    return psycopg2.connect(
        DATABASE_URL,
        sslmode="require",
        connect_timeout=5,
    )

app = FastAPI(
    title="Creator Monetization API",
    version="1.0.0",
)

@app.on_event("startup")
async def startup_event():
    logger.info("🚀 Startup event triggered")

    try:
        run_migrations()
        logger.info("✅ Migrations complete")
    except Exception as e:
        logger.error(f"❌ Migration error: {e}")

    try:
        await telegram_app.initialize()

        webhook_url = os.getenv("WEBHOOK_URL")
        if webhook_url:
            await telegram_app.bot.set_webhook(
                url=webhook_url,
                allowed_updates=["message", "callback_query"]
            )
            logger.info(f"🌐 Webhook set: {webhook_url}")

        logger.info("🤖 Telegram bot initialized")

    except Exception as e:
        logger.error(f"❌ Telegram init failed: {e}")

@app.on_event("shutdown")
async def shutdown_event():
    try:
        await telegram_app.shutdown()
        logger.info("🛑 Telegram bot shutdown")
    except Exception as e:
        logger.error(f"❌ Telegram shutdown failed: {e}")

app.include_router(telegram_router)

@app.get("/health")
def health():
    return {"status": "ok"}

@app.get("/db/test")
def db_test():
    try:
        conn = get_db()
        conn.close()
        return {"db": "ok"}
    except Exception as e:
        return {"db": "error", "detail": str(e)}

@app.post("/pricing/calculate")
def calculate_pricing(payload: Dict[str, Any]):
    try:
        avg_views = int(payload["avg_views"])
        engagement = float(payload["engagement_rate"])
    except Exception:
        raise HTTPException(400, "Invalid payload")

    recommended = int((avg_views * engagement) * 2)
    minimum = int(recommended * 0.7)

    return {
        "recommended_price": recommended,
        "minimum_price": minimum,
    }

@app.post("/paystack/init")
def paystack_init(payload: Dict[str, Any]):
    try:
        email = payload["email"]
        amount = int(payload["amount"])
        telegram_id = str(payload["metadata"]["telegram_id"])
    except Exception:
        raise HTTPException(400, "Invalid payload")

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
        logger.error("❌ Paystack init failed: %s", response.text)
        raise HTTPException(400, "Paystack initialization failed")

    conn = get_db()
    try:
        cur = conn.cursor()
        cur.execute(
            """
            INSERT INTO payments (reference, telegram_id, amount, status)
            VALUES (%s, %s, %s, 'pending')
            """,
            (reference, telegram_id, amount),
        )
        conn.commit()
    finally:
        conn.close()

    return response.json()["data"]

@app.post("/paystack/webhook")
async def paystack_webhook(request: Request):
    raw_body = await request.body()
    signature = request.headers.get("x-paystack-signature")

    if not signature:
        raise HTTPException(400, "Missing Paystack signature")

    expected_signature = hmac.new(
        PAYSTACK_SECRET_KEY.encode(),
        raw_body,
        hashlib.sha512,
    ).hexdigest()

    if not hmac.compare_digest(signature, expected_signature):
        raise HTTPException(400, "Invalid Paystack signature")

    event = json.loads(raw_body)

    if event.get("event") != "charge.success":
        return {"status": "ignored"}

    data = event["data"]
    reference = data["reference"]
    telegram_id = str(data["metadata"]["telegram_id"])

    conn = get_db()
    try:
        cur = conn.cursor()
        cur.execute(
            "UPDATE payments SET status='success' WHERE reference=%s",
            (reference,),
        )
        cur.execute(
            """
            INSERT INTO creators (telegram_id, is_pro, pro_activated_at)
            VALUES (%s, TRUE, CURRENT_TIMESTAMP)
            ON CONFLICT (telegram_id)
            DO UPDATE SET
                is_pro = TRUE,
                pro_activated_at = CURRENT_TIMESTAMP
            """,
            (telegram_id,),
        )
        conn.commit()
    finally:
        conn.close()

    logger.info("✅ Creator %s upgraded to PRO", telegram_id)
    return {"status": "upgraded"}
