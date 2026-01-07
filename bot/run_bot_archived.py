# bot/run_bot.py
import os
import sys
from pathlib import Path
import logging

# -------------------------------------------------
# PATH SETUP
# -------------------------------------------------
PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

# -------------------------------------------------
# LOGGING
# -------------------------------------------------
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("creator-bot")

# -------------------------------------------------
# ENV (RENDER ONLY)
# -------------------------------------------------
BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
BASE_URL = os.getenv("BASE_URL")

if not BOT_TOKEN:
    raise RuntimeError("❌ TELEGRAM_BOT_TOKEN missing")

if not BASE_URL:
    raise RuntimeError("❌ BASE_URL missing")

# -------------------------------------------------
# TELEGRAM
# -------------------------------------------------
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    filters,
)

# -------------------------------------------------
# HANDLERS
# -------------------------------------------------
from bot.handlers.start import start_message
from bot.handlers.pricing import pricing_calc
from bot.handlers.deal import deal_script, deal_step_handler
from bot.handlers.subscribe import subscribe_command, pay_command
from bot.handlers.status import status

# -------------------------------------------------
# APP
# -------------------------------------------------
app = Application.builder().token(BOT_TOKEN).build()

# COMMANDS
app.add_handler(CommandHandler("start", start_message))
app.add_handler(CommandHandler("status", status))
app.add_handler(CommandHandler("upgrade", subscribe_command))
app.add_handler(CommandHandler("pay", pay_command))
app.add_handler(CommandHandler("deal", deal_script))

# TEXT (ORDER MATTERS)
app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, pricing_calc))
app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, deal_step_handler))

# -------------------------------------------------
# RUN
# -------------------------------------------------
logger.info("🤖 Telegram Bot started (Polling mode)")
app.run_polling()
