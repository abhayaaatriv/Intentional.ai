# Intentional.ai — CapabilityGuard

> **Proactive Intent Enforcement for Autonomous Financial Agents**

Intentional.ai is a financial AI agent platform built on the ArmorClaw enforcement framework. Instead of hoping autonomous agents behave, every action is cryptographically scoped and validated against declarative policies before reaching any real-world API.

---

## The Problem We Solve

Traditional AI agent systems give agents a broad API key and monitor logs after the fact. **That is reactive.** By the time you see the log, the trade is placed, the data is leaked, the damage is done.

Intentional.ai shifts to **proactive intent enforcement**: every agent action is treated as a request for permission, validated against a signed mandate before execution.

---

## Architecture: Three Layers

<img width="561" height="567" alt="Screenshot 2026-04-08 at 11 15 23 PM" src="https://github.com/user-attachments/assets/3da03e1e-aabe-4570-95ab-24c83970a153" />


---

## 🆕 ArmorIQ Integration (NEW)

This version includes **ArmorClaw Intent Assurance** powered by ArmorIQ. Every agent action is now validated against:
1. **Agent Identity Verification** - Confirm agent is who it claims to be
2. **OPA Policies** - Traditional declarative policy checks
3. **ArmorIQ Policies** - ML-powered intent assurance with threat intelligence
4. **Threat Scoring** - Real-time risk evaluation

See [QUICKSTART.md](QUICKSTART.md) for 5-minute setup or [SETUP_GUIDE.md](SETUP_GUIDE.md) for detailed instructions.

---

## Quick Start

