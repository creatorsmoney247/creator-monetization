# bot/bot.py

from telegram import Update
from telegram.ext import (
    ApplicationBuilder,
    ContextTypes,
    MessageHandler,
    CommandHandler,
    filters,
)
import os
import logging
from dotenv import load_dotenv
from typing import cast

# ---------- BUSINESS HANDLERS ----------
from bot.handlers.deal import deal_script
from bot.handlers.subscribe import subscribe_command, pay_command
from bot.handlers.pricing import pricing_calc, pricing_command


# ---------- ENV ----------
load_dotenv()

_raw_token = os.getenv("TELEGRAM_BOT_TOKEN")
if not _raw_token:
    raise RuntimeError("❌ TELEGRAM_BOT_TOKEN is missing in .env")

BOT_TOKEN: str = cast(str, _raw_token)
BOT_NAME: str = os.getenv("BOT_NAME", "CreatorMonetizationBot")

# ---------- LOGGING ----------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger("bot")

# ---------- SAFE REPLY ----------
async def reply(update: Update, text: str, parse_mode: str | None = None):
    message = update.effective_message
    if message:
        await message.reply_text(text, parse_mode=parse_mode)


# ---------- BASIC COMMANDS ----------
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await reply(
        update,
        f"👋 Welcome to **{BOT_NAME}**\n\n"
        "This bot helps creators stop undercharging and understand their real value.\n\n"
        "📊 **Start by sending your stats in this format:**\n"
        "`followers avg_views engagement_rate`\n\n"
        "Example:\n"
        "`50k 12k 0.08`\n\n"
        "You’ll instantly see:\n"
        "• What brands SHOULD pay you\n"
        "• If you’re undercharging\n"
        "• Whether upgrading makes sense\n\n"
        "👉 **Type your stats to continue**\n\n"
        "ℹ️ Need help understanding the numbers?\n"
        "Type `/help` anytime.",
        parse_mode="Markdown",
    )


async def help_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await reply(
        update,
        "🧭 **Creator Monetization Bot – Help**\n\n"
        "**How this bot works:**\n"
        "1️⃣ Send your stats (followers, views, engagement)\n"
        "2️⃣ See what brands SHOULD pay you\n"
        "3️⃣ Upgrade to PRO to apply this pricing\n\n"
        "📊 **Understanding your price:**\n"
        "• **Recommended price** — what you should confidently charge brands\n"
        "• **Minimum acceptable** — the lowest amount you should accept\n\n"
        "📌 Always start with the recommended price.\n"
        "Only negotiate down — never up.\n\n"
        "🔓 **PRO unlocks:**\n"
        "• Brand deal reply scripts (`deal`)\n"
        "• Monetization tools\n\n"
        "📊 **Stats format:**\n"
        "`followers avg_views engagement_rate`\n"
        "Example:\n"
        "`50k 12k 0.08`\n\n"
        "👉 **Next actions:**\n"
        "• Type your stats to begin\n"
        "• Type `upgrade` to unlock PRO",
        parse_mode="Markdown",
    )

# ---------- SINGLE TEXT ROUTER (CORE BRAIN) ----------
async def text_router(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = update.effective_message
    if not message or not message.text:
        return

    text = message.text.strip().lower()

    # ---- PAYMENT FLOW ----
    if text == "pay":
        await pay_command(update, context)
        return

    if text == "upgrade":
        await subscribe_command(update, context)
        return

    # ---- INFO ----
    if text == "pricing":
        await pricing_command(update, context)
        return

    # ---- PRO FEATURE ----
    if text == "deal":
        await deal_script(update, context)
        return

    # ---- PRICING CALCULATION (MUST STAY LAST) ----
    if len(text.split()) == 3:
        await pricing_calc(update, context)
        return

    # ---- FALLBACK ----
    await reply(
        update,
        "❓ I didn’t understand that.\n\n"
        "Try:\n"
        "`pay`\n"
        "`upgrade`\n"
        "`pricing`\n"
        "`deal`\n"
        "`50k 12k 0.08`",
        parse_mode="Markdown",
    )

# ---------- ERROR HANDLER ----------
async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE):
    logger.error("Unhandled error", exc_info=context.error)
    if isinstance(update, Update):
        await reply(update, "❌ Something went wrong. Please try again.")

# ---------- MAIN ----------
def main():
    print("🤖 Creator Monetization Bot starting (STABLE MODE)...")

    app = ApplicationBuilder().token(BOT_TOKEN).build()

    # Slash commands
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_cmd))

    # ONE text handler ONLY
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, text_router))

    app.add_error_handler(error_handler)

    app.run_polling()

if __name__ == "__main__":
    main()
