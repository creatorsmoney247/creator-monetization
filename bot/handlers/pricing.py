# bot/handlers/pricing.py

import os
import re
import requests
from typing import Optional

# -------------------------------------------------
# TELEGRAM CONFIG
# -------------------------------------------------
TELEGRAM_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_API = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}"

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


def engagement_position(er: float) -> str:
    if er >= 0.08:
        return "upper"
    if er >= 0.05:
        return "middle"
    return "lower"


def tier_from_views(avg_views: int):
    if avg_views < 1_000:
        return ("Starter", "₦2,000 – ₦5,000")
    if avg_views < 5_000:
        return ("Early-Growth", "₦3,000 – ₦10,000")
    if avg_views < 15_000:
        return ("Growth", "₦10,000 – ₦25,000")
    if avg_views < 50_000:
        return ("Rising", "₦15,000 – ₦40,000")
    if avg_views < 150_000:
        return ("Established", "₦40,000 – ₦100,000")
    return ("Premium", "₦100,000+")


def send_message(chat_id: int, text: str, parse_mode: Optional[str] = "Markdown"):
    requests.post(
        f"{TELEGRAM_API}/sendMessage",
        json={
            "chat_id": chat_id,
            "text": text,
            "parse_mode": parse_mode,
        },
        timeout=10,
    )

# -------------------------------------------------
# WEBHOOK HANDLER (USED BY FASTAPI)
# -------------------------------------------------
async def handle_pricing(message: dict):
    chat_id = message["chat"]["id"]
    text = message.get("text", "").strip()

    parts = re.split(r"\s+", text)
    if len(parts) != 3:
        send_message(
            chat_id,
            "❌ **Invalid format**\n\n"
            "Use:\n"
            "`followers avg_views engagement_rate`\n\n"
            "Example:\n"
            "`10k 2k 0.05`",
        )
        return

    try:
        followers = parse_number(parts[0])
        avg_views = parse_number(parts[1])
        er = float(parts[2])
        if not (0 < er <= 1):
            raise ValueError
    except Exception:
        send_message(
            chat_id,
            "❌ **Invalid values**\n\n"
            "Followers/views must be numbers.\n"
            "Engagement rate must be between 0 and 1.",
        )
        return

    tier, range_text = tier_from_views(avg_views)
    pos = engagement_position(er)

    send_message(
        chat_id,
        "📊 **Creator Market Insight (Nigeria)**\n\n"
        f"**Category:** {tier} Creator\n\n"
        "Creators with similar reach typically earn:\n"
        f"• **{range_text} per post/video**\n\n"
        f"Your engagement suggests you may sit toward the **{pos}** end of this range.\n\n"
        "⚠️ These are **indicative ranges**, not guarantees.\n"
        "Pay varies by popularity, content quality, brand budget, and negotiation.\n\n"
        "👉 **Next action:**\n"
        "Type `upgrade` to learn how to position yourself confidently.",
    )
