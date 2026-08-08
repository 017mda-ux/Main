"""Expected value and Kelly sizing for binary contracts.

Conventions: prices are in cents (0-100), probabilities in [0, 1].
A YES contract bought at price p pays 100 on a yes settlement, 0 otherwise.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from .fees import STANDARD_RATE, fee_cents_exact


def ev_yes_cents(q: float, yes_price_cents: float, rate: float = STANDARD_RATE) -> float:
    """Expected profit in cents per YES contract taken at ``yes_price_cents``,
    net of the (unrounded) taker fee, given model probability ``q`` of yes."""
    fee = fee_cents_exact(yes_price_cents, 1, rate)
    return q * 100.0 - yes_price_cents - fee


def ev_no_cents(q: float, no_price_cents: float, rate: float = STANDARD_RATE) -> float:
    """Expected profit in cents per NO contract taken at ``no_price_cents``."""
    fee = fee_cents_exact(no_price_cents, 1, rate)
    return (1.0 - q) * 100.0 - no_price_cents - fee


def kelly_fraction(q: float, cost_cents: float, payout_cents: float = 100.0) -> float:
    """Kelly-optimal fraction of bankroll for a binary bet.

    ``cost_cents`` is the all-in cost per contract (price + fee),
    ``payout_cents`` the gross payout on a win, ``q`` the win probability.
    Returns 0 when the bet is not +EV.
    """
    net_win = payout_cents - cost_cents
    if net_win <= 0 or cost_cents <= 0:
        return 0.0
    b = net_win / cost_cents  # net odds received on the wager
    f = q - (1.0 - q) / b
    return max(0.0, f)


@dataclass
class TradeDecision:
    """A recommended taker trade on one market."""

    side: str                 # "yes" or "no"
    price_cents: int          # ask you would lift
    prob: float               # model probability that this side wins
    ev_cents: float           # expected profit per contract, net of fees
    kelly: float              # full-Kelly fraction of bankroll
    edge_prob: float          # prob - fee-adjusted breakeven prob

    def stake_contracts(self, bankroll_cents: float, kelly_multiplier: float = 0.25,
                        max_fraction: float = 0.05) -> int:
        """Contracts to buy at fractional Kelly, capped at ``max_fraction``
        of bankroll. Fractional Kelly (default quarter) is deliberate:
        model probabilities are estimates, and full Kelly on an
        overestimated edge is how bankrolls die."""
        frac = min(self.kelly * kelly_multiplier, max_fraction)
        budget = bankroll_cents * frac
        return max(0, int(budget // max(self.price_cents, 1)))


def evaluate_market(q: float, yes_ask_cents: Optional[int], no_ask_cents: Optional[int],
                    rate: float = STANDARD_RATE,
                    min_ev_cents: float = 2.0) -> Optional[TradeDecision]:
    """Pick the better side (if any) to take, given model probability ``q``
    of a yes settlement and the current best asks.

    ``min_ev_cents`` is the minimum net expected profit per contract to act.
    Keep it well above zero: it is the buffer against model error and
    adverse selection, which a raw EV calculation cannot see.
    """
    best: Optional[TradeDecision] = None

    if yes_ask_cents is not None and 0 < yes_ask_cents < 100:
        ev = ev_yes_cents(q, yes_ask_cents, rate)
        if ev >= min_ev_cents:
            cost = yes_ask_cents + fee_cents_exact(yes_ask_cents, 1, rate)
            best = TradeDecision(
                side="yes", price_cents=yes_ask_cents, prob=q, ev_cents=ev,
                kelly=kelly_fraction(q, cost), edge_prob=q - cost / 100.0,
            )

    if no_ask_cents is not None and 0 < no_ask_cents < 100:
        ev = ev_no_cents(q, no_ask_cents, rate)
        if ev >= min_ev_cents and (best is None or ev > best.ev_cents):
            cost = no_ask_cents + fee_cents_exact(no_ask_cents, 1, rate)
            best = TradeDecision(
                side="no", price_cents=no_ask_cents, prob=1.0 - q, ev_cents=ev,
                kelly=kelly_fraction(1.0 - q, cost), edge_prob=(1.0 - q) - cost / 100.0,
            )

    return best
