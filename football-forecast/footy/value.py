"""Finding bets worth making, and sizing them.

Three rules drive this module:

1. **A positive edge is not a bet.**  Model error, stale prices and the margin
   you cannot see all eat into a thin edge, so a selection has to clear an
   explicit threshold on *both* expected value and probability edge before it
   is flagged.  The thresholds are yours to set; the defaults are deliberately
   not zero.
2. **Stake with fractional Kelly.**  Full Kelly is optimal only if your
   probabilities are exactly right, which they are not.  A quarter to a half
   of Kelly gives up little growth for a large reduction in variance.
3. **Legs from the same match are not independent.**  Multiplying them is the
   most common way to turn a modest edge into a guaranteed loss.  This module
   will not do it: same-match legs are either priced exactly off the shared
   scoreline matrix, or the parlay is refused.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Mapping, Optional, Sequence

import numpy as np

from .markets import Selection
from .odds import remove_overround
from .types import BookOdds


@dataclass
class ValueConfig:
    """Thresholds and staking policy."""

    min_ev: float = 0.03
    min_prob_edge: float = 0.02
    kelly_fraction: float = 0.25
    max_stake_fraction: float = 0.05
    max_total_stake_fraction: float = 0.25
    min_odds: float = 1.30
    max_odds: float = 15.0
    max_overround: float = 0.08
    devig_method: str = "shin"
    bankroll: float = 1000.0
    allow_push_markets: bool = True

    def __post_init__(self) -> None:
        if not 0 < self.kelly_fraction <= 1:
            raise ValueError("kelly_fraction must be in (0, 1]; 0.25-0.5 is the sane range")
        if self.min_ev < 0 or self.min_prob_edge < 0:
            raise ValueError("thresholds must be non-negative")


@dataclass
class ValueBet:
    match_id: str
    market: str
    selection: str
    odds: float
    model_prob: float
    market_prob: float
    edge: float
    ev: float
    kelly_full: float
    kelly_fraction_used: float
    stake: float
    overround: float
    has_push: bool = False
    home: str = ""
    away: str = ""
    competition: str = ""

    @property
    def fair_odds(self) -> float:
        return 1.0 / self.model_prob if self.model_prob > 0 else float("inf")

    def as_row(self) -> dict[str, object]:
        return {
            "match": f"{self.home} v {self.away}" if self.home else self.match_id,
            "competition": self.competition,
            "market": self.market,
            "selection": self.selection,
            "odds": round(self.odds, 3),
            "fair_odds": round(self.fair_odds, 3),
            "model_prob": round(self.model_prob, 4),
            "market_prob": round(self.market_prob, 4),
            "edge": round(self.edge, 4),
            "ev": round(self.ev, 4),
            "stake": round(self.stake, 2),
        }


def kelly_stake(
    win_prob: float, lose_prob: float, odds: float, fraction: float = 0.25, cap: float = 1.0
) -> tuple[float, float]:
    """Full and fractional Kelly for a bet that may push.

    With push probability ``1 - win - lose`` the growth-optimal fraction is::

        f* = (p_win * (o - 1) - p_lose) / ((o - 1) * (p_win + p_lose))

    which reduces to the textbook ``(po - 1) / (o - 1)`` when nothing can push.
    Negative values mean no bet rather than a lay.
    """
    b = odds - 1.0
    live = win_prob + lose_prob
    if b <= 0 or live <= 0:
        return 0.0, 0.0
    full = (win_prob * b - lose_prob) / (b * live)
    if full <= 0:
        return 0.0, 0.0
    return full, min(full * fraction, cap)


def find_value_bets(
    board: Mapping[str, Mapping[str, Selection]],
    book: BookOdds,
    config: Optional[ValueConfig] = None,
    forecast=None,
) -> list[ValueBet]:
    """Compare a priced board against a bookmaker's book.

    Only markets the bookmaker quotes *completely* are considered, because the
    overround cannot be identified from a partial book -- and an un-de-vigged
    comparison would manufacture edges that do not exist.
    """
    config = config or ValueConfig()
    bets: list[ValueBet] = []
    meta = {
        "home": getattr(forecast, "home", ""),
        "away": getattr(forecast, "away", ""),
        "competition": getattr(forecast, "competition", ""),
    }

    for market, quoted in book.markets().items():
        model_sels = board.get(market)
        if not model_sels or len(quoted) < 2:
            continue
        if not set(quoted).issubset(model_sels):
            continue  # book quotes something we did not price; skip rather than guess

        try:
            devig = remove_overround(quoted, method=config.devig_method)
        except ValueError:
            continue
        if devig.overround > config.max_overround:
            continue

        for selection, odds in quoted.items():
            sel = model_sels[selection]
            if sel.has_push and not config.allow_push_markets:
                continue
            if not config.min_odds <= odds <= config.max_odds:
                continue

            model_p = sel.fair_probability
            market_p = devig.probabilities[selection]
            edge = model_p - market_p
            ev = sel.expected_value(odds)

            if ev < config.min_ev or edge < config.min_prob_edge:
                continue

            full, frac = kelly_stake(
                sel.win_prob, sel.lose_prob, odds,
                fraction=config.kelly_fraction, cap=config.max_stake_fraction,
            )
            if frac <= 0:
                continue

            bets.append(
                ValueBet(
                    match_id=book.match_id, market=market, selection=selection, odds=float(odds),
                    model_prob=model_p, market_prob=market_p, edge=edge, ev=ev,
                    kelly_full=full, kelly_fraction_used=frac,
                    stake=frac * config.bankroll, overround=devig.overround,
                    has_push=sel.has_push, **meta,
                )
            )

    bets.sort(key=lambda b: -b.ev)
    return bets


def apply_bankroll_cap(bets: Sequence[ValueBet], config: ValueConfig) -> list[ValueBet]:
    """Scale a simultaneous slate down so total exposure respects the cap.

    Kelly fractions are derived one bet at a time; firing twenty of them on the
    same afternoon is not what Kelly sized you for.
    """
    total = sum(b.stake for b in bets)
    limit = config.max_total_stake_fraction * config.bankroll
    if total <= limit or total <= 0:
        return list(bets)
    scale = limit / total
    for b in bets:
        b.stake *= scale
        b.kelly_fraction_used *= scale
    return list(bets)


# --------------------------------------------------------------------------
# Parlays
# --------------------------------------------------------------------------


@dataclass
class ParlayLeg:
    match_id: str
    market: str
    selection: str
    odds: float


@dataclass
class ParlayEvaluation:
    legs: list[ParlayLeg]
    combined_odds: float
    joint_prob: float
    naive_independent_prob: float
    ev: float
    kelly_full: float
    stake: float
    correlated_groups: list[list[ParlayLeg]] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    priced: bool = True

    @property
    def correlation_factor(self) -> float:
        """Exact joint divided by the naive independent product.

        Above 1 means the legs reinforce each other (the naive number
        *understates* the parlay); below 1 means they fight, and the naive
        number is the dangerous kind of wrong -- it overstates your chances.
        """
        if self.naive_independent_prob <= 0:
            return float("nan")
        return self.joint_prob / self.naive_independent_prob


def evaluate_parlay(
    legs: Sequence[ParlayLeg],
    boards: Mapping[str, Mapping[str, Mapping[str, Selection]]],
    forecasts: Mapping[str, object],
    config: Optional[ValueConfig] = None,
    on_correlation: str = "exact",
) -> ParlayEvaluation:
    """Price a parlay, treating same-match legs as the correlated bets they are.

    ``on_correlation``:

    ``exact``
        Compute the true joint probability of same-match legs from that match's
        scoreline matrix.  This is available precisely because every market was
        derived from one distribution.
    ``reject``
        Refuse to price any parlay containing same-match legs.

    In neither mode are same-match legs multiplied together.
    """
    config = config or ValueConfig()
    if on_correlation not in {"exact", "reject"}:
        raise ValueError("on_correlation must be 'exact' or 'reject'")
    if not legs:
        raise ValueError("a parlay needs at least one leg")

    warnings: list[str] = []
    groups: dict[str, list[ParlayLeg]] = {}
    for leg in legs:
        groups.setdefault(leg.match_id, []).append(leg)

    correlated = [g for g in groups.values() if len(g) > 1]
    combined_odds = float(np.prod([leg.odds for leg in legs]))

    def leg_selection(leg: ParlayLeg) -> Selection:
        board = boards.get(leg.match_id)
        if board is None or leg.market not in board or leg.selection not in board[leg.market]:
            raise KeyError(f"no priced selection for {leg.match_id} {leg.market}/{leg.selection}")
        return board[leg.market][leg.selection]

    naive = 1.0
    for leg in legs:
        naive *= leg_selection(leg).fair_probability

    if correlated and on_correlation == "reject":
        names = ", ".join(
            f"{g[0].match_id} ({len(g)} legs)" for g in correlated
        )
        warnings.append(
            f"refused: {len(correlated)} same-match group(s) [{names}] are correlated; "
            "multiplying their probabilities would misprice the parlay"
        )
        return ParlayEvaluation(
            list(legs), combined_odds, float("nan"), naive, float("nan"), 0.0, 0.0,
            correlated, warnings, priced=False,
        )

    joint = 1.0
    for match_id, group in groups.items():
        if len(group) == 1:
            sel = leg_selection(group[0])
            if sel.has_push:
                warnings.append(
                    f"{match_id} {group[0].market}/{group[0].selection} can push; "
                    "a void leg re-prices the whole parlay and is not modelled here"
                )
            joint *= sel.fair_probability
            continue

        forecast = forecasts.get(match_id)
        matrix = getattr(forecast, "matrix", None)
        if matrix is None:
            warnings.append(
                f"refused: {match_id} has {len(group)} correlated legs but no scoreline "
                "matrix is available to price them jointly"
            )
            return ParlayEvaluation(
                list(legs), combined_odds, float("nan"), naive, float("nan"), 0.0, 0.0,
                correlated, warnings, priced=False,
            )

        weights = np.ones_like(matrix, dtype=float)
        for leg in group:
            sel = leg_selection(leg)
            if sel.has_push:
                warnings.append(
                    f"{match_id} {leg.market}/{leg.selection} can push inside a correlated "
                    "group; treating a push as a loss, which is conservative"
                )
            weights *= sel.win_weights
        group_prob = float((matrix * weights).sum())
        warnings.append(
            f"{match_id}: {len(group)} legs from the same match priced jointly "
            f"(exact {group_prob:.4f} vs naive independent "
            f"{float(np.prod([leg_selection(l).fair_probability for l in group])):.4f})"
        )
        joint *= group_prob

    ev = joint * (combined_odds - 1.0) - (1.0 - joint)
    full, frac = kelly_stake(
        joint, 1.0 - joint, combined_odds,
        fraction=config.kelly_fraction, cap=config.max_stake_fraction,
    )
    return ParlayEvaluation(
        legs=list(legs), combined_odds=combined_odds, joint_prob=joint,
        naive_independent_prob=naive, ev=ev, kelly_full=full,
        stake=frac * config.bankroll, correlated_groups=correlated,
        warnings=warnings, priced=True,
    )
