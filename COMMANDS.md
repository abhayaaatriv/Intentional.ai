# Quick Commands Reference

Quick copy-paste commands for common tasks.

## Initial Setup (one time)

```bash
# Clone repo
git clone https://github.com/abhayaaatriv/Intentional.ai.git
cd Intentional.ai
git checkout armor-claw-integration

# Create virtual environment
python3 -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# Install dependencies
pip install -r backend/requirements.txt

# Copy and edit .env
cp .env.example .env
# Edit .env with your ArmorIQ API key and other credentials

# Initialize database
python backend/init_db.py
```

## Start Services (run in separate terminals)

**Terminal 1: OPA Policy Engine**
```bash
docker run -p 8181:8181 openpolicyagent/opa:latest run --server
```

**Terminal 2: Backend Gateway**
```bash
cd backend
python -m gateway.main
```

**Terminal 3: Frontend Dashboard**
```bash
cd frontend
python -m http.server 8080
```

## Open Dashboard

```bash
# Open in browser
http://localhost:8080
```

## Common API Tests

### Health Checks
```bash
# Gateway health
curl http://localhost:8000/health

# ArmorIQ health
curl http://localhost:8000/armoriq/health

# OPA health
curl http://localhost:8181/health
```

### Compliance Metrics
```bash
# Get compliance statistics
curl http://localhost:8000/compliance/stats

# Get compliance report (all time)
curl http://localhost:8000/compliance/report

# Get compliance report for agent (requires start_time and end_time)
curl "http://localhost:8000/compliance/report?agent_id=research-agent&start_time=0&end_time=9999999999"
```

### Audit Logs
```bash
# Get recent audit logs
curl http://localhost:8000/logs

# Get last 20 entries
curl "http://localhost:8000/logs?limit=20"

# Get last 50 entries
curl "http://localhost:8000/logs?limit=50"
```

### ArmorIQ Endpoints
```bash
# List active policies
curl http://localhost:8000/armoriq/policies

# Get threat intelligence for agent
curl "http://localhost:8000/armoriq/threat-intel?agent_id=research-agent"

# Verify agent identity
curl -X POST http://localhost:8000/armoriq/verify-agent \
  -H "Content-Type: application/json" \
  -d '{"agent_id":"test-agent","token":"test-token"}'
```

## Database Operations

### Check Database Status
```bash
# List all tables
sqlite3 audit.db ".tables"

# Show audit_log schema
sqlite3 audit.db ".schema audit_log"

# Count audit entries
sqlite3 audit.db "SELECT COUNT(*) FROM audit_log;"

# Show last 5 entries
sqlite3 audit.db "SELECT * FROM audit_log LIMIT 5;"

# Show agent registry
sqlite3 audit.db "SELECT * FROM agents;"

# Show policies
sqlite3 audit.db "SELECT policy_id, policy_name, enabled FROM policies;"
```

### Inspect Compliance Data
```bash
# Show entries with ArmorIQ fields
sqlite3 audit.db "SELECT agent_id, action, opa_verdict, armoriq_verdict, threat_score FROM audit_log;"

# Show entries where both passed
sqlite3 audit.db "SELECT * FROM audit_log WHERE opa_verdict=1 AND armoriq_verdict=1;"

# Show entries where either failed
sqlite3 audit.db "SELECT * FROM audit_log WHERE opa_verdict=0 OR armoriq_verdict=0;"

# Show entries with threat_score > 50
sqlite3 audit.db "SELECT agent_id, action, threat_score FROM audit_log WHERE threat_score > 50;"

# Show compliance statistics
sqlite3 audit.db "SELECT 
  COUNT(*) as total,
  SUM(CASE WHEN opa_verdict=1 THEN 1 ELSE 0 END) as opa_passed,
  SUM(CASE WHEN armoriq_verdict=1 THEN 1 ELSE 0 END) as armoriq_passed,
  SUM(CASE WHEN opa_verdict=1 AND armoriq_verdict=1 THEN 1 ELSE 0 END) as both_passed,
  AVG(threat_score) as avg_threat
FROM audit_log;"
```

### Reset Database
```bash
# Backup first
cp audit.db audit.db.backup

# Delete database
rm audit.db

# Reinitialize
python backend/init_db.py
```

## Testing

### Run Integration Tests
```bash
cd backend
pip install pytest
pytest tests/test_armoriq_integration.py -v
```

### Run Specific Test
```bash
pytest tests/test_armoriq_integration.py::test_agent_identity_verification -v
```

### Run with Coverage
```bash
pytest tests/test_armoriq_integration.py --cov=armoriq --cov=audit --cov=agents --cov=policies
```

## Debugging

### View Gateway Logs
```bash
# Run with debug output
PYTHONUNBUFFERED=1 python -m gateway.main
```

### Check Service Ports
```bash
# List services using ports
lsof -i :8000  # Gateway
lsof -i :8001  # Orchestrator
lsof -i :8080  # Frontend
lsof -i :8181  # OPA
```

### Kill Process on Port
```bash
# Kill gateway
lsof -i :8000 | grep LISTEN | awk '{print $2}' | xargs kill -9

# Kill frontend
lsof -i :8080 | grep LISTEN | awk '{print $2}' | xargs kill -9
```

