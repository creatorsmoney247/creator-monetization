import os
import psycopg2
from psycopg2.extras import RealDictCursor
import logging

logger = logging.getLogger(__name__)

# -------------------------------------------------
# DATABASE CONFIG (RENDER / SUPABASE)
# -------------------------------------------------
DATABASE_URL = os.getenv("DATABASE_URL")

if not DATABASE_URL:
    raise RuntimeError("❌ DATABASE_URL is not set")


# -------------------------------------------------
# DB CONNECTION (LAZY, SAFE)
# -------------------------------------------------
def get_db() -> psycopg2.extensions.connection:
    """
    Returns a new PostgreSQL connection.
    Caller is responsible for closing it.
    Safe for Supabase (SSL required).
    """
    try:
        conn = psycopg2.connect(
            DATABASE_URL,
            cursor_factory=RealDictCursor,
            sslmode="require",      # REQUIRED for Supabase external connections
            connect_timeout=5,      # Prevents Supabase 30-60s hangs
        )
        return conn

    except Exception as e:
        logger.exception(f"❌ Database connection failed → {e}")
        raise RuntimeError("Database connection failed") from e
