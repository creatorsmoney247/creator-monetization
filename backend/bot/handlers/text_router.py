from telegram import Update
from telegram.ext import ContextTypes

from bot.handlers.pricing import pricing_calc
from bot.handlers.deal import deal_step_handler
from bot.handlers.subscribe import subscribe_command, pay_command
from .help import help_message


async def text_router(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Single entry point for ALL non-command text.
    Routes based on user state and keywords.
    """

    if not update.message or not update.message.text:
        return

    user_data = context.user_data or {}
    text = update.message.text.strip()
    text_lower = text.lower()

    # -------------------------------------------------
    # COMMAND / KEYWORD ROUTING
    # -------------------------------------------------

    # HELP
    if text_lower in ("/help", "help", "?", "how"):
        await help_message(update, context)
        return

    # SUBSCRIBE / UPGRADE
    if text_lower in ("/subscribe", "upgrade", "pro", "subscribe"):
        await subscribe_command(update, context)
        return

    # PAY COMMAND (manual trigger)
    if text_lower in ("/pay", "pay"):
        await pay_command(update, context)
        return

    # DEAL FLOW ENTRY
    if text_lower in ("/deal", "deal", "pricing", "rates"):
        user_data["mode"] = "deal"
        await deal_step_handler(update, context)
        return

    # DEAL FLOW CONTINUATION
    if user_data.get("mode") == "deal":
        await deal_step_handler(update, context)
        return

    # -------------------------------------------------
    # DEFAULT → PRICING CALCULATOR
    # -------------------------------------------------
    await pricing_calc(update, context)
