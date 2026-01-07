from backend.app.db import get_db

conn = get_db()
cur = conn.cursor()

cur.execute("SELECT COUNT(*) FROM creators")
print("Creators count:", cur.fetchone())

conn.close()
