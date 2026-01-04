# backend/app/routes/telegram_webhook.py

import sys
from pathlib import Path
from fastapi import APIRouter, Request

# -------------------------------------------------
# ENSURE PROJECT ROOT IS IN PYTHON PATH
# -------------------------------------------------
PROJECT_ROOT = Path(__file__).resolve().parents[3]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

# -------------------------------------------------
# BOT HANDLERS (NOW SAFE)
# -------------------------------------------------
from bot.handlers.start import handle_start
from bot.handlers.pricing import handle_pricing

router = APIRouter()

@router.post("/bot{token}")
async def telegram_webhook(token: str, request: Request):
    update = await request.json()

    message = update.get("message", {})
    text = message.get("text", "")

    if text == "/start":
        await handle_start(message)

    elif text.startswith("price"):
        await handle_pricing(message)

    return {"ok": True}
