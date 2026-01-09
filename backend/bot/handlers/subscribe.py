# backend/bot/handlers/subscribe.py

import logging
import os
import requests
from typing import Optional

from telegram import Update
from telegram.ext import ContextTypes

logger = logging.getLogger(__name__)

# -------------------------------------------------
# CONFIG
# -------------------------------------------------
PRO_AMOUNT_KOBO = 1_000_000  # ₦10,000

# PUBLIC BACKEND URL (Render)
PUBLIC_BACKEND_URL = "https://creator-monetization.onrender.com"

# BASE_URL for local override
BASE_URL = os.getenv("BASE_URL")

def get_backend_url() -> str:
    """
    Determines correct backend URL priority:
    1. Explicit BASE_URL if provided
    2. Render public URL
    3. Local fallback
    """
    if BASE_URL:
        return BASE_URL.rstrip("/")

    if os.getenv("RENDER") == "true":
        return PUBLIC_BACKEND_URL

    return "http://127.0.0.1:8000"


# -------------------------------------------------
# SAFE REPLY
# -------------------------------------------------
async def safe_reply(
    message,
    text: str,
    parse_mode: Optional[str] = "Markdown",
    disable_web_page_preview: bool = True,
):
    if not message:
        return

    await message.reply_text(
        text,
        parse_mode=parse_mode,
        disable_web_page_preview=disable_web_page_preview,
    )


# -------------------------------------------------
# /subscribe COMMAND
# -------------------------------------------------
async def subscribe_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = update.effective_message
    if not message:
        return

    await safe_reply(
        message,
        "🔓 *Upgrade to PRO Creator*\n\n"
        "PRO shows you *how to turn your reach into income*.\n\n"
        "🧠 *What PRO unlocks (delivered within 24 hours):*\n"
        "• Market Positioning Blueprint\n"
        "• Brand Deal Reply Scripts\n"
        "• Negotiation Playbook\n"
        "• Pricing Mistakes to Avoid\n"
        "• Campaign Bundling Strategy\n"
        "• Professional Brand Language\n\n"
        "💳 *₦10,000 one-time*\n\n"
        "👉 *Next step:* Type `pay` to continue.",
    )


# -------------------------------------------------
# /pay COMMAND
# -------------------------------------------------
async def pay_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = update.effective_message
    user = update.effective_user

    if not message or not user:
        return

    backend_url = get_backend_url()
    payment_init_url = f"{backend_url}/paystack/init"

    await safe_reply(
        message,
        "💳 *Initializing secure payment...*"
    )

    payload = {
        "email": f"user{user.id}@gmail.com",
        "amount": PRO_AMOUNT_KOBO,
        "metadata": {"telegram_id": user.id}
    }

    logger.info(f"[PAY] Init → {payment_init_url}")

    try:
        response = requests.post(
            payment_init_url,
            json=payload,
            timeout=20
        )
        response.raise_for_status()
        raw = response.json()

    except Exception as e:
        logger.error(f"[PAY] Init failed → {e}")
        await safe_reply(
            message,
            "❌ Payment service temporarily unavailable.\nPlease try again shortly."
        )
        return

    # Normalize Paystack response shape
    if isinstance(raw, dict):
        if "authorization_url" in raw:
            auth_url = raw["authorization_url"]
        elif "data" in raw and isinstance(raw["data"], dict):
            auth_url = raw["data"].get("authorization_url")
        else:
            auth_url = None
    else:
        auth_url = None

    if not auth_url:
        logger.error(f"[PAY] Unexpected response: {raw}")
        await safe_reply(
            message,
            "⚠️ Unexpected payment response.\nPlease try again later."
        )
        return

    await safe_reply(
        message,
        f"👉 *Complete payment here:*\n{auth_url}",
        disable_web_page_preview=False
    )
