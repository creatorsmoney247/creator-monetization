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

# Prefer Render-provided BASE_URL, otherwise fallback to production default
BACKEND_BASE_URL = os.getenv(
    "BASE_URL",
    "https://creator-monetization.onrender.com"
).rstrip("/")


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

    await safe_reply(
        message,
        "💳 *Initializing secure payment...*"
    )

    payload = {
        "email": f"user{user.id}@gmail.com",   # placeholder but valid
        "amount": PRO_AMOUNT_KOBO,
        "metadata": {"telegram_id": user.id}
    }

    payment_init_url = f"{BACKEND_BASE_URL}/paystack/init"

    logger.info(f"Payment init → {payment_init_url}")

    try:
        response = requests.post(
            payment_init_url,
            json=payload,
            timeout=20,  # ↑ Paystack can be slow
        )
        response.raise_for_status()
        data = response.json()

    except Exception as e:
        logger.error(f"Payment init failed: {e}")
        await safe_reply(
            message,
            "❌ Payment service temporarily unavailable.\nPlease try again shortly."
        )
        return

    if "authorization_url" not in data:
        logger.error(f"Payment init malformed response: {data}")
        await safe_reply(
            message,
            "⚠️ Unexpected payment response.\nPlease try again later."
        )
        return

    payment_url = data["authorization_url"]

    await safe_reply(
        message,
        f"👉 *Complete payment here:*\n{payment_url}",
        disable_web_page_preview=False
    )
