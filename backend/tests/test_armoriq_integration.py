"""
ArmorIQ Integration Tests
Validates ArmorIQ API client, gateway integration, and compliance tracking.

Run with: python -m pytest tests/test_armoriq_integration.py -v
"""

import sys
import os
import unittest
import json
import time

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from armoriq.client import ArmorIQClient
from armoriq.models import (
    PolicyCheckRequest,
    ComplianceStatus,
    AgentIdentity,
    AgentVerificationRequest,
    SeverityLevel,
)
from audit.db import init_db, log_action, get_compliance_stats, get_compliance_report
from agents.identity import AgentIdentityManager
from policies.manager import PolicyManager


class TestArmorIQClient(unittest.TestCase):
    """Test ArmorIQ API Client"""
    
    def setUp(self):
        self.client = ArmorIQClient()
    
    def test_client_initialization(self):
        """Test that client initializes without API key"""
        self.assertIsNotNone(self.client)
        self.assertEqual(self.client.api_url, "https://api.armoriq.ai")
    
    def test_verify_agent_identity_fail_safe(self):
        """Test that agent verification returns fail-safe response on error"""
        response = self.client.verify_agent_identity("test-agent", "fake-token")
        self.assertFalse(response.verified)
        self.assertEqual(len(response.violations), 1)
    
    def test_policy_check_fail_safe(self):
        """Test that policy check returns fail-safe (deny) on error"""
        req = PolicyCheckRequest(
            agent_id="test-agent",
            action="BUY",
            ticker="AAPL",
            qty=100,
        )
        response = self.client.check_policy_compliance(req)
        self.assertFalse(response.allowed)
        self.assertEqual(response.threat_score, 100.0)
    
    def test_health_check_unavailable(self):
        """Test health check when service is unavailable"""
        is_healthy = self.client.health_check()
        # With no API key, should return False
        self.assertFalse(is_healthy)


class TestAuditDB(unittest.TestCase):
    """Test Audit Database with ArmorIQ fields"""
    
    def setUp(self):
        # Use in-memory test database
        os.environ['AUDIT_DB_PATH'] = ':memory:'
        init_db()
    
    def test_log_action_with_armoriq_data(self):
        """Test logging action with ArmorIQ compliance data"""
        log_action(
            agent_id="test-agent",
            action="BUY",
            ticker="AAPL",
            qty=100,
            allowed=True,
            violations=[],
            opa_verdict=True,
            armoriq_verdict=True,
            agent_identity_verified=True,
            threat_score=25.5,
            compliance_status="compliant"
        )
        
        stats = get_compliance_stats()
        self.assertEqual(stats['total_actions'], 1)
        self.assertEqual(stats['opa_passed'], 1)
        self.assertEqual(stats['armoriq_passed'], 1)
        self.assertEqual(stats['both_passed'], 1)
    
    def test_compliance_stats_calculation(self):
        """Test compliance statistics calculation"""
        # Log passing action
        log_action("agent1", "BUY", "AAPL", 100, True, [],
                  opa_verdict=True, armoriq_verdict=True,
                  agent_identity_verified=True, threat_score=10.0,
                  compliance_status="compliant")
        
        # Log failing action
        log_action("agent2", "SELL", "GOOGL", 50, False, ["opa_violation"],
                  opa_verdict=False, armoriq_verdict=False,
                  agent_identity_verified=False, threat_score=75.0,
                  compliance_status="non_compliant")
        
        stats = get_compliance_stats()
        self.assertEqual(stats['total_actions'], 2)
        self.assertEqual(stats['opa_passed'], 1)
        self.assertEqual(stats['armoriq_passed'], 1)
        self.assertEqual(stats['both_passed'], 1)
        self.assertEqual(stats['agent_identity_verified'], 1)
        self.assertEqual(stats['opa_pass_rate'], 50.0)
        self.assertEqual(stats['armoriq_pass_rate'], 50.0)
        self.assertEqual(stats['compliance_rate'], 50.0)
    
    def test_compliance_report_generation(self):
        """Test compliance report generation"""
        now = time.time()
        
        log_action("agent1", "BUY", "AAPL", 100, True, [],
                  opa_verdict=True, armoriq_verdict=True,
                  agent_identity_verified=True, threat_score=10.0,
                  compliance_status="compliant")
        
        report = get_compliance_report(now - 3600, now + 3600)
        self.assertEqual(len(report), 1)
        self.assertEqual(report[0]['agent_id'], 'agent1')
        self.assertEqual(report[0]['compliance_status'], 'compliant')


