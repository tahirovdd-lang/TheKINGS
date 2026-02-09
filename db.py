import sqlite3
from typing import Any, Dict

DB_PATH = "data.sqlite"


def get_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    with get_conn() as con:
        con.execute("""
        CREATE TABLE IF NOT EXISTS appointments(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            user_name TEXT,
            user_phone TEXT,
            master_id INTEGER,
            master_name TEXT,
            date TEXT,
            time TEXT,
            duration_min INTEGER,
            total_price INTEGER,
            services_json TEXT,
            comment TEXT,
            status TEXT DEFAULT 'pending',
            created_at TEXT DEFAULT (datetime('now'))
        )
        """)
        con.execute("CREATE INDEX IF NOT EXISTS idx_user ON appointments(user_id)")
        con.execute("CREATE INDEX IF NOT EXISTS idx_slot ON appointments(master_id, date, time)")
        con.commit()


def slot_taken(master_id: int, date: str, time: str) -> bool:
    with get_conn() as con:
        row = con.execute(
            "SELECT id FROM appointments WHERE master_id=? AND date=? AND time=? AND status IN ('pending','confirmed')",
            (master_id, date, time)
        ).fetchone()
        return bool(row)


def create_appointment(data: Dict[str, Any]) -> int:
    with get_conn() as con:
        cur = con.execute("""
            INSERT INTO appointments(
                user_id, user_name, user_phone,
                master_id, master_name,
                date, time,
                duration_min, total_price,
                services_json, comment, status
            )
            VALUES(?,?,?,?,?,?,?,?,?,?,?,?)
        """, (
            data["user_id"],
            data.get("user_name", ""),
            data.get("user_phone", ""),
            data["master_id"],
            data.get("master_name", ""),
            data["date"],
            data["time"],
            data.get("duration_min", 0),
            data.get("total_price", 0),
            data.get("services_json", "[]"),
            data.get("comment", ""),
            data.get("status", "pending"),
        ))
        con.commit()
        return int(cur.lastrowid)
