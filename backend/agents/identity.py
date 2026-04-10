"""
Agent Identity Management Module
Handles agent registration, verification, and capability scope management with ArmorIQ.
"""

import os
import json
import time
import logging
from typing import Optional, List
import sqlite3

logger = logging.getLogger(__name__)

DB_PATH = os.getenv("AUDIT_DB_PATH", "audit.db")


class AgentIdentityManager:
    """
    Manages agent identities with ArmorIQ integration.
    
    Tracks:
      - Agent registration and provisioning
      - Agent capabilities and allowed actions
      - Agent verification status
      - Agent reputation and risk scores
    """
    
    def __init__(self, armoriq_client=None):
        """
        Initialize identity manager.
        
        Args:
            armoriq_client: Optional ArmorIQ client for registration
        """
        self.armoriq_client = armoriq_client
        self._init_agents_table()
    
    def _init_agents_table(self):
        """Initialize agents table if it doesn't exist."""
        conn = sqlite3.connect(DB_PATH)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS agents (
                id                  INTEGER PRIMARY KEY AUTOINCREMENT,
                agent_id            TEXT    UNIQUE NOT NULL,
                agent_name          TEXT    NOT NULL,
                capabilities        TEXT    DEFAULT '[]',  -- JSON array
                allowed_actions     TEXT    DEFAULT '[]',  -- JSON array
                ticker_scope        TEXT    DEFAULT '[]',  -- JSON array
                max_qty             INTEGER DEFAULT 0,
                destination_scope   TEXT    DEFAULT 'internal',
                registered_at       REAL    NOT NULL,
                verified            INTEGER DEFAULT 0,     -- 0 or 1
                verification_timestamp REAL DEFAULT 0.0,
                status              TEXT    DEFAULT 'active'  -- active|suspended|revoked
            )
        """)
        conn.commit()
        conn.close()
    
    def register_agent(
        self,
        agent_id: str,
        agent_name: str,
        capabilities: List[str],
        allowed_actions: List[str],
        ticker_scope: List[str],
        max_qty: int = 0,
        destination_scope: str = "internal",
    ) -> bool:
        """
        Register a new agent with capability scope.
        
        Returns True on success, False on failure.
        """
        try:
            conn = sqlite3.connect(DB_PATH)
            conn.execute(
                """INSERT INTO agents
                   (agent_id, agent_name, capabilities, allowed_actions, 
                    ticker_scope, max_qty, destination_scope, registered_at, status)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (agent_id, agent_name, json.dumps(capabilities), json.dumps(allowed_actions),
                 json.dumps(ticker_scope), max_qty, destination_scope, time.time(), "active")
            )
            conn.commit()
            conn.close()
            
            # Register with ArmorIQ if client available
            if self.armoriq_client:
                from armoriq.models import AgentIdentity
                identity = AgentIdentity(
                    agent_id=agent_id,
                    agent_name=agent_name,
                    capabilities=capabilities,
                    allowed_actions=allowed_actions,
                    ticker_scope=ticker_scope,
                    max_qty=max_qty,
                    destination_scope=destination_scope,
                    registered_at=time.time(),
                )
                self.armoriq_client.register_agent(identity)
            
            logger.info(f"Agent {agent_id} registered successfully")
            return True
        
        except sqlite3.IntegrityError:
            logger.warning(f"Agent {agent_id} already registered")
            return False
        except Exception as e:
            logger.error(f"Failed to register agent {agent_id}: {e}")
            return False
    
    def verify_agent(self, agent_id: str) -> bool:
        """
        Mark agent as verified.
        
        Returns True on success, False if agent not found.
        """
        try:
            conn = sqlite3.connect(DB_PATH)
            result = conn.execute(
                "UPDATE agents SET verified=1, verification_timestamp=? WHERE agent_id=?",
                (time.time(), agent_id)
            )
            conn.commit()
            conn.close()
            
            if result.rowcount > 0:
                logger.info(f"Agent {agent_id} verified")
                return True
            else:
                logger.warning(f"Agent {agent_id} not found")
                return False
        except Exception as e:
            logger.error(f"Failed to verify agent {agent_id}: {e}")
            return False
    
    def update_agent_scope(
        self,
        agent_id: str,
        capabilities: List[str] = None,
        allowed_actions: List[str] = None,
        ticker_scope: List[str] = None,
        max_qty: int = None,
    ) -> bool:
        """
        Update agent's capabilities and scope.
        
        Returns True on success, False if agent not found.
        """
        try:
            conn = sqlite3.connect(DB_PATH)
            
            # Build update clause
            updates = []
            params = []
            
            if capabilities is not None:
                updates.append("capabilities = ?")
                params.append(json.dumps(capabilities))
            if allowed_actions is not None:
                updates.append("allowed_actions = ?")
                params.append(json.dumps(allowed_actions))
            if ticker_scope is not None:
                updates.append("ticker_scope = ?")
                params.append(json.dumps(ticker_scope))
            if max_qty is not None:
                updates.append("max_qty = ?")
                params.append(max_qty)
            
            if not updates:
                return True  # Nothing to update
            
            params.append(agent_id)
            query = f"UPDATE agents SET {', '.join(updates)} WHERE agent_id = ?"
            
            result = conn.execute(query, params)
            conn.commit()
            conn.close()
            
            if result.rowcount > 0:
                # Update with ArmorIQ if client available
                if self.armoriq_client:
                    self.armoriq_client.update_agent_scope(
                        agent_id,
                        capabilities or [],
                        ticker_scope or [],
                        max_qty or 0
                    )
                logger.info(f"Agent {agent_id} scope updated")
                return True
            else:
                logger.warning(f"Agent {agent_id} not found")
                return False
        except Exception as e:
            logger.error(f"Failed to update agent {agent_id} scope: {e}")
            return False
    
    def suspend_agent(self, agent_id: str) -> bool:
        """
        Suspend an agent (disable without deleting).
        
        Returns True on success, False if agent not found.
        """
        try:
            conn = sqlite3.connect(DB_PATH)
            result = conn.execute(
                "UPDATE agents SET status='suspended' WHERE agent_id=?",
                (agent_id,)
            )
            conn.commit()
            conn.close()
            
            if result.rowcount > 0:
                logger.info(f"Agent {agent_id} suspended")
                return True
            else:
                logger.warning(f"Agent {agent_id} not found")
                return False
        except Exception as e:
            logger.error(f"Failed to suspend agent {agent_id}: {e}")
            return False
    
    def revoke_agent(self, agent_id: str) -> bool:
        """
        Revoke an agent (permanent disable).
        
        Returns True on success, False if agent not found.
        """
        try:
            conn = sqlite3.connect(DB_PATH)
            result = conn.execute(
                "UPDATE agents SET status='revoked' WHERE agent_id=?",
                (agent_id,)
            )
            conn.commit()
            conn.close()
            
            if result.rowcount > 0:
                # Revoke with ArmorIQ if client available
                if self.armoriq_client:
                    self.armoriq_client.revoke_agent(agent_id)
                logger.info(f"Agent {agent_id} revoked")
                return True
            else:
                logger.warning(f"Agent {agent_id} not found")
                return False
        except Exception as e:
            logger.error(f"Failed to revoke agent {agent_id}: {e}")
            return False
    
    def get_agent(self, agent_id: str) -> Optional[dict]:
        """
        Get agent details.
        
        Returns agent dict or None if not found.
        """
        try:
            conn = sqlite3.connect(DB_PATH)
            row = conn.execute(
                "SELECT * FROM agents WHERE agent_id=?",
                (agent_id,)
            ).fetchone()
            conn.close()
            
            if not row:
                return None
            
            return {
                "id": row[0],
                "agent_id": row[1],
                "agent_name": row[2],
                "capabilities": json.loads(row[3]),
                "allowed_actions": json.loads(row[4]),
                "ticker_scope": json.loads(row[5]),
                "max_qty": row[6],
                "destination_scope": row[7],
                "registered_at": row[8],
                "verified": bool(row[9]),
                "verification_timestamp": row[10],
                "status": row[11],
            }
        except Exception as e:
            logger.error(f"Failed to get agent {agent_id}: {e}")
            return None
    
    def list_agents(self, status: str = "active") -> List[dict]:
        """
        List all agents with optional status filter.
        
        Returns list of agent dicts.
        """
        try:
            conn = sqlite3.connect(DB_PATH)
            
            if status:
                rows = conn.execute(
                    "SELECT * FROM agents WHERE status=? ORDER BY registered_at DESC",
                    (status,)
                ).fetchall()
            else:
                rows = conn.execute(
                    "SELECT * FROM agents ORDER BY registered_at DESC"
                ).fetchall()
            
            conn.close()
            
            return [
                {
                    "id": r[0],
                    "agent_id": r[1],
                    "agent_name": r[2],
                    "capabilities": json.loads(r[3]),
                    "allowed_actions": json.loads(r[4]),
                    "ticker_scope": json.loads(r[5]),
                    "max_qty": r[6],
                    "destination_scope": r[7],
                    "registered_at": r[8],
                    "verified": bool(r[9]),
                    "verification_timestamp": r[10],
                    "status": r[11],
                }
                for r in rows
            ]
        except Exception as e:
            logger.error(f"Failed to list agents: {e}")
            return []
