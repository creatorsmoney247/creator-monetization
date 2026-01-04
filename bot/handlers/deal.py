from telegram import Update
from telegram.ext import ContextTypes
import sqlite3
import os
from dotenv import load_dotenv
from typing import cast, Dict, Any
from datetime import datetime

load_dotenv()

# ---------- DATABASE ----------

_raw_db_path = os.getenv("BOT_DB_PATH")
if not _raw_db_path:
    raise RuntimeError("❌ BOT_DB_PATH not set in .env")

DB_PATH: str = cast(str, _raw_db_path)


# ---------- DB HELPERS ----------

def is_pro_user(telegram_id: int) -> bool:
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    try:
        cur.execute(
            "SELECT is_pro FROM creators WHERE telegram_id = ?",
            (str(telegram_id),),
        )
        row = cur.fetchone()
        return bool(row and row[0] == 1)
    finally:
        conn.close()


def has_submitted_pro_request(telegram_id: int) -> bool:
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    try:
        cur.execute(
            "SELECT 1 FROM pro_requests WHERE telegram_id = ?",
            (str(telegram_id),),
        )
        return cur.fetchone() is not None
    finally:
        conn.close()


def save_pro_request(data: Dict[str, Any]) -> None:
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute(
        """
        INSERT INTO pro_requests
        (telegram_id, email, full_name, brand_name, phone, requested_at, delivery_status)
        VALUES (?, ?, ?, ?, ?, ?, 'pending')
        """,
        (
            data["telegram_id"],
            data["email"],
            data["full_name"],
            data.get("brand_name"),
            data.get("phone"),
            datetime.utcnow().isoformat(),
        ),
    )
    conn.commit()
    conn.close()


# ---------- DEAL COMMAND ----------

async def deal_script(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = update.effective_message
    user = update.effective_user

    if not message or not user:
        return

    # 🔒 PRO GATE
    if not is_pro_user(user.id):
        await message.reply_text(
            "🔒 **PRO Feature**\n\n"
            "Brand deal resources are available on **PRO** only.\n\n"
            "👉 Type `upgrade` to unlock PRO.",
            parse_mode="Markdown",
        )
        return

    # ✅ Already submitted
    if has_submitted_pro_request(user.id):
        await message.reply_text(
            "📦 **PRO Pack In Progress**\n\n"
            "Your details have already been received.\n"
            "Your PRO Creator Monetization Pack\n"
            "will be delivered to your email within **24 hours**.\n\n"
            "Thank you for upgrading.",
            parse_mode="Markdown",
        )
        return

    # ---------- START SAFE DATA COLLECTION ----------
    # ---------- START SAFE DATA COLLECTION ----------
    user_data: dict = {}
    context.user_data = user_data

    user_data["step"] = "email"


    await message.reply_text(

        "📝 **PRO Brand Deal Setup**\n\n"
        "To personalize your PRO Creator Monetization Pack\n"
        "and deliver it to you by email, please provide\n"
        "a few details.\n\n"
        "⏱ Takes less than 1 minute.\n"
        "🔒 Your data is used only for delivery.\n\n"
        "📧 **Enter your email address:**",
        parse_mode="Markdown",
    )


# ---------- STEP HANDLER ----------

async def deal_step_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = update.effective_message
    user = update.effective_user

    if not message or not user:
        return

    if context.user_data is None:
        return

    user_data = context.user_data
    if not isinstance(user_data, dict):
        return

    

    step = user_data.get("step")
    if not step:
        return

    text = (message.text or "").strip()

    # ---------- EMAIL ----------
    if step == "email":
        if "@" not in text or "." not in text:
            await message.reply_text("❌ Please enter a valid email address.")
            return

        user_data["email"] = text
        user_data["step"] = "full_name"
        await message.reply_text("👤 **Enter your full name:**")
        return

    # ---------- FULL NAME ----------
    if step == "full_name":
        user_data["full_name"] = text
        user_data["step"] = "brand_name"
        await message.reply_text(
            "🏢 **Enter your creator brand or company name**\n"
            "(or type `skip`):"
        )
        return

    # ---------- BRAND ----------
    if step == "brand_name":
        user_data["brand_name"] = None if text.lower() == "skip" else text
        user_data["step"] = "phone"
        await message.reply_text(
            "📞 **Enter your phone number**\n"
            "(or type `skip`):"
        )
        return

    # ---------- PHONE + SAVE ----------
    if step == "phone":
        user_data["phone"] = None if text.lower() == "skip" else text

        save_pro_request({
            "telegram_id": str(user.id),
            "email": user_data["email"],
            "full_name": user_data["full_name"],
            "brand_name": user_data.get("brand_name"),
            "phone": user_data.get("phone"),
        })

        context.user_data = {}  # ✅ safe reset

        await message.reply_text(
            "✅ **Details Received Successfully**\n\n"
            "📦 Your **PRO Creator Monetization Pack**\n"
            "will be delivered to your email within **24 hours**.\n\n"
            "Thank you for upgrading to PRO.",
            parse_mode="Markdown",
        )
