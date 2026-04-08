"""
CapabilityGuard — SQLite Audit Log
Schema: audit_log(id, agent_id, action, ticker, qty, allowed, violations, timestamp)
"""
import sqlite3
import time
import json
import os

DB_PATH = os.getenv("AUDIT_DB_PATH", "audit.db")


def init_db():
    conn = sqlite3.connect(DB_PATH)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS audit_log (
            id         INTEGER PRIMARY KEY AUTOINCREMENT,
            agent_id   TEXT    NOT NULL,
            action     TEXT    NOT NULL,
            ticker     TEXT    DEFAULT '',
            qty        INTEGER DEFAULT 0,
            allowed    INTEGER NOT NULL,   -- 0 or 1
            violations TEXT    DEFAULT '[]', -- JSON array of strings
            timestamp  REAL    NOT NULL
        )
    """)
    conn.commit()
    conn.close()


def log_action(agent_id: str, action: str, ticker: str, qty: int,
               allowed: bool, violations: list[str]):
    conn = sqlite3.connect(DB_PATH)
    conn.execute(
        """INSERT INTO audit_log
           (agent_id, action, ticker, qty, allowed, violations, timestamp)
           VALUES (?, ?, ?, ?, ?, ?, ?)""",
        (agent_id, action, ticker, qty, int(allowed),
         json.dumps(violations), time.time())
    )
    conn.commit()
    conn.close()


def get_recent_logs(limit: int = 100) -> list[dict]:
    conn = sqlite3.connect(DB_PATH)
    rows = conn.execute(
        "SELECT * FROM audit_log ORDER BY timestamp DESC LIMIT ?", (limit,)
    ).fetchall()
    conn.close()
    return [
        {
            "id": r[0], "agent_id": r[1], "action": r[2],
            "ticker": r[3], "qty": r[4], "allowed": bool(r[5]),
            "violations": json.loads(r[6]), "timestamp": r[7],
        }
        for r in rows
    ]


def get_stats() -> dict:
    conn = sqlite3.connect(DB_PATH)
    total = conn.execute("SELECT COUNT(*) FROM audit_log").fetchone()[0]
    allowed = conn.execute("SELECT COUNT(*) FROM audit_log WHERE allowed=1").fetchone()[0]
    conn.close()
    return {"total": total, "allowed": allowed, "blocked": total - allowed}
