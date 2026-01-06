import os
import psycopg2
from typing import Union


# -------------------------------------------------
# ENV
# -------------------------------------------------
def get_required_env(name: str) -> str:
    value = os.getenv(name)
    if not value or not value.strip():
        raise RuntimeError(f"❌ Missing required env var: {name}")
    return value


DATABASE_URL = get_required_env("DATABASE_URL")


# -------------------------------------------------
# DB
# -------------------------------------------------
def get_db():
    return psycopg2.connect(DATABASE_URL)


# -------------------------------------------------
# PRO CHECK
# -------------------------------------------------
def is_pro_user(telegram_id: Union[str, int]) -> bool:
    """
    Returns True if the user is a PRO user.
    """
    conn = get_db()
    cur = conn.cursor()

    cur.execute(
        "SELECT is_pro FROM creators WHERE telegram_id = %s",
        (str(telegram_id),),
    )
    row = cur.fetchone()

    cur.close()
    conn.close()

    return bool(row and row[0] is True)
