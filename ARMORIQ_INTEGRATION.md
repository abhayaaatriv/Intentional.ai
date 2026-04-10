# ArmorIQ Integration Guide

## Overview

Intentional.ai has been enhanced with **ArmorIQ Intent Assurance** for real-time compliance monitoring, policy enforcement, and agent identity verification. This integration adds a critical security layer to the existing CapabilityGuard + OPA policy system.

## Architecture

### Integration Flow

```
User Mandate → Orchestrator
    ↓
Agent executes with JWT token → Gateway /validate
    ↓
Gateway Validation Pipeline:
  1. Decode JWT + validate signature
  2. OPA policy check (existing)
  3. [NEW] Agent identity verification via ArmorIQ
  4. [NEW] ArmorIQ compliance policy check
  5. [NEW] Threat intelligence evaluation
  6. [NEW] Log decision with ArmorIQ data
  7. Return verdict (both OPA AND ArmorIQ must pass)
    ↓
Dashboard receives:
  - OPA verdict
  - [NEW] ArmorIQ compliance status
  - [NEW] Threat alerts
  - [NEW] Agent identity verification result
```

### Fail-Safe Design

- **If ArmorIQ is unreachable**: System defaults to DENY (fail-safe)
- **Both policies must pass**: OPA AND ArmorIQ verdicts are required
- **Identity verification**: Agent identity must be verified or action is blocked
- **Threat intelligence**: High threat scores trigger alerts and may block actions

## Setup & Configuration

### 1. Environment Variables

Create/update `.env` with ArmorIQ credentials:

```bash
# .env or environment variables
ARMORIQ_API_KEY=your-armoriq-api-key
ARMORIQ_API_URL=https://api.armoriq.ai
ARMORIQ_WEBHOOK_SECRET=optional-webhook-secret
```

Get your API key from: https://armoriq.ai

### 2. Database Migration

Run the migration to add ArmorIQ fields to audit schema:

```bash
cd backend
python migrations/001_armoriq_integration.py
```

This creates/updates:
- `audit_log` table with ArmorIQ columns
- `agents` table for identity management
- `policies` table for policy versioning
- `policy_versions` table for rollback capability

### 3. Start Services

```bash
# Terminal 1: OPA
docker run -p 8181:8181 openpolicyagent/opa:latest run --server

# Terminal 2: Backend services
cd backend
python gateway/main.py

# Terminal 3: Frontend
cd frontend
python -m http.server 8080
```

## Module Overview

### ArmorIQ API Client (`backend/armoriq/client.py`)

**Purpose**: HTTP client for all ArmorIQ API interactions

**Key Methods**:
- `verify_agent_identity(agent_id, token)` - Verify agent via ArmorIQ
- `check_policy_compliance(req)` - Check action against policies
- `register_agent(identity)` - Register new agent
- `update_agent_scope(agent_id, capabilities, ...)` - Update agent permissions
- `revoke_agent(agent_id)` - Disable agent
- `get_threat_intelligence(agent_id)` - Get threat score
- `get_policies()` - Fetch active policies
- `sync_policies()` - Sync from ArmorIQ
- `health_check()` - Check API availability

**Error Handling**: All failures return fail-safe responses (deny/unavailable)

### Gateway Integration (`backend/gateway/main.py`)

**Enhanced Validation Endpoint**: `POST /validate`

**Changes**:
- After OPA check, calls ArmorIQ identity verification
- Runs ArmorIQ policy compliance check
- Fetches threat intelligence
- Logs all verdicts to audit trail
- Broadcasts expanded webhook payload

**New Endpoints**:
- `POST /armoriq/verify-agent` - Manual agent verification
- `POST /armoriq/check-compliance` - Standalone policy check
- `GET /armoriq/policies` - List active policies
- `GET /armoriq/threat-intel` - Get agent threat score
- `GET /armoriq/health` - Check ArmorIQ availability
- `GET /compliance/stats` - Compliance statistics
- `GET /compliance/report` - Generate compliance reports

### Agent Identity Manager (`backend/agents/identity.py`)

**Purpose**: Manage agent identities with ArmorIQ

