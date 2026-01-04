# backend/app/models/creator.py
# (SQLite-only model definition for reference)

"""
This file documents the creators table structure.
No ORM is used. SQLite is handled directly in main.py.
"""

CREATORS_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS creators (
    telegram_id TEXT PRIMARY KEY,
    username TEXT,
    is_pro INTEGER DEFAULT 0,
    pro_activated_at TEXT
)
"""
