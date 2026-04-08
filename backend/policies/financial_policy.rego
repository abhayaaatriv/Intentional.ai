package financial

import rego.v1

default allow := false

# ── ALLOW: all four gates must pass ──────────────────────────────────────────
allow if {
    action_permitted
    ticker_allowed
    qty_within_limit
    destination_allowed
}

# ── GATE 1: action must be in token's allowed_actions ────────────────────────
action_permitted if {
    input.action in input.token.allowed_actions
}

# ── GATE 2: ticker must match token scope ────────────────────────────────────
ticker_allowed if {
    input.token.ticker_scope[_] == "*"
}

ticker_allowed if {
    input.token.ticker_scope[_] == input.ticker
}

# ── GATE 3: quantity within token limit (0 = unlimited) ──────────────────────
qty_within_limit if {
    input.token.max_qty == 0
}

qty_within_limit if {
    input.qty <= input.token.max_qty
}

# ── GATE 4: data destination must match token scope ──────────────────────────
destination_allowed if {
    input.action != "SEND_DATA"
}

destination_allowed if {
    input.action == "SEND_DATA"
    input.destination == input.token.destination_scope
}

# ── VIOLATION REASONS (surfaced in audit log) ─────────────────────────────────
violation contains "action_not_permitted" if {
    not action_permitted
}

violation contains "ticker_out_of_scope" if {
    action_permitted
    not ticker_allowed
}

violation contains "qty_exceeded" if {
    action_permitted
    ticker_allowed
    not qty_within_limit
}

violation contains "unauthorized_destination" if {
    input.action == "SEND_DATA"
    input.destination != input.token.destination_scope
}