### View Database Issues
```bash
# Check database integrity
sqlite3 audit.db "PRAGMA integrity_check;"

# Vacuum/optimize database
sqlite3 audit.db "VACUUM;"

# Check foreign keys
sqlite3 audit.db "PRAGMA foreign_keys;"
```

## Development

### Format Code
```bash
# Install black
pip install black

# Format all Python files
black backend/
```

### Check Imports
```bash
# Check for unused imports
pip install vulture
vulture backend/
```

### Type Checking
```bash
# Install mypy
pip install mypy

# Check types
mypy backend/armoriq/
mypy backend/gateway/
```

## Deployment

### Build Docker Image
```bash
# (If using Docker Compose)
docker-compose build
docker-compose up
```

### Check All Services Running
```bash
# Verify all health checks pass
for url in http://localhost:8000/health http://localhost:8080 http://localhost:8181/health; do
  echo "Checking $url..."
  curl -s "$url" | head -c 50
  echo ""
done
```

### Create Database Dump
```bash
# Backup audit log to SQL
sqlite3 audit.db ".dump audit_log" > audit_log_backup.sql

# Export to CSV
sqlite3 audit.db ".mode csv" ".output audit_log.csv" "SELECT * FROM audit_log;"
```

## Environment

### View Current Environment
```bash
# Show ArmorIQ config
echo "API Key: ${ARMORIQ_API_KEY:0:10}..."
echo "Base URL: $ARMORIQ_API_BASE_URL"

# Show all env vars starting with ARMORIQ
env | grep ARMORIQ
```

### Load Environment
```bash
# From .env file
set -a
source .env
set +a

# Verify
echo $ARMORIQ_API_KEY
```

## Common Fixes

### Fix: "no such table: audit_log"
```bash
python backend/init_db.py
```

### Fix: "Port already in use"
```bash
# Gateway
lsof -i :8000 | grep LISTEN | awk '{print $2}' | xargs kill -9

# Frontend
lsof -i :8080 | grep LISTEN | awk '{print $2}' | xargs kill -9
```

### Fix: "ARMORIQ_API_KEY not set"
```bash
export ARMORIQ_API_KEY="your-key-here"
python backend/init_db.py
```

### Fix: "ArmorIQ unavailable"
```bash
# Check API key is valid
curl https://api.armoriq.ai/health \
  -H "Authorization: Bearer $ARMORIQ_API_KEY"

# Check network
ping api.armoriq.ai
```

### Fix: WebSocket connection failed
```bash
# Verify gateway is running
curl http://localhost:8000/health

# Check logs
tail -f gateway.log
```

## Performance Monitoring

### Monitor Gateway Performance
```bash
# Count requests per minute
sqlite3 audit.db "SELECT 
  COUNT(*) as count,
  datetime(timestamp, 'unixepoch', 'localtime') as minute
FROM audit_log
GROUP BY minute
LIMIT 10;"
```

### Check Average Decision Time
```bash
# Average OPA vs ArmorIQ verdict time (theoretical)
sqlite3 audit.db "SELECT 
  COUNT(*) as total_decisions,
  SUM(CASE WHEN opa_verdict=1 THEN 1 ELSE 0 END) as approved,
  SUM(CASE WHEN opa_verdict=0 THEN 1 ELSE 0 END) as rejected,
  ROUND(100.0 * SUM(CASE WHEN opa_verdict=1 THEN 1 ELSE 0 END) / COUNT(*), 2) as approval_rate
FROM audit_log;"
```

## Useful Scripts

### Clean Old Logs (keep last 1000)
```bash
sqlite3 audit.db "DELETE FROM audit_log WHERE id NOT IN (SELECT id FROM audit_log ORDER BY timestamp DESC LIMIT 1000);"
```

### Export Daily Summary
```bash
sqlite3 audit.db "SELECT 
  date(timestamp, 'unixepoch', 'localtime') as day,
  COUNT(*) as total,
  SUM(CASE WHEN opa_verdict=1 THEN 1 ELSE 0 END) as opa_pass,
  SUM(CASE WHEN armoriq_verdict=1 THEN 1 ELSE 0 END) as armoriq_pass,
  ROUND(AVG(threat_score), 2) as avg_threat
FROM audit_log
GROUP BY day
ORDER BY day DESC;"
```

### Monitor Threat Spikes
```bash
sqlite3 audit.db "SELECT 
  timestamp,
  agent_id,
  action,
  ticker,
  threat_score
FROM audit_log
WHERE threat_score > 70
ORDER BY threat_score DESC;"
```

## Documentation Links

- **QUICKSTART.md** - 5-minute setup
- **SETUP_GUIDE.md** - Complete installation
- **ARMORIQ_INTEGRATION.md** - API reference
- **IMPLEMENTATION_SUMMARY.md** - Architecture
- **DELIVERY_CHECKLIST.md** - Verification
- **INTEGRATION_COMPLETE.md** - Status summary

---

All commands assume you're in the project root directory. For Windows, use `venv\Scripts\activate` instead of `source venv/bin/activate`.
