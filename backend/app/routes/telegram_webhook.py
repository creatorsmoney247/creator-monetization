import os
import logging
from fastapi import APIRouter, Request
from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    filters,
)

# -------------------------------------------------
# LOGGING
# -------------------------------------------------
logger = logging.getLogger("telegram-webhook")

# -------------------------------------------------
# ENV
# -------------------------------------------------
BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
if not BOT_TOKEN:
    raise RuntimeError("TELEGRAM_BOT_TOKEN is missing")

# -------------------------------------------------
# TELEGRAM APPLICATION
# -------------------------------------------------
telegram_app: Application = (
    Application.builder()
    .token(BOT_TOKEN)
    .build()
)

# -------------------------------------------------
# IMPORT HANDLERS (NO backend. PREFIXES)
# -------------------------------------------------
from bot.handlers.start import start_message
from bot.handlers.pricing import pricing_calc
from bot.handlers.deal import deal_script, deal_step_handler
from bot.handlers.subscribe import subscribe_command, pay_command
from bot.handlers.status import status
from bot.handlers.text_router import text_router
from bot.handlers.callbacks_platform import platform_selected
from bot.callbacks_niche import niche_selected


# -------------------------------------------------
# REGISTER CALLBACK HANDLERS
# -------------------------------------------------
telegram_app.add_handler(
    CallbackQueryHandler(platform_selected, pattern=r"^platform_")
)

telegram_app.add_handler(
    CallbackQueryHandler(niche_selected, pattern=r"^niche_")
)

# -------------------------------------------------
# REGISTER BOT COMMANDS
# -------------------------------------------------
telegram_app.add_handler(CommandHandler("start", start_message))
telegram_app.add_handler(CommandHandler("upgrade", subscribe_command))
telegram_app.add_handler(CommandHandler("pay", pay_command))
telegram_app.add_handler(CommandHandler("deal", deal_script))
telegram_app.add_handler(CommandHandler("status", status))

# -------------------------------------------------
# REGISTER TEXT ROUTER (NON-COMMAND TEXT)
# -------------------------------------------------
telegram_app.add_handler(
    MessageHandler(filters.TEXT & ~filters.COMMAND, text_router)
)

# -------------------------------------------------
# FASTAPI ROUTER
# -------------------------------------------------
router = APIRouter(prefix="/telegram")

# -------------------------------------------------
# WEBHOOK ENDPOINT (REQUIRED BY TELEGRAM)
# -------------------------------------------------
@router.post("/webhook")
async def telegram_webhook(request: Request):
    """
    Receives Telegram webhook updates and routes to python-telegram-bot.
    """
    payload = await request.json()

    try:
        update = Update.de_json(payload, telegram_app.bot)
        await telegram_app.process_update(update)
    except Exception as e:
        logger.error("❌ Error processing Telegram update: %s", e)

    return {"ok": True}
