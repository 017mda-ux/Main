"""Kalshi trading-fee math.

Kalshi charges a taker fee per executed order of:

    fee = ceil_to_cent( rate * contracts * P * (1 - P) )

where P is the execution price in dollars (price_cents / 100) and the
standard rate is 0.07. A few series use a reduced rate (e.g. some index
markets); pass ``rate`` explicitly if you trade those. Maker (resting)
orders are free on most series.

The fee is quadratic in P with its maximum at P = 0.50 — this matters a
lot for EV: an apparent 1c edge at a 50c price is fully consumed by the
~1.75c round-trip-equivalent fee, while the same edge at 90c costs only
~0.63c in fees.
"""

from __future__ import annotations

import math

STANDARD_RATE = 0.07


def fee_cents_exact(price_cents: float, contracts: float = 1, rate: float = STANDARD_RATE) -> float:
    """Unrounded fee in cents. Use this inside EV math to avoid the
    per-order ceiling distorting per-contract expected values."""
    p = price_cents / 100.0
    return rate * contracts * p * (1.0 - p) * 100.0


def fee_cents(price_cents: int, contracts: int = 1, rate: float = STANDARD_RATE) -> int:
    """Actual fee charged for an order, in cents (rounded up to the next
    cent, as Kalshi does per order)."""
    return math.ceil(fee_cents_exact(price_cents, contracts, rate) - 1e-9)


def effective_cost_cents(price_cents: float, rate: float = STANDARD_RATE) -> float:
    """Per-contract all-in cost of taking liquidity at ``price_cents``."""
    return price_cents + fee_cents_exact(price_cents, 1, rate)
