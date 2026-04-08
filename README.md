# CapabilityGuard — Mandate-Scoped Agent Delegation

> Financial AI agent with ArmorClaw enforcement: every sub-agent action is validated against a cryptographically-scoped JWT before reaching Alpaca.

---

## Architecture

```
User Mandate
    │
    ▼
Orchestrator (FastAPI :8001)
    │  LLM → IntentGraph → mint 3 JWT tokens
    ▼
┌───────────────────────────────────────────────────────┐
│  ArmorClaw Gateway (FastAPI :8000)                    │
│  POST /validate → OPA Rego → audit log → verdict      │
└───────────────────────────────────────────────────────┘
    │                       │
    ▼                       ▼
ResearchAgent          ExecutionAgent          ReportAgent
[READ only]            [BUY/SELL bounded]      [LOG internal]
[AAPL scoped]          [AAPL scoped, max:10]   [any ticker]
    │                       │
    ▼                       ▼
 yfinance               Alpaca Paper API
```

---

## Quick Start

### 1. Clone & configure

```bash
git clone <repo>
cd capabilityguard
cp .env.example .env
# Edit .env — fill in API keys
```

### 2. Replace these API keys in `.env`

| Key | Where to get it |
|-----|-----------------|
| `OPENAI_API_KEY` | platform.openai.com |
| `ALPACA_API_KEY` | alpaca.markets (free paper account) |
| `ALPACA_SECRET_KEY` | alpaca.markets |
| `JWT_SECRET` | `python -c "import secrets; print(secrets.token_hex(32))"` |

### 3. Docker Compose (recommended)

```bash
docker-compose up
# Frontend: http://localhost:3000
# Gateway:  http://localhost:8000
# OPA:      http://localhost:8181
```

### 4. Manual (dev)

```bash
# Terminal 1 — OPA
brew install opa  # or: curl -L https://openpolicyagent.org/downloads/latest/opa_linux_amd64 -o opa && chmod +x opa
opa run --server backend/policies/

# Terminal 2 — Gateway (ArmorClaw)
cd backend
pip install -r requirements.txt
uvicorn gateway.main:app --port 8000 --reload

# Terminal 3 — Orchestrator
uvicorn orchestrator.main:app --port 8001 --reload

# Terminal 4 — Frontend
cd frontend && python -m http.server 3000
```

### 5. Run the demo script

```bash
python demo.py
```

---

## API Reference

### Gateway (ArmorClaw) — :8000

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/validate` | Validate agent action against JWT + OPA |
| GET | `/logs` | Recent audit log entries |
| GET | `/stats` | Allowed/blocked counts |
| GET | `/health` | Health check |
| WS | `/ws/audit` | Live audit feed (dashboard uses this) |

### Orchestrator — :8001

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/parse-intent` | LLM → IntentGraph JSON |
| POST | `/mint-tokens` | IntentGraph → 3 JWTs |
| POST | `/run-mandate` | parse + mint in one call |

---

## Demo Flow (judges see this)

```
Mandate: "Research AAPL and buy 5 shares if PE ratio is under 25"

Orchestrator
  ├── mints research-agent token  [READ only, AAPL]
  ├── mints execution-agent token [BUY only, AAPL, max:5]
  └── mints report-agent token   [LOG only, internal]

ResearchAgent  READ AAPL         → ✅ ALLOWED
ExecutionAgent BUY AAPL ×5      → ✅ ALLOWED
ExecutionAgent SELL AAPL ×5     → ❌ BLOCKED (action_not_permitted)
ReportAgent    POST external URL → ❌ BLOCKED (unauthorized_destination)
ExecutionAgent BUY MSFT ×2      → ❌ BLOCKED (ticker_out_of_scope)
ExecutionAgent BUY AAPL ×50     → ❌ BLOCKED (qty_exceeded)
```

**The winning sentence for judges:** "The Research Agent's token *literally cannot execute a trade* even if the agent code tried to — ArmorClaw's OPA policy rejects the action before it reaches Alpaca. The security is architectural, not bolted on."

---

## File Structure

```
capabilityguard/
├── backend/
│   ├── gateway/main.py       ← ArmorClaw enforcement gateway
│   ├── orchestrator/main.py  ← Intent parser + token minter
│   ├── agents/
│   │   ├── research/agent.py
│   │   ├── execution/agent.py + alpaca_client.py
│   │   └── report/agent.py
│   ├── policies/financial_policy.rego  ← OPA Rego rules
│   ├── audit/db.py           ← SQLite audit log
│   ├── shared/tokens.py      ← JWT mint/decode
│   ├── requirements.txt
│   └── Dockerfile
├── frontend/
│   └── index.html            ← Dashboard (connects to real backend via WS)
├── docker-compose.yml
├── demo.py                   ← Judge demo script
└── .env.example
```
