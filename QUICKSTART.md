# Quick Start - ArmorIQ Integration

Get the ArmorIQ integration running in 5 minutes.

## Prerequisites

- Python 3.8+
- OPA (Open Policy Agent)
- ArmorIQ API key from https://armoriq.ai

## 1. Set Environment Variables (1 min)

```bash
export ARMORIQ_API_KEY="your-armoriq-api-key-here"
export ARMORIQ_API_URL="https://api.armoriq.ai"
export JWT_SECRET="your-secret-key-min-32-characters-long"
export ALPACA_API_KEY="your-alpaca-paper-key"
export ALPACA_SECRET_KEY="your-alpaca-paper-secret"
```

Or create `.env`:
```bash
cp .env.example .env
# Edit .env with your credentials
```

## 2. Run Database Initialization (1 min)

From the project root:

```bash
python backend/init_db.py
```

This will initialize all required tables. Expected output:
```
============================================================
ArmorIQ Intentional.ai Database Initialization
============================================================

Database path: audit.db

[1/2] Initializing audit log table...
✓ Audit log initialized

[2/2] Running ArmorIQ integration migration...
[Migration] Creating new audit_log table with ArmorIQ fields...
[Migration] ✓ Audit log migration complete
[Migration] ✓ All tables created successfully
[Migration] ✓ ArmorIQ integration migration complete!

============================================================
✓ Database initialization complete!
============================================================
```

## 3. Start Services (2 min)

**Terminal 1: OPA**
```bash
docker run -p 8181:8181 openpolicyagent/opa:latest run --server
```

**Terminal 2: Backend Gateway**
```bash
cd backend
pip install -r requirements.txt
python -m gateway.main
```

Expected: `INFO:     Uvicorn running on http://0.0.0.0:8000`

**Terminal 3: Frontend**
```bash
cd frontend
python -m http.server 8080
```

Expected: `Serving HTTP on 0.0.0.0 port 8080`

## 4. Access Dashboard (instant)

Open http://localhost:8080 in your browser

You should see:
- CapabilityGuard interface with ArmorClaw branding
- **NEW**: Compliance Dashboard showing:
  - OPA Pass Rate: 0%
  - ArmorIQ Compliance: 0%
  - Agent Identity Verified: 0%
  - Real-time Alerts (empty)
  - Agent Registry (loading)

## 5. Test the Integration (1 min)

In the dashboard:

1. **Mandate Input**: Copy this example mandate:
   ```
   Invest $50,000 across AAPL, GOOGL. Buy AAPL with limit $30k, 
   GOOGL with limit $20k. Research first then execute.
   ```

2. **Click**: "▶ Run Full Demo"

3. **Watch**: 
   - Pipeline animates through Orchestrator → Agent → ArmorClaw
   - Verdict Panel shows ALLOWED/BLOCKED
   - Audit Log populates with entries
   - **NEW**: Compliance Dashboard updates with:
     - Pass rates update
     - Threat score appears
     - Alerts panel shows any violations
     - Agent registry shows registered agent

## What's New: ArmorIQ Integration

### Dashboard Additions

1. **Compliance Metrics** (6 cards):
   - OPA Pass Rate
   - ArmorIQ Compliance
   - Both Passed
   - Identity Verified Rate
   - Avg Threat Score
   - Active Violations

2. **Real-time Alerts**:
   - Color-coded by severity
   - Shows policy violations
   - Auto-scrolling feed

3. **Agent Registry**:
   - Lists registered agents
   - Shows verification status
   - Displays capabilities

### Behind the Scenes

The gateway now:
- Verifies agent identity via ArmorIQ
- Checks actions against ArmorIQ policies
- Evaluates threat intelligence
- Logs compliance data to audit trail
- Requires BOTH OPA and ArmorIQ approval

## API Testing

### Health Check
```bash
curl http://localhost:8000/health
curl http://localhost:8000/armoriq/health
```

### Get Compliance Stats
```bash
curl http://localhost:8000/compliance/stats
```

Example response:
```json
{
  "total_actions": 5,
  "opa_passed": 5,
  "armoriq_passed": 5,
  "both_passed": 5,
  "agent_identity_verified": 5,
  "avg_threat_score": 18.5,
  "max_threat_score": 45.0,
  "opa_pass_rate": 100.0,
  "armoriq_pass_rate": 100.0,
  "compliance_rate": 100.0
}
```

### Get Audit Logs
```bash
curl http://localhost:8000/logs?limit=5
```

### Check Agent Status
```bash
curl http://localhost:8000/armoriq/threat-intel?agent_id=research-agent
```

## Troubleshooting

### ArmorIQ Key Not Set
```
Error: ARMORIQ_API_KEY not set
```
→ Set environment variable: `export ARMORIQ_API_KEY="..."`

### Database Migration Fails
```
Error: sqlite3.OperationalError
```
→ Check permissions: `ls -la audit.db`
→ Re-run migration: `python backend/migrations/001_armoriq_integration.py`

### Dashboard Metrics Show 0%
→ Normal! Trigger "Run Full Demo" to generate actions
→ Metrics update as actions flow through gateway

### OPA Unreachable
```
Error: opa_unreachable
```
→ Start OPA: `docker run -p 8181:8181 openpolicyagent/opa:latest run --server`

## Next Steps

1. **Explore Compliance Reports**:
   ```bash
   curl http://localhost:8000/compliance/report
   ```

2. **Register Custom Agents**:
   - See `backend/agents/identity.py`
   - Implements `register_agent()`, `update_agent_scope()`, etc.

3. **Configure ArmorIQ Policies**:
   - See `backend/policies/manager.py`
   - Implements `sync_armoriq_policies()`, `enable_policy()`, etc.

4. **Run Integration Tests**:
   ```bash
   cd backend
   python -m pytest tests/test_armoriq_integration.py -v
   ```

## Full Documentation

For detailed info, see:
- **ARMORIQ_INTEGRATION.md** - Complete setup & API reference
- **IMPLEMENTATION_SUMMARY.md** - Architecture & components
- **Code comments** - Inline documentation

## Key Files

| File | Purpose |
|------|---------|
| `backend/armoriq/client.py` | ArmorIQ API client |
| `backend/armoriq/models.py` | Data models |
| `backend/gateway/main.py` | Enhanced gateway with ArmorIQ |
| `backend/agents/identity.py` | Agent identity management |
| `backend/policies/manager.py` | Policy management |
| `backend/audit/db.py` | Enhanced audit log |
| `frontend/index.html` | Dashboard with compliance UI |
| `backend/migrations/001_armoriq_integration.py` | Database migration |
| `backend/tests/test_armoriq_integration.py` | Integration tests |

## Getting Help

1. Check logs: `curl http://localhost:8001/logs`
2. Read ARMORIQ_INTEGRATION.md troubleshooting section
3. Verify ArmorIQ API key is valid
4. Run tests: `pytest backend/tests/ -v`
5. Check database: `sqlite3 audit.db ".schema"`

## What's Working

✓ Agent identity verification via ArmorIQ
✓ Policy compliance checking
✓ Real-time threat intelligence
✓ Comprehensive audit logging
✓ Live compliance dashboard
✓ Fail-safe design (deny on errors)
✓ Full integration test coverage

Enjoy the enhanced security!
