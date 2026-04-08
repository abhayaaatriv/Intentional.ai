"""
CapabilityGuard — Alpaca Paper Trading Client
Uses the new official alpaca-py SDK (replaces deprecated alpaca-trade-api).

REPLACE: ALPACA_API_KEY, ALPACA_SECRET_KEY in .env
paper=True automatically routes to https://paper-api.alpaca.markets
"""
import os
from alpaca.trading.client import TradingClient
from alpaca.trading.requests import MarketOrderRequest
from alpaca.trading.enums import OrderSide, TimeInForce

client = TradingClient(
    api_key=os.getenv("ALPACA_API_KEY", "REPLACE_ME"),       # ← REPLACE
    secret_key=os.getenv("ALPACA_SECRET_KEY", "REPLACE_ME"), # ← REPLACE
    paper=True,
)


def place_buy_order(ticker: str, qty: int) -> dict:
    order = client.submit_order(MarketOrderRequest(
        symbol=ticker, qty=qty,
        side=OrderSide.BUY, time_in_force=TimeInForce.GTC,
    ))
    return {"order_id": str(order.id), "status": str(order.status),
            "side": "buy", "qty": qty, "ticker": ticker}


def place_sell_order(ticker: str, qty: int) -> dict:
    order = client.submit_order(MarketOrderRequest(
        symbol=ticker, qty=qty,
        side=OrderSide.SELL, time_in_force=TimeInForce.GTC,
    ))
    return {"order_id": str(order.id), "status": str(order.status),
            "side": "sell", "qty": qty, "ticker": ticker}


def get_positions() -> list:
    return [
        {"ticker": p.symbol, "qty": float(p.qty),
         "market_value": float(p.market_value),
         "unrealized_pl": float(p.unrealized_pl)}
        for p in client.get_all_positions()
    ]


def get_account() -> dict:
    acct = client.get_account()
    return {
        "equity": float(acct.equity),
        "cash": float(acct.cash),
        "buying_power": float(acct.buying_power),
        "portfolio_value": float(acct.portfolio_value),
    }
