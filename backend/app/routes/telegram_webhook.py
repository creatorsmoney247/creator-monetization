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
    raise RuntimeError("TELEGRAM_BOT_TOKEN missing")

# -------------------------------------------------
# TELEGRAM APPLICATION
# -------------------------------------------------
telegram_app: Application = (
    Application.builder()
    .token(BOT_TOKEN)
    .build()
)

# -------------------------------------------------
# IMPORT HANDLERS  (IMPORTANT: no 'backend.' prefix)
# -------------------------------------------------
from bot.handlers.start import start_message
from bot.handlers.pricing import pricing_calc
from bot.handlers.deal import deal_script, deal_step_handler
from bot.handlers.subscribe import subscribe_command, pay_command
from bot.handlers.status import status
from bot.handlers.text_router import text_router

# -------------------------------------------------
# REGISTER CALLBACK HANDLERS
# -------------------------------------------------
from bot.handlers.callbacks_platform import platform_selected
telegram_app.add_handler(
    CallbackQueryHandler(platform_selected, pattern="^platform_")
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
# WEBHOOK ENDPOINT
# -------------------------------------------------
@router.post("/webhook")
async def telegram_webhook(request: Request):
    """
    Receives Telegram webhook updates and routes them to PTB.
    """
    payload = await request.json()

    try:
        update = Update.de_json(payload, telegram_app.bot)
        await telegram_app.process_update(update)
    except Exception as e:
        logger.error("❌ Error processing Telegram update: %s", e)

    return {"ok": True}

# -------------------------------------------------
# OPTIONAL: STARTUP / SHUTDOWN HOOKS (SAFE FOR RENDER)
# -------------------------------------------------
@router.on_event("startup")
async def telegram_startup():
    try:
        await telegram_app.initialize()
        logger.info("🤖 Telegram bot initialized")
    except Exception as e:
        logger.error("❌ Telegram init failed: %s", e)

@router.on_event("shutdown")
async def telegram_shutdown():
    try:
        await telegram_app.shutdown()
        logger.info("🛑 Telegram bot shutdown")
    except Exception as e:
        logger.error("❌ Telegram shutdown failed: %s", e)
