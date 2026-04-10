# Documentation Index - ArmorIQ Integration

Complete guide to all documentation for the ArmorClaw Intent Assurance integration.

## 📋 Start Here

**First time?** → Start with **[QUICKSTART.md](QUICKSTART.md)** (5 minutes)

**Need detailed setup?** → See **[SETUP_GUIDE.md](SETUP_GUIDE.md)** (step-by-step)

**Want to verify everything?** → Check **[DELIVERY_CHECKLIST.md](DELIVERY_CHECKLIST.md)**

## 📚 Documentation Map

### Getting Started
| Document | Purpose | Time |
|----------|---------|------|
| **[QUICKSTART.md](QUICKSTART.md)** | 5-minute setup with examples | 5 min |
| **[SETUP_GUIDE.md](SETUP_GUIDE.md)** | Complete step-by-step guide | 15 min |
| **[COMMANDS.md](COMMANDS.md)** | Copy-paste commands for common tasks | Reference |

### Reference
| Document | Purpose | For |
|----------|---------|-----|
| **[ARMORIQ_INTEGRATION.md](ARMORIQ_INTEGRATION.md)** | API docs & troubleshooting | Developers |
| **[IMPLEMENTATION_SUMMARY.md](IMPLEMENTATION_SUMMARY.md)** | Architecture & components | Architects |
| **[DELIVERY_CHECKLIST.md](DELIVERY_CHECKLIST.md)** | Verification checklist | DevOps/QA |
| **[INTEGRATION_COMPLETE.md](INTEGRATION_COMPLETE.md)** | Completion status & stats | Project Managers |

### Configuration
| Document | Purpose |
|----------|---------|
| **.env.example** | Environment variables template |
| **README.md** | Project overview |

---

## 📖 Reading Guide by Role

### 🚀 I want to get started quickly
1. Read: [QUICKSTART.md](QUICKSTART.md) (5 min)
2. Run: `python backend/init_db.py`
3. Start services following the terminal commands
4. Open dashboard at http://localhost:8080
5. Click "Run Full Demo"

### 🔧 I need complete installation instructions
1. Read: [SETUP_GUIDE.md](SETUP_GUIDE.md) (step 1-9)
2. Follow verification checklist
3. Test with sample commands from [COMMANDS.md](COMMANDS.md)
4. Refer to troubleshooting section as needed

### 📊 I'm integrating with my system
1. Read: [ARMORIQ_INTEGRATION.md](ARMORIQ_INTEGRATION.md) - API reference
2. Check: [IMPLEMENTATION_SUMMARY.md](IMPLEMENTATION_SUMMARY.md) - Architecture
3. Review: Backend code in `backend/armoriq/` and `backend/gateway/`
4. Test endpoints using [COMMANDS.md](COMMANDS.md)

### 🏗️ I'm deploying to production
1. Read: [SETUP_GUIDE.md](SETUP_GUIDE.md) - Full setup
2. Check: [DELIVERY_CHECKLIST.md](DELIVERY_CHECKLIST.md) - Pre-deploy verification
3. Review: Security section in [ARMORIQ_INTEGRATION.md](ARMORIQ_INTEGRATION.md)
4. Monitor: Using [COMMANDS.md](COMMANDS.md) database queries

### 🐛 I'm debugging an issue
1. Check: [SETUP_GUIDE.md](SETUP_GUIDE.md) - Common Issues section
2. Use: [COMMANDS.md](COMMANDS.md) - Debugging commands
3. Refer: [ARMORIQ_INTEGRATION.md](ARMORIQ_INTEGRATION.md) - Troubleshooting
4. Test: Health checks from [COMMANDS.md](COMMANDS.md)

### 👨‍💻 I'm contributing code
1. Read: [IMPLEMENTATION_SUMMARY.md](IMPLEMENTATION_SUMMARY.md) - Architecture
2. Review: Code structure and patterns in backend/
3. Check: Testing section in [SETUP_GUIDE.md](SETUP_GUIDE.md)
4. Add tests following examples in backend/tests/

---

## 🎯 Common Tasks

### Task: Set up for the first time
**Documents**: [QUICKSTART.md](QUICKSTART.md) → [SETUP_GUIDE.md](SETUP_GUIDE.md)
```bash
python backend/init_db.py
# Start services (3 terminals)
# Open http://localhost:8080
```

