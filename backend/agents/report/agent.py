"""
CapabilityGuard — Report Agent
Logs internally only. Blocked from posting to external URLs.
"""
import requests
import json
import os
import time

GATEWAY_URL = os.getenv("GATEWAY_URL", "http://localhost:8000/validate")


class ReportAgent:
    def __init__(self, token: str):
        self.token = token
        self.agent_id = "report-agent-01"

    def _validate(self, action: str, destination: str = "internal") -> dict:
        resp = requests.post(GATEWAY_URL, json={
            "agent_id": self.agent_id,
            "token": self.token,
            "action": action,
            "destination": destination,
        }, timeout=5)
        resp.raise_for_status()
        return resp.json()

    def log_internally(self, event: dict) -> dict:
        verdict = self._validate("LOG", "internal")
        if not verdict["allowed"]:
            return {"status": "BLOCKED", "reasons": verdict["violations"]}
        # Write to local structured log
        entry = {"timestamp": time.time(), "event": event}
        with open("report_log.jsonl", "a") as f:
            f.write(json.dumps(entry) + "\n")
        return {"status": "OK", "logged": entry}

    def send_external(self, url: str, payload: dict) -> dict:
        """
        Demonstrates unauthorized_destination block.
        Token is scoped to internal — this will always be blocked.
        """
        verdict = self._validate("SEND_DATA", "external")
        if not verdict["allowed"]:
            return {"status": "BLOCKED", "reasons": verdict["violations"],
                    "reason": verdict["reason"]}
        import requests as r
        return r.post(url, json=payload).json()
