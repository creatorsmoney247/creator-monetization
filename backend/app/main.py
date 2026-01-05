# backend/app/main.py

# -------------------------------------------------
# PATH SETUP (PROJECT ROOT)
# -------------------------------------------------
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

# -------------------------------------------------
# STANDARD IMPORTS
# -------------------------------------------------
import os
import json
import hmac
import hashlib
import sqlite3
import logging
import requests
import uuid
from fastapi import FastAPI, Request, HTTPException
from dotenv import load_dotenv

# -------------------------------------------------
# ROUTES (ABSOLUTE, PRODUCTION-SAFE)
# -------------------------------------------------
from backend.app.routes.telegram_webhook import router as telegram_router

# -------------------------------------------------
# LOGGING
# -------------------------------------------------
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("creator-backend")

# -------------------------------------------------
# ENV
# -------------------------------------------------
load_dotenv()

def get_required_env(name: str) -> str:
    value = os.getenv(name)
    if not value or not value.strip():
        raise RuntimeError(f"❌ Missing required env var: {name}")
    return value

PAYSTACK_SECRET_KEY = get_required_env("PAYSTACK_SECRET_KEY")
BOT_DB_PATH = get_required_env("BOT_DB_PATH")

# -------------------------------------------------
# DATABASE
# -------------------------------------------------
BOT_DB_PATH = get_required_env("BOT_DB_PATH")
DB_PATH = Path(BOT_DB_PATH)

def get_db():
    return sqlite3.connect(DB_PATH, check_same_thread=False)

def init_db():
    # Only create parent dirs if not Render disk
    if not str(DB_PATH).startswith("/data/"):
        DB_PATH.parent.mkdir(parents=True, exist_ok=True)

    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    cur = conn.cursor()

    cur.execute("""
        CREATE TABLE IF NOT EXISTS creators (
            telegram_id TEXT PRIMARY KEY,
            username TEXT,
            is_pro INTEGER DEFAULT 0,
            pro_activated_at TEXT
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS payments (
            reference TEXT PRIMARY KEY,
            telegram_id TEXT NOT NULL,
            amount INTEGER NOT NULL,
            status TEXT NOT NULL
        )
    """)

    conn.commit()
    conn.close()

# -------------------------------------------------
# APP
# -------------------------------------------------
app = FastAPI(title="Creator Monetization Backend")
app.include_router(telegram_router)

init_db()

# -------------------------------------------------
# HEALTH
# -------------------------------------------------
@app.get("/health")
def health():
    return {"status": "ok"}

# -------------------------------------------------
# PRICING
# -------------------------------------------------
@app.post("/pricing/calculate")
def calculate_pricing(payload: dict):
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
# PAYSTACK INIT
# -------------------------------------------------
@app.post("/paystack/init")
def paystack_init(payload: dict):
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
        raise HTTPException(status_code=400, detail="Paystack init failed")

    conn = get_db()
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO payments VALUES (?, ?, ?, 'pending')",
        (reference, telegram_id, amount),
    )
    conn.commit()
    conn.close()

    return response.json()["data"]

# -------------------------------------------------
# PAYSTACK WEBHOOK
# -------------------------------------------------
@app.post("/paystack/webhook")
async def paystack_webhook(request: Request):
    raw = await request.body()
    signature = request.headers.get("x-paystack-signature")

    expected = hmac.new(
        PAYSTACK_SECRET_KEY.encode(),
        raw,
        hashlib.sha512
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

    cur.execute("UPDATE payments SET status='success' WHERE reference=?", (reference,))
    cur.execute("""
        INSERT INTO creators (telegram_id, is_pro, pro_activated_at)
        VALUES (?, 1, CURRENT_TIMESTAMP)
        ON CONFLICT(telegram_id)
        DO UPDATE SET is_pro=1, pro_activated_at=CURRENT_TIMESTAMP
    """, (telegram_id,))

    conn.commit()
    conn.close()

    return {"status": "upgraded"}
