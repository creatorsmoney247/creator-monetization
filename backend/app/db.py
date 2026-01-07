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
def get_db():
    """
    Returns a new PostgreSQL connection.
    Caller is responsible for closing it.
    """
    try:
        return psycopg2.connect(
            DATABASE_URL,
            cursor_factory=RealDictCursor,
            sslmode="require",      # REQUIRED for Supabase
            connect_timeout=10,     # Prevents startup hangs
        )
    except Exception:
        logger.exception("❌ Failed to connect to database")
        raise
