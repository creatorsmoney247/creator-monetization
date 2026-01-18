# backend/bot/handlers/elite_package.py

from __future__ import annotations
from typing import Dict, Any, cast, Optional

from datetime import datetime
from telegram import Update, Message, CallbackQuery
from telegram.ext import ContextTypes

from app.db import get_db


# =================================================
# DB SAVE FUNCTION
# =================================================
def save_elite_request(data: Dict[str, Any]) -> None:
    conn = get_db()
    try:
        cur = conn.cursor()
        cur.execute(
            """
            INSERT INTO pro_requests
            (telegram_id, email, full_name, brand_name, phone, requested_at, delivery_status)
            VALUES (%s, %s, %s, %s, %s, %s, 'elite')
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
# ENTRY POINT (Triggered via Inline Button)
# =================================================
async def elite_package_start(update: Update, context: ContextTypes.DEFAULT_TYPE):

    query: Optional[CallbackQuery] = update.callback_query
    if query is None:
        return

    await query.answer()

    raw_msg = query.message
    if raw_msg is None:
        return

    msg = cast(Message, raw_msg)

    # Safe user_data dict
    state = cast(Dict[str, Any], context.user_data)
    state.clear()
    state["mode"] = "elite"
    state["step"] = "email"

    await msg.reply_text(
        "📦 *ELITE Deal Packaging — Intake Form*\n\n"
        "We will prepare your brand-ready creator packaging.\n\n"
        "📧 First — enter your *email address:*",
        parse_mode="Markdown",
    )


# =================================================
# MULTI-STEP FORM HANDLER
# =================================================
async def elite_package_step(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:

    raw_msg = update.effective_message
    if raw_msg is None:
        return

    msg = cast(Message, raw_msg)

    user = update.effective_user
    if not user:
        return

    state = cast(Dict[str, Any], context.user_data)
    step = state.get("step")
    if step is None:
        return

    text = msg.text.strip() if msg.text else ""

    # ---------------- EMAIL ----------------
    if step == "email":
        if "@" not in text or "." not in text:
            await msg.reply_text("❌ Please enter a valid email address.")
            return

        state["email"] = text
        state["step"] = "full_name"

        await msg.reply_text(
            "👤 Enter your *Full Name:*",
            parse_mode="Markdown"
        )
        return

    # ---------------- FULL NAME ----------------
    if step == "full_name":
        if not text:
            await msg.reply_text("❌ Name cannot be empty.")
            return

        state["full_name"] = text
        state["step"] = "brand_name"

        await msg.reply_text(
            "🏢 Enter your *Creator Brand Name* (or type `skip`):",
            parse_mode="Markdown"
        )
        return

    # ---------------- BRAND NAME ----------------
    if step == "brand_name":
        state["brand_name"] = None if text.lower() == "skip" else text
        state["step"] = "phone"

        await msg.reply_text(
            "📞 Enter your *Phone Number* (or type `skip`):",
            parse_mode="Markdown"
        )
        return

    # ---------------- PHONE + SAVE ----------------
    if step == "phone":
        state["phone"] = None if text.lower() == "skip" else text

        save_elite_request(
            {
                "telegram_id": str(user.id),
                "email": state["email"],
                "full_name": state["full_name"],
                "brand_name": state.get("brand_name"),
                "phone": state.get("phone"),
            }
        )

        state.clear()

        await msg.reply_text(
            "🎉 *ELITE Request Received!*\n\n"
            "Our team will prepare your deliverables and email you within *24 hours*.\n\n"
            "Deliverables include:\n"
            "✔ Pricing & Usage Rights\n"
            "✔ Deal Positioning\n"
            "✔ Negotiation Language\n"
            "✔ Brand Pitch Assets\n\n"
            "📨 Watch your inbox 👀",
            parse_mode="Markdown"
        )
