import os
import uuid
import requests
import logging
import psycopg2

logger = logging.getLogger(__name__)

PAYSTACK_SECRET_KEY = os.getenv("PAYSTACK_SECRET_KEY")
DATABASE_URL = os.getenv("DATABASE_URL")


def get_db():
    return psycopg2.connect(DATABASE_URL)


def init_paystack_payment(email: str, amount: int, telegram_id: str) -> str:
    reference = str(uuid.uuid4())

    response = requests.post(
        "https://api.paystack.co/transaction/initialize",
        headers={
            "Authorization": f"Bearer {PAYSTACK_SECRET_KEY}",
            "Content-Type": "application/json",
        },
        json={
            "email": email,
            "amount": amount,
            "reference": reference,
            "metadata": {"telegram_id": telegram_id},
        },
        timeout=10,
    )

    if not response.ok:
        logger.error(response.text)
        raise RuntimeError("Paystack init failed")

    # Save pending payment
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
    conn.close()

    return response.json()["data"]["authorization_url"]
