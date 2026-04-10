"""
CapabilityGuard — ArmorClaw Enforcement Gateway
FastAPI server that sits between all agents and Alpaca/external APIs.

Every agent action must pass through POST /validate.
OPA at localhost:8181 evaluates Rego policy.
All decisions are written to SQLite audit log.

────────────────────────────────────────────────
REPLACE THESE:
  JWT_SECRET    → in .env (min 32 chars, random)
  OPA_URL       → http://localhost:8181/v1/data/financial  (default)
  AUDIT_DB_PATH → path to audit.db (default: ./audit.db)
────────────────────────────────────────────────
"""

from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import requests
import jwt
import time
import json
import os
import sys
import logging

sys.path.append(os.path.join(os.path.dirname(__file__), ".."))
from shared.tokens import decode_token, JWT_SECRET
from audit.db import init_db, log_action, get_recent_logs, get_stats, get_compliance_stats, get_compliance_report
from armoriq.client import ArmorIQClient
from armoriq.models import PolicyCheckRequest, ComplianceStatus

logger = logging.getLogger(__name__)

# ── CONFIG ───────────────────────────────────────────────────────────────────
OPA_URL = os.getenv("OPA_URL", "http://localhost:8181/v1/data/financial")
ALPACA_BASE = os.getenv("ALPACA_BASE_URL", "https://paper-api.alpaca.markets")
ALPACA_KEY = os.getenv("ALPACA_API_KEY", "REPLACE_ME")
ALPACA_SECRET = os.getenv("ALPACA_SECRET_KEY", "REPLACE_ME")

# Initialize ArmorIQ client
armoriq_client = ArmorIQClient()

app = FastAPI(title="CapabilityGuard ArmorClaw Gateway", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # tighten in production
    allow_methods=["*"],
    allow_headers=["*"],
)

# WebSocket connections for live dashboard feed
active_connections: list[WebSocket] = []

init_db()


# ── MODELS ───────────────────────────────────────────────────────────────────
class ActionRequest(BaseModel):
    agent_id: str
    token: str
    action: str          # READ | BUY | SELL | LOG | SEND_DATA
    ticker: str = ""
    qty: int = 0
    destination: str = "internal"
    metadata: dict = {}


class ValidateResponse(BaseModel):
    allowed: bool
    violations: list[str]
    agent_id: str
    action: str
    ticker: str
    reason: str
    opa_verdict: bool = False
    armoriq_verdict: bool = False
    agent_identity_verified: bool = False
    threat_score: float = 0.0
    compliance_status: str = "unknown"


# ── WEBSOCKET BROADCAST ───────────────────────────────────────────────────────
async def broadcast(data: dict):
    dead = []
    for ws in active_connections:
        try:
            await ws.send_text(json.dumps(data))
        except Exception:
            dead.append(ws)
    for ws in dead:
        active_connections.remove(ws)


@app.websocket("/ws/audit")
async def audit_ws(websocket: WebSocket):
    await websocket.accept()
    active_connections.append(websocket)
    # Send last 20 entries on connect
    logs = get_recent_logs(20)
    await websocket.send_text(json.dumps({"type": "history", "entries": logs}))
    try:
        while True:
            await websocket.receive_text()  # keep alive
    except WebSocketDisconnect:
        active_connections.remove(websocket)


