import logging
import os
import httpx
import asyncio
from typing import Optional

from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import ContextTypes

logger = logging.getLogger(__name__)

# -------------------------------------------------
# CONFIG
# -------------------------------------------------
PRO_AMOUNT_KOBO = 1_000_000   # ₦10,000 one-time
ELITE_BASE_FEE_KOBO = 2_500_000  # ₦25,000 per package (editable)

PUBLIC_BACKEND_URL = "https://creator-monetization.onrender.com"
BASE_URL = os.getenv("BASE_URL")


def get_backend_url() -> str:
    """
    Determines correct backend URL priority:
    1. Explicit BASE_URL if provided (local/override)
    2. Render public URL if RENDER=true
    3. Local fallback for development
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
        "• Done-For-You Brand Deal Packaging\n"
        "• Market-ready Deliverables\n"
        "• Baseline Pricing + Usage Rights\n"
        "• Whitelisting/UGC Positioning\n"
        "• Pitch-ready for Brands/Agencies\n\n"
        "👇 Select an option to continue:",
        parse_mode="Markdown",
        disable_web_page_preview=True,
    )

    await message.reply_text(
        "Need help choosing?\nJust type: `help tiers`",
        parse_mode="Markdown",
        reply_markup=keyboard
    )


# -------------------------------------------------
# /pay COMMAND (PRO BILLING)
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
        "metadata": {"telegram_id": user.id},
    }

    logger.info(f"[PAY] Init → {payment_init_url}")

    raw = None
    for attempt in range(3):
        try:
            async with httpx.AsyncClient(timeout=20) as client:
                resp = await client.post(payment_init_url, json=payload)
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

    # Normalize Paystack response
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
