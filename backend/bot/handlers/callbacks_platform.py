from __future__ import annotations
from typing import Optional, Dict, Any, cast

from telegram import Update, CallbackQuery
from telegram.ext import ContextTypes
from bot.keyboards.niches import niche_keyboard


async def platform_selected(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Handles platform button selection safely.
    Avoids MaybeInaccessibleMessage issues.
    """

    query: Optional[CallbackQuery] = update.callback_query
    if query is None:
        return

    await query.answer()

    data = query.data
    msg = query.message  # no type annotation (critical)

    # validate message access
    if msg is None or msg.chat is None:
        return

    chat_id = msg.chat.id  # correct way to get chat id

    if data is None:
        await context.bot.send_message(chat_id, "⚠️ Missing platform data.")
        return

    if not data.startswith("platform_"):
        await context.bot.send_message(chat_id, "⚠️ Unknown platform selection.")
        return

    platform = data.replace("platform_", "").lower()

    # safe user_data update
    ud = cast(Dict[str, Any], context.user_data)
    ud["platform"] = platform

    await context.bot.send_message(
        chat_id,
        f"🎯 Platform selected: *{platform.title()}*",
        parse_mode="Markdown"
    )

    await context.bot.send_message(
        chat_id,
        "📂 Now select your *niche:*",
        parse_mode="Markdown",
        reply_markup=niche_keyboard()
    )
