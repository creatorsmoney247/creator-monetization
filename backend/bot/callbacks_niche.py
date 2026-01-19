from __future__ import annotations
from typing import Optional, Dict, Any, cast

from telegram import Update, CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
import httpx

from bot.handlers.subscribe import get_backend_url
from app.services.pro_service import is_user_pro

# -------------------------------------------------
# PLATFORM NORMALIZATION MAP
# -------------------------------------------------
PLATFORM_MAP: Dict[str, str] = {
    "instagram": "instagram",
    "tiktok": "tiktok",
    "ytshorts": "youtube",
    "youtube": "youtube",
    "twitter": "twitter",
    "facebook": "facebook",
    "other": "instagram"
}

# -------------------------------------------------
# NICHE NORMALIZATION MAP
# -------------------------------------------------
NICHE_MAP: Dict[str, str] = {
    "fashion": "beauty",
    "beauty": "beauty",
    "tech": "tech",
    "comedy": "comedy",
    "lifestyle": "lifestyle",
    "food": "lifestyle",
    "music": "entertainment",
    "fitness": "fitness",
    "other": "general"
}


# =================================================
# CALLBACK: NICHE SELECTED
# =================================================
async def niche_selected(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query: Optional[CallbackQuery] = update.callback_query
    if query is None:
        return

    await query.answer()

    msg = query.message
    if msg is None or msg.chat is None:
        return

    chat_id = msg.chat.id
    data = query.data or ""

    if not data.startswith("niche_"):
        await context.bot.send_message(chat_id, "⚠️ Unknown niche selection.")
        return

    raw_niche = data.replace("niche_", "").lower()
    normalized_niche = NICHE_MAP.get(raw_niche, "general")

    ud = cast(Dict[str, Any], context.user_data)
    ud["niche"] = normalized_niche

    await context.bot.send_message(
        chat_id,
        f"🎯 Niche selected: *{raw_niche.title()}*",
        parse_mode="Markdown"
    )

    await context.bot.send_message(chat_id, "📈 Generating pricing insights...")
    await generate_pricing(chat_id, context)


# =================================================
# GENERATE PRICING (RANGE MODE)
# =================================================
async def generate_pricing(chat_id: int, context: ContextTypes.DEFAULT_TYPE) -> None:
    ud = cast(Dict[str, Any], context.user_data)

    followers = ud.get("stats", {}).get("followers")
    avg_views = ud.get("stats", {}).get("avg_views")
    engagement = ud.get("stats", {}).get("engagement")

    raw_platform = ud.get("platform")
    niche = ud.get("niche")

    # ---- SAFE PLATFORM NORMALIZATION ----
    raw = str(raw_platform).strip().lower() if raw_platform is not None else ""
    platform = PLATFORM_MAP.get(raw, "instagram")

    if not platform or not niche:
        await context.bot.send_message(chat_id, "⚠️ Missing platform or niche. Start again with /start.")
        return

    # ---- PRO STATUS ----
    is_pro_user = is_user_pro(str(chat_id))

    backend_url = get_backend_url()
    url = f"{backend_url}/pricing/range"   # <--- RANGE ENDPOINT

    payload = {
        "telegram_id": str(chat_id),
        "followers": followers,
        "avg_views": avg_views,
        "engagement_rate": engagement,
        "platform": platform,
        "niche": niche
    }

    # ---- BACKEND CALL ----
    try:
        async with httpx.AsyncClient(timeout=20) as client:
            resp = await client.post(url, json=payload)
            resp.raise_for_status()
            result = resp.json()
    except Exception as e:
        await context.bot.send_message(chat_id, f"⚠️ Backend pricing error: {e}")
        return

    # ---- BACKEND ERROR HANDLING ----
    if result.get("error"):
        await context.bot.send_message(chat_id, "⚠️ Not enough data to compute pricing. Provide followers or avg views.")
        return

    mode = result.get("mode", "unknown")
    min_ngn = result.get("min")
    mid_ngn = result.get("mid")
    max_ngn = result.get("max")
    usage_months = result.get("usage_months", 3)

    # ---- MESSAGE BUILD ----
    text = (
        "📊 *Creator Pricing Insight*\n\n"
        f"*Platform:* {platform.title()}\n"
        f"*Niche:* {niche.title()}\n"
    )

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

    text += (
        f"💰 *Pricing Range (NGN):*\n"
        f"• *Minimum:* ₦{min_ngn:,}\n"
        f"• *Midline:* ₦{mid_ngn:,}\n"
        f"• *Premium:* ₦{max_ngn:,}\n\n"
        f"*Usage Rights:* {usage_months}-Month\n"
    )

    # ---- BUTTON & WHITELISTING LOGIC ----
    buttons = []

    if not is_pro_user:
        text += (
            "🔒 *Whitelisting Rights:* Locked (PRO only)\n"
            "✨ Unlock PRO for usage + whitelisting + export."
        )
        buttons.append([InlineKeyboardButton("🔐 Unlock PRO", callback_data="upgrade_pro")])
    else:
        text += "💼 *PRO Unlocked:* Whitelisting available\n"
        buttons.append([InlineKeyboardButton("📁 Export Ratecard", callback_data="export_ratecard")])

    await context.bot.send_message(
        chat_id,
        text,
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(buttons)
    )
