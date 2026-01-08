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
# TELEGRAM APPLICATION
# -------------------------------------------------
telegram_app: Application = (
    Application.builder()
    .token(BOT_TOKEN)
    .build()
)

# -------------------------------------------------
# IMPORT HANDLERS (IMPORTANT: NO 'backend.' PREFIX)
# -------------------------------------------------
from bot.handlers.start import start_message
from bot.handlers.pricing import pricing_calc
from bot.handlers.deal import deal_script, deal_step_handler
from bot.handlers.subscribe import subscribe_command, pay_command
from bot.handlers.status import status
from bot.handlers.text_router import text_router

# -------------------------------------------------
# REGISTER BOT COMMANDS
# -------------------------------------------------
telegram_app.add_handler(CommandHandler("start", start_message))
telegram_app.add_handler(CommandHandler("upgrade", subscribe_command))
telegram_app.add_handler(CommandHandler("pay", pay_command))
telegram_app.add_handler(CommandHandler("deal", deal_script))
telegram_app.add_handler(CommandHandler("status", status))

# -------------------------------------------------
# REGISTER TEXT ROUTER (NON-COMMANDS)
# -------------------------------------------------
telegram_app.add_handler(
    MessageHandler(filters.TEXT & ~filters.COMMAND, text_router)
)

# -------------------------------------------------
# FASTAPI ROUTER
# -------------------------------------------------
router = APIRouter(prefix="/telegram")


@router.post("/webhook")
async def telegram_webhook(request: Request):
    """
    Receives Telegram webhook updates and routes them to PTB.
    """
    payload = await request.json()
    update = Update.de_json(payload, telegram_app.bot)
    await telegram_app.process_update(update)
    return {"ok": True}
