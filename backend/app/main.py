# backend/app/main.py

import os
import json
import hmac
import hashlib
import logging
from typing import Dict, Any

import psycopg2
from fastapi import FastAPI, Request, HTTPException

from .db_auto_migrate import run_migrations

# Telegram Webhook Router + App
from app.routes.telegram_webhook import router as telegram_router
from app.routes.telegram_webhook import telegram_app

# Sub-routers
from app.routes.pricing import router as pricing_router
from app.routes.paystack_routes import router as paystack_router

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("creator-backend")


# ============================================================
# ENVIRONMENT
# ============================================================
def get_required_env(name: str) -> str:
    value = os.getenv(name)
    if not value or not value.strip():
        raise RuntimeError(f"❌ Missing required env var: {name}")
    return value

DATABASE_URL = get_required_env("DATABASE_URL")
PAYSTACK_SECRET_KEY = get_required_env("PAYSTACK_SECRET_KEY")
WEBHOOK_URL = os.getenv("WEBHOOK_URL")  # optional


# ============================================================
# DB CONNECTION (Supabase / Render)
# ============================================================
def get_db():
    return psycopg2.connect(
        DATABASE_URL,
        sslmode="require",
        connect_timeout=5,
    )


# ============================================================
# FASTAPI APPLICATION
# ============================================================
app = FastAPI(
    title="Creator Monetization Backend",
    version="2.0.0",
    description="Hybrid Pricing Engine + Telegram Bot + Paystack"
)


# ============================================================
# APPLICATION STARTUP
# ============================================================
@app.on_event("startup")
async def startup_event():
    logger.info("🚀 Backend starting up...")

    # 1) DATABASE MIGRATIONS
    try:
        run_migrations()
        logger.info("🛠 DB migrations complete")
    except Exception as e:
        logger.error(f"❌ Migration error: {e}")

    # 2) TELEGRAM BOT INITIALIZATION
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


# ============================================================
# APPLICATION SHUTDOWN
# ============================================================
@app.on_event("shutdown")
async def shutdown_event():
    try:
        await telegram_app.shutdown()
        logger.info("🛑 Telegram bot shutdown complete")
    except Exception as e:
        logger.error(f"❌ Telegram shutdown failed: {e}")


# ============================================================
# ROUTER REGISTRATION (ORDER MATTERS)
# ============================================================

# Pricing Engine (must come before webhook to prevent 404 interception)
app.include_router(pricing_router)

# Paystack Init + Checkout API
app.include_router(paystack_router)

# Telegram Webhook Receiver
app.include_router(telegram_router)


# ============================================================
# HEALTHCHECKS
# ============================================================
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


# ============================================================
# PAYSTACK WEBHOOK (PRO ACTIVATION)
# ============================================================
@app.post("/paystack/webhook")
async def paystack_webhook(request: Request):
    raw_body = await request.body()
    signature = request.headers.get("x-paystack-signature")

    if not signature:
        raise HTTPException(status_code=400, detail="Missing Paystack signature")

    expected = hmac.new(
        PAYSTACK_SECRET_KEY.encode(),
        raw_body,
        hashlib.sha512
    ).hexdigest()

    if not hmac.compare_digest(signature, expected):
        raise HTTPException(status_code=400, detail="Invalid Paystack signature")

    event = json.loads(raw_body)

    if event.get("event") != "charge.success":
        logger.info("📨 Non-billing webhook received — ignored.")
        return {"status": "ignored"}

    data = event.get("data", {})
    reference = data.get("reference")
    meta = data.get("metadata", {}) or {}
    telegram_id = str(meta.get("telegram_id"))

    if not reference or not telegram_id:
        logger.error("❌ Webhook missing reference or telegram_id")
        return {"status": "invalid"}

    conn = get_db()
    try:
        cur = conn.cursor()

        cur.execute(
            "UPDATE payments SET status='success', paid_at=CURRENT_TIMESTAMP WHERE reference=%s",
            (reference,),
        )

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
        logger.error(f"❌ Webhook DB error → {e}")
        conn.rollback()
        raise HTTPException(status_code=500, detail="Internal Error")
    finally:
        conn.close()

    logger.info(f"🎉 PRO Activated for Telegram User {telegram_id} (Ref: {reference})")
    return {"status": "upgraded", "telegram_id": telegram_id}
