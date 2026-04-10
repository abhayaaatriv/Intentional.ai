"""
ArmorIQ Request/Response Models
Pydantic schemas for all ArmorIQ API interactions.
"""

from pydantic import BaseModel, Field
from typing import List, Dict, Optional
from enum import Enum
import json


class SeverityLevel(str, Enum):
    """Threat/violation severity levels."""
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFO = "info"


class ComplianceStatus(str, Enum):
    """Agent compliance status."""
    COMPLIANT = "compliant"
    NON_COMPLIANT = "non_compliant"
    PENDING = "pending"
    UNKNOWN = "unknown"


class ArmorIQViolation(BaseModel):
    """A single policy violation from ArmorIQ."""
    policy_id: str
    policy_name: str
    violation_type: str  # "intent_mismatch", "unauthorized_scope", "identity_unverified", etc.
    severity: SeverityLevel
    description: str
    timestamp: float


class AgentIdentity(BaseModel):
    """Agent identity registration and verification."""
    agent_id: str
    agent_name: str
    capabilities: List[str] = Field(default_factory=list)  # ["READ", "BUY", "SELL", etc.]
    allowed_actions: List[str] = Field(default_factory=list)
    ticker_scope: List[str] = Field(default_factory=list)
    max_qty: int = 0
    destination_scope: str = "internal"
    registered_at: Optional[float] = None
    verified: bool = False
    verification_timestamp: Optional[float] = None


class PolicyCheckRequest(BaseModel):
    """Request to check action against ArmorIQ policies."""
    agent_id: str
    action: str
    ticker: str = ""
    qty: int = 0
    destination: str = "internal"
    token_data: Dict = Field(default_factory=dict)
    metadata: Dict = Field(default_factory=dict)


class PolicyCheckResponse(BaseModel):
    """Response from ArmorIQ policy check."""
    allowed: bool
    compliance_status: ComplianceStatus
    violations: List[ArmorIQViolation] = Field(default_factory=list)
    threat_score: float = 0.0  # 0.0-100.0
    policies_checked: int = 0
    check_duration_ms: float = 0.0
    timestamp: float


class ThreatIntelligence(BaseModel):
    """Threat intelligence data from ArmorIQ."""
    agent_id: str
    threat_score: float  # 0.0-100.0
    risk_level: SeverityLevel
    threat_indicators: List[str] = Field(default_factory=list)
    last_updated: float
    confidence: float = 0.95  # 0.0-1.0


class AgentVerificationRequest(BaseModel):
    """Request to verify agent identity via ArmorIQ."""
    agent_id: str
    token: str
    timestamp: float = 0.0


class AgentVerificationResponse(BaseModel):
    """Response from agent identity verification."""
    agent_id: str
    verified: bool
    verification_method: str  # "jwt", "certificate", "cross_check", etc.
    identity_confidence: float = 0.95
    violations: List[ArmorIQViolation] = Field(default_factory=list)
    timestamp: float


class ComplianceReport(BaseModel):
    """Compliance report for audit trail."""
    report_id: str
    agent_id: str
    action: str
    ticker: str = ""
    qty: int = 0
    opa_verdict: bool
    armoriq_verdict: bool
    compliance_status: ComplianceStatus
    violations: List[ArmorIQViolation] = Field(default_factory=list)
    threat_score: float
    identity_verified: bool
    audit_trail_id: Optional[int] = None
    timestamp: float


class PolicyDefinition(BaseModel):
    """ArmorIQ Policy Definition."""
    policy_id: str
    policy_name: str
    description: str
    rules: List[Dict] = Field(default_factory=list)
    enabled: bool = True
    created_at: float
    updated_at: float
    version: str = "1.0"


class WebhookEvent(BaseModel):
    """Event from ArmorIQ webhook."""
    event_type: str  # "violation", "alert", "compliance_change", "threat_update"
    agent_id: Optional[str] = None
    policy_id: Optional[str] = None
    severity: SeverityLevel
    message: str
    timestamp: float
    metadata: Dict = Field(default_factory=dict)
