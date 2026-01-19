# backend/bot/handlers/pricing.py

import re
from typing import cast, Dict, Any, Optional
from telegram import Update
from telegram.ext import ContextTypes

from bot.keyboards.platforms import platform_keyboard


# -------------------------------------------------
# PARSER HELPERS
# -------------------------------------------------
def parse_number(value: str) -> int:
    """
    Parses: 50k, 12k, 1.2m, 10000, 500,000
    """
    value = value.strip().replace(",", "").lower()
    if value.endswith("k"):
        return int(float(value[:-1]) * 1_000)
    if value.endswith("m"):
        return int(float(value[:-1]) * 1_000_000)
    return int(float(value))


def parse_engagement(er_raw: str) -> float:
    """
    Converts engagement into a proper decimal rate (0 < x <= 1)
    Handles:
        - 0.08  => 0.08
        - 8%    => 0.08
        - 8     => 0.08
        - 0.8%  => 0.008
    """
    er_str = er_raw.strip().replace("%", "")

    try:
        er = float(er_str)
    except:
        raise ValueError("Invalid engagement")

    # If user typed `8` meaning 8%
    if er > 1:
        er = er / 100.0

    # If user typed `0.8%` → 0.008
    if 0 < er <= 100 and "%" in er_raw:
        er = er / 100.0

    if not (0 < er <= 1):
        raise ValueError("Engagement must be between 0 and 1")

    return er


# -------------------------------------------------
# MAIN TEXT → STATS PARSER
# -------------------------------------------------
async def pricing_calc(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Parses raw user text into stats and stores them for the hybrid pricing pipeline.
    After parsing, the bot asks for PLATFORM selection.
    """

    message = update.effective_message
    if not message or not message.text:
        return

    text = message.text.strip()
    parts = re.split(r"\s+", text)

    followers: Optional[int] = None
    avg_views: Optional[int] = None
    engagement: Optional[float] = None

    try:
        # -------------------------
        # Case: followers only
        # Ex: "50k"
        # -------------------------
        if len(parts) == 1:
            followers = parse_number(parts[0])

        # -------------------------
        # Case: views + engagement
        # Ex: "12000 0.08"
        # -------------------------
        elif len(parts) == 2:
            avg_views = parse_number(parts[0])
            engagement = parse_engagement(parts[1])

        # -------------------------
        # Case: followers + views + engagement
        # Ex: "50k 12000 0.08"
        # -------------------------
        elif len(parts) == 3:
            followers = parse_number(parts[0])
            avg_views = parse_number(parts[1])
            engagement = parse_engagement(parts[2])

        else:
            await _invalid_format(message)
            return

    except Exception:
        await _invalid_format(message)
        return

    # ---- Save parsed stats persistently ----
    ud = cast(Dict[str, Any], context.user_data)
    ud.setdefault("stats", {})
    ud["stats"].update({
        "followers": followers,
        "avg_views": avg_views,
        "engagement": engagement,
    })

    # ---- Ask for platform next ----
    await message.reply_text(
        "📱 Which *platform* are you pricing for?",
        reply_markup=platform_keyboard(),
        parse_mode="Markdown"
    )


# -------------------------------------------------
# INVALID FORMAT RESPONSE
# -------------------------------------------------
async def _invalid_format(message):
    await message.reply_text(
        "❌ *Invalid format*\n\n"
        "Use one of the following:\n"
        "`50k` — followers only\n"
        "`12000 0.08` — views + engagement\n"
        "`50k 12000 0.08` — followers + views + engagement\n\n"
        "*Examples:*\n"
        "`50k`\n"
        "`12000 0.08`\n"
        "`50k 12000 0.08`\n",
        parse_mode="Markdown",
    )
