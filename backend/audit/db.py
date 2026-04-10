"""
CapabilityGuard — SQLite Audit Log
Extended schema with ArmorIQ compliance data:
  audit_log(id, agent_id, action, ticker, qty, allowed, violations, timestamp,
            opa_verdict, armoriq_verdict, armoriq_policy_id, armoriq_violations,
            agent_identity_verified, threat_score, compliance_status)
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
            id                       INTEGER PRIMARY KEY AUTOINCREMENT,
            agent_id                 TEXT    NOT NULL,
            action                   TEXT    NOT NULL,
            ticker                   TEXT    DEFAULT '',
            qty                      INTEGER DEFAULT 0,
            allowed                  INTEGER NOT NULL,   -- 0 or 1
            violations               TEXT    DEFAULT '[]', -- JSON array (OPA)
            timestamp                REAL    NOT NULL,
            
            -- ArmorIQ extended fields
            opa_verdict              INTEGER DEFAULT 0,   -- 0 or 1
            armoriq_verdict          INTEGER DEFAULT 0,   -- 0 or 1
            armoriq_policy_id        TEXT    DEFAULT '',
            armoriq_violations       TEXT    DEFAULT '[]', -- JSON array
            agent_identity_verified  INTEGER DEFAULT 0,   -- 0 or 1
            threat_score             REAL    DEFAULT 0.0,
            compliance_status        TEXT    DEFAULT 'unknown'  -- compliant|non_compliant|unknown
        )
    """)
    conn.commit()
    conn.close()


def log_action(agent_id: str, action: str, ticker: str, qty: int,
               allowed: bool, violations: list[str], opa_verdict: bool = None,
               armoriq_verdict: bool = None, armoriq_policy_id: str = "",
               armoriq_violations: list = None, agent_identity_verified: bool = False,
               threat_score: float = 0.0, compliance_status: str = "unknown"):
    """
    Log action with OPA and ArmorIQ verdicts.
    
    If opa_verdict/armoriq_verdict not provided, uses 'allowed' for backward compatibility.
    """
    if opa_verdict is None:
        opa_verdict = allowed
    if armoriq_verdict is None:
        armoriq_verdict = allowed
    if armoriq_violations is None:
        armoriq_violations = []
    
    conn = sqlite3.connect(DB_PATH)
    conn.execute(
        """INSERT INTO audit_log
           (agent_id, action, ticker, qty, allowed, violations, timestamp,
            opa_verdict, armoriq_verdict, armoriq_policy_id, armoriq_violations,
            agent_identity_verified, threat_score, compliance_status)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (agent_id, action, ticker, qty, int(allowed),
         json.dumps(violations), time.time(),
         int(opa_verdict), int(armoriq_verdict), armoriq_policy_id,
         json.dumps(armoriq_violations), int(agent_identity_verified),
         threat_score, compliance_status)
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
            "opa_verdict": bool(r[8]), "armoriq_verdict": bool(r[9]),
            "armoriq_policy_id": r[10], "armoriq_violations": json.loads(r[11]),
            "agent_identity_verified": bool(r[12]), "threat_score": r[13],
            "compliance_status": r[14],
        }
        for r in rows
    ]


def get_stats() -> dict:
    conn = sqlite3.connect(DB_PATH)
    total = conn.execute("SELECT COUNT(*) FROM audit_log").fetchone()[0]
    allowed = conn.execute("SELECT COUNT(*) FROM audit_log WHERE allowed=1").fetchone()[0]
    conn.close()
    return {"total": total, "allowed": allowed, "blocked": total - allowed}


def get_compliance_stats() -> dict:
    """Get compliance statistics from audit log."""
    conn = sqlite3.connect(DB_PATH)
    total = conn.execute("SELECT COUNT(*) FROM audit_log").fetchone()[0]
    opa_passed = conn.execute("SELECT COUNT(*) FROM audit_log WHERE opa_verdict=1").fetchone()[0]
    armoriq_passed = conn.execute("SELECT COUNT(*) FROM audit_log WHERE armoriq_verdict=1").fetchone()[0]
    both_passed = conn.execute(
        "SELECT COUNT(*) FROM audit_log WHERE opa_verdict=1 AND armoriq_verdict=1"
    ).fetchone()[0]
    verified = conn.execute("SELECT COUNT(*) FROM audit_log WHERE agent_identity_verified=1").fetchone()[0]
    
    avg_threat = conn.execute("SELECT AVG(threat_score) FROM audit_log").fetchone()[0]
    max_threat = conn.execute("SELECT MAX(threat_score) FROM audit_log").fetchone()[0]
    
    conn.close()
    
    return {
        "total_actions": total,
        "opa_passed": opa_passed,
        "armoriq_passed": armoriq_passed,
        "both_passed": both_passed,
        "agent_identity_verified": verified,
        "avg_threat_score": avg_threat or 0.0,
        "max_threat_score": max_threat or 0.0,
        "opa_pass_rate": (opa_passed / total * 100) if total > 0 else 0.0,
        "armoriq_pass_rate": (armoriq_passed / total * 100) if total > 0 else 0.0,
        "compliance_rate": (both_passed / total * 100) if total > 0 else 0.0,
    }


def get_compliance_report(start_time: float, end_time: float, agent_id: str = None) -> list[dict]:
    """Get compliance report for a time range, optionally filtered by agent."""
    conn = sqlite3.connect(DB_PATH)
    
    if agent_id:
        rows = conn.execute(
            """SELECT * FROM audit_log 
               WHERE timestamp >= ? AND timestamp <= ? AND agent_id = ?
               ORDER BY timestamp DESC""",
            (start_time, end_time, agent_id)
        ).fetchall()
    else:
        rows = conn.execute(
            """SELECT * FROM audit_log 
               WHERE timestamp >= ? AND timestamp <= ?
               ORDER BY timestamp DESC""",
            (start_time, end_time)
        ).fetchall()
    
    conn.close()
    
    return [
        {
            "id": r[0], "agent_id": r[1], "action": r[2],
            "ticker": r[3], "qty": r[4], "allowed": bool(r[5]),
            "violations": json.loads(r[6]), "timestamp": r[7],
            "opa_verdict": bool(r[8]), "armoriq_verdict": bool(r[9]),
            "armoriq_policy_id": r[10], "armoriq_violations": json.loads(r[11]),
            "agent_identity_verified": bool(r[12]), "threat_score": r[13],
            "compliance_status": r[14],
        }
        for r in rows
    ]
