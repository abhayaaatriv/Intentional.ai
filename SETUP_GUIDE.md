# Complete Setup Guide - ArmorIQ Integration

This guide walks through setting up Intentional.ai with the ArmorIQ integration from scratch.

## Prerequisites

- Python 3.8+
- pip or conda
- Docker (optional, for OPA)
- Git (for cloning the repo)
- Valid ArmorIQ API key

## Directory Structure

```
intentional.ai/
├── backend/
│   ├── armoriq/              ← New: ArmorIQ client & models
│   │   ├── __init__.py
│   │   ├── client.py         ← API client with fail-safe defaults
│   │   └── models.py         ← Pydantic models
│   ├── agents/
│   │   ├── identity.py       ← New: Agent registration & verification
│   │   └── execution/
│   ├── policies/
│   │   ├── manager.py        ← New: Policy sync & versioning
│   │   └── financial_policy.rego
│   ├── audit/
│   │   └── db.py             ← Enhanced with compliance fields
│   ├── gateway/
│   │   └── main.py           ← Enhanced with ArmorIQ checks
│   ├── migrations/
│   │   └── 001_armoriq_integration.py
│   ├── tests/
│   │   └── test_armoriq_integration.py
│   ├── init_db.py            ← New: Database initialization
│   └── requirements.txt       ← Updated with aiohttp
├── frontend/
│   └── index.html            ← Enhanced with compliance dashboard
├── .env.example
├── ARMORIQ_INTEGRATION.md    ← Detailed setup & API docs
├── IMPLEMENTATION_SUMMARY.md ← Architecture overview
├── QUICKSTART.md             ← 5-minute quick start
└── SETUP_GUIDE.md            ← This file
```

## Step-by-Step Setup

### 1. Clone and Enter Project

```bash
git clone https://github.com/abhayaaatriv/Intentional.ai.git
cd Intentional.ai
git checkout armor-claw-integration
```

### 2. Create Virtual Environment

```bash
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install --upgrade pip
```

### 3. Install Dependencies

```bash
pip install -r backend/requirements.txt
```

Check versions:
```bash
pip list | grep -E "fastapi|pydantic|aiohttp|pyjwt"
```

### 4. Set Up Environment Variables

Copy the example file:
```bash
cp .env.example .env
```

Edit `.env` with your values:
```bash
# ArmorIQ credentials
ARMORIQ_API_KEY="your-armoriq-api-key-here"
ARMORIQ_API_BASE_URL="https://api.armoriq.ai"

# JWT secret (min 32 chars)
JWT_SECRET="your-secret-key-minimum-32-characters-long"

# Alpaca API (for demo)
ALPACA_API_KEY="PK123456789ABCDEF"
ALPACA_SECRET_KEY="your-secret-key"

# Database
AUDIT_DB_PATH="audit.db"

# Server ports
GATEWAY_PORT="8000"
ORCHESTRATOR_PORT="8001"

# OPA
OPA_URL="http://localhost:8181/v1/data/financial"
```

Verify environment is loaded:
```bash
source .env
echo "API Key: $ARMORIQ_API_KEY"
```

### 5. Initialize Database

**Important**: Always run from project root

```bash
python backend/init_db.py
```

Expected output:
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

**If you see**: `ERROR: no such table: audit_log`
- → Make sure you're running from project root
- → Check AUDIT_DB_PATH is correct
- → Run init again: it handles both fresh and existing databases

Verify database was created:
```bash
ls -lh audit.db
sqlite3 audit.db ".tables"  # Should show: agents audit_log policies ...
```

### 6. Start OPA (Policy Engine)

**Terminal 1:**
```bash
docker run -p 8181:8181 openpolicyagent/opa:latest run --server
```

Test OPA is running:
```bash
curl http://localhost:8181/health
# Returns: {"result":true}
```

### 7. Start Backend Services

**Terminal 2: Gateway**
```bash
cd backend
python -m gateway.main
```

Should output:
```
[2024-XX-XX XX:XX:XX] Starting ArmorClaw Gateway...
INFO:     Uvicorn running on http://0.0.0.0:8000 (Press CTRL+C to quit)
```

Test gateway is running:
```bash
curl http://localhost:8000/health
# Returns: {"status":"ok","service":"armorclaw-gateway","timestamp":1234567890}
```

**Terminal 3: Frontend**
```bash
cd frontend
python -m http.server 8080
```

Should output:
```
Serving HTTP on 0.0.0.0 port 8080 (http://0.0.0.0:8080/) ...
```

### 8. Access Dashboard

Open browser to: **http://localhost:8080**

You should see:
- CapabilityGuard header with ArmorClaw branding
- "Compliance Dashboard" section below verdict panel
- 6 metric cards showing 0% (no actions yet)
- Real-time Alerts panel
- Agent Registry section

### 9. Test the Integration

In the dashboard:

1. **Copy mandate**:
   ```
   Invest $50,000 across AAPL, GOOGL. Buy AAPL with limit $30k, 
   GOOGL with limit $20k. Research first then execute.
   ```

2. **Paste into mandate input** (top left)

3. **Click "▶ Run Full Demo"**

4. **Watch pipeline**:
   - Orchestrator processes mandate
   - Agent decomposes into tasks
   - Gateway validates each action
   - **NEW**: Compliance metrics update!
   - Verdict panel shows ALLOWED/BLOCKED
   - Audit log populates

