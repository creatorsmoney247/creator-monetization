import os  
import uuid
import requests
import logging
import psycopg2
from typing import Optional
import time

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
    return psycopg2.connect(
        DATABASE_URL,
        sslmode="require",
        connect_timeout=5,
    )


# -------------------------------------------------
# INIT PAYSTACK PAYMENT
# -------------------------------------------------
def init_paystack_payment(email: str, amount: int, telegram_id: str) -> str:
    """
    Create a Paystack payment session and store a 'pending' payment entry.
    Returns an `authorization_url` string.
    """
    start = time.time()
    reference = str(uuid.uuid4())
    logger.info(f"[TRACE] start init ref={reference}")

    # ----------------------- STAGE 1: PREP -----------------------
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

    logger.info(f"[TRACE] stage=prep t={time.time() - start:.3f}s")

    # ----------------------- STAGE 2: PAYSTACK REQUEST -----------
    t2 = time.time()
    logger.info("[TRACE] stage=paystack_request start")

    try:
        response = requests.post(
            "https://api.paystack.co/transaction/initialize",
            headers=headers,
            json=payload,
            timeout=20,
        )
    except requests.RequestException as e:
        logger.error(f"[TRACE] stage=paystack_request FAIL t={time.time() - t2:.3f}s error={e}")
        raise RuntimeError("Unable to reach Paystack")

    logger.info(f"[TRACE] stage=paystack_request end t={time.time() - t2:.3f}s")

    if not response.ok:
        logger.error(f"[TRACE] Paystack API failed [{response.status_code}] → {response.text}")
        raise RuntimeError("Paystack init failed")

    # ----------------------- STAGE 3: PARSE PAYSTACK RESPONSE ----
    t3 = time.time()
    try:
        data = response.json()
        logger.info(f"[TRACE] stage=paystack_parse t={time.time() - t3:.3f}s")
    except ValueError:
        logger.error(f"[TRACE] stage=paystack_parse FAIL t={time.time() - t3:.3f}s")
        raise RuntimeError("Invalid response from Paystack")

    auth_url: Optional[str] = data.get("data", {}).get("authorization_url")
    if not auth_url:
        logger.error(f"[TRACE] stage=paystack_parse MISSING_URL data={data}")
        raise RuntimeError("Missing authorization_url")

    # ----------------------- STAGE 4: DB INSERT ------------------
    t4 = time.time()
    logger.info("[TRACE] stage=db_connect start")

    conn = None
    try:
        conn = get_db()
        logger.info(f"[TRACE] stage=db_connect end t={time.time() - t4:.3f}s")

        cur = conn.cursor()
        cur.execute(
            """
            INSERT INTO payments (reference, telegram_id, amount, status)
            VALUES (%s, %s, %s, 'pending')
            """,
            (reference, telegram_id, amount),
        )

        conn.commit()
        logger.info(f"[TRACE] stage=db_insert end t={time.time() - t4:.3f}s")

    except Exception as e:
        if conn:
            conn.rollback()
        logger.error(f"[TRACE] stage=db_insert FAIL t={time.time() - t4:.3f}s error={e}")
        raise RuntimeError("Database error while saving payment")

    finally:
        if conn:
            conn.close()

    # ----------------------- DONE -------------------------------
    logger.info(f"[TRACE] done total_t={time.time() - start:.3f}s")

    return auth_url
