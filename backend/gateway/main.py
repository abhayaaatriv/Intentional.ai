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

sys.path.append(os.path.join(os.path.dirname(__file__), ".."))
from shared.tokens import decode_token, JWT_SECRET
from audit.db import init_db, log_action, get_recent_logs, get_stats

# ── CONFIG ───────────────────────────────────────────────────────────────────
OPA_URL = os.getenv("OPA_URL", "http://localhost:8181/v1/data/financial")
ALPACA_BASE = os.getenv("ALPACA_BASE_URL", "https://paper-api.alpaca.markets")
ALPACA_KEY = os.getenv("ALPACA_API_KEY", "REPLACE_ME")
ALPACA_SECRET = os.getenv("ALPACA_SECRET_KEY", "REPLACE_ME")

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
    The ArmorClaw gate. Called by EVERY agent before performing any action.

    Flow:
      1. Decode + verify JWT
      2. Send action + token claims to OPA
      3. OPA evaluates financial_policy.rego
      4. Write to audit log
      5. Broadcast over WebSocket to live dashboard
      6. Return verdict
    """
    # ── STEP 1: decode JWT ──────────────────────────────────────────────────
    try:
        token_data = decode_token(req.token)
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired")
    except jwt.InvalidTokenError as e:
        raise HTTPException(status_code=401, detail=f"Invalid token: {e}")

    # ── STEP 2: OPA evaluation ──────────────────────────────────────────────
    opa_input = {
        "input": {
            "action": req.action,
            "ticker": req.ticker,
            "qty": req.qty,
            "destination": req.destination,
            "token": token_data,
        }
    }
    try:
        opa_resp = requests.post(OPA_URL, json=opa_input, timeout=3).json()
        allowed = opa_resp.get("result", {}).get("allow", False)
        violations = list(opa_resp.get("result", {}).get("violation", set()))
    except requests.RequestException:
        # OPA unreachable → fail closed (deny by default)
        allowed = False
        violations = ["opa_unreachable"]

    # ── STEP 3: audit log ───────────────────────────────────────────────────
    log_action(req.agent_id, req.action, req.ticker, req.qty, allowed, violations)

    # ── STEP 4: broadcast to dashboard ─────────────────────────────────────
    entry = {
        "type": "entry",
        "agent_id": req.agent_id,
        "action": req.action,
        "ticker": req.ticker,
        "qty": req.qty,
        "allowed": allowed,
        "violations": violations,
        "timestamp": time.time(),
    }
    await broadcast(entry)

    # ── STEP 5: build human-readable reason ─────────────────────────────────
    if allowed:
        reason = f"Action '{req.action}' on {req.ticker} is within token scope."
    else:
        reasons = {
            "action_not_permitted": f"'{req.action}' not in token allowed_actions {token_data.get('allowed_actions')}",
            "ticker_out_of_scope": f"'{req.ticker}' not in ticker_scope {token_data.get('ticker_scope')}",
            "qty_exceeded": f"qty {req.qty} exceeds token max_qty {token_data.get('max_qty')}",
            "unauthorized_destination": f"destination '{req.destination}' != token scope '{token_data.get('destination_scope')}'",
            "opa_unreachable": "OPA policy server is unreachable — failing closed",
        }
        reason = "; ".join(reasons.get(v, v) for v in violations)

    return ValidateResponse(
        allowed=allowed,
        violations=violations,
        agent_id=req.agent_id,
        action=req.action,
        ticker=req.ticker,
        reason=reason,
    )


# ── AUDIT ENDPOINTS ───────────────────────────────────────────────────────────
@app.get("/logs")
def get_logs(limit: int = 100):
    return get_recent_logs(limit)


@app.get("/stats")
def get_stats_endpoint():
    return get_stats()


@app.get("/health")
def health():
    return {"status": "ok", "service": "armorclaw-gateway", "timestamp": time.time()}
