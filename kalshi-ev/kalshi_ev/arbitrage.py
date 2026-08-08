"""Structural mispricing scanner.

These are the only *model-free* positive-EV trades on Kalshi: they pay
regardless of the outcome, so the only requirements are correct fee math
and actually getting filled on every leg. Three patterns:

1. Buy-all-YES: in a mutually-exclusive, exhaustive event, exactly one
   market settles yes and pays 100. If the sum of best YES asks plus
   fees is under 100, buying one of each locks a profit.
2. Buy-all-NO: in the same structure, n-1 of n markets settle no. If
   the sum of best NO asks plus fees is under (n-1)*100, same deal.
3. Box: in a single market, YES ask + NO ask + fees < 100.

Caveats baked into the output:
- Executable size is the *minimum* ask depth across legs — an arb you
  can only half-fill is a directional bet on the missing legs.
- Exhaustiveness matters: Kalshi range events normally include catch-all
  tails ("X or above"), but verify before treating buy-all-YES as
  risk-free. `assumes_exhaustive` is set on those opportunities.
- These windows are small and close fast; treat sub-cent profits as
  noise, not income.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from .client import Orderbook
from .fees import STANDARD_RATE, fee_cents_exact


@dataclass
class ArbOpportunity:
    kind: str                       # "all_yes" | "all_no" | "box"
    event_ticker: str
    legs: List[Dict[str, Any]]      # [{ticker, side, price_cents, qty_available}]
    cost_cents: float               # per one unit (one contract per leg), incl. fees
    payout_cents: float             # guaranteed payout per unit
    profit_cents: float             # payout - cost, per unit
    max_units: int                  # min depth across legs
    assumes_exhaustive: bool = False

    @property
    def roi(self) -> float:
        return self.profit_cents / self.cost_cents if self.cost_cents else 0.0


def _legs_cost(legs: List[Dict[str, Any]], rate: float) -> float:
    return sum(l["price_cents"] + fee_cents_exact(l["price_cents"], 1, rate) for l in legs)


def scan_event(event: Dict[str, Any], books: Dict[str, Orderbook],
               rate: float = STANDARD_RATE,
               min_profit_cents: float = 1.0) -> List[ArbOpportunity]:
    """Scan one event (with its markets' orderbooks) for structural arbs."""
    out: List[ArbOpportunity] = []
    event_ticker = event.get("event_ticker", "?")
    markets = [m for m in (event.get("markets") or []) if m.get("ticker") in books]
    mutually_exclusive = bool(event.get("mutually_exclusive"))

    # ── box arb per market (works regardless of event structure) ─────
    for m in markets:
        book = books[m["ticker"]]
        ya, na = book.best_yes_ask, book.best_no_ask
        if ya is None or na is None or not (0 < ya < 100 and 0 < na < 100):
            continue
        legs = [
            {"ticker": m["ticker"], "side": "yes", "price_cents": ya,
             "qty_available": book.yes_ask_qty},
            {"ticker": m["ticker"], "side": "no", "price_cents": na,
             "qty_available": book.no_ask_qty},
        ]
        cost = _legs_cost(legs, rate)
        profit = 100.0 - cost
        if profit >= min_profit_cents:
            out.append(ArbOpportunity(
                kind="box", event_ticker=event_ticker, legs=legs,
                cost_cents=cost, payout_cents=100.0, profit_cents=profit,
                max_units=min(l["qty_available"] for l in legs),
            ))

    if not mutually_exclusive or len(markets) < 2:
        return out

    # ── buy-all-YES ──────────────────────────────────────────────────
    yes_legs = []
    for m in markets:
        book = books[m["ticker"]]
        ya = book.best_yes_ask
        if ya is None or not (0 < ya < 100):
            yes_legs = []
            break
        yes_legs.append({"ticker": m["ticker"], "side": "yes",
                         "price_cents": ya, "qty_available": book.yes_ask_qty})
    if yes_legs:
        cost = _legs_cost(yes_legs, rate)
        profit = 100.0 - cost
        if profit >= min_profit_cents:
            out.append(ArbOpportunity(
                kind="all_yes", event_ticker=event_ticker, legs=yes_legs,
                cost_cents=cost, payout_cents=100.0, profit_cents=profit,
                max_units=min(l["qty_available"] for l in yes_legs),
                assumes_exhaustive=True,
            ))

    # ── buy-all-NO ───────────────────────────────────────────────────
    no_legs = []
    for m in markets:
        book = books[m["ticker"]]
        na = book.best_no_ask
        if na is None or not (0 < na < 100):
            no_legs = []
            break
        no_legs.append({"ticker": m["ticker"], "side": "no",
                        "price_cents": na, "qty_available": book.no_ask_qty})
    if no_legs:
        payout = (len(no_legs) - 1) * 100.0
        cost = _legs_cost(no_legs, rate)
        profit = payout - cost
        if profit >= min_profit_cents:
            out.append(ArbOpportunity(
                kind="all_no", event_ticker=event_ticker, legs=no_legs,
                cost_cents=cost, payout_cents=payout, profit_cents=profit,
                max_units=min(l["qty_available"] for l in no_legs),
                assumes_exhaustive=True,
            ))

    return out
