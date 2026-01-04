from fastapi import APIRouter, Request
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
