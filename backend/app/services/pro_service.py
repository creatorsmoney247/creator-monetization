import datetime
from app.db import get_db

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
    
    if expires and expires < datetime.datetime.utcnow():
        return False
    
    return True
