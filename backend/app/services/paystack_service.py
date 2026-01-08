import os
import uuid
import requests
import logging
import psycopg2
from typing import Optional

logger = logging.getLogger("creator-backend.paystack-service")


# -------------------------------------------------
# ENV
# -------------------------------------------------
def get_required_env(name: str) -> str:
    value = os.getenv(name)
    if not value or not value.strip():
        raise RuntimeError(f"❌ Missing required env var: {name}")
    return value


PAYSTACK_SECRET_KEY = get_required_env("PAYSTACK_SECRET_KEY")
DATABASE_URL = get_required_env("DATABASE_URL")


# -------------------------------------------------
# DB
# -------------------------------------------------
def get_db():
    return psycopg2.connect(DATABASE_URL)


# -------------------------------------------------
# INIT PAYSTACK PAYMENT
# -------------------------------------------------
def init_paystack_payment(email: str, amount: int, telegram_id: str) -> str:
    """
    Create a Paystack payment session and store a 'pending' payment entry.
    Returns an `authorization_url` string.
    """
    reference = str(uuid.uuid4())

    payload = {
        "email": email,
        "amount": amount,
        "reference": reference,
        "metadata": {"telegram_id": telegram_id},
    }

    headers = {
        "Authorization": f"Bearer {PAYSTACK_SECRET_KEY}",
        "Content-Type": "application/json",
    }

    logger.info(f"Initializing Paystack payment → {email}, ₦{amount/100}, ref={reference}")

    try:
        response = requests.post(
            "https://api.paystack.co/transaction/initialize",
            headers=headers,
            json=payload,
            timeout=20,  # Paystack can be slow; 10s causes timeouts
        )
    except requests.RequestException as e:
        logger.error(f"Paystack connection error → {e}")
        raise RuntimeError("Unable to reach Paystack")

    if not response.ok:
        logger.error(f"Paystack API failed [{response.status_code}] → {response.text}")
        raise RuntimeError("Paystack init failed")

    try:
        data = response.json()
    except ValueError:
        logger.error("Invalid JSON from Paystack init")
        raise RuntimeError("Invalid response from Paystack")

    auth_url: Optional[str] = data.get("data", {}).get("authorization_url")
    if not auth_url:
        logger.error(f"Missing authorization_url in response → {data}")
        raise RuntimeError("Missing authorization_url from Paystack")

    # -------------------------------------------------
    # SAVE PENDING PAYMENT IN DB
    # -------------------------------------------------
    conn = None
    try:
        conn = get_db()
        cur = conn.cursor()

        cur.execute(
            """
            INSERT INTO payments (reference, telegram_id, amount, status)
            VALUES (%s, %s, %s, 'pending')
            """,
            (reference, telegram_id, amount),
        )

        conn.commit()
        logger.info(f"Payment logged as pending → ref={reference}, tg={telegram_id}")

    except Exception as e:
        if conn:
            conn.rollback()
        logger.error(f"DB insert failed for payment ref={reference} → {e}")
        raise RuntimeError("Database error while saving payment")

    finally:
        if conn:
            conn.close()

    return auth_url
