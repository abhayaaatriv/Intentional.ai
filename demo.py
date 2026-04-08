"""
CapabilityGuard — End-to-End Demo Script
Run this in front of judges: python demo.py

Requires:
  - OPA running on :8181
  - Gateway (ArmorClaw) running on :8000
  - Orchestrator running on :8001
  - Alpaca paper keys in .env

Flow demonstrated:
  1. Parse mandate → IntentGraph
  2. Mint 3 bounded JWTs
  3. ResearchAgent READ AAPL      → ✅ ALLOWED
  4. ExecutionAgent BUY AAPL ×5  → ✅ ALLOWED
  5. ExecutionAgent SELL AAPL ×5 → ❌ BLOCKED (action_not_permitted)
  6. ReportAgent SEND_DATA ext   → ❌ BLOCKED (unauthorized_destination)
  7. ExecutionAgent BUY MSFT ×2  → ❌ BLOCKED (ticker_out_of_scope)
  8. Print full audit log
"""
import requests
import json
import time

ORCHESTRATOR = "http://localhost:8001"
GATEWAY = "http://localhost:8000"

GREEN  = "\033[92m"
RED    = "\033[91m"
YELLOW = "\033[93m"
BOLD   = "\033[1m"
RESET  = "\033[0m"


def sep(title=""):
    print(f"\n{BOLD}{'─'*60}{RESET}")
    if title:
        print(f"{BOLD}  {title}{RESET}")
    print()


def show_verdict(label: str, result: dict):
    if result.get("status") == "BLOCKED" or not result.get("allowed", True):
        vios = result.get("reasons", result.get("violations", []))
        print(f"  {RED}✗ BLOCKED{RESET}  {label}")
        print(f"    Violations: {', '.join(vios)}")
        print(f"    Reason: {result.get('reason', '')}")
    else:
        print(f"  {GREEN}✓ ALLOWED{RESET}  {label}")
        print(f"    Result: {json.dumps({k:v for k,v in result.items() if k not in ('status','reasons','violations')}, indent=2)[:120]}")


def main():
    print(f"\n{BOLD}{'═'*60}")
    print("  CapabilityGuard — Live Demo")
    print(f"{'═'*60}{RESET}\n")

    # ── STEP 1: Parse mandate ────────────────────────────────────────────────
    sep("STEP 1 — Parse Mandate → IntentGraph")
    mandate = "Research AAPL and buy 5 shares if PE ratio is under 25"
    print(f"  Mandate: \"{mandate}\"\n")

    resp = requests.post(f"{ORCHESTRATOR}/run-mandate", json={"mandate": mandate})
    data = resp.json()
    ig = data["intent_graph"]
    tokens = data["tokens"]

    print(f"  Intent Graph:")
    print(f"    allowed_tickers: {ig['allowed_tickers']}")
    print(f"    allowed_actions: {ig['allowed_actions']}")
    print(f"    blocked_actions: {ig['blocked_actions']}")
    print(f"    condition:       {ig['condition']}")
    print(f"    max_qty:         {ig['max_qty']}")

    # ── STEP 2: Show tokens ──────────────────────────────────────────────────
    sep("STEP 2 — Capability Tokens Minted")
    for agent_id, jwt_str in tokens.items():
        print(f"  {YELLOW}{agent_id}{RESET}")
        print(f"    JWT: {jwt_str[:40]}...{jwt_str[-8:]}")

    # ── STEP 3–7: Simulate agent actions ─────────────────────────────────────
    sep("STEP 3–7 — Agent Actions Through ArmorClaw Gate")

    # Import agents (they call gateway internally)
    import sys, os
    sys.path.insert(0, os.path.dirname(__file__))
    from backend.agents.research.agent import ResearchAgent
    from backend.agents.execution.agent import ExecutionAgent
    from backend.agents.report.agent import ReportAgent

    research  = ResearchAgent(tokens["research-agent-01"])
    execution = ExecutionAgent(tokens["execution-agent-01"])
    report    = ReportAgent(tokens["report-agent-01"])

    print(f"\n{BOLD}3. ResearchAgent — READ AAPL{RESET}")
    show_verdict("READ AAPL", research.fetch_pe_ratio("AAPL"))
    time.sleep(0.3)

    print(f"\n{BOLD}4. ExecutionAgent — BUY AAPL ×5{RESET}")
    show_verdict("BUY AAPL ×5", execution.buy("AAPL", 5))
    time.sleep(0.3)

    print(f"\n{BOLD}5. ExecutionAgent — SELL AAPL ×5  (token is BUY_ONLY){RESET}")
    show_verdict("SELL AAPL ×5", execution.sell("AAPL", 5))
    time.sleep(0.3)

    print(f"\n{BOLD}6. ReportAgent — POST to external API{RESET}")
    show_verdict("SEND_DATA to external URL", report.send_external(
        "https://httpbin.org/post", {"portfolio": "leaked"}
    ))
    time.sleep(0.3)

    print(f"\n{BOLD}7. ExecutionAgent — BUY MSFT ×2  (MSFT not in ticker scope){RESET}")
    show_verdict("BUY MSFT ×2", execution.buy("MSFT", 2))

    # ── STEP 8: Audit log ────────────────────────────────────────────────────
    sep("STEP 8 — Audit Log")
    logs = requests.get(f"{GATEWAY}/logs?limit=10").json()
    stats = requests.get(f"{GATEWAY}/stats").json()

    print(f"  Total: {stats['total']}  |  Allowed: {GREEN}{stats['allowed']}{RESET}  |  Blocked: {RED}{stats['blocked']}{RESET}\n")
    for entry in reversed(logs[:7]):
        verdict = f"{GREEN}✓{RESET}" if entry["allowed"] else f"{RED}✗{RESET}"
        vio = f"  [{', '.join(entry['violations'])}]" if entry['violations'] else ""
        print(f"  {verdict} {entry['agent_id']:<22} {entry['action']:<12} {entry['ticker'] or '—':<6}{vio}")

    print(f"\n{BOLD}{'═'*60}{RESET}")
    print(f"  Demo complete. {GREEN}This is your winning moment.{RESET}")
    print(f"{'═'*60}\n")


if __name__ == "__main__":
    main()
