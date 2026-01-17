import psycopg2
from app.db import get_db

MIGRATIONS = [
    """
    ALTER TABLE creators ADD COLUMN IF NOT EXISTS pro_expires_at TIMESTAMP WITH TIME ZONE;
    """,
    """
    ALTER TABLE creators ADD COLUMN IF NOT EXISTS whitelisting_enabled BOOLEAN DEFAULT FALSE;
    """,
    """
    ALTER TABLE creators ADD COLUMN IF NOT EXISTS usage_rights_months INTEGER DEFAULT 3;
    """,
    """
    ALTER TABLE creators ADD COLUMN IF NOT EXISTS creator_type TEXT;
    """,
    """
    ALTER TABLE payments ADD COLUMN IF NOT EXISTS plan TEXT;
    """,
    """
    ALTER TABLE payments ADD COLUMN IF NOT EXISTS paid_at TIMESTAMP WITH TIME ZONE;
    """,
    """
    ALTER TABLE payments ADD COLUMN IF NOT EXISTS currency TEXT DEFAULT 'NGN';
    """
]

def run_migrations():
    conn = None
    try:
        conn = get_db()
        cur = conn.cursor()
        for sql in MIGRATIONS:
            cur.execute(sql)
        conn.commit()
        cur.close()
    except Exception as e:
        print(f"DB Migration Error: {e}")
        if conn:
            conn.rollback()
    finally:
        if conn:
            conn.close()
