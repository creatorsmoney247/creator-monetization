# bot/handlers/start.py

import os
import requests

TELEGRAM_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_API = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}"

def send_message(chat_id: int, text: str):
    requests.post(
        f"{TELEGRAM_API}/sendMessage",
        json={"chat_id": chat_id, "text": text},
        timeout=10,
    )

async def handle_start(message: dict):
    chat_id = message["chat"]["id"]
    send_message(
        chat_id,
        "👋 Welcome to **Creator Monetization Bot**\n\n"
        "Send your stats like:\n"
        "`50k 12k 0.08`\n\n"
        "I’ll estimate your creator market range."
    )
