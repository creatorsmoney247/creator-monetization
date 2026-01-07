from telegram import Update
from telegram.ext import ContextTypes

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if context.user_data:
        context.user_data.clear()

    await update.message.reply_text(
        "✅ Action cancelled.\n\nYou can start again anytime."
    )
