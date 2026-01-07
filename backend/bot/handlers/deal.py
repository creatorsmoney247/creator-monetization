from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from datetime import datetime
from typing import Dict, Any

from app.db import get_db


# =================================================
# DB HELPERS
# =================================================

def is_pro_user(telegram_id: int) -> bool:
    """
    Returns True if user has PRO access.
    """
    conn = get_db()
    try:
        cur = conn.cursor()
        cur.execute(
            "SELECT is_pro FROM creators WHERE telegram_id = %s",
            (str(telegram_id),),
        )
        row = cur.fetchone()
        return bool(row and row[0])
    finally:
        conn.close()


def save_pro_request(data: Dict[str, Any]) -> None:
    """
    Persists PRO delivery request.
    """
    conn = get_db()
    try:
        cur = conn.cursor()
        cur.execute(
            """
            INSERT INTO pro_requests
            (telegram_id, email, full_name, brand_name, phone, requested_at)
            VALUES (%s, %s, %s, %s, %s, %s)
            """,
            (
                data["telegram_id"],
                data["email"],
                data["full_name"],
                data.get("brand_name"),
                data.get("phone"),
                datetime.utcnow(),
            ),
        )
        conn.commit()
    finally:
        conn.close()


# =================================================
# DEAL ENTRY (PRO ONLY)
# =================================================
async def deal_script(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    message = update.effective_message
    user = update.effective_user

    if not message or not user:
        return

    # -----------------------------
    # PRO GATE
    # -----------------------------
    if not is_pro_user(user.id):
        keyboard = InlineKeyboardMarkup(
            [[InlineKeyboardButton("🚀 Upgrade to PRO", callback_data="upgrade_pro")]]
        )

        await message.reply_text(
            "🔒 *PRO Required*\n\n"
            "Brand deal scripts unlock **only after upgrading**.\n\n"
            "Tap below to continue 👇",
            reply_markup=keyboard,
            parse_mode="Markdown",
        )
        return

    # -----------------------------
    # INITIALIZE DEAL STATE
    # -----------------------------
    user_data = context.user_data
    if user_data is None:
        return  # satisfies type checker

    user_data.clear()
    user_data["mode"] = "deal"
    user_data["step"] = "email"

    await message.reply_text(
        "📝 *PRO Brand Deal Setup*\n\n"
        "📧 *Enter your email address:*",
        parse_mode="Markdown",
    )


# =================================================
# MULTI-STEP DEAL FLOW
# =================================================
async def deal_step_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    message = update.effective_message
    user = update.effective_user

    if not message or not user:
        return

    user_data = context.user_data
    if user_data is None:
        return  # satisfies type checker

    step = user_data.get("step")
    if not step:
        return

    text = message.text.strip() if message.text else ""

    # ---------- EMAIL ----------
    if step == "email":
        if "@" not in text or "." not in text:
            await message.reply_text("❌ Please enter a valid email address.")
            return

        user_data["email"] = text
        user_data["step"] = "full_name"

        await message.reply_text(
            "👤 *Enter your full name:*",
            parse_mode="Markdown",
        )
        return

    # ---------- FULL NAME ----------
    if step == "full_name":
        if not text:
            await message.reply_text("❌ Name cannot be empty.")
            return

        user_data["full_name"] = text
        user_data["step"] = "brand_name"

        await message.reply_text(
            "🏢 *Enter your creator brand or company name*\n"
            "(or type `skip`):",
            parse_mode="Markdown",
        )
        return

    # ---------- BRAND ----------
    if step == "brand_name":
        user_data["brand_name"] = None if text.lower() == "skip" else text
        user_data["step"] = "phone"

        await message.reply_text(
            "📞 *Enter your phone number*\n"
            "(or type `skip`):",
            parse_mode="Markdown",
        )
        return

    # ---------- PHONE + SAVE ----------
    if step == "phone":
        user_data["phone"] = None if text.lower() == "skip" else text

        save_pro_request(
            {
                "telegram_id": str(user.id),
                "email": user_data["email"],
                "full_name": user_data["full_name"],
                "brand_name": user_data.get("brand_name"),
                "phone": user_data.get("phone"),
            }
        )

        # -----------------------------
        # CLEAR DEAL STATE
        # -----------------------------
        user_data.clear()

        await message.reply_text(
            "✅ *Details Received Successfully*\n\n"
            "📦 Your *PRO Creator Monetization Pack*\n"
            "will be delivered to your email within *24 hours*.\n\n"
            "Welcome to *PRO* 💼🚀",
            parse_mode="Markdown",
        )
