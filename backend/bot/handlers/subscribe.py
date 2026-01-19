# backend/bot/handlers/subscribe.py

from __future__ import annotations

import logging
import os
import httpx
import asyncio
from typing import Optional

from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import ContextTypes

from app.services.pro_service import is_user_pro

logger = logging.getLogger(__name__)

# -------------------------------------------------
# CONFIG
# -------------------------------------------------
PRO_AMOUNT_KOBO = 1_000_000          # ₦10,000 one-time
ELITE_BASE_FEE_KOBO = 2_500_000      # ₦25,000 per package

PUBLIC_BACKEND_URL = "https://creator-monetization.onrender.com"
BASE_URL = os.getenv("BASE_URL")     # optional override for Render deployments


def get_backend_url() -> str:
    """
    1) use BASE_URL if provided
    2) else fallback to PUBLIC_BACKEND_URL
    """
    if BASE_URL and BASE_URL.strip():
        return BASE_URL.strip().rstrip("/")
    return PUBLIC_BACKEND_URL


# -------------------------------------------------
# SAFE REPLY (no crash if message missing)
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


# =================================================
# /subscribe COMMAND
# =================================================
async def subscribe_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = update.effective_message
    if not message:
        return

    keyboard = InlineKeyboardMarkup(
        [
            [InlineKeyboardButton("🚀 Upgrade to PRO (₦10,000)", callback_data="upgrade_pro")],
            [InlineKeyboardButton("📦 ELITE Deal Packaging (₦25,000)", callback_data="elite_package")],
        ]
    )

    await safe_reply(
        message,
        "🔥 *Creator Monetization Tiers*\n\n"
        "Choose your current monetization path:\n\n"
        "🆓 *FREE*\n"
        "• Pricing Insights Only\n"
        "• Followers/View Benchmarking\n\n"
        "💼 *PRO — ₦10,000 one-time*\n"
        "• Monetization Toolkit\n"
        "• Brand Deal Scripts\n"
        "• Negotiation Playbook\n"
        "• Positioning Blueprint\n"
        "• Campaign Bundling Strategy\n\n"
        "🏛 *ELITE — ₦25,000 per package*\n"
        "• Done-For-You Deal Packaging\n"
        "• Baseline Pricing + Usage Rights\n"
        "• Whitelisting/UGC Positioning\n"
        "• Pitch-ready Deliverables\n\n"
        "👇 Select an option to continue:",
        parse_mode="Markdown",
        disable_web_page_preview=True,
    )

    await message.reply_text(
        "Need help choosing?\nJust type: `help tiers`",
        parse_mode="Markdown",
        reply_markup=keyboard
    )


# =================================================
# UPGRADE PRO CALLBACK (PAYSTACK INIT)
# =================================================
async def upgrade_pro(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    if not query or not query.message or not query.message.chat:
        return

    chat_id = query.message.chat.id
    telegram_id = str(chat_id)

    # Already PRO?
    if is_user_pro(telegram_id):
        await context.bot.send_message(
            chat_id,
            "🎉 *You're already PRO!*\n\n"
            "You already have:\n"
            "✔ Whitelisting\n"
            "✔ USD Pricing\n"
            "✔ Export Tools\n"
            "✔ Negotiation Scripts",
            parse_mode="Markdown"
        )
        return

    backend_url = get_backend_url()
    init_url = f"{backend_url}/paystack/init"

    payload = {
        "telegram_id": telegram_id
    }

    await context.bot.send_message(
        chat_id,
        "💳 *Generating secure checkout link...*",
        parse_mode="Markdown"
    )

    try:
        async with httpx.AsyncClient(timeout=20) as client:
            resp = await client.post(init_url, json=payload)
            resp.raise_for_status()
            data = resp.json()
    except Exception as e:
        logger.error(f"[UPGRADE_PRO] Init error → {e}")
        await context.bot.send_message(
            chat_id,
            "❌ Payment initialization failed.\nPlease try again shortly."
        )
        return

    # Extract Paystack payment link
    auth_url = (
        data.get("authorization_url")
        or data.get("data", {}).get("authorization_url")
        or None
    )

    if not auth_url:
        logger.error(f"[UPGRADE_PRO] Missing authorization_url → {data}")
        await context.bot.send_message(chat_id, "⚠️ Payment link unavailable. Try again later.")
        return

    btn = InlineKeyboardButton("💳 Pay with Paystack", url=auth_url)

    await context.bot.send_message(
        chat_id,
        "💼 *PRO Upgrade — ₦10,000 One-Time*\n\n"
        "You are unlocking:\n"
        "✔ USD Dual Pricing\n"
        "✔ Whitelisting Rights\n"
        "✔ Ratecard Export Tools\n"
        "✔ Brand Deal Scripts\n"
        "✔ Negotiation Playbooks\n"
        "✔ Monetization Frameworks\n\n"
        "Click below to continue:👇",
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup([[btn]])
    )


# =================================================
# /pay COMMAND (LEGACY BOT PAYMENT)
# =================================================
async def pay_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = update.effective_message
    user = update.effective_user

    if not message or not user:
        return

    backend_url = get_backend_url()
    init_url = f"{backend_url}/paystack/init"

    await safe_reply(message, "💳 *Initializing secure payment...*")

    payload = {
        "email": f"user{user.id}@gmail.com",
        "amount": PRO_AMOUNT_KOBO,
        "metadata": {"telegram_id": user.id},
    }

    logger.info(f"[PAY] Init → {init_url}")

    raw = None
    for attempt in range(3):
        try:
            async with httpx.AsyncClient(timeout=20) as client:
                resp = await client.post(init_url, json=payload)
                resp.raise_for_status()
                raw = resp.json()
                break
        except Exception as e:
            logger.warning(f"[PAY] Attempt {attempt+1}/3 failed → {e}")
            if attempt < 2:
                await asyncio.sleep(3)
            else:
                logger.error(f"[PAY] Init failed after 3 attempts → {e}")
                await safe_reply(
                    message,
                    "❌ Payment service temporarily unavailable.\nPlease try again shortly."
                )
                return

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
        await safe_reply(message, "⚠️ Unexpected payment response.\nPlease try again later.")
        return

    await safe_reply(
        message,
        f"👉 *Complete payment here:*\n{auth_url}",
        disable_web_page_preview=False
    )
