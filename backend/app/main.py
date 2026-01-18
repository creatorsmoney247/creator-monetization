# backend/app/main.py

import os
import json
import hmac
import hashlib
import logging
import uuid
from typing import Dict, Any

import requests
import psycopg2
from fastapi import FastAPI, Request, HTTPException
from telegram.constants import ParseMode

from .db_auto_migrate import run_migrations
from app.routes.telegram_webhook import router as telegram_router
from app.routes.telegram_webhook import telegram_app

# Routers
from app.routes.pricing import router as pricing_router   # <--- NEW (Dedicated Pricing Router)
from app.routes.paystack_routes import router as paystack_router   # <--- OPTIONAL if you split out Paystack

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("creator-backend")


# ------------------------------------------------------------
# ENVIRONMENT HELPERS
# ------------------------------------------------------------
def get_required_env(name: str) -> str:
    value = os.getenv(name)
    if not value or not value.strip():
        raise RuntimeError(f"❌ Missing required env var: {name}")
    return value


DATABASE_URL = get_required_env("DATABASE_URL")
PAYSTACK_SECRET_KEY = get_required_env("PAYSTACK_SECRET_KEY")
WEBHOOK_URL = os.getenv("WEBHOOK_URL")  # Optional, for production bot webhook


# ------------------------------------------------------------
# DATABASE CONNECTION
# ------------------------------------------------------------
def get_db():
    return psycopg2.connect(
        DATABASE_URL,
        sslmode="require",
        connect_timeout=5,
    )


# ------------------------------------------------------------
# FASTAPI APP
# ------------------------------------------------------------
app = FastAPI(
    title="Creator Monetization API",
    version="2.0.0",
    description="Telegram Creator Monetization Backend (Hybrid Pricing + PRO + Paystack)"
)


# ------------------------------------------------------------
# LIFECYCLE EVENTS
# ------------------------------------------------------------
@app.on_event("startup")
async def startup_event():
    logger.info("🚀 Backend starting up...")

    # Migrations
    try:
        run_migrations()
        logger.info("🛠 DB migrations complete")
    except Exception as e:
        logger.error(f"❌ Migration error: {e}")

    # Telegram Bot Init
    try:
        await telegram_app.initialize()

        if WEBHOOK_URL:
            await telegram_app.bot.set_webhook(
                url=WEBHOOK_URL,
                allowed_updates=["message", "callback_query"]
            )
            logger.info(f"🌐 Telegram webhook set: {WEBHOOK_URL}")

        logger.info("🤖 Telegram bot initialized successfully")

    except Exception as e:
        logger.error(f"❌ Telegram init failed: {e}")


@app.on_event("shutdown")
async def shutdown_event():
    try:
        await telegram_app.shutdown()
        logger.info("🛑 Telegram bot shutdown")
    except Exception as e:
        logger.error(f"❌ Telegram shutdown failed: {e}")


# ------------------------------------------------------------
# ROUTER REGISTRATION
# ------------------------------------------------------------
app.include_router(telegram_router)
app.include_router(pricing_router)
app.include_router(paystack_router)    # If using paystack_routes.py


# ------------------------------------------------------------
# HEALTH + STATUS ENDPOINTS
# ------------------------------------------------------------
@app.get("/health")
def health():
    return {"status": "ok", "service": "creator-backend"}


@app.get("/db/test")
def db_test():
    try:
        conn = get_db()
        conn.close()
        return {"db": "ok"}
    except Exception as e:
        return {"db": "error", "detail": str(e)}


# ------------------------------------------------------------
# PAYSTACK WEBHOOK HANDLER (ENHANCED)
# ------------------------------------------------------------
@app.post("/paystack/webhook")
async def paystack_webhook(request: Request):
    raw_body = await request.body()
    signature = request.headers.get("x-paystack-signature")

    if not signature:
        raise HTTPException(status_code=400, detail="Missing Paystack signature")

    expected_signature = hmac.new(
        PAYSTACK_SECRET_KEY.encode(),
        raw_body,
        hashlib.sha512,
    ).hexdigest()

    if not hmac.compare_digest(signature, expected_signature):
        raise HTTPException(status_code=400, detail="Invalid Paystack signature")

    event = json.loads(raw_body)

    if event.get("event") != "charge.success":
        logger.info("📩 Non-success webhook received, ignoring.")
        return {"status": "ignored"}

    data = event["data"]
    reference = data["reference"]
    telegram_id = str(data["metadata"]["telegram_id"])

    conn = get_db()
    try:
        cur = conn.cursor()

        # Mark payment as complete
        cur.execute(
            "UPDATE payments SET status='success', paid_at=CURRENT_TIMESTAMP WHERE reference=%s",
            (reference,),
        )

        # Apply PRO Upgrade
        cur.execute(
            """
            INSERT INTO creators (telegram_id, is_pro, pro_activated_at, pro_expires_at, whitelisting_enabled)
            VALUES (%s, TRUE, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP + INTERVAL '365 days', TRUE)
            ON CONFLICT (telegram_id)
            DO UPDATE SET
                is_pro = TRUE,
                pro_activated_at = CURRENT_TIMESTAMP,
                pro_expires_at = CURRENT_TIMESTAMP + INTERVAL '365 days',
                whitelisting_enabled = TRUE
            """,
            (telegram_id,)
        )

        conn.commit()

    except Exception as e:
        logger.error(f"❌ Webhook DB error: {e}")
        try:
            conn.rollback()
        except:
            pass
        raise HTTPException(status_code=500, detail="Internal webhook error")
    finally:
        conn.close()

    logger.info(f"🎉 Creator {telegram_id} upgraded to PRO via Paystack reference {reference}")
    return {"status": "upgraded", "telegram_id": telegram_id}
