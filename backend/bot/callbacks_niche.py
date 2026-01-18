from __future__ import annotations
from typing import Optional, Dict, Any, cast
from telegram import Update, CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
import httpx

from bot.handlers.subscribe import get_backend_url
from app.services.pro_service import is_user_pro


async def niche_selected(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    if query is None:
        return
    
    await query.answer()
    
    msg = query.message
    if msg is None or msg.chat is None:
        return
    
    chat_id = msg.chat.id
    data = query.data
    
    if data is None or not data.startswith("niche_"):
        await context.bot.send_message(chat_id, "⚠️ Unknown niche selection.")
        return
    
    niche = data.replace("niche_", "").lower()
    
    ud = cast(Dict[str, Any], context.user_data)
    ud["niche"] = niche
    
    await context.bot.send_message(
        chat_id,
        f"🎯 Niche selected: *{niche.title()}*",
        parse_mode="Markdown"
    )
    
    await context.bot.send_message(chat_id, "📈 Generating pricing insights...")

    await generate_pricing(chat_id, context)


async def generate_pricing(chat_id: int, context: ContextTypes.DEFAULT_TYPE) -> None:
    ud = cast(Dict[str, Any], context.user_data)
    
    followers = ud.get("stats", {}).get("followers")
    avg_views = ud.get("stats", {}).get("avg_views")
    engagement = ud.get("stats", {}).get("engagement")
    platform = ud.get("platform")
    niche = ud.get("niche")
    
    if not platform or not niche:
        await context.bot.send_message(chat_id, "⚠️ Missing platform or niche. Start again with /start.")
        return
    
    # PRO status (DB check)
    is_pro_user = is_user_pro(str(chat_id))
    
    backend_url = get_backend_url()
    url = f"{backend_url}/pricing/calculate"

    payload = {
        "telegram_id": str(chat_id),
        "followers": followers,
        "avg_views": avg_views,
        "engagement_rate": engagement,
        "platform": platform,
        "niche": niche
    }

    try:
        async with httpx.AsyncClient(timeout=20) as client:
            resp = await client.post(url, json=payload)
            resp.raise_for_status()
            result = resp.json()
    except Exception as e:
        await context.bot.send_message(chat_id, f"⚠️ Backend pricing error: {e}")
        return
    
    # At this point result = hybrid_pricing_engine output
    mode = result["mode"]
    rec_ngn = result["recommended_ngn"]
    min_ngn = result["minimum_ngn"]
    wl_ngn = result.get("whitelist_ngn")
    rec_usd = result["recommended_usd"]
    wl_usd = result.get("whitelist_usd")
    usage_months = result["usage_months"]

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
        f"💰 *Recommended Rate:* ₦{rec_ngn:,}\n"
        f"🟡 *Minimum Acceptable:* ₦{min_ngn:,}\n"
        f"*Usage Rights:* {usage_months}-Month\n"
    )

    if not is_pro_user:
        text += (
            "\n🔒 *Whitelisting Rights:* Locked (PRO only)\n"
            "✨ Unlock PRO for whitelisting + USD dual pricing."
        )
        buttons = [[InlineKeyboardButton("🔐 Unlock PRO", callback_data="upgrade_pro")]]
    else:
        if wl_ngn:
            text += (
                f"\n💥 *With Whitelisting:* ₦{wl_ngn:,}\n"
                f"💱 *USD Rate:* ~${rec_usd:,.2f}\n"
            )
            if wl_usd:
                text += f"💱 *USD + Whitelisting:* ~${wl_usd:,.2f}\n"
        buttons = [[InlineKeyboardButton("📁 Export Ratecard", callback_data="export_ratecard")]]

    await context.bot.send_message(
        chat_id,
        text,
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(buttons)
    )
