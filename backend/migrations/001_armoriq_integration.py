"""
Database Migration: ArmorIQ Integration
This migration adds ArmorIQ compliance fields to audit_log and creates new tables
for agent identity and policy management.

Run with: python migrations/001_armoriq_integration.py
"""

import sqlite3
import os
import sys

DB_PATH = os.getenv("AUDIT_DB_PATH", "audit.db")


def migrate():
    """Execute migration to add ArmorIQ fields."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    print("[Migration] Starting ArmorIQ integration migration...")
    
    try:
        # Check if migration already applied
        cursor.execute("PRAGMA table_info(audit_log)")
        columns = [col[1] for col in cursor.fetchall()]
        
        if "armoriq_verdict" in columns:
            print("[Migration] ArmorIQ fields already exist - skipping migration")
            return True
        
        # Step 1: Backup existing table
        print("[Migration] Backing up existing audit_log...")
        cursor.execute("""
            ALTER TABLE audit_log RENAME TO audit_log_backup
        """)
        
        # Step 2: Create new table with extended schema
        print("[Migration] Creating new audit_log table with ArmorIQ fields...")
        cursor.execute("""
            CREATE TABLE audit_log (
                id                       INTEGER PRIMARY KEY AUTOINCREMENT,
                agent_id                 TEXT    NOT NULL,
                action                   TEXT    NOT NULL,
                ticker                   TEXT    DEFAULT '',
                qty                      INTEGER DEFAULT 0,
                allowed                  INTEGER NOT NULL,
                violations               TEXT    DEFAULT '[]',
                timestamp                REAL    NOT NULL,
                
                opa_verdict              INTEGER DEFAULT 0,
                armoriq_verdict          INTEGER DEFAULT 0,
                armoriq_policy_id        TEXT    DEFAULT '',
                armoriq_violations       TEXT    DEFAULT '[]',
                agent_identity_verified  INTEGER DEFAULT 0,
                threat_score             REAL    DEFAULT 0.0,
                compliance_status        TEXT    DEFAULT 'unknown'
            )
        """)
        
        # Step 3: Copy data from backup
        print("[Migration] Migrating data from backup...")
        cursor.execute("""
            INSERT INTO audit_log 
            (id, agent_id, action, ticker, qty, allowed, violations, timestamp,
             opa_verdict, armoriq_verdict)
            SELECT id, agent_id, action, ticker, qty, allowed, violations, timestamp,
                   allowed, allowed
            FROM audit_log_backup
        """)
        
        # Step 4: Drop backup table
        print("[Migration] Cleaning up backup table...")
        cursor.execute("DROP TABLE audit_log_backup")
        
        conn.commit()
        print("[Migration] ✓ Audit log migration complete")
        
        # Step 5: Create agents table
        print("[Migration] Creating agents table...")
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS agents (
                id                  INTEGER PRIMARY KEY AUTOINCREMENT,
                agent_id            TEXT    UNIQUE NOT NULL,
                agent_name          TEXT    NOT NULL,
                capabilities        TEXT    DEFAULT '[]',
                allowed_actions     TEXT    DEFAULT '[]',
                ticker_scope        TEXT    DEFAULT '[]',
                max_qty             INTEGER DEFAULT 0,
                destination_scope   TEXT    DEFAULT 'internal',
                registered_at       REAL    NOT NULL,
                verified            INTEGER DEFAULT 0,
                verification_timestamp REAL DEFAULT 0.0,
                status              TEXT    DEFAULT 'active'
            )
        """)
        
        # Step 6: Create policies table
        print("[Migration] Creating policies table...")
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS policies (
                id              INTEGER PRIMARY KEY AUTOINCREMENT,
                policy_id       TEXT    UNIQUE NOT NULL,
                policy_name     TEXT    NOT NULL,
                description     TEXT    DEFAULT '',
                source          TEXT    DEFAULT 'armoriq',
                content         TEXT    NOT NULL,
                version         TEXT    DEFAULT '1.0',
                enabled         INTEGER DEFAULT 1,
                created_at      REAL    NOT NULL,
                updated_at      REAL    NOT NULL,
                applied_at      REAL    DEFAULT 0.0
            )
        """)
        
        # Step 7: Create policy_versions table
        print("[Migration] Creating policy_versions table...")
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS policy_versions (
                id              INTEGER PRIMARY KEY AUTOINCREMENT,
                policy_id       TEXT    NOT NULL,
                version         TEXT    NOT NULL,
                content         TEXT    NOT NULL,
                created_at      REAL    NOT NULL,
                rollback_status INTEGER DEFAULT 0
            )
        """)
        
        # Step 8: Create policy_tests table
        print("[Migration] Creating policy_tests table...")
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS policy_tests (
                id              INTEGER PRIMARY KEY AUTOINCREMENT,
                policy_id       TEXT    NOT NULL,
                test_input      TEXT    NOT NULL,
                expected_result INTEGER NOT NULL,
                actual_result   INTEGER NOT NULL,
                passed          INTEGER NOT NULL,
                tested_at       REAL    NOT NULL
            )
        """)
        
        conn.commit()
        print("[Migration] ✓ All tables created successfully")
        print("[Migration] ✓ ArmorIQ integration migration complete!")
        
        return True
    
    except Exception as e:
        print(f"[Migration] ERROR: {e}")
        conn.rollback()
        return False
    
    finally:
        conn.close()


if __name__ == "__main__":
    success = migrate()
    sys.exit(0 if success else 1)
