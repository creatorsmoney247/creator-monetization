# backend/bot/handlers/subscribe.py

import logging
import requests
from typing import Optional

from telegram import Update
from telegram.ext import ContextTypes

logger = logging.getLogger(__name__)

# -------------------------------------------------
# CONFIG
# -------------------------------------------------
PRO_AMOUNT_KOBO = 1_000_000  # ₦10,000
BACKEND_BASE_URL = "https://creator-monetization.onrender.com"


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
# SUBSCRIBE COMMAND
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
# PAY COMMAND
# -------------------------------------------------
async def pay_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = update.effective_message
    user = update.effective_user

    if not message or not user:
        return

    await message.reply_text(
        "💳 *Initializing secure payment...*",
        parse_mode="Markdown"
    )

    payload = {
        "email": f"user{user.id}@gmail.com",   # VALID placeholder email
        "amount": PRO_AMOUNT_KOBO,             # USE config
        "metadata": {"telegram_id": user.id}
    }

    try:
        response = requests.post(
            "http://localhost:10000/paystack/init",
            json=payload,
            timeout=10,
        )
        response.raise_for_status()
        data = response.json()
    except Exception as e:
        logger.error(f"Payment init failed: {e}")
        await message.reply_text(
            "❌ Payment service temporarily unavailable.\nPlease try again shortly.",
            parse_mode="Markdown"
        )
        return

    payment_url = data["authorization_url"]

    await message.reply_text(
        f"👉 *Complete payment here:*\n{payment_url}",
        parse_mode="Markdown",
        disable_web_page_preview=False,
    )