**Key Functions**:
- `register_agent()` - Register with capabilities
- `verify_agent()` - Mark as verified
- `update_agent_scope()` - Change permissions
- `suspend_agent()` - Temporarily disable
- `revoke_agent()` - Permanently disable
- `get_agent()` - Retrieve details
- `list_agents()` - List all agents

**Database**: Tracks agent registration, verification, and status

### Policy Manager (`backend/policies/manager.py`)

**Purpose**: Manage ArmorIQ and OPA policies

**Key Functions**:
- `sync_armoriq_policies()` - Fetch from ArmorIQ
- `enable_policy()` / `disable_policy()` - Toggle policies
- `test_policy()` - Test against sample input
- `rollback_policy()` - Revert to previous version
- `get_policy_versions()` - View history
- `get_policy_test_results()` - See test coverage

**Database**: Tracks policies, versions, tests, and rollback history

### Enhanced Audit Log (`backend/audit/db.py`)

**New Fields**:
- `opa_verdict` - OPA policy result (0/1)
- `armoriq_verdict` - ArmorIQ compliance result (0/1)
- `armoriq_policy_id` - Applied policy ID
- `armoriq_violations` - JSON array of violations
- `agent_identity_verified` - Identity check result (0/1)
- `threat_score` - Risk score (0.0-100.0)
- `compliance_status` - Overall status (compliant/non_compliant/unknown)

**New Query Functions**:
- `get_compliance_stats()` - Aggregate statistics
- `get_compliance_report(start, end, agent_id)` - Detailed report

### Compliance Dashboard (Frontend)

**Display Elements**:
- **Metrics Row**: OPA pass rate, ArmorIQ compliance, both passed, identity verified, threat score, active violations
- **Real-time Alerts**: Live feed of compliance violations and threats
- **Agent Registry**: List of registered agents with verification status
- **Threat Indicator**: Color-coded threat level (critical/elevated/safe)

**Updates via WebSocket**: Dashboard auto-updates as actions flow through gateway

## Usage Examples

### 1. Register an Agent

```python
from agents.identity import AgentIdentityManager
from armoriq.client import ArmorIQClient

client = ArmorIQClient()
manager = AgentIdentityManager(armoriq_client=client)

manager.register_agent(
    agent_id="exec-agent",
    agent_name="Execution Agent",
    capabilities=["BUY", "SELL", "LOG"],
    allowed_actions=["BUY", "SELL"],
    ticker_scope=["AAPL", "GOOGL", "MSFT"],
    max_qty=1000,
    destination_scope="internal"
)
```

### 2. Verify Agent Identity (Automatic in Gateway)

The gateway automatically verifies agent identity:

```python
verification = armoriq_client.verify_agent_identity(agent_id, jwt_token)
if not verification.verified:
    print(f"Violations: {verification.violations}")
    # Action is blocked
```

### 3. Check Policy Compliance (Automatic in Gateway)

```python
from armoriq.models import PolicyCheckRequest

req = PolicyCheckRequest(
    agent_id="exec-agent",
    action="BUY",
    ticker="AAPL",
    qty=500,
    destination="internal",
)

response = armoriq_client.check_policy_compliance(req)
print(f"Allowed: {response.allowed}")
print(f"Compliance: {response.compliance_status}")
print(f"Threat Score: {response.threat_score}")
```

### 4. Sync Policies from ArmorIQ

```python
from policies.manager import PolicyManager

pm = PolicyManager(armoriq_client=client)
pm.sync_armoriq_policies()
policies = pm.list_active_policies()
```

### 5. Generate Compliance Report

```python
import time
from audit.db import get_compliance_report

start = time.time() - 3600  # Last hour
end = time.time()

report = get_compliance_report(start, end, agent_id="exec-agent")
for entry in report:
    print(f"{entry['action']}: OPA={entry['opa_verdict']}, ArmorIQ={entry['armoriq_verdict']}")
```

## Testing

### Run Integration Tests

```bash
cd backend
python -m pytest tests/test_armoriq_integration.py -v
```

**Tests Cover**:
- ArmorIQ API client fail-safe behavior
- Audit database schema and queries
- Agent identity management
- Policy versioning and rollback
- Full compliance flow integration

