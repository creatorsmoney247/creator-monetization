import os
import logging
from fastapi import APIRouter, Request
from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
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
    raise RuntimeError("TELEGRAM_BOT_TOKEN missing")

# -------------------------------------------------
# TELEGRAM APPLICATION (WEBHOOK MODE)
# -------------------------------------------------
telegram_app: Application = (
    Application.builder()
    .token(BOT_TOKEN)
    .build()
)

# -------------------------------------------------
# IMPORT BOT HANDLERS
# -------------------------------------------------


from backend.bot.handlers.start import start_message
from backend.bot.handlers.pricing import pricing_calc
from backend.bot.handlers.deal import deal_script, deal_step_handler
from backend.bot.handlers.subscribe import subscribe_command, pay_command
from backend.bot.handlers.status import status
from backend.bot.handlers.text_router import text_router

# -------------------------------------------------
# REGISTER COMMAND HANDLERS
# -------------------------------------------------
telegram_app.add_handler(CommandHandler("start", start_message))
telegram_app.add_handler(CommandHandler("upgrade", subscribe_command))
telegram_app.add_handler(CommandHandler("pay", pay_command))
telegram_app.add_handler(CommandHandler("deal", deal_script))
telegram_app.add_handler(CommandHandler("status", status))

# -------------------------------------------------
# REGISTER TEXT HANDLER (ONE ONLY)
# -------------------------------------------------
telegram_app.add_handler(
    MessageHandler(filters.TEXT & ~filters.COMMAND, text_router)
)

# -------------------------------------------------
# FASTAPI ROUTER
# -------------------------------------------------
router = APIRouter(prefix="/telegram")


@router.on_event("startup")
async def telegram_startup():
    """
    REQUIRED for webhook mode.
    Initializes python-telegram-bot application.
    """
    await telegram_app.initialize()
    logger.info("✅ Telegram application initialized")


@router.on_event("shutdown")
async def telegram_shutdown():
    await telegram_app.shutdown()
    logger.info("🛑 Telegram application shutdown")


@router.post("/webhook")
async def telegram_webhook(request: Request):
    """
    Receives Telegram updates and forwards them
    to python-telegram-bot dispatcher.
    """
    payload = await request.json()

    update = Update.de_json(payload, telegram_app.bot)

    await telegram_app.process_update(update)

    return {"ok": True}