### Prerequisites
- Python 3.8+
- Docker (for OPA)
- Alpaca Markets account (free paper trading)
- OpenAI API key (for agent reasoning)
- ArmorIQ API key (from https://armoriq.ai)

### 1. Clone and configure

```bash
git clone <repo>
cd intentional
cp .env.example .env
```

### 2. Install dependencies and initialize database

```bash
pip install -r backend/requirements.txt
python backend/init_db.py
```

### 3. Fill in `.env`

```bash
cp .env.example .env

# Generate a secret
JWT_SECRET=$(python -c "import secrets; print(secrets.token_hex(32))")

OPENAI_API_KEY=sk-...                      # platform.openai.com
ALPACA_API_KEY=...                         # alpaca.markets → Paper Trading → API Keys
ALPACA_SECRET_KEY=...
ARMORIQ_API_KEY=...                        # armoriq.ai (NEW)
OPA_URL=http://localhost:8181/v1/data/financial
AUDIT_DB_PATH=audit.db
```

### 4. Start Services

**Terminal 1: OPA**
```bash
docker run -p 8181:8181 openpolicyagent/opa:latest run --server
```

**Terminal 2: Gateway**
```bash
cd backend
python -m gateway.main
```

**Terminal 3: Frontend**
```bash
cd frontend
python -m http.server 8080
```

| Service | URL |
|---------|-----|
| Frontend Dashboard | http://localhost:8080 |
| ArmorClaw Gateway | http://localhost:8000 |
| OPA Policy Engine | http://localhost:8181 |

### 5. Test

```bash
curl http://localhost:8000/health
curl http://localhost:8000/armoriq/health
curl http://localhost:8000/compliance/stats
```

Open http://localhost:8080 and try "Run Full Demo" button.
<img width="564" height="145" alt="Screenshot 2026-04-08 at 11 15 42 PM" src="https://github.com/user-attachments/assets/c0cdb767-3c18-496f-9913-36e6db1a5889" />

---

## API Reference

### Gateway (ArmorClaw) — :8000

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/validate` | Validate action (JWT + OPA + ArmorIQ) |
| `GET` | `/logs` | Recent audit log entries |
| `GET` | `/stats` | Allowed / blocked counts |
| `GET` | `/compliance/stats` | **(NEW)** Compliance metrics |
| `GET` | `/compliance/report` | **(NEW)** Detailed compliance report |
| `GET` | `/armoriq/health` | **(NEW)** ArmorIQ API status |
| `POST` | `/armoriq/verify-agent` | **(NEW)** Verify agent identity |
| `POST` | `/armoriq/check-compliance` | **(NEW)** Check ArmorIQ policies |
| `GET` | `/armoriq/threat-intel` | **(NEW)** Get threat intelligence |
| `GET` | `/health` | Health check |
| `WS` | `/ws/audit` | Live audit feed |

**Example request:**
```json
POST /validate
{
  "agent_id": "execution-agent-01",
  "token": "<signed-jwt>",
  "action": "BUY",
  "ticker": "AAPL",
  "qty": 5,
  "destination": "internal"
}
```

**Example response (BLOCKED):**
```json
{
  "allowed": false,
  "violations": ["ticker_out_of_scope"],
  "agent_id": "execution-agent-01",
  "action": "BUY",
  "ticker": "MSFT",
  "reason": "'MSFT' not in ticker_scope ['AAPL']",
  "opa_verdict": false,
  "armoriq_verdict": true,
  "agent_identity_verified": true,
  "threat_score": 25.5,
  "compliance_status": "non_compliant"
}
```

### Orchestrator — :8001

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/parse-intent` | LLM → IntentGraph JSON |
| `POST` | `/mint-tokens` | IntentGraph → 3 JWTs |
| `POST` | `/run-mandate` | Parse + mint in one call |

---

## OPA Policy Rules

Located in `backend/policies/financial_policy.rego`:

```rego
package financial
import rego.v1

default allow := false

allow if {
    action_permitted
    ticker_allowed
    qty_within_limit
    destination_allowed
}

# Violation reasons surfaced in audit log
violation contains "action_not_permitted"   if { not action_permitted }
violation contains "ticker_out_of_scope"    if { not ticker_allowed }
violation contains "qty_exceeded"           if { not qty_within_limit }
violation contains "unauthorized_destination" if {
    input.action == "SEND_DATA"
    input.destination != input.token.destination_scope
}
```

---

## JWT Token Structure

Each agent receives a scoped JWT minted by the Orchestrator:

```json
{
  "agent_id": "execution-agent-01",
  "allowed_actions": ["BUY"],
  "ticker_scope": ["AAPL"],
  "max_qty": 5,
  "destination_scope": "internal",
  "exp": 1712600000,
  "iat": 1712599700
}
```

Tokens expire in **300 seconds**. The Gateway validates signature, expiry, and scope on every single request.

---

## Demo Flow

```
Mandate: "Research AAPL and buy 5 shares if PE ratio is under 25"

Orchestrator mints 3 tokens:
  research-agent-01   → [READ], AAPL, max_qty: 0
  execution-agent-01  → [BUY],  AAPL, max_qty: 5
  report-agent-01     → [LOG],  *, destination: internal

ResearchAgent  READ AAPL         → ✅ ALLOWED
ExecutionAgent BUY AAPL ×5      → ✅ ALLOWED  (Alpaca paper order placed)
ExecutionAgent SELL AAPL ×5     → ❌ BLOCKED  (action_not_permitted)
ReportAgent    POST external URL → ❌ BLOCKED  (unauthorized_destination)
ExecutionAgent BUY MSFT ×2      → ❌ BLOCKED  (ticker_out_of_scope)
ExecutionAgent BUY AAPL ×50     → ❌ BLOCKED  (qty_exceeded)
```

> "The Execution Agent's JWT token literally cannot authorize a SELL — even if the agent code tried to call sell(), ArmorClaw's OPA policy rejects it before the request reaches Alpaca. The security is architectural, not bolted on."

---

## Tech Stack

| Component | Technology | Why |
|-----------|-----------|-----|
| Gateway | FastAPI + Uvicorn | Async WebSocket, sub-ms routing |
| Policy Engine | OPA + Rego v1 | Declarative, stateless, composable |
| Token Auth | PyJWT HS256 | Signed, scoped, time-limited |
| Intent Parser | GPT-4o-mini | NL → structured JSON, low cost |
| Paper Trading | Alpaca Markets API | Free paper mode, REST + WebSocket |
| Market Data | yfinance + Alpaca Data | PE ratios, real-time quotes |
| Audit Store | SQLite | Zero infra, queryable, immutable |
| Live Feed | FastAPI WebSocket | Streams verdicts to dashboard |
| Containers | Docker Compose | One-command spin-up |
| Agent Framework | OpenClaw | Mandatory per competition rules |

---
<img width="326" height="517" alt="Screenshot 2026-04-08 at 11 16 12 PM" src="https://github.com/user-attachments/assets/aaaf9e6e-ee77-4148-8cef-dcb89c4b2dd5" />

## File Structure

```
intentional/
├── backend/
│   ├── gateway/main.py          ← ArmorClaw enforcement gateway
│   ├── orchestrator/main.py     ← Intent parser + token minter
│   ├── agents/
│   │   ├── research/agent.py    ← READ-only market data agent
│   │   ├── execution/agent.py   ← BUY/SELL execution agent
│   │   └── report/agent.py      ← LOG-only reporting agent
│   ├── policies/
│   │   └── financial_policy.rego ← OPA Rego rules
│   ├── shared/tokens.py         ← JWT mint / decode
│   ├── audit/db.py              ← SQLite audit log
│   └── requirements.txt
├── frontend/
│   └── index.html               ← Dashboard (connects via WebSocket)
├── docker-compose.yml
├── demo.py                      ← End-to-end judge demo script
├── .env.example
└── README.md
```
<img width="284" height="131" alt="Screenshot 2026-04-08 at 11 16 27 PM" src="https://github.com/user-attachments/assets/6c8f2567-14d8-4765-acee-e2f22d143d91" />

---

## Documentation

| Document | Purpose |
|----------|---------|
| **[QUICKSTART.md](QUICKSTART.md)** | 5-minute setup guide with examples |
| **[SETUP_GUIDE.md](SETUP_GUIDE.md)** | Complete step-by-step installation |
| **[ARMORIQ_INTEGRATION.md](ARMORIQ_INTEGRATION.md)** | ArmorIQ API details and troubleshooting |
| **[IMPLEMENTATION_SUMMARY.md](IMPLEMENTATION_SUMMARY.md)** | Architecture and component overview |
| **[DELIVERY_CHECKLIST.md](DELIVERY_CHECKLIST.md)** | Verification checklist |

### Key Features (NEW with ArmorIQ)

✅ **ArmorClaw Intent Assurance** - Agent identity verification
✅ **Dual-Policy Enforcement** - OPA + ArmorIQ must both approve
✅ **Real-time Threat Intelligence** - ML-powered risk scoring
✅ **Live Compliance Dashboard** - Monitor metrics and alerts
✅ **Comprehensive Audit Trail** - All decisions logged with context
✅ **Agent Identity Management** - Registration, verification, revocation
✅ **Policy Versioning** - Version control with rollback support
✅ **Fail-Safe Design** - Deny by default if service unavailable

---

## Core Philosophy

> This approach replaces **"hope"** with **hard-coded rules of engagement**.
>
> Autonomous agents get the speed and scale they need. The ArmorClaw Gateway ensures they stay within financial and ethical guardrails — not by restricting their thinking, but by validating their actions.
>
> **Mandate → Intent Graph → Scoped JWT → ArmorClaw Gate → OPA Verdict → Execution or Block**

---

*Built for the APOGEE, BITS PILANI, ArmorIQ Hackathon 2026 &mdash; Intentional.ai*
