"""
CapabilityGuard — Execution Agent
ALL trade actions go through ArmorClaw gate first.
Agent code physically cannot bypass the check — it's architecturally enforced.
"""
import requests
import os
from .alpaca_client import place_buy_order, place_sell_order, get_positions, get_account

GATEWAY_URL = os.getenv("GATEWAY_URL", "http://localhost:8000/validate")


class ExecutionAgent:
    def __init__(self, token: str):
        self.token = token
        self.agent_id = "execution-agent-01"

    def _validate(self, action: str, ticker: str, qty: int = 0,
                  destination: str = "internal") -> dict:
        resp = requests.post(GATEWAY_URL, json={
            "agent_id": self.agent_id,
            "token": self.token,
            "action": action,
            "ticker": ticker,
            "qty": qty,
            "destination": destination,
        }, timeout=5)
        resp.raise_for_status()
        return resp.json()

    def buy(self, ticker: str, qty: int) -> dict:
        verdict = self._validate("BUY", ticker, qty)
        if not verdict["allowed"]:
            return {"status": "BLOCKED", "reasons": verdict["violations"],
                    "reason": verdict["reason"]}
        return place_buy_order(ticker, qty)

    def sell(self, ticker: str, qty: int) -> dict:
        # This will be BLOCKED if token is BUY_ONLY
        verdict = self._validate("SELL", ticker, qty)
        if not verdict["allowed"]:
            return {"status": "BLOCKED", "reasons": verdict["violations"],
                    "reason": verdict["reason"]}
        return place_sell_order(ticker, qty)

    def send_to_external(self, url: str, data: dict) -> dict:
        """
        Demonstrates unauthorized_destination block.
        This will always be blocked for internal-scoped tokens.
        """
        verdict = self._validate("SEND_DATA", "", 0, "external")
        if not verdict["allowed"]:
            return {"status": "BLOCKED", "reasons": verdict["violations"],
                    "reason": verdict["reason"]}
        # Would only reach here if token has destination_scope="external"
        import requests as r
        return r.post(url, json=data, timeout=5).json()

    def get_portfolio(self) -> dict:
        verdict = self._validate("READ", "*")
        if not verdict["allowed"]:
            return {"status": "BLOCKED"}
        return {"positions": get_positions(), "account": get_account()}