### Manual Testing

1. **Parse a Mandate**: Dashboard → "Run Full Demo"
2. **Trigger Actions**: Execute BUY/SELL/READ actions
3. **Monitor Compliance**: Watch dashboard metrics and alerts update
4. **Check Logs**: `curl http://localhost:8001/logs` for audit trail

## Compliance Metrics

The system tracks and displays:

- **OPA Pass Rate**: Percentage of actions passing OPA policies
- **ArmorIQ Compliance Rate**: Percentage passing ArmorIQ policies
- **Both Passed**: Actions that passed both OPA and ArmorIQ
- **Identity Verified Rate**: Percentage of agents verified
- **Avg Threat Score**: Average threat intelligence score
- **Active Violations**: Recent policy violations

## Troubleshooting

### ArmorIQ API Key Issues

```
Error: ARMORIQ_API_KEY not set — ArmorIQ checks will fail safe (deny)
```

**Solution**: Set `ARMORIQ_API_KEY` environment variable

### Connection Timeouts

```
Error: ArmorIQ request timeout
```

**Solution**: 
- Check network connectivity to `https://api.armoriq.ai`
- Increase timeout in `client.py` (currently 5 seconds)
- Check API key validity

### Gateway Returns All Violations

If gateway blocks all actions:
1. Check agent is registered: `curl http://localhost:8001/logs`
2. Verify agent identity: `POST http://localhost:8001/armoriq/verify-agent`
3. Check threat score: `GET http://localhost:8001/armoriq/threat-intel?agent_id=XXX`

### Database Errors

If you see SQLite errors:
1. Run migration: `python migrations/001_armoriq_integration.py`
2. Check `AUDIT_DB_PATH` is valid
3. Ensure write permissions to database directory

## Performance Considerations

### Caching

- Policies are cached for 5 minutes (`PolicyManager.cache_ttl`)
- Agent verifications are cached per request
- Threat intelligence is fetched on-demand

### Timeout

- Default API timeout: 5 seconds
- Retry logic: 2 retries with exponential backoff
- Fail-safe default: DENY if service unavailable

### Scalability

For production deployments:
- Use connection pooling for database
- Implement Redis caching for policies
- Deploy gateway behind load balancer
- Consider dedicated ArmorIQ SLA

## Security Best Practices

1. **Fail-Safe Defaults**: System denies by default if services unavailable
2. **Identity Verification**: All agents must be verified by ArmorIQ
3. **Policy Enforcement**: Both OPA and ArmorIQ must approve actions
4. **Audit Trail**: All decisions logged with full context
5. **Secret Management**: Store API keys in secure vault (not in code)
6. **HTTPS Only**: All ArmorIQ API calls require TLS

## Next Steps

1. Configure ArmorIQ API key in environment
2. Run database migration
3. Start backend services
4. Test with demo mandate
5. Monitor compliance dashboard
6. Configure ArmorIQ policies for your use cases

## Support

For issues or questions:
- Check logs: `curl http://localhost:8001/logs`
- Review compliance report: `curl http://localhost:8001/compliance/report`
- ArmorIQ docs: https://armoriq.ai
- GitHub: https://github.com/abhayaaatriv/Intentional.ai

## API Reference

### POST /validate

**Request**:
```json
{
  "agent_id": "exec-agent",
  "token": "jwt.token.here",
  "action": "BUY",
  "ticker": "AAPL",
  "qty": 100,
  "destination": "internal",
  "metadata": {}
}
```

**Response**:
```json
{
  "allowed": true,
  "violations": [],
  "agent_id": "exec-agent",
  "action": "BUY",
  "ticker": "AAPL",
  "reason": "Action 'BUY' on AAPL is compliant with all policies.",
  "opa_verdict": true,
  "armoriq_verdict": true,
  "agent_identity_verified": true,
  "threat_score": 15.5,
  "compliance_status": "compliant"
}
```

## Changelog

### v1.0.0 (Initial Release)

- ArmorIQ API client with fail-safe defaults
- Gateway integration for identity verification
- Policy compliance checking
- Agent identity management
- Policy versioning and rollback
- Enhanced audit logging
- Compliance dashboard
- Integration tests