### Task: Understand the architecture
**Documents**: [IMPLEMENTATION_SUMMARY.md](IMPLEMENTATION_SUMMARY.md) → [ARMORIQ_INTEGRATION.md](ARMORIQ_INTEGRATION.md)
- Read architecture overview
- Review API endpoints
- Check data flow diagrams

### Task: Add a new agent
**Documents**: [IMPLEMENTATION_SUMMARY.md](IMPLEMENTATION_SUMMARY.md) → Code in `backend/agents/identity.py`
- See example: `register_agent()` function
- Test using [COMMANDS.md](COMMANDS.md) API examples

### Task: Configure ArmorIQ policies
**Documents**: [ARMORIQ_INTEGRATION.md](ARMORIQ_INTEGRATION.md) → Code in `backend/policies/manager.py`
- See policy sync methods
- Review policy_check_compliance flow

### Task: Debug a failed validation
**Documents**: [SETUP_GUIDE.md](SETUP_GUIDE.md) Common Issues → [COMMANDS.md](COMMANDS.md) Database Queries
- Check audit log: `curl http://localhost:8000/logs`
- Inspect database: `sqlite3 audit.db "SELECT * FROM audit_log LIMIT 1;"`
- Review compliance report: `curl http://localhost:8000/compliance/stats`

### Task: Deploy to production
**Documents**: [DELIVERY_CHECKLIST.md](DELIVERY_CHECKLIST.md) → [ARMORIQ_INTEGRATION.md](ARMORIQ_INTEGRATION.md)
- Complete pre-deployment verification
- Configure environment variables
- Set up monitoring and alerting

### Task: Run tests
**Documents**: [SETUP_GUIDE.md](SETUP_GUIDE.md) - Running Tests section
```bash
pytest backend/tests/test_armoriq_integration.py -v
```

### Task: Export compliance report
**Documents**: [COMMANDS.md](COMMANDS.md) - Database Operations section
- Use provided SQL queries
- Export to CSV or JSON
- Create dashboard visualizations

---

## 🔍 Find Information By Topic

### Installation & Setup
- Initial setup: [QUICKSTART.md](QUICKSTART.md) sections 1-4
- Detailed setup: [SETUP_GUIDE.md](SETUP_GUIDE.md) sections 1-9
- Database: [SETUP_GUIDE.md](SETUP_GUIDE.md) Step 5 or [COMMANDS.md](COMMANDS.md) Database Operations
- Environment: [SETUP_GUIDE.md](SETUP_GUIDE.md) Step 4 or [COMMANDS.md](COMMANDS.md) Environment

### API & Integration
- Gateway endpoints: [ARMORIQ_INTEGRATION.md](ARMORIQ_INTEGRATION.md) API Reference
- ArmorIQ client: [IMPLEMENTATION_SUMMARY.md](IMPLEMENTATION_SUMMARY.md) Components
- Compliance: [ARMORIQ_INTEGRATION.md](ARMORIQ_INTEGRATION.md) Compliance Endpoints
- Testing: [COMMANDS.md](COMMANDS.md) API Tests or [COMMANDS.md](COMMANDS.md) Testing

### Architecture & Design
- Overview: [IMPLEMENTATION_SUMMARY.md](IMPLEMENTATION_SUMMARY.md)
- Data flow: [IMPLEMENTATION_SUMMARY.md](IMPLEMENTATION_SUMMARY.md) Architecture Diagram
- Database schema: [IMPLEMENTATION_SUMMARY.md](IMPLEMENTATION_SUMMARY.md) Database Tables
- Security: [ARMORIQ_INTEGRATION.md](ARMORIQ_INTEGRATION.md) Security Features

### Troubleshooting
- Common issues: [SETUP_GUIDE.md](SETUP_GUIDE.md) Common Issues section
- Debugging: [SETUP_GUIDE.md](SETUP_GUIDE.md) Advanced Configuration
- Database issues: [COMMANDS.md](COMMANDS.md) Debugging section
- API issues: [ARMORIQ_INTEGRATION.md](ARMORIQ_INTEGRATION.md) Troubleshooting

