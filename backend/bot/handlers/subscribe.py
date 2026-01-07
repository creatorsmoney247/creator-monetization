# backend/bot/handlers/subscribe.py

import os
import logging
from typing import Optional

import requests
from telegram import Update
from telegram.ext import ContextTypes

logger = logging.getLogger(__name__)

# -------------------------------------------------
# CONFIG
# -------------------------------------------------
BASE_URL = os.getenv("BASE_URL")
if not BASE_URL:
    raise RuntimeError("BASE_URL environment variable not set")


PRO_AMOUNT_KOBO = 500_000  # ₦5,000 (example welcome price)

# -------------------------------------------------
# SAFE REPLY HELPER
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
        "You’ve seen where you stand in the creator market.\n"
        "PRO shows you *how to turn that position into income*.\n\n"
        "🧠 *What PRO unlocks (delivered within 24 hours):*\n"
        "• Market Positioning Blueprint\n"
        "• Brand Deal Reply Scripts (real scenarios)\n"
        "• Negotiation Playbook (what to say & when)\n"
        "• Pricing Mistakes to Avoid\n"
        "• Campaign Bundling Strategy\n"
        "• Professional Language Brands Respect\n\n"
        "📦 You’ll receive a *PRO Creator Monetization Pack*\n"
        "with PDFs, editable scripts, and examples.\n\n"
        "💳 *₦5,000 one-time (early access)*\n\n"
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

    await safe_reply(
        message,
        "💳 *Secure Payment (Paystack)*\n\n"
        "You’ll be redirected to Paystack to complete payment.\n"
        "After payment, your PRO access is unlocked automatically.\n\n"
        "⏱ Delivery: within *24 hours*.",
    )

    payload = {
        "email": f"user{user.id}@telegram.local",  # placeholder
        "amount": PRO_AMOUNT_KOBO,
        "metadata": {
            "telegram_id": str(user.id),
        },
    }

    try:
        response = requests.post(
            f"{BASE_URL}/paystack/init",
            json=payload,
            timeout=15,
        )
        response.raise_for_status()
        data = response.json()
    except Exception as e:
        logger.exception("Paystack init failed")
        await safe_reply(
            message,
            "🚧 *Payment service temporarily unavailable*\n\n"
            "Please try again shortly.",
        )
        return

    payment_url = data.get("authorization_url")
    if not payment_url:
        await safe_reply(
            message,
            "❌ *Payment initialization failed*\n\n"
            "Please try again later.",
        )
        return

    await safe_reply(
        message,
        f"👉 *Complete payment here:*\n{payment_url}",
        disable_web_page_preview=False,
    )
