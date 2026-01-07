from telegram.ext import CommandHandler, MessageHandler, filters

from bot.handlers.start import start_message
from bot.handlers.pricing import pricing_calc
from bot.handlers.deal import deal_script, deal_step_handler
from bot.handlers.subscribe import subscribe_command, pay_command
from bot.handlers.text_router import text_router


def register_handlers(app):
    # ---------- COMMANDS ----------
    app.add_handler(CommandHandler("start", start_message))
    app.add_handler(CommandHandler("help", start_message))
    app.add_handler(CommandHandler("deal", deal_script))
    app.add_handler(CommandHandler("upgrade", subscribe_command))
    app.add_handler(CommandHandler("pay", pay_command))

    # ---------- PRICING (MUST COME FIRST) ----------
    app.add_handler(
        MessageHandler(
            filters.TEXT & ~filters.COMMAND,
            pricing_calc,
        )
    )

    # ---------- DEAL MULTI-STEP (LAST) ----------
    app.add_handler(
        MessageHandler(
            filters.TEXT & ~filters.COMMAND,
            deal_step_handler,
        )
    )
