# backend/bot/handlers/text_router.py

from __future__ import annotations

from typing import Dict, Any, cast

from telegram import Update
from telegram.ext import ContextTypes

from bot.handlers.pricing import pricing_calc
from bot.handlers.deal import deal_step_handler
from bot.handlers.subscribe import subscribe_command, pay_command, upgrade_pro
from bot.handlers.elite_package import elite_package_step


async def text_router(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Single entry point for ALL non-command text messages.
    Handles:
        ✓ Paystack email input
        ✓ PRO upgrade keywords
        ✓ Deal flows (state controlled)
        ✓ Elite packaging (state controlled)
        ✓ Default pricing input
    """

    message = update.message
    if message is None or not message.text:
        return

    text = message.text.strip()
    text_lower = text.lower()

    # Pylance-safe cast to Dict instead of Optional
    user_data = cast(Dict[str, Any], context.user_data or {})

    # =====================================================
    # 1) PAYSTACK EMAIL CAPTURE FLOW
    # =====================================================
    if user_data.get("awaiting_pay_email"):
        if "@" not in text or "." not in text:
            await message.reply_text("❌ Please enter a valid email address.")
            return

        user_data["pay_email"] = text
        user_data.pop("awaiting_pay_email", None)

        # Run payment flow now that email exists
        await pay_command(update, context)
        return

    # =====================================================
    # 2) KEYWORD ROUTING FOR PRO UPGRADE / SUBSCRIBE
    # =====================================================
    if text_lower in ("upgrade", "pro", "subscribe", "join pro", "unlock pro"):
        await subscribe_command(update, context)
        return

    # =====================================================
    # 3) STATE MACHINE ROUTING — DEAL MODE
    # =====================================================
    mode = user_data.get("mode")

    if mode == "deal":
        await deal_step_handler(update, context)
        return

    # =====================================================
    # 4) STATE MACHINE ROUTING — ELITE PACKAGE MODE
    # =====================================================
    if mode == "elite":
        await elite_package_step(update, context)
        return

    # =====================================================
    # 5) FALLBACK: PRICE CALCULATOR INPUT
    # =====================================================
    await pricing_calc(update, context)


# =============================================================
# CALLBACK ROUTER (Inline Keyboard)
# MUST BE REGISTERED IN APPLICATION HANDLER
# =============================================================
async def callback_router(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    if not query or not query.message or not query.message.chat:
        return  # Pylance-safe guard

    data = query.data or ""
    await query.answer()

    chat_id = query.message.chat.id

    # -------------------------
    # PRO UPGRADE CALLBACK
    # -------------------------
    if data == "upgrade_pro":
        return await upgrade_pro(update, context)

    # -------------------------
    # ELITE PACKAGE CALLBACK
    # -------------------------
    if data == "elite_package":
        user_data = cast(Dict[str, Any], context.user_data or {})
        user_data["mode"] = "elite"
        return await elite_package_step(update, context)

    # -------------------------
    # EXPORT RATECARD (PRO only)
    # Placeholder until export feature ships
    # -------------------------
    if data == "export_ratecard":
        await context.bot.send_message(
            chat_id,
            "📁 Export Feature Coming Soon!\nYou'll be able to download branded ratecards."
        )
        return

    # -------------------------
    # UNKNOWN CALLBACK
    # -------------------------
    await context.bot.send_message(chat_id, "⚠️ Unknown action.")
