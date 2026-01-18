# backend/bot/handlers/callbacks_niche.py

from __future__ import annotations
from typing import Optional, Dict, Any, cast
import os
import requests

from telegram import Update, CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes

# BACKEND URL (from env or default)
BACKEND_URL = os.getenv("BACKEND_URL", "http://localhost:8000")

async def niche_selected(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Handles Niche selection via inline buttons.
    """

    query: Optional[CallbackQuery] = update.callback_query
    if query is None:
        return

    await query.answer()

    data = query.data
    msg = query.message

    if msg is None or msg.chat is None:
        return

    chat_id = msg.chat.id

    if data is None or not data.startswith("niche_"):
        await context.bot.send_message(chat_id, "⚠️ Unknown niche selection.")
        return

    raw_niche = data.replace("niche_", "").lower()

    NICHE_MAP = {
        "fashion": "beauty",
        "tech": "tech",
        "comedy": "comedy",
        "lifestyle": "lifestyle",
        "food": "lifestyle",
        "music": "entertainment",
        "fitness": "fitness",
        "other": "general",
    }

    niche = NICHE_MAP.get(raw_niche, "general")


    ud = cast(Dict[str, Any], context.user_data)
    ud["niche"] = niche

    await context.bot.send_message(
        chat_id,
        f"🎯 Niche selected: *{niche.title()}*",
        parse_mode="Markdown"
    )

    await context.bot.send_message(
        chat_id,
        "📈 Generating pricing insights..."
    )

    # -----------------------------
    # BACKEND PRICING CALL
    # -----------------------------
    stats = ud.get("stats", {})
    payload = {
        "telegram_id": str(chat_id),
        "followers": stats.get("followers"),
        "avg_views": stats.get("avg_views"),
        "engagement_rate": stats.get("engagement"),
        "platform": ud.get("platform"),
        "niche": ud.get("niche"),
    }

    try:
        resp = requests.post(f"{BACKEND_URL}/pricing/calculate", json=payload, timeout=12)
        resp.raise_for_status()
        result = resp.json()
    except Exception as e:
        await context.bot.send_message(chat_id, f"⚠️ Backend pricing error: {e}")
        return

    # Save backend result
    ud["pricing_result"] = result

    # Render output
    await generate_pricing(chat_id, context)


async def generate_pricing(chat_id: int, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Formats FREE + PRO pricing output using backend hybrid results.
    """

    ud = cast(Dict[str, Any], context.user_data)
    result = ud.get("pricing_result")

    if not result:
        await context.bot.send_message(chat_id, "⚠️ Missing pricing result. Start again with /start.")
        return

    platform = result.get("platform")
    niche = result.get("niche")
    mode = result.get("mode")
    followers = result.get("followers")
    avg_views = result.get("avg_views")
    engagement = result.get("engagement")
    rec_ngn = result.get("recommended_ngn")
    min_ngn = result.get("minimum_ngn")
    wl_ngn = result.get("whitelist_ngn")
    rec_usd = result.get("recommended_usd")
    wl_usd = result.get("whitelist_usd")
    usage_months = result.get("usage_months", 3)
    is_pro_user = result.get("is_pro", False)

    # HEADER
    text = (
        "📊 *Creator Pricing Insight*\n\n"
        f"*Platform:* {platform.title()}\n"
        f"*Niche:* {niche.title()}\n"
    )

    # Stats section
    if mode == "full":
        text += (
            f"*Followers:* {followers:,}\n"
            f"*Avg Views:* {avg_views:,}\n"
            f"*Engagement:* {engagement:.2%}\n\n"
        )
    elif mode == "followers_only":
        text += f"*Followers:* {followers:,}\n\n"
    elif mode == "views_only":
        text += f"*Avg Views:* {avg_views:,}\n\n"

    # Base pricing
    text += (
        f"💰 *Recommended Rate:* ₦{rec_ngn:,}\n"
        f"🟡 *Minimum Acceptable:* ₦{min_ngn:,}\n"
        f"*Usage Rights:* {usage_months}-Month\n"
    )

    # FREE vs PRO logic
    if not is_pro_user:
        text += (
            "\n🔒 *Whitelisting Rights:* Locked (PRO only)\n"
            "Whitelisting allows brands to run ads with your content.\n\n"
            "✨ Unlock PRO to access:\n"
            "• Whitelisting Pricing\n"
            "• Usage Rights Controls\n"
            "• USD + NGN Dual Rates\n"
            "• Negotiation Scripts\n"
            "• Exportable Ratecards\n"
        )
    else:
        if wl_ngn:
            text += (
                f"\n💥 *With Whitelisting:* ₦{wl_ngn:,}\n"
                f"💱 *USD Rate:* ~${rec_usd:,.2f}\n"
            )
            if wl_usd:
                text += f"💱 *USD + Whitelisting:* ~${wl_usd:,.2f}\n"

    # CTA buttons
    buttons = []

    if not is_pro_user:
        buttons.append([
            InlineKeyboardButton("🔐 Unlock PRO", callback_data="upgrade_pro"),
            InlineKeyboardButton("📦 Deal Packaging", callback_data="deal_packaging")
        ])
    else:
        buttons.append([
            InlineKeyboardButton("📦 Deal Packaging", callback_data="deal_packaging"),
            InlineKeyboardButton("📁 Export Ratecard", callback_data="export_ratecard")
        ])

    reply_markup = InlineKeyboardMarkup(buttons)

    await context.bot.send_message(
        chat_id,
        text,
        parse_mode="Markdown",
        reply_markup=reply_markup
    )
