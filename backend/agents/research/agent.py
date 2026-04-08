"""
CapabilityGuard — Research Agent (OpenClaw)
Fetches market data. MUST call ArmorClaw gateway before any data access.

REPLACE: GATEWAY_URL if deploying remotely
"""
import requests
import yfinance as yf
import os

GATEWAY_URL = os.getenv("GATEWAY_URL", "http://localhost:8000/validate")


class ResearchAgent:
    def __init__(self, token: str):
        self.token = token
        self.agent_id = "research-agent-01"

    def _validate(self, action: str, ticker: str = "", qty: int = 0) -> dict:
        resp = requests.post(GATEWAY_URL, json={
            "agent_id": self.agent_id,
            "token": self.token,
            "action": action,
            "ticker": ticker,
            "qty": qty,
        }, timeout=5)
        resp.raise_for_status()
        return resp.json()

    def fetch_pe_ratio(self, ticker: str) -> dict:
        verdict = self._validate("READ", ticker)
        if not verdict["allowed"]:
            return {"status": "BLOCKED", "reasons": verdict["violations"],
                    "reason": verdict["reason"]}
        # ── REPLACE yfinance with Alpaca Data API for production ──
        stock = yf.Ticker(ticker)
        info = stock.info
        return {
            "status": "OK",
            "ticker": ticker,
            "pe_ratio": info.get("trailingPE"),
            "price": info.get("currentPrice"),
            "name": info.get("shortName"),
            "market_cap": info.get("marketCap"),
        }

    def check_condition(self, ticker: str, condition: str) -> bool:
        """
        Evaluates a simple condition string like 'PE_RATIO < 25'.
        Extend this for more complex conditions.
        """
        data = self.fetch_pe_ratio(ticker)
        if data.get("status") != "OK":
            return False
        if "PE_RATIO" in condition and data.get("pe_ratio"):
            threshold = float(condition.split("<")[-1].strip())
            return data["pe_ratio"] < threshold
        return False
