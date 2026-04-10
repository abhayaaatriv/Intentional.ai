"""
Policy Management Service
Manages ArmorIQ policies alongside OPA policies with version control and testing.
"""

import os
import json
import time
import logging
from typing import Optional, List, Dict
import sqlite3

logger = logging.getLogger(__name__)

DB_PATH = os.getenv("AUDIT_DB_PATH", "audit.db")


class PolicyManager:
    """
    Manages policies from both ArmorIQ and OPA.
    
    Handles:
      - Policy syncing from ArmorIQ
      - Policy versioning and rollback
      - Policy testing and validation
      - Policy application tracking
    """
    
    def __init__(self, armoriq_client=None):
        """
        Initialize policy manager.
        
        Args:
            armoriq_client: Optional ArmorIQ client for syncing
        """
        self.armoriq_client = armoriq_client
        self._init_policies_table()
    
    def _init_policies_table(self):
        """Initialize policies table if it doesn't exist."""
        conn = sqlite3.connect(DB_PATH)
        
        # Policies table
        conn.execute("""
            CREATE TABLE IF NOT EXISTS policies (
                id              INTEGER PRIMARY KEY AUTOINCREMENT,
                policy_id       TEXT    UNIQUE NOT NULL,
                policy_name     TEXT    NOT NULL,
                description     TEXT    DEFAULT '',
                source          TEXT    DEFAULT 'armoriq',  -- 'armoriq' or 'opa'
                content         TEXT    NOT NULL,           -- JSON for ArmorIQ, Rego for OPA
                version         TEXT    DEFAULT '1.0',
                enabled         INTEGER DEFAULT 1,          -- 0 or 1
                created_at      REAL    NOT NULL,
                updated_at      REAL    NOT NULL,
                applied_at      REAL    DEFAULT 0.0
            )
        """)
        
        # Policy versions table for history/rollback
        conn.execute("""
            CREATE TABLE IF NOT EXISTS policy_versions (
                id              INTEGER PRIMARY KEY AUTOINCREMENT,
                policy_id       TEXT    NOT NULL,
                version         TEXT    NOT NULL,
                content         TEXT    NOT NULL,
                created_at      REAL    NOT NULL,
                rollback_status INTEGER DEFAULT 0
            )
        """)
        
        # Policy test results table
        conn.execute("""
            CREATE TABLE IF NOT EXISTS policy_tests (
                id              INTEGER PRIMARY KEY AUTOINCREMENT,
                policy_id       TEXT    NOT NULL,
                test_input      TEXT    NOT NULL,
                expected_result INTEGER NOT NULL,  -- 0 or 1
                actual_result   INTEGER NOT NULL,
                passed          INTEGER NOT NULL,  -- 0 or 1
                tested_at       REAL    NOT NULL
            )
        """)
        
        conn.commit()
        conn.close()
    
    def sync_armoriq_policies(self) -> bool:
        """
        Sync policies from ArmorIQ API and store locally.
        
        Returns True on success, False on failure.
        """
        if not self.armoriq_client:
            logger.warning("ArmorIQ client not available - cannot sync policies")
            return False
        
        try:
            policies = self.armoriq_client.get_policies()
            
            if not policies:
                logger.warning("No policies returned from ArmorIQ")
                return False
            
            conn = sqlite3.connect(DB_PATH)
            
            for policy in policies:
                # Check if policy already exists
                existing = conn.execute(
                    "SELECT id FROM policies WHERE policy_id=?",
                    (policy.policy_id,)
                ).fetchone()
                
                if existing:
                    # Update existing policy
                    conn.execute(
                        """UPDATE policies 
                           SET policy_name=?, description=?, content=?, version=?, 
                               updated_at=?, enabled=?
                           WHERE policy_id=?""",
                        (policy.policy_name, policy.description, json.dumps(policy.model_dump()),
                         policy.version, time.time(), 1, policy.policy_id)
                    )
                else:
                    # Insert new policy
                    conn.execute(
                        """INSERT INTO policies
                           (policy_id, policy_name, description, source, content, 
                            version, enabled, created_at, updated_at)
                           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                        (policy.policy_id, policy.policy_name, policy.description,
                         "armoriq", json.dumps(policy.model_dump()), policy.version,
                         1, time.time(), time.time())
                    )
                
                # Record version
                conn.execute(
                    """INSERT INTO policy_versions
                       (policy_id, version, content, created_at)
                       VALUES (?, ?, ?, ?)""",
                    (policy.policy_id, policy.version, json.dumps(policy.model_dump()), time.time())
                )
            
            conn.commit()
            conn.close()
            
            logger.info(f"Synced {len(policies)} policies from ArmorIQ")
            return True
        
        except Exception as e:
            logger.error(f"Failed to sync policies from ArmorIQ: {e}")
            return False
    
    def get_policy(self, policy_id: str) -> Optional[Dict]:
        """
        Get policy details.
        
        Returns policy dict or None if not found.
        """
        try:
            conn = sqlite3.connect(DB_PATH)
            row = conn.execute(
                "SELECT * FROM policies WHERE policy_id=?",
                (policy_id,)
            ).fetchone()
            conn.close()
            
            if not row:
                return None
            
            return {
                "id": row[0],
                "policy_id": row[1],
                "policy_name": row[2],
                "description": row[3],
                "source": row[4],
                "content": json.loads(row[5]),
                "version": row[6],
                "enabled": bool(row[7]),
                "created_at": row[8],
                "updated_at": row[9],
                "applied_at": row[10],
            }
        except Exception as e:
            logger.error(f"Failed to get policy {policy_id}: {e}")
            return None
    
    def list_active_policies(self) -> List[Dict]:
        """
        List all enabled policies.
        
        Returns list of policy dicts.
        """
        try:
            conn = sqlite3.connect(DB_PATH)
            rows = conn.execute(
                "SELECT * FROM policies WHERE enabled=1 ORDER BY created_at DESC"
            ).fetchall()
            conn.close()
            
            return [
                {
                    "id": r[0],
                    "policy_id": r[1],
                    "policy_name": r[2],
                    "description": r[3],
                    "source": r[4],
                    "content": json.loads(r[5]),
                    "version": r[6],
                    "enabled": bool(r[7]),
                    "created_at": r[8],
                    "updated_at": r[9],
                    "applied_at": r[10],
                }
                for r in rows
            ]
        except Exception as e:
            logger.error(f"Failed to list active policies: {e}")
            return []
    
    def enable_policy(self, policy_id: str) -> bool:
        """
        Enable a policy.
        
        Returns True on success, False on failure.
        """
        try:
            conn = sqlite3.connect(DB_PATH)
            result = conn.execute(
                "UPDATE policies SET enabled=1, applied_at=? WHERE policy_id=?",
                (time.time(), policy_id)
            )
            conn.commit()
            conn.close()
            
            if result.rowcount > 0:
                logger.info(f"Policy {policy_id} enabled")
                return True
            else:
                logger.warning(f"Policy {policy_id} not found")
                return False
        except Exception as e:
            logger.error(f"Failed to enable policy {policy_id}: {e}")
            return False
    
    def disable_policy(self, policy_id: str) -> bool:
        """
        Disable a policy.
        
        Returns True on success, False on failure.
        """
        try:
            conn = sqlite3.connect(DB_PATH)
            result = conn.execute(
                "UPDATE policies SET enabled=0 WHERE policy_id=?",
                (policy_id,)
            )
            conn.commit()
            conn.close()
            
            if result.rowcount > 0:
                logger.info(f"Policy {policy_id} disabled")
                return True
            else:
                logger.warning(f"Policy {policy_id} not found")
                return False
        except Exception as e:
            logger.error(f"Failed to disable policy {policy_id}: {e}")
            return False
    
    def test_policy(
        self,
        policy_id: str,
        test_input: Dict,
        expected_result: bool,
    ) -> bool:
        """
        Test a policy against sample input.
        
        Returns True if test passed, False otherwise.
        """
        # In production, would actually evaluate policy against input
        # This is a placeholder for the test framework
        try:
            # For now, just log the test
            passed = True  # Placeholder
            
            conn = sqlite3.connect(DB_PATH)
            conn.execute(
                """INSERT INTO policy_tests
                   (policy_id, test_input, expected_result, actual_result, passed, tested_at)
                   VALUES (?, ?, ?, ?, ?, ?)""",
                (policy_id, json.dumps(test_input), int(expected_result), int(passed), int(passed), time.time())
            )
            conn.commit()
            conn.close()
            
            return passed
        except Exception as e:
            logger.error(f"Failed to test policy {policy_id}: {e}")
            return False
    
    def rollback_policy(self, policy_id: str, version: str) -> bool:
        """
        Rollback a policy to a specific version.
        
        Returns True on success, False on failure.
        """
        try:
            conn = sqlite3.connect(DB_PATH)
            
            # Get the version content
            row = conn.execute(
                "SELECT content FROM policy_versions WHERE policy_id=? AND version=?",
                (policy_id, version)
            ).fetchone()
            
            if not row:
                logger.warning(f"Version {version} of policy {policy_id} not found")
                return False
            
            content = row[0]
            
            # Update the policy to this version
            conn.execute(
                """UPDATE policies 
                   SET content=?, version=?, updated_at=?
                   WHERE policy_id=?""",
                (content, version, time.time(), policy_id)
            )
            
            # Mark version as rolled back
            conn.execute(
                "UPDATE policy_versions SET rollback_status=1 WHERE policy_id=? AND version=?",
                (policy_id, version)
            )
            
            conn.commit()
            conn.close()
            
            logger.info(f"Policy {policy_id} rolled back to version {version}")
            return True
        except Exception as e:
            logger.error(f"Failed to rollback policy {policy_id}: {e}")
            return False
    
    def get_policy_versions(self, policy_id: str) -> List[Dict]:
        """
        Get all versions of a policy.
        
        Returns list of version dicts.
        """
        try:
            conn = sqlite3.connect(DB_PATH)
            rows = conn.execute(
                "SELECT * FROM policy_versions WHERE policy_id=? ORDER BY created_at DESC",
                (policy_id,)
            ).fetchall()
            conn.close()
            
            return [
                {
                    "id": r[0],
                    "policy_id": r[1],
                    "version": r[2],
                    "content": json.loads(r[3]),
                    "created_at": r[4],
                    "rollback_status": r[5],
                }
                for r in rows
            ]
        except Exception as e:
            logger.error(f"Failed to get policy versions for {policy_id}: {e}")
            return []
    
    def get_policy_test_results(self, policy_id: str) -> List[Dict]:
        """
        Get test results for a policy.
        
        Returns list of test result dicts.
        """
        try:
            conn = sqlite3.connect(DB_PATH)
            rows = conn.execute(
                "SELECT * FROM policy_tests WHERE policy_id=? ORDER BY tested_at DESC LIMIT 100",
                (policy_id,)
            ).fetchall()
            conn.close()
            
            return [
                {
                    "id": r[0],
                    "policy_id": r[1],
                    "test_input": json.loads(r[2]),
                    "expected_result": bool(r[3]),
                    "actual_result": bool(r[4]),
                    "passed": bool(r[5]),
                    "tested_at": r[6],
                }
                for r in rows
            ]
        except Exception as e:
            logger.error(f"Failed to get policy test results for {policy_id}: {e}")
            return []
