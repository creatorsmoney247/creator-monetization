from telegram import Update
from telegram.ext import ContextTypes
from typing import Any, Mapping
from app.db import get_db


async def status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # -----------------------------------
    # SAFETY CHECKS
    # -----------------------------------
    if not update.message or not update.effective_user:
        return

    telegram_id = str(update.effective_user.id)

    # -----------------------------------
    # DATABASE QUERY
    # -----------------------------------
    conn = get_db()
    row: Any | None = None

    try:
        cur = conn.cursor()
        cur.execute(
            """
            SELECT is_pro, pro_activated_at
            FROM creators
            WHERE telegram_id = %s
            """,
            (telegram_id,),
        )
        row = cur.fetchone()
    finally:
        conn.close()

    # -----------------------------------
    # NO RECORD → FREE USER
    # -----------------------------------
    if row is None:
        await update.message.reply_text(
            "🆓 *Account Status: FREE*\n\n"
            "You are currently on the free plan.\n"
            "Type `upgrade` to unlock PRO features.",
            parse_mode="Markdown",
        )
        return

    # -----------------------------------
    # HANDLE dict / sqlite Row / tuple
    # -----------------------------------
    is_pro: bool
    activated_at: Any

    if isinstance(row, Mapping):
        # dict or sqlite3.Row
        is_pro = bool(row.get("is_pro"))
        activated_at = row.get("pro_activated_at")
    else:
        # tuple fallback
        is_pro = bool(row[0])
        activated_at = row[1]

    # -----------------------------------
    # RESPONSE
    # -----------------------------------
    if is_pro:
        await update.message.reply_text(
            "💼 *Account Status: PRO*\n\n"
            f"Activated on: `{activated_at}`\n\n"
            "You have full access to PRO features.",
            parse_mode="Markdown",
        )
    else:
        await update.message.reply_text(
            "🆓 *Account Status: FREE*\n\n"
            "Upgrade anytime to unlock PRO features.",
            parse_mode="Markdown",
        )
