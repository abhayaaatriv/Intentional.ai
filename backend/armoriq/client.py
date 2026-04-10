"""
ArmorIQ API Client
HTTP client for all ArmorIQ API interactions with proper error handling,
retry logic, caching, and fail-safe defaults.
"""

import os
import time
import json
import logging
from typing import Optional, List, Dict
import requests
from .models import (
    PolicyCheckRequest,
    PolicyCheckResponse,
    AgentIdentity,
    AgentVerificationRequest,
    AgentVerificationResponse,
    ComplianceStatus,
    ThreatIntelligence,
    ArmorIQViolation,
    SeverityLevel,
    PolicyDefinition,
)

logger = logging.getLogger(__name__)


class ArmorIQClient:
    """
    Client for ArmorIQ Intent Assurance API.
    
    Handles:
      - Agent identity verification
      - Policy checks and enforcement
      - Threat intelligence queries
      - Compliance reporting
      - Automatic retries and fail-safe defaults
    """
    
    def __init__(self):
        self.api_key = os.getenv("ARMORIQ_API_KEY", "")
        self.api_url = os.getenv("ARMORIQ_API_URL", "https://api.armoriq.ai")
        self.webhook_secret = os.getenv("ARMORIQ_WEBHOOK_SECRET", "")
        self.timeout = 5  # seconds
        self.max_retries = 2
        self.cache = {}  # Simple in-memory cache for policies
        self.cache_ttl = 300  # 5 minutes
        
        if not self.api_key:
            logger.warning("ARMORIQ_API_KEY not set - ArmorIQ checks will fail safe (deny)")
    
    def _make_request(
        self,
        method: str,
        endpoint: str,
        data: Optional[Dict] = None,
        retry_count: int = 0
    ) -> Optional[Dict]:
        """
        Make authenticated request to ArmorIQ API with retry logic.
        On failure, returns None (fail-safe: deny by default).
        """
        url = f"{self.api_url}{endpoint}"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        
        try:
            if method == "POST":
                response = requests.post(url, json=data, headers=headers, timeout=self.timeout)
            elif method == "GET":
                response = requests.get(url, headers=headers, timeout=self.timeout)
            else:
                logger.error(f"Unsupported HTTP method: {method}")
                return None
            
            response.raise_for_status()
            return response.json()
        
        except requests.exceptions.ConnectionError as e:
            logger.warning(f"ArmorIQ connection error: {e}")
            if retry_count < self.max_retries:
                time.sleep(0.5 * (retry_count + 1))  # exponential backoff
                return self._make_request(method, endpoint, data, retry_count + 1)
            return None
        
        except requests.exceptions.Timeout:
            logger.warning(f"ArmorIQ request timeout at {url}")
            if retry_count < self.max_retries:
                return self._make_request(method, endpoint, data, retry_count + 1)
            return None
        
        except requests.exceptions.RequestException as e:
            logger.error(f"ArmorIQ request failed: {e}")
            return None
        
        except Exception as e:
            logger.error(f"Unexpected error in ArmorIQ request: {e}")
            return None
    
    def verify_agent_identity(
        self,
        agent_id: str,
        token: str,
    ) -> AgentVerificationResponse:
        """
        Verify agent identity via ArmorIQ cross-check.
        
        Returns verification response, or fail-safe (not_verified) on error.
        """
        req = AgentVerificationRequest(
            agent_id=agent_id,
            token=token,
            timestamp=time.time()
        )
        
        response_data = self._make_request(
            "POST",
            "/api/v1/agents/verify",
            req.model_dump()
        )
        
        if not response_data:
            # Fail-safe: deny verification on API failure
            logger.warning(f"Agent {agent_id} identity verification failed - failing safe")
            return AgentVerificationResponse(
                agent_id=agent_id,
                verified=False,
                verification_method="failed",
                identity_confidence=0.0,
                violations=[
                    ArmorIQViolation(
                        policy_id="system",
                        policy_name="ArmorIQ Unavailable",
                        violation_type="service_unavailable",
                        severity=SeverityLevel.CRITICAL,
                        description="ArmorIQ service unavailable - failing safe",
                        timestamp=time.time()
                    )
                ],
                timestamp=time.time()
            )
        
        return AgentVerificationResponse(**response_data)
    
    def check_policy_compliance(
        self,
        req: PolicyCheckRequest,
    ) -> PolicyCheckResponse:
        """
        Check if action complies with ArmorIQ policies.
        
        Returns compliance verdict, or fail-safe (deny) on error.
        """
        response_data = self._make_request(
            "POST",
            "/api/v1/policies/check",
            req.model_dump()
        )
        
        if not response_data:
            # Fail-safe: deny on API failure
            logger.warning(f"Policy check failed for agent {req.agent_id} - failing safe")
            return PolicyCheckResponse(
                allowed=False,
                compliance_status=ComplianceStatus.UNKNOWN,
                violations=[
                    ArmorIQViolation(
                        policy_id="system",
                        policy_name="ArmorIQ Unavailable",
                        violation_type="service_unavailable",
                        severity=SeverityLevel.CRITICAL,
                        description="ArmorIQ service unavailable - failing safe",
                        timestamp=time.time()
                    )
                ],
                threat_score=100.0,  # Maximum threat when service unavailable
                timestamp=time.time()
            )
        
        return PolicyCheckResponse(**response_data)
    
    def register_agent(
        self,
        identity: AgentIdentity,
    ) -> bool:
        """
        Register agent with ArmorIQ for identity management.
        
        Returns True on success, False on failure.
        """
        response_data = self._make_request(
            "POST",
            "/api/v1/agents/register",
            identity.model_dump()
        )
        
        if not response_data:
            logger.error(f"Failed to register agent {identity.agent_id} with ArmorIQ")
            return False
        
        success = response_data.get("success", False)
        if success:
            logger.info(f"Agent {identity.agent_id} registered with ArmorIQ")
        
        return success
    
    def update_agent_scope(
        self,
        agent_id: str,
        capabilities: List[str],
        ticker_scope: List[str],
        max_qty: int,
    ) -> bool:
        """
        Update agent's scope and capabilities in ArmorIQ.
        
        Returns True on success, False on failure.
        """
        payload = {
            "agent_id": agent_id,
            "capabilities": capabilities,
            "ticker_scope": ticker_scope,
            "max_qty": max_qty,
            "updated_at": time.time()
        }
        
        response_data = self._make_request(
            "POST",
            f"/api/v1/agents/{agent_id}/scope",
            payload
        )
        
        if not response_data:
            logger.error(f"Failed to update scope for agent {agent_id}")
            return False
        
        return response_data.get("success", False)
    
    def revoke_agent(self, agent_id: str) -> bool:
        """
        Revoke/disable agent in ArmorIQ.
        
        Returns True on success, False on failure.
        """
        response_data = self._make_request(
            "POST",
            f"/api/v1/agents/{agent_id}/revoke",
            {"revoked_at": time.time()}
        )
        
        if not response_data:
            logger.error(f"Failed to revoke agent {agent_id}")
            return False
        
        return response_data.get("success", False)
    
    def get_threat_intelligence(self, agent_id: str) -> ThreatIntelligence:
        """
        Get current threat intelligence for an agent.
        
        Returns threat intel, or fail-safe (unknown) on error.
        """
        response_data = self._make_request(
            "GET",
            f"/api/v1/threat-intel/{agent_id}"
        )
        
        if not response_data:
            logger.warning(f"Failed to fetch threat intel for {agent_id}")
            return ThreatIntelligence(
                agent_id=agent_id,
                threat_score=50.0,  # Unknown threat level
                risk_level=SeverityLevel.MEDIUM,
                threat_indicators=[],
                last_updated=time.time(),
            )
        
        return ThreatIntelligence(**response_data)
    
    def get_policies(self) -> List[PolicyDefinition]:
        """
        Fetch all active policies from ArmorIQ.
        
        Uses simple in-memory cache to avoid excessive API calls.
        Returns empty list on failure.
        """
        # Check cache
        cache_key = "policies_list"
        if cache_key in self.cache:
            cached_data, cached_time = self.cache[cache_key]
            if time.time() - cached_time < self.cache_ttl:
                return cached_data
        
        response_data = self._make_request("GET", "/api/v1/policies")
        
        if not response_data:
            logger.warning("Failed to fetch policies from ArmorIQ")
            return []
        
        policies = [PolicyDefinition(**p) for p in response_data.get("policies", [])]
        
        # Cache result
        self.cache[cache_key] = (policies, time.time())
        
        return policies
    
    def sync_policies(self) -> bool:
        """
        Sync policies from ArmorIQ (typically called during startup or on schedule).
        
        Returns True if sync successful, False on failure.
        """
        policies = self.get_policies()
        if not policies:
            logger.error("Failed to sync policies from ArmorIQ")
            return False
        
        logger.info(f"Synced {len(policies)} policies from ArmorIQ")
        return True
    
    def generate_compliance_report(
        self,
        start_time: float,
        end_time: float,
        agent_id: Optional[str] = None,
    ) -> Dict:
        """
        Generate compliance report from ArmorIQ.
        
        Returns report data, or empty dict on failure.
        """
        payload = {
            "start_time": start_time,
            "end_time": end_time,
        }
        if agent_id:
            payload["agent_id"] = agent_id
        
        response_data = self._make_request(
            "POST",
            "/api/v1/reports/compliance",
            payload
        )
        
        if not response_data:
            logger.warning("Failed to generate compliance report from ArmorIQ")
            return {}
        
        return response_data
    
    def health_check(self) -> bool:
        """
        Check if ArmorIQ API is available.
        
        Returns True if healthy, False otherwise.
        """
        response_data = self._make_request("GET", "/api/v1/health")
        return response_data is not None and response_data.get("status") == "ok"