5. **Check compliance dashboard**:
   - OPA Pass Rate updates
   - ArmorIQ Compliance shows result
   - Agent registry shows registered agent
   - Threat score appears
   - Alerts show any violations

## Verification Checklist

### Database
- [ ] `audit.db` exists and is > 50KB
- [ ] Tables created: `sqlite3 audit.db ".tables" | grep -E "audit_log|agents|policies"`
- [ ] Audit table has ArmorIQ fields: `sqlite3 audit.db "PRAGMA table_info(audit_log);" | grep -E "opa_verdict|armoriq_verdict"`

### Backend Services
- [ ] OPA is running: `curl http://localhost:8181/health` returns `{"result":true}`
- [ ] Gateway is running: `curl http://localhost:8000/health` returns `{"status":"ok",...}`
- [ ] ArmorIQ client is initialized: Check gateway startup logs for no errors

### Frontend
- [ ] Dashboard loads at `http://localhost:8080`
- [ ] Compliance Dashboard section is visible
- [ ] Metric cards show (even if 0%)
- [ ] Browser console has no errors: Press F12, check Console tab

### API Integration
```bash
# Test compliance stats
curl http://localhost:8000/compliance/stats
# Returns: {"total_actions":0,"opa_passed":0,...}

# Test ArmorIQ health
curl http://localhost:8000/armoriq/health
# Returns: {"status":"ok|unavailable","service":"armoriq",...}

# Test agent verification
curl -X POST http://localhost:8000/armoriq/verify-agent \
  -H "Content-Type: application/json" \
  -d '{"agent_id":"test-agent","token":"test-token"}'
```

## Common Issues

### Issue: "ERROR: no such table: audit_log"

**Cause**: Running migration directly instead of init_db.py

**Solution**:
```bash
# ✗ Wrong:
python backend/migrations/001_armoriq_integration.py

# ✓ Correct:
python backend/init_db.py
```

### Issue: Port Already in Use

**For port 8000 (gateway)**:
```bash
# Find process using port 8000
lsof -i :8000
# Kill it
kill -9 <PID>
# Or use different port
export GATEWAY_PORT=8001
```

**For port 8080 (frontend)**:
```bash
python -m http.server 8081
```

### Issue: "ARMORIQ_API_KEY not set"

**Solution**:
```bash
# Load environment
source .env

# Verify
echo $ARMORIQ_API_KEY

# Or set directly
export ARMORIQ_API_KEY="your-key-here"
```

### Issue: ArmorIQ API Unreachable

**Symptom**: Gateway logs show "ArmorIQ unavailable"

**Check**:
1. API key is valid: Try in Postman/curl to https://api.armoriq.ai/health
2. Network connectivity: `ping api.armoriq.ai`
3. Base URL is correct in .env

**Fail-safe**: Gateway denies all actions when ArmorIQ unavailable (secure by default)

### Issue: Compliance Dashboard Metrics Not Updating

**Cause**: No actions executed yet

**Solution**: Run "▶ Run Full Demo" to generate actions

**Debug**:
```bash
# Check audit log
curl http://localhost:8000/logs

# Check if entries have ArmorIQ fields
curl http://localhost:8000/logs | grep -E "armoriq_verdict|threat_score"
```

### Issue: WebSocket Connection Failed

**Symptom**: Browser console shows WebSocket error

**Check**:
1. Gateway is running: `curl http://localhost:8000/health`
2. Browser is on correct port: http://localhost:8080
3. No firewall blocking localhost

**Fix**: Restart gateway:
```bash
pkill -f "gateway.main"
python backend/gateway/main.py
```

## Advanced Configuration

### Custom Database Location

```bash
export AUDIT_DB_PATH="/path/to/custom/audit.db"
python backend/init_db.py
```

### Custom OPA URL

```bash
export OPA_URL="http://my-opa-server:8181/v1/data/financial"
python -m backend.gateway.main
```

### Enable Debug Logging

Edit `backend/gateway/main.py` and change:
```python
logging.basicConfig(level=logging.DEBUG)
```

Then restart gateway.

## Running Tests

```bash
cd backend
pip install pytest
pytest tests/test_armoriq_integration.py -v
```

Expected:
```
test_agent_identity_verification PASSED
test_policy_compliance_check PASSED
test_threat_intelligence_scoring PASSED
...
12 passed in 0.45s
```

## Production Deployment

See `ARMORIQ_INTEGRATION.md` for:
- Security best practices
- Performance optimization
- High availability setup
- Monitoring and alerting
- Database backups

## Getting Help

1. **Check logs**:
   ```bash
   tail -f gateway.log
   tail -f frontend.log
   ```

2. **Read documentation**:
   - `ARMORIQ_INTEGRATION.md` - API details
   - `IMPLEMENTATION_SUMMARY.md` - Architecture
   - Code comments in Python files

3. **Verify integration**:
   ```bash
   python backend/init_db.py
   curl http://localhost:8000/armoriq/health
   ```

4. **Run test suite**:
   ```bash
   pytest backend/tests/ -v
   ```

5. **Check database integrity**:
   ```bash
   sqlite3 audit.db "SELECT COUNT(*) FROM audit_log;"
   ```

## Next Steps

1. Customize OPA policies in `backend/policies/financial_policy.rego`
2. Register custom agents using `backend/agents/identity.py`
3. Configure ArmorIQ policies via dashboard
4. Set up monitoring and alerting
5. Deploy to Vercel or production environment

Enjoy the enhanced security with ArmorClaw Intent Assurance!
