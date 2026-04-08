"""
CapabilityGuard — JWT Capability Token mint/decode
Replace JWT_SECRET with a long random string in your .env
"""
import jwt
import time
import os
from dataclasses import dataclass, field
from typing import List

JWT_SECRET = os.getenv("JWT_SECRET", "CHANGE-THIS-SECRET-IN-PRODUCTION-MIN-32-CHARS")
ALGORITHM = "HS256"


@dataclass
class CapabilityToken:
    agent_id: str
    allowed_actions: List[str]   # ["BUY"], ["READ"], ["LOG"]
    ticker_scope: List[str]      # ["AAPL"] or ["*"]
    max_qty: int                 # 0 = unlimited (non-trade agents)
    destination_scope: str       # "internal" or "external"
    expires_in: int = 300        # seconds — 5 min default


def mint_token(token: CapabilityToken) -> str:
    now = time.time()
    payload = {
        "agent_id": token.agent_id,
        "allowed_actions": token.allowed_actions,
        "ticker_scope": token.ticker_scope,
        "max_qty": token.max_qty,
        "destination_scope": token.destination_scope,
        "exp": now + token.expires_in,
        "iat": now,
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=ALGORITHM)


def decode_token(token_str: str) -> dict:
    return jwt.decode(token_str, JWT_SECRET, algorithms=[ALGORITHM])