### Operations & Monitoring
- Starting services: [QUICKSTART.md](QUICKSTART.md) Step 3-4
- Health checks: [COMMANDS.md](COMMANDS.md) Health Checks
- Logs: [COMMANDS.md](COMMANDS.md) Debugging section
- Metrics: [COMMANDS.md](COMMANDS.md) Performance Monitoring
- Database: [COMMANDS.md](COMMANDS.md) Database Operations

### Development & Testing
- Architecture: [IMPLEMENTATION_SUMMARY.md](IMPLEMENTATION_SUMMARY.md)
- Code structure: [IMPLEMENTATION_SUMMARY.md](IMPLEMENTATION_SUMMARY.md) File Structure
- Testing: [SETUP_GUIDE.md](SETUP_GUIDE.md) Running Tests
- Test suite: [COMMANDS.md](COMMANDS.md) Testing

---

## 📊 Document Statistics

| Document | Lines | Purpose |
|----------|-------|---------|
| QUICKSTART.md | 257 | 5-minute setup |
| SETUP_GUIDE.md | 448 | Complete installation |
| ARMORIQ_INTEGRATION.md | 416 | API reference |
| IMPLEMENTATION_SUMMARY.md | 384 | Architecture |
| DELIVERY_CHECKLIST.md | 368 | Verification |
| INTEGRATION_COMPLETE.md | 349 | Status summary |
| COMMANDS.md | 411 | Command reference |
| DOCUMENTATION_INDEX.md | This file | Navigation |

**Total**: 2,800+ lines of documentation

---

## ✅ Pre-Deployment Checklist

Before going to production, ensure:

1. **Setup Complete**
   - [ ] All prerequisites installed
   - [ ] Database initialized: `python backend/init_db.py`
   - [ ] Environment variables configured
   - See: [DELIVERY_CHECKLIST.md](DELIVERY_CHECKLIST.md)

2. **Services Verified**
   - [ ] OPA running: `curl http://localhost:8181/health`
   - [ ] Gateway running: `curl http://localhost:8000/health`
   - [ ] Dashboard loading: http://localhost:8080
   - [ ] ArmorIQ connected: `curl http://localhost:8000/armoriq/health`
   - See: [COMMANDS.md](COMMANDS.md) Health Checks

3. **Tests Passing**
   - [ ] Integration tests run: `pytest backend/tests/ -v`
   - [ ] Full demo works in dashboard
   - [ ] Compliance metrics update correctly
   - See: [SETUP_GUIDE.md](SETUP_GUIDE.md) Running Tests

4. **Documentation Reviewed**
   - [ ] Architecture understood: [IMPLEMENTATION_SUMMARY.md](IMPLEMENTATION_SUMMARY.md)
   - [ ] API endpoints documented: [ARMORIQ_INTEGRATION.md](ARMORIQ_INTEGRATION.md)
   - [ ] Troubleshooting reviewed: [SETUP_GUIDE.md](SETUP_GUIDE.md)

---

## 🆘 Need Help?

### I'm stuck on setup
→ [SETUP_GUIDE.md](SETUP_GUIDE.md) Common Issues section

### API integration isn't working
→ [ARMORIQ_INTEGRATION.md](ARMORIQ_INTEGRATION.md) Troubleshooting section

### Dashboard metrics not updating
→ [COMMANDS.md](COMMANDS.md) Common Fixes

### I found a bug
→ Check [DELIVERY_CHECKLIST.md](DELIVERY_CHECKLIST.md) for verification procedures

### I want to extend the system
→ [IMPLEMENTATION_SUMMARY.md](IMPLEMENTATION_SUMMARY.md) then review code comments

---

## 📝 Document Navigation

Quick links between documents:

- **From QUICKSTART**: → [SETUP_GUIDE.md](SETUP_GUIDE.md) for details
- **From SETUP_GUIDE**: → [COMMANDS.md](COMMANDS.md) for operations
- **From COMMANDS**: → [ARMORIQ_INTEGRATION.md](ARMORIQ_INTEGRATION.md) for API docs
- **From ARMORIQ_INTEGRATION**: → [IMPLEMENTATION_SUMMARY.md](IMPLEMENTATION_SUMMARY.md) for architecture
- **From IMPLEMENTATION_SUMMARY**: → [DELIVERY_CHECKLIST.md](DELIVERY_CHECKLIST.md) for verification

---

**Last Updated**: 2026-04-10

All documentation is maintained in sync with the codebase. Check the README for version information.
