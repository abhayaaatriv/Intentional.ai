#!/usr/bin/env python3
"""
Database initialization script for ArmorIQ integration.
Initializes audit.db with all required tables and schemas.

Run with: python backend/init_db.py
"""

import os
import sys

# Add backend to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from audit.db import init_db
from migrations.001_armoriq_integration import migrate


def main():
    """Initialize the database."""
    print("=" * 60)
    print("ArmorIQ Intentional.ai Database Initialization")
    print("=" * 60)
    
    db_path = os.getenv("AUDIT_DB_PATH", "audit.db")
    print(f"\nDatabase path: {db_path}")
    
    # Step 1: Initialize audit log
    print("\n[1/2] Initializing audit log table...")
    try:
        init_db()
        print("✓ Audit log initialized")
    except Exception as e:
        print(f"✗ Error initializing audit log: {e}")
        return False
    
    # Step 2: Run migration
    print("\n[2/2] Running ArmorIQ integration migration...")
    try:
        success = migrate()
        if success:
            print("✓ Migration completed successfully")
        else:
            print("✗ Migration failed")
            return False
    except Exception as e:
        print(f"✗ Error running migration: {e}")
        return False
    
    print("\n" + "=" * 60)
    print("✓ Database initialization complete!")
    print("=" * 60)
    print("\nYou can now:")
    print("1. Start the gateway: python backend/gateway/main.py")
    print("2. Start the orchestrator: python backend/orchestrator/main.py")
    print("3. Open the dashboard: http://localhost:8080")
    
    return True


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
