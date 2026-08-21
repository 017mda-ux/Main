"""Turning bookmaker prices into the market's true implied probabilities.

Raw inverse odds sum to more than one; the excess is the overround (vig), and
it has to come out before any comparison with the model is meaningful.  *How*
you take it out matters more than people expect: naive proportional scaling
assumes the margin is spread evenly across selections, which systematically
overstates the fair price of longshots and understates favourites.

Four methods are provided:

``multiplicative``
    Scale every implied probability by the same factor.  Simple, and the right
    default only for tight two-way markets.
``power``
    Solve ``sum(q_i ** k) = 1``.  Applies more margin to longshots.
``shin``
    Shin's (1992) insider-trading model.  Usually the best-behaved choice for
    three-way match odds, and the default here.
``odds_ratio``
    Keeps the odds ratio between fair and quoted prices constant.

All four agree closely on a balanced two-way book and diverge most where it
matters: a 1X2 book with a big favourite and a long-priced away side.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Mapping, Sequence

import numpy as np
from scipy.optimize import brentq

METHODS = ("shin", "power", "multiplicative", "odds_ratio")


@dataclass
class DevigResult:
    """De-vigged probabilities plus enough diagnostics to audit the call."""

    probabilities: dict[str, float]
    overround: float
    method: str
    diagnostics: dict[str, float] = field(default_factory=dict)

    @property
    def fair_odds(self) -> dict[str, float]:
        return {k: (1.0 / p if p > 0 else float("inf")) for k, p in self.probabilities.items()}

    def get(self, selection: str) -> float:
        return self.probabilities[selection]


def _raw(odds: Mapping[str, float]) -> tuple[list[str], np.ndarray]:
    keys = list(odds)
    values = np.array([float(odds[k]) for k in keys])
    if np.any(values <= 1.0) or np.any(~np.isfinite(values)):
        raise ValueError(
            f"decimal odds must all exceed 1.0 and be finite, got {dict(odds)}"
        )
    return keys, 1.0 / values


def _solve(fn, lo: float, hi: float, fallback: float) -> tuple[float, bool]:
    try:
        f_lo, f_hi = fn(lo), fn(hi)
        if f_lo * f_hi > 0:
            return fallback, False
        return float(brentq(fn, lo, hi, xtol=1e-12, maxiter=200)), True
    except (ValueError, RuntimeError):
        return fallback, False


def remove_overround(odds: Mapping[str, float], method: str = "shin") -> DevigResult:
    """Strip the bookmaker margin from one complete market.

    ``odds`` must contain every selection in the market -- de-vigging a partial
    book is meaningless, since the margin is only observable across the full
    set of mutually exclusive outcomes.
    """
    if len(odds) < 2:
        raise ValueError("need at least two selections to identify the overround")
    if method not in METHODS:
        raise ValueError(f"unknown method {method!r}; expected one of {METHODS}")

    keys, q = _raw(odds)
    booksum = float(q.sum())
    diagnostics: dict[str, float] = {"booksum": booksum}

    if booksum <= 1.0:
        # No margin (or a genuine arbitrage): normalising is all that is left.
        probs = q / booksum
        diagnostics["no_margin"] = 1.0
        return DevigResult(
            {k: float(v) for k, v in zip(keys, probs)}, booksum - 1.0, method, diagnostics
        )

    if method == "multiplicative":
        probs = q / booksum

    elif method == "power":
        k, ok = _solve(lambda k: float(np.sum(q**k)) - 1.0, 0.2, 5.0, 1.0)
        probs = q**k if ok else q / booksum
        diagnostics["k"] = k

    elif method == "shin":
        def shin_probs(z: float) -> np.ndarray:
            root = np.sqrt(z * z + 4.0 * (1.0 - z) * q * q / booksum)
            return (root - z) / (2.0 * (1.0 - z))

        z, ok = _solve(lambda z: float(shin_probs(z).sum()) - 1.0, 0.0, 0.9, 0.0)
        probs = shin_probs(z) if ok else q / booksum
        diagnostics["z"] = z

    else:  # odds_ratio
        def or_probs(c: float) -> np.ndarray:
            return q / (c + q - c * q)

        c, ok = _solve(lambda c: float(or_probs(c).sum()) - 1.0, 1e-6, 100.0, 1.0)
        probs = or_probs(c) if ok else q / booksum
        diagnostics["c"] = c

    probs = np.clip(probs, 1e-12, None)
    probs = probs / probs.sum()  # guard against solver slack
    return DevigResult(
        {k: float(v) for k, v in zip(keys, probs)}, booksum - 1.0, method, diagnostics
    )


def devig_book(
    markets: Mapping[str, Mapping[str, float]], method: str = "shin"
) -> dict[str, DevigResult]:
    """De-vig every complete market in a book, skipping ones that are partial."""
    out: dict[str, DevigResult] = {}
    for market, sels in markets.items():
        if len(sels) < 2:
            continue
        try:
            out[market] = remove_overround(sels, method=method)
        except ValueError:
            continue
    return out


def overround(odds: Mapping[str, float] | Sequence[float]) -> float:
    values = odds.values() if isinstance(odds, Mapping) else odds
    return float(sum(1.0 / float(o) for o in values)) - 1.0


def margin_per_selection(odds: Mapping[str, float], method: str = "shin") -> dict[str, float]:
    """How much margin sits on each selection -- useful for spotting a book
    that is only shaded on one side."""
    fair = remove_overround(odds, method=method).probabilities
    return {k: (1.0 / float(odds[k])) - fair[k] for k in odds}
