from telegram import Update
from telegram.ext import ContextTypes
from backend.app.db import get_db

async def status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    if not user:
        return

    conn = get_db()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT is_pro, pro_activated_at FROM creators WHERE telegram_id = %s",
                (str(user.id),),
            )
            row = cur.fetchone()
    finally:
        conn.close()

    if not row:
        await update.message.reply_text(
            "🆓 **Account Status: FREE**\n\n"
            "You are currently on the free plan.\n"
            "Type `upgrade` to unlock PRO features.",
            parse_mode="Markdown",
        )
        return

    if row["is_pro"]:
        await update.message.reply_text(
            "💼 **Account Status: PRO**\n\n"
            f"Activated on: {row['pro_activated_at']}\n\n"
            "You have full access to PRO features.",
            parse_mode="Markdown",
        )
    else:
        await update.message.reply_text(
            "🆓 **Account Status: FREE**\n\n"
            "Upgrade anytime to unlock PRO.",
            parse_mode="Markdown",
        )
