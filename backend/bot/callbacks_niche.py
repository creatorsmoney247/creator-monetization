from __future__ import annotations
from typing import Optional, Dict, Any, cast

from telegram import Update, CallbackQuery
from telegram.ext import ContextTypes


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

    chat_id = msg.chat.id  # <-- FIXED HERE

    # Validate callback data
    if data is None or not data.startswith("niche_"):
        await context.bot.send_message(chat_id, "⚠️ Unknown niche selection.")
        return

    niche = data.replace("niche_", "").lower()

    # Store in user_data
    ud = cast(Dict[str, Any], context.user_data)
    ud["niche"] = niche

    await context.bot.send_message(
        chat_id,
        f"🎯 Niche selected: *{niche.title()}*",
        parse_mode="Markdown"
    )

    await context.bot.send_message(
        chat_id,
        "📈 Generating pricing insights...",
    )

    # Generate free pricing
    await generate_free_pricing(chat_id, context)


async def generate_free_pricing(chat_id: int, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Simple mock pricing for free users.
    """
    ud = cast(Dict[str, Any], context.user_data)

    followers = ud.get("stats", {}).get("followers")
    avg_views = ud.get("stats", {}).get("avg_views")
    engagement = ud.get("stats", {}).get("engagement")
    platform = ud.get("platform")
    niche = ud.get("niche")

    # Guard missing data
    if followers is None or avg_views is None or engagement is None or platform is None or niche is None:
        await context.bot.send_message(chat_id, "⚠️ Missing data. Start again with /start.")
        return

    # ---- Mock pricing model (upgrade later) ----
    recommended = int((avg_views * engagement) * 2)
    minimum = int(recommended * 0.7)

    text = (
        "📊 *Creator Market Insight (Nigeria)*\n\n"
        f"*Platform:* {platform.title() if isinstance(platform, str) else platform}\n"
        f"*Niche:* {niche.title() if isinstance(niche, str) else niche}\n\n"
        f"*Followers:* {followers:,}\n"
        f"*Avg Views:* {avg_views:,}\n"
        f"*Engagement:* {engagement:.2%}\n\n"
        "💵 *Recommended Brand Rate:*\n"
        f"• Typical: *₦{recommended:,}*\n"
        f"• Minimum you should accept: *₦{minimum:,}*\n\n"
        "⚠️ This is a *FREE estimate*.\n"
        "PRO unlocks whitelisting + usage rights + negotiation scripts.\n\n"
        "✨ Type `upgrade` to unlock serious pricing."
    )

    await context.bot.send_message(chat_id, text, parse_mode="Markdown")
