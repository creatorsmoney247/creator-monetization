# bot/handlers/pricing.py

import re
from typing import cast, Dict, Any, Optional
from telegram import Update
from telegram.ext import ContextTypes

from bot.keyboards.platforms import platform_keyboard


# -------------------------------------------------
# PARSER HELPERS
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
# TEXT → STATS PARSER
# -------------------------------------------------
async def pricing_calc(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Parses the raw user text into stats, stores them,
    then hands off to platform selection → niche → hybrid engine.

    IMPORTANT: This function MUST NOT generate pricing itself.
    """

    message = update.effective_message
    if not message or not message.text:
        return

    text = message.text.strip()
    parts = re.split(r"\s+", text)

    followers: Optional[int] = None
    avg_views: Optional[int] = None
    engagement: Optional[float] = None

    # ---- Parsing Logic ----
    try:
        if len(parts) == 1:
            # followers only
            followers = parse_number(parts[0])

        elif len(parts) == 2:
            # interpret as views + engagement
            try:
                engagement = parse_engagement(parts[1])
                avg_views = parse_number(parts[0])
            except ValueError:
                await _invalid_format(message)
                return

        elif len(parts) == 3:
            # full stats
            followers = parse_number(parts[0])
            avg_views = parse_number(parts[1])
            engagement = parse_engagement(parts[2])

        else:
            await _invalid_format(message)
            return

    except Exception:
        await _invalid_format(message)
        return

    # ---- Save parsed stats ----
    ud = cast(Dict[str, Any], context.user_data)
    ud["stats"] = {
        "followers": followers,
        "avg_views": avg_views,
        "engagement": engagement,
    }

    # ---- IMPORTANT ----
    # Do NOT generate pricing here. Hand off to hybrid pipeline.
    await message.reply_text(
        "📱 Which *platform* are you pricing for? (Instagram, TikTok, YouTube, etc.)",
        reply_markup=platform_keyboard(),
        parse_mode="Markdown"
    )


# -------------------------------------------------
# STANDARD INVALID FORMAT RESPONSE
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
        "`50k 12000 0.08`",
        parse_mode="Markdown",
    )