# ── CORE ENDPOINT ────────────────────────────────────────────────────────────
@app.post("/validate", response_model=ValidateResponse)
async def validate_action(req: ActionRequest):
    """
    The ArmorClaw gate with ArmorIQ Intent Assurance. Called by EVERY agent before performing any action.

    Flow:
      1. Decode + verify JWT
      2. [NEW] Verify agent identity via ArmorIQ
      3. Send action + token claims to OPA
      4. [NEW] Check action against ArmorIQ policies
      5. [NEW] Get threat intelligence
      6. Write to audit log with ArmorIQ data
      7. Broadcast over WebSocket to live dashboard
      8. Return verdict (both OPA and ArmorIQ must pass)
    """
    opa_verdict = False
    armoriq_verdict = False
    agent_identity_verified = False
    threat_score = 0.0
    compliance_status = ComplianceStatus.UNKNOWN
    armoriq_violations = []
    armoriq_policy_id = ""

    # ── STEP 1: decode JWT ──────────────────────────────────────────────────
    try:
        token_data = decode_token(req.token)
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired")
    except jwt.InvalidTokenError as e:
        raise HTTPException(status_code=401, detail=f"Invalid token: {e}")

    # ── STEP 2: Verify agent identity via ArmorIQ ──────────────────────────
    identity_response = armoriq_client.verify_agent_identity(req.agent_id, req.token)
    agent_identity_verified = identity_response.verified
    if not agent_identity_verified:
        armoriq_violations.extend([
            {"policy": v.policy_name, "violation": v.violation_type, "severity": v.severity}
            for v in identity_response.violations
        ])

    # ── STEP 3: OPA evaluation ──────────────────────────────────────────────
    opa_input = {
        "input": {
            "action": req.action,
            "ticker": req.ticker,
            "qty": req.qty,
            "destination": req.destination,
            "token": token_data,
        }
    }
    opa_violations = []
    try:
        opa_resp = requests.post(OPA_URL, json=opa_input, timeout=3).json()
        opa_verdict = opa_resp.get("result", {}).get("allow", False)
        opa_violations = list(opa_resp.get("result", {}).get("violation", set()))
    except requests.RequestException:
        # OPA unreachable → fail closed (deny by default)
        opa_verdict = False
        opa_violations = ["opa_unreachable"]

    # ── STEP 4: Check action against ArmorIQ policies ──────────────────────
    policy_check_req = PolicyCheckRequest(
        agent_id=req.agent_id,
        action=req.action,
        ticker=req.ticker,
        qty=req.qty,
        destination=req.destination,
        token_data=token_data,
        metadata=req.metadata,
    )
    policy_response = armoriq_client.check_policy_compliance(policy_check_req)
    armoriq_verdict = policy_response.allowed
    compliance_status = policy_response.compliance_status
    threat_score = policy_response.threat_score
    armoriq_violations = [
        {"policy": v.policy_name, "violation": v.violation_type, "severity": v.severity}
        for v in policy_response.violations
    ]
    if policy_response.violations:
        armoriq_policy_id = policy_response.violations[0].policy_id if policy_response.violations else ""

    # ── STEP 5: Get threat intelligence ──────────────────────────────────
    threat_intel = armoriq_client.get_threat_intelligence(req.agent_id)
    threat_score = max(threat_score, threat_intel.threat_score)  # Use highest threat score

    # ── STEP 6: Final verdict: BOTH OPA and ArmorIQ must pass ────────────
    allowed = opa_verdict and armoriq_verdict and agent_identity_verified
    all_violations = opa_violations + [v["violation"] for v in armoriq_violations]

    # ── STEP 7: audit log ───────────────────────────────────────────────────
    log_action(
        req.agent_id, req.action, req.ticker, req.qty, allowed, all_violations,
        opa_verdict=opa_verdict,
        armoriq_verdict=armoriq_verdict,
        armoriq_policy_id=armoriq_policy_id,
        armoriq_violations=armoriq_violations,
        agent_identity_verified=agent_identity_verified,
        threat_score=threat_score,
        compliance_status=compliance_status.value
    )

    # ── STEP 8: broadcast to dashboard ─────────────────────────────────────
    entry = {
        "type": "entry",
        "agent_id": req.agent_id,
        "action": req.action,
        "ticker": req.ticker,
        "qty": req.qty,
        "allowed": allowed,
        "violations": all_violations,
        "opa_verdict": opa_verdict,
        "armoriq_verdict": armoriq_verdict,
        "agent_identity_verified": agent_identity_verified,
        "threat_score": threat_score,
        "compliance_status": compliance_status.value,
        "timestamp": time.time(),
    }
    await broadcast(entry)

    # ── STEP 9: build human-readable reason ────────────────────────────────
    reasons = []
    if not agent_identity_verified:
        reasons.append("Agent identity verification failed via ArmorIQ")
    if not opa_verdict:
        reasons.extend([
            f"OPA: '{req.action}' not in token allowed_actions {token_data.get('allowed_actions')}",
            f"OPA: '{req.ticker}' not in ticker_scope {token_data.get('ticker_scope')}",
            f"OPA: qty {req.qty} exceeds token max_qty {token_data.get('max_qty')}",
            f"OPA: destination '{req.destination}' != token scope '{token_data.get('destination_scope')}'",
        ])
    if not armoriq_verdict:
        reasons.extend([f"ArmorIQ: {v['violation']}" for v in armoriq_violations])
    if threat_score > 50:
        reasons.append(f"High threat score: {threat_score}")
    
    reason = "; ".join(r for r in reasons if r) if reasons else f"Action '{req.action}' on {req.ticker} is compliant with all policies."

    return ValidateResponse(
        allowed=allowed,
        violations=all_violations,
        agent_id=req.agent_id,
        action=req.action,
        ticker=req.ticker,
        reason=reason,
        opa_verdict=opa_verdict,
        armoriq_verdict=armoriq_verdict,
        agent_identity_verified=agent_identity_verified,
        threat_score=threat_score,
        compliance_status=compliance_status.value,
    )


# ── AUDIT ENDPOINTS ───────────────────────────────────────────────────────────
@app.get("/logs")
def get_logs(limit: int = 100):
    return get_recent_logs(limit)


@app.get("/stats")
def get_stats_endpoint():
    return get_stats()


@app.get("/compliance/stats")
def get_compliance_stats_endpoint():
    """Get compliance statistics from ArmorIQ integration."""
    return get_compliance_stats()


@app.get("/compliance/report")
def get_compliance_report_endpoint(start_time: float, end_time: float, agent_id: str = None):
    """Generate compliance report for a time range."""
    return get_compliance_report(start_time, end_time, agent_id)


# ── ARMORIQ ENDPOINTS ────────────────────────────────────────────────────────
@app.post("/armoriq/verify-agent")
def verify_agent(agent_id: str, token: str):
    """Verify agent identity via ArmorIQ."""
    response = armoriq_client.verify_agent_identity(agent_id, token)
    return response.model_dump()


@app.post("/armoriq/check-compliance")
def check_compliance(req: PolicyCheckRequest):
    """Check action against ArmorIQ policies."""
    response = armoriq_client.check_policy_compliance(req)
    return response.model_dump()


@app.get("/armoriq/policies")
def get_armoriq_policies():
    """List all active ArmorIQ policies."""
    policies = armoriq_client.get_policies()
    return {"policies": [p.model_dump() for p in policies]}


@app.get("/armoriq/threat-intel")
def get_threat_intel(agent_id: str):
    """Get threat intelligence for an agent."""
    threat_intel = armoriq_client.get_threat_intelligence(agent_id)
    return threat_intel.model_dump()


@app.get("/armoriq/health")
def armoriq_health():
    """Check ArmorIQ API availability."""
    is_healthy = armoriq_client.health_check()
    return {
        "status": "ok" if is_healthy else "unavailable",
        "service": "armoriq",
        "timestamp": time.time()
    }


@app.get("/health")
def health():
    return {"status": "ok", "service": "armorclaw-gateway", "timestamp": time.time()}
