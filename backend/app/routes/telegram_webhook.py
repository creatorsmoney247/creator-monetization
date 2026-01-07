import os
import json
import logging
from fastapi import APIRouter, Request, HTTPException
from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters,
)

# -----------------------------
# LOGGING
# -----------------------------
logger = logging.getLogger("telegram-webhook")

# -----------------------------
# ENV
# -----------------------------
BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
if not BOT_TOKEN:
    raise RuntimeError("TELEGRAM_BOT_TOKEN missing")

# -----------------------------
# TELEGRAM APP (NO POLLING)
# -----------------------------
telegram_app = Application.builder().token(BOT_TOKEN).build()

# -----------------------------
# IMPORT HANDLERS
# -----------------------------
from bot.handlers.start import start_message
from bot.handlers.pricing import pricing_calc
from bot.handlers.deal import deal_script, deal_step_handler
from bot.handlers.subscribe import subscribe_command, pay_command
from bot.handlers.status import status

telegram_app.add_handler(CommandHandler("start", start_message))
telegram_app.add_handler(CommandHandler("upgrade", subscribe_command))
telegram_app.add_handler(CommandHandler("pay", pay_command))
telegram_app.add_handler(CommandHandler("deal", deal_script))

telegram_app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, pricing_calc))
telegram_app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, deal_step_handler))

# -----------------------------
# FASTAPI ROUTER
# -----------------------------
router = APIRouter(prefix="/telegram")

@router.post("/webhook")
async def telegram_webhook(request: Request):
    try:
        payload = await request.json()
        update = Update.de_json(payload, telegram_app.bot)
        await telegram_app.process_update(update)
        return {"ok": True}
    except Exception as e:
        logger.exception("Telegram webhook failed")
        raise HTTPException(status_code=500, detail=str(e))
