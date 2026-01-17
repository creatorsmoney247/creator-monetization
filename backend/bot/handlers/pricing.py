# bot/handlers/pricing.py

import re
from typing import cast, Dict, Any
from telegram import Update
from telegram.ext import ContextTypes

from bot.keyboards.platforms import platform_keyboard


# -------------------------------------------------
# HELPERS
# -------------------------------------------------
def parse_number(value: str) -> int:
    value = value.strip().replace(",", "").lower()
    if value.endswith("k"):
        return int(float(value[:-1]) * 1_000)
    if value.endswith("m"):
        return int(float(value[:-1]) * 1_000_000)
    return int(float(value))


def parse_engagement(er_raw: str) -> float:
    """Parses engagement rate ensuring it is between 0 and 1."""
    er = float(er_raw)
    if not (0 < er <= 1):
        raise ValueError("Invalid engagement")
    return er


# -------------------------------------------------
# TELEGRAM HANDLER (USED BY text_router)
# -------------------------------------------------
async def pricing_calc(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = update.effective_message
    if not message or not message.text:
        return

    text = message.text.strip()
    parts = re.split(r"\s+", text)

    if len(parts) != 3:
        return  # allow text_router to continue

    try:
        followers = parse_number(parts[0])
        avg_views = parse_number(parts[1])
        engagement = parse_engagement(parts[2])
    except Exception:
        await message.reply_text(
            "❌ *Invalid format*\n\n"
            "Use:\n"
            "`followers avg_views engagement_rate`\n\n"
            "Example:\n"
            "`50k 12000 0.08`",
            parse_mode="Markdown",
        )
        return

 
    # ----------- Pylance-safe handling for user_data ----------
    ud = cast(Dict[str, Any], context.user_data)

    ud["stats"] = {
        "followers": followers,
        "avg_views": avg_views,
        "engagement": engagement,
    }
# ----------------------------------------------------------

    # ----------------------------------------------------------

    await message.reply_text(
        "📱 Which *platform* are you pricing for?",
        reply_markup=platform_keyboard(),
        parse_mode="Markdown"
    )