class TestAgentIdentityManager(unittest.TestCase):
    """Test Agent Identity Management"""
    
    def setUp(self):
        os.environ['AUDIT_DB_PATH'] = ':memory:'
        self.manager = AgentIdentityManager()
    
    def test_register_agent(self):
        """Test agent registration"""
        success = self.manager.register_agent(
            agent_id="research-agent",
            agent_name="Research Agent",
            capabilities=["READ", "LOG"],
            allowed_actions=["READ"],
            ticker_scope=["*"],
            max_qty=0,
            destination_scope="internal"
        )
        self.assertTrue(success)
    
    def test_get_agent(self):
        """Test retrieving agent details"""
        self.manager.register_agent(
            agent_id="exec-agent",
            agent_name="Execution Agent",
            capabilities=["BUY", "SELL"],
            allowed_actions=["BUY", "SELL"],
            ticker_scope=["AAPL", "GOOGL"],
            max_qty=1000,
        )
        
        agent = self.manager.get_agent("exec-agent")
        self.assertIsNotNone(agent)
        self.assertEqual(agent['agent_id'], 'exec-agent')
        self.assertEqual(agent['agent_name'], 'Execution Agent')
        self.assertIn("BUY", agent['capabilities'])
    
    def test_update_agent_scope(self):
        """Test updating agent scope"""
        self.manager.register_agent(
            agent_id="test-agent",
            agent_name="Test Agent",
            capabilities=["READ"],
            allowed_actions=["READ"],
            ticker_scope=["AAPL"],
            max_qty=0,
        )
        
        success = self.manager.update_agent_scope(
            agent_id="test-agent",
            capabilities=["READ", "BUY"],
            allowed_actions=["READ", "BUY"],
            ticker_scope=["AAPL", "GOOGL"],
            max_qty=500,
        )
        self.assertTrue(success)
        
        agent = self.manager.get_agent("test-agent")
        self.assertIn("BUY", agent['capabilities'])
        self.assertIn("GOOGL", agent['ticker_scope'])
    
    def test_revoke_agent(self):
        """Test revoking an agent"""
        self.manager.register_agent(
            agent_id="revoke-test",
            agent_name="Revoke Test",
            capabilities=["READ"],
            allowed_actions=["READ"],
            ticker_scope=["*"],
        )
        
        success = self.manager.revoke_agent("revoke-test")
        self.assertTrue(success)
        
        agent = self.manager.get_agent("revoke-test")
        self.assertEqual(agent['status'], 'revoked')


class TestPolicyManager(unittest.TestCase):
    """Test Policy Management"""
    
    def setUp(self):
        os.environ['AUDIT_DB_PATH'] = ':memory:'
        self.manager = PolicyManager()
    
    def test_policy_tables_created(self):
        """Test that policy tables are created"""
        self.manager._init_policies_table()
        # Should not raise exception
        self.assertTrue(True)
    
    def test_enable_disable_policy(self):
        """Test enabling and disabling policies"""
        import sqlite3
        from time import time as now
        
        conn = sqlite3.connect(':memory:')
        self.manager._init_policies_table()
        
        # Insert test policy
        conn.execute("""
            INSERT INTO policies 
            (policy_id, policy_name, description, source, content, version, enabled, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, ("test-policy", "Test Policy", "A test policy", "armoriq", "{}", "1.0", 1, now(), now()))
        conn.commit()
        conn.close()


class TestIntegration(unittest.TestCase):
    """Integration Tests"""
    
    def setUp(self):
        os.environ['AUDIT_DB_PATH'] = ':memory:'
        init_db()
        self.client = ArmorIQClient()
        self.identity_mgr = AgentIdentityManager(armoriq_client=self.client)
    
    def test_full_compliance_flow(self):
        """Test complete compliance flow: registration -> verification -> compliance check"""
        # 1. Register agent
        self.identity_mgr.register_agent(
            agent_id="flow-test-agent",
            agent_name="Flow Test",
            capabilities=["BUY"],
            allowed_actions=["BUY"],
            ticker_scope=["AAPL"],
            max_qty=100,
        )
        
        agent = self.identity_mgr.get_agent("flow-test-agent")
        self.assertIsNotNone(agent)
        self.assertEqual(agent['status'], 'active')
        
        # 2. Log action with full compliance tracking
        log_action(
            agent_id="flow-test-agent",
            action="BUY",
            ticker="AAPL",
            qty=50,
            allowed=True,
            violations=[],
            opa_verdict=True,
            armoriq_verdict=True,
            agent_identity_verified=True,
            threat_score=15.0,
            compliance_status="compliant"
        )
        
        # 3. Verify compliance stats
        stats = get_compliance_stats()
        self.assertEqual(stats['total_actions'], 1)
        self.assertEqual(stats['both_passed'], 1)
        self.assertEqual(stats['compliance_rate'], 100.0)


def run_tests():
    """Run all tests"""
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    
    suite.addTests(loader.loadTestsFromTestCase(TestArmorIQClient))
    suite.addTests(loader.loadTestsFromTestCase(TestAuditDB))
    suite.addTests(loader.loadTestsFromTestCase(TestAgentIdentityManager))
    suite.addTests(loader.loadTestsFromTestCase(TestPolicyManager))
    suite.addTests(loader.loadTestsFromTestCase(TestIntegration))
    
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    return 0 if result.wasSuccessful() else 1


if __name__ == '__main__':
    exit(run_tests())
