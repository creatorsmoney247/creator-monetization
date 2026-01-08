# backend/bot/handlers/subscribe.py

import logging
from typing import Optional

from telegram import Update
from telegram.ext import ContextTypes

from app.services.paystack_service import init_paystack_payment

logger = logging.getLogger(__name__)

# -------------------------------------------------
# CONFIG
# -------------------------------------------------
PRO_AMOUNT_KOBO = 1_000_000  # ₦10,000


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
# PAY COMMAND (STEP 1: ASK FOR EMAIL)
# -------------------------------------------------
async def pay_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = update.effective_message
    user = update.effective_user

    if not message or not user:
        return

    user_data = context.user_data
    if user_data is None:
        return

    # Ask for email if we don't have it yet
    if "pay_email" not in user_data:
        user_data["awaiting_pay_email"] = True
        await safe_reply(
            message,
            "📧 *Enter your email address*\n\n"
            "This is required for Paystack payment and receipt delivery.",
        )
        return

    email = user_data["pay_email"]

    # -------------------------------------------------
    # INIT PAYSTACK PAYMENT
    # -------------------------------------------------
    try:
        payment_url = init_paystack_payment(
            email=email,
            amount=PRO_AMOUNT_KOBO,
            telegram_id=str(user.id),
        )
    except Exception:
        logger.exception("Paystack init failed")
        await safe_reply(
            message,
            "🚧 *Payment service temporarily unavailable*\n\n"
            "Please try again shortly.",
        )
        return

    await safe_reply(
        message,
        f"👉 *Complete payment here:*\n{payment_url}",
        disable_web_page_preview=False,
    )
