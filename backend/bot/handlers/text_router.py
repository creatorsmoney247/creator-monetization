from telegram import Update
from telegram.ext import ContextTypes

from bot.handlers.deal import deal_step_handler
from bot.handlers.pricing import pricing_calc
from bot.handlers.subscribe import subscribe_command


async def text_router(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Single entry point for ALL non-command text.
    Routes based on user state and keywords.
    """

    if not update.message or not update.message.text:
        return

    user_data = context.user_data
    if user_data is None:
        return  # satisfies Pylance

    text = update.message.text.strip().lower()

    # --------------------------------
    # UPGRADE / SUBSCRIBE KEYWORDS
    # --------------------------------
    if text in ("upgrade", "pro", "subscribe"):
        await subscribe_command(update, context)
        return

    # --------------------------------
    # DEAL FLOW (STATE-BASED)
    # --------------------------------
    mode = user_data.get("mode")

    if mode == "deal":
        await deal_step_handler(update, context)
        return

    # --------------------------------
    # DEFAULT → PRICING
    # --------------------------------
    await pricing_calc(update, context)
