# backend/app/services/pro_service.py

import datetime
from typing import Optional
from app.db import get_db


def normalize_dt(value: Optional[object]) -> Optional[datetime.datetime]:
    """
    Ensures dt from DB is timezone-aware for safe comparison.
    Handles str/datetime/None.
    """
    if value is None:
        return None

    if isinstance(value, datetime.datetime):
        # ensure timezone awareness
        if value.tzinfo is None:
            return value.replace(tzinfo=datetime.timezone.utc)
        return value

    # Handle string values: "2026-01-20T12:33:00+00"
    try:
        dt = datetime.datetime.fromisoformat(str(value))
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=datetime.timezone.utc)
        return dt
    except Exception:
        return None


def is_user_pro(telegram_id: str) -> bool:
    conn = get_db()
    cur = conn.cursor()

    cur.execute("""
        SELECT is_pro, pro_expires_at
        FROM creators
        WHERE telegram_id = %s
    """, (telegram_id,))

    row = cur.fetchone()
    conn.close()

    if not row:
        return False

    is_pro, expires = row
    if not is_pro:
        return False

    expires_dt = normalize_dt(expires)
    if expires_dt is None:
        # Invalid timestamp means treat as expired
        return False

    # Compare using UTC-aware current time
    now = datetime.datetime.now(datetime.timezone.utc)
    return expires_dt > now
