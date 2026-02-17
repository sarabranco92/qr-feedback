import os
import sqlite3
from pathlib import Path

# Local dev default: data/app.db
# On Render: set DB_PATH=/data/app.db (persistent disk mount)
DB_PATH = Path(os.environ.get("DB_PATH", "data/app.db"))

def get_conn() -> sqlite3.Connection:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db() -> None:
    conn = get_conn()
    cur = conn.cursor()

    cur.execute("""
    CREATE TABLE IF NOT EXISTS businesses (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        slug TEXT UNIQUE NOT NULL,
        name TEXT NOT NULL,
        created_at TEXT DEFAULT (datetime('now'))
    );
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS reviews (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        business_id INTEGER NOT NULL,
        rating INTEGER NOT NULL CHECK (rating BETWEEN 1 AND 5),
        comment TEXT,
        contact_email TEXT,
        created_at TEXT DEFAULT (datetime('now')),
        seen INTEGER DEFAULT 0,
        flagged INTEGER DEFAULT 0,
        FOREIGN KEY (business_id) REFERENCES businesses(id)
    );
    """)

    # Seed demo business
    cur.execute(
        "INSERT OR IGNORE INTO businesses (slug, name) VALUES (?, ?);",
        ("demo", "Demo Shop")
    )

    conn.commit()
    conn.close()
