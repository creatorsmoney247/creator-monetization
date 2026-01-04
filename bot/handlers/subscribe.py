# bot/handlers/subscribe.py

from telegram import Update
from telegram.ext import ContextTypes
import requests
import logging
from typing import Optional

API_URL = "http://127.0.0.1:8000"
PRO_AMOUNT_KOBO = 500000  # ₦5,000

logger = logging.getLogger(__name__)


# ---------- HELPERS ----------

async def safe_reply(
    message,
    text: str,
    parse_mode: Optional[str] = None,
    disable_web_page_preview: bool = True,
):
    if not message:
        return

    await message.reply_text(
        text,
        parse_mode=parse_mode,
        disable_web_page_preview=disable_web_page_preview,
    )


# ---------- SUBSCRIBE / PAY ----------
async def subscribe_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = update.effective_message
    if not message:
        return

    await message.reply_text(
        "🔓 **Upgrade to PRO Creator**\n\n"
        "You’ve seen where you stand in the creator market.\n"
        "PRO shows you **how to use that position to get paid properly**.\n\n"
        "🧠 **What PRO unlocks (delivered by email within 24 hours):**\n"
        "• Your **Market Positioning Blueprint**\n"
        "• **Brand Deal Reply Scripts** (multiple real scenarios)\n"
        "• A **Negotiation Playbook** (what to say & when)\n"
        "• **Pricing Mistakes to Avoid** (creator protection)\n"
        "• **Campaign Bundling Strategy** (earn more per deal)\n"
        "• A **Professional Language Guide** brands respect\n\n"
        "📦 You’ll receive a personalized PRO Creator Monetization Pack\n"
        "with PDFs, editable scripts, and practical examples.\n\n"
        "💳 **₦10,000 (Welcome pack for first 100 customers) / month**\n"
        "No contracts. Cancel anytime.\n\n"
        "👉 **Next step:**\n"
        "Type `pay` to unlock PRO.",
        parse_mode="Markdown",
    )

async def pay_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = update.effective_message
    user = update.effective_user

    if not message or not user:
        return

    await message.reply_text(
        "💳 **Secure Payment (Paystack)**\n\n"
        "You’ll be redirected to Paystack to complete payment.\n"
        "After successful payment, return here and type `deal`.\n\n"
        "⏱ PRO pack delivery: within **24 hours**.",
        parse_mode="Markdown",
    )

    payload = {
        "email": f"user{user.id}@telegram.local",  # placeholder email
        "amount": 500000,  # ₦5,000 in kobo
        "metadata": {
            "telegram_id": user.id
        }
    }

    try:
        res = requests.post(
            "http://127.0.0.1:8000/paystack/init",
            json=payload,
            timeout=10,
        )
        res.raise_for_status()
        data = res.json()
    except Exception:
        await message.reply_text("❌ Payment service temporarily unavailable.")
        return

    payment_url = data["authorization_url"]
    await message.reply_text(
        f"👉 **Complete payment here:**\n{payment_url}"
    )
