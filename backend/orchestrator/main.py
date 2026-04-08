"""
CapabilityGuard — Orchestrator Agent
Parses user mandate → Intent Graph → mints scoped JWTs for sub-agents.

REPLACE: OPENAI_API_KEY in .env (or swap model= for any OpenAI-compatible API)
"""
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import openai
import json
import os
import sys
import re

sys.path.append(os.path.join(os.path.dirname(__file__), ".."))
from shared.tokens import CapabilityToken, mint_token

# ── CONFIG ──────────────────────────────────────────────────────────────────
openai.api_key = os.getenv("OPENAI_API_KEY", "REPLACE_ME")  # ← REPLACE

app = FastAPI(title="CapabilityGuard Orchestrator", version="1.0.0")
app.add_middleware(
    CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"]
)

# ── SYSTEM PROMPT ────────────────────────────────────────────────────────────
INTENT_SYSTEM = """You are a financial intent parser for a secure trading system.
Given a user mandate, extract and return ONLY valid JSON with this exact schema:

{
  "mandate_summary": "brief summary",
  "allowed_tickers": ["AAPL"],
  "allowed_actions": ["READ", "BUY"],
  "blocked_actions": ["SELL", "SEND_DATA"],
  "max_qty": 10,
  "condition": "PE_RATIO < 25",
  "destination_scope": "internal"
}

Rules:
- allowed_actions: only include READ, BUY, SELL, LOG — no others
- always include LOG in allowed_actions
- always include SEND_DATA in blocked_actions
- destination_scope: always "internal" unless user explicitly says external
- max_qty: extract from mandate or default to 10
- Return ONLY raw JSON. No markdown, no explanation, no backticks."""


# ── MODELS ───────────────────────────────────────────────────────────────────
class MandateRequest(BaseModel):
    mandate: str


class IntentGraph(BaseModel):
    mandate_summary: str
    allowed_tickers: list[str]
    allowed_actions: list[str]
    blocked_actions: list[str]
    max_qty: int
    condition: str
    destination_scope: str


class MintedTokens(BaseModel):
    intent_graph: dict
    tokens: dict[str, str]  # agent_id → JWT string


# ── ENDPOINTS ─────────────────────────────────────────────────────────────────
@app.post("/parse-intent", response_model=IntentGraph)
def parse_intent(req: MandateRequest):
    """
    LLM call → structured IntentGraph JSON.
    Retries once on JSON parse failure.
    REPLACE openai model with your preferred provider.
    """
    for attempt in range(2):
        try:
            resp = openai.chat.completions.create(
                model="gpt-4o-mini",  # ← REPLACE if using different provider
                messages=[
                    {"role": "system", "content": INTENT_SYSTEM},
                    {"role": "user", "content": req.mandate},
                ],
                temperature=0,
            )
            raw = resp.choices[0].message.content.strip()
            # strip any accidental markdown fences
            raw = re.sub(r"```json?\s*|\s*```", "", raw).strip()
            return json.loads(raw)
        except json.JSONDecodeError:
            if attempt == 1:
                raise HTTPException(status_code=422, detail="LLM returned unparseable JSON")
            continue
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))


@app.post("/mint-tokens", response_model=MintedTokens)
def mint_tokens(ig: IntentGraph):
    """
    Given an IntentGraph, mint 3 scoped JWTs:
      - research-agent:  READ only, no trade
      - execution-agent: BUY/SELL per mandate, bounded qty
      - report-agent:    LOG only, internal destination only
    """
    exec_actions = [a for a in ig.allowed_actions if a in ("BUY", "SELL")]

    research_tok = CapabilityToken(
        agent_id="research-agent-01",
        allowed_actions=["READ"],
        ticker_scope=ig.allowed_tickers,
        max_qty=0,
        destination_scope="internal",
    )
    execution_tok = CapabilityToken(
        agent_id="execution-agent-01",
        allowed_actions=exec_actions or ["BUY"],
        ticker_scope=ig.allowed_tickers,
        max_qty=ig.max_qty,
        destination_scope="internal",
    )
    report_tok = CapabilityToken(
        agent_id="report-agent-01",
        allowed_actions=["LOG"],
        ticker_scope=["*"],
        max_qty=0,
        destination_scope="internal",
    )

    return MintedTokens(
        intent_graph=ig.dict(),
        tokens={
            "research-agent-01": mint_token(research_tok),
            "execution-agent-01": mint_token(execution_tok),
            "report-agent-01": mint_token(report_tok),
        },
    )


@app.post("/run-mandate")
def run_mandate(req: MandateRequest):
    """
    Convenience: parse + mint in one call.
    Returns intent_graph + all three tokens.
    """
    ig = parse_intent(req)
    return mint_tokens(ig)


@app.get("/health")
def health():
    return {"status": "ok", "service": "orchestrator"}
