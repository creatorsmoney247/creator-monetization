from telegram import Update
from telegram.ext import ContextTypes

from bot.handlers.pricing import pricing_calc
from bot.handlers.deal import deal_step_handler
from bot.handlers.subscribe import subscribe_command, pay_command
from bot.handlers.elite_package import elite_package_step


async def text_router(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Single entry point for ALL non-command text.
    Routes based on user state and keywords.
    """

    message = update.message
    if message is None or not message.text:
        return

    user_data = context.user_data
    if user_data is None:
        return  # Satisfies Pylance

    text = message.text.strip()
    text_lower = text.lower()

    # --------------------------------
    # PAYMENT EMAIL CAPTURE (PAYSTACK)
    # --------------------------------
    if user_data.get("awaiting_pay_email"):
        if "@" not in text or "." not in text:
            await message.reply_text("❌ Please enter a valid email address.")
            return

        user_data["pay_email"] = text
        user_data.pop("awaiting_pay_email", None)

        # Re-run /pay now that email is available
        await pay_command(update, context)
        return

    # --------------------------------
    # UPGRADE / SUBSCRIBE KEYWORDS
    # --------------------------------
    if text_lower in ("upgrade", "pro", "subscribe"):
        await subscribe_command(update, context)
        return

    # --------------------------------
    # DEAL FLOW (STATE-BASED)
    # --------------------------------
    mode = user_data.get("mode")

    if mode == "deal":
        await deal_step_handler(update, context)
        return

    if mode == "elite":
        await elite_package_step(update, context)
        return

    # --------------------------------
    # DEFAULT → PRICING
    # --------------------------------
    await pricing_calc(update, context)
