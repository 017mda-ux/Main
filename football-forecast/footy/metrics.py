"""Scoring rules and calibration.

Profit is a noisy, slow read on whether a model is any good; a few hundred bets
is nowhere near enough to separate skill from variance.  Proper scoring rules
converge far faster because every match contributes information, not just the
ones you bet on.  So the backtest reports Brier, log loss and RPS alongside
profit, and -- more importantly -- reports them for the *market* too.  The
market's de-vigged closing line is the benchmark that matters.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Mapping, Sequence

import numpy as np

OUTCOMES = ("H", "D", "A")
_EPS = 1e-15


def _stack(probs: Sequence[Mapping[str, float]], outcomes: Sequence[str]) -> tuple[np.ndarray, np.ndarray]:
    if len(probs) != len(outcomes):
        raise ValueError("probabilities and outcomes must be the same length")
    if not probs:
        raise ValueError("nothing to score")
    p = np.array([[row.get(k, 0.0) for k in OUTCOMES] for row in probs], dtype=float)
    p = np.clip(p, _EPS, None)
    p = p / p.sum(axis=1, keepdims=True)
    y = np.zeros_like(p)
    for i, res in enumerate(outcomes):
        y[i, OUTCOMES.index(res)] = 1.0
    return p, y


def brier_score(probs: Sequence[Mapping[str, float]], outcomes: Sequence[str]) -> float:
    """Multiclass Brier score: mean squared error over the outcome vector.

    Range 0 (perfect) to 2 (confidently wrong).  An uninformative 1/3-1/3-1/3
    forecast scores 0.667.
    """
    p, y = _stack(probs, outcomes)
    return float(np.mean(np.sum((p - y) ** 2, axis=1)))


def log_loss(probs: Sequence[Mapping[str, float]], outcomes: Sequence[str]) -> float:
    """Mean negative log likelihood.  Punishes confident mistakes hardest,
    which is exactly the failure mode that empties a bankroll."""
    p, y = _stack(probs, outcomes)
    return float(-np.mean(np.sum(y * np.log(p), axis=1)))


def ranked_probability_score(
    probs: Sequence[Mapping[str, float]], outcomes: Sequence[str]
) -> float:
    """RPS over the ordered H-D-A scale.

    Football's three outcomes are ordered, so calling a home win when the away
    side wins should cost more than calling a draw.  Brier treats those errors
    the same; RPS does not, which is why it is the standard in the literature.
    """
    p, y = _stack(probs, outcomes)
    cp, cy = np.cumsum(p[:, :-1], axis=1), np.cumsum(y[:, :-1], axis=1)
    return float(np.mean(np.sum((cp - cy) ** 2, axis=1) / (len(OUTCOMES) - 1)))


@dataclass
class CalibrationBin:
    lower: float
    upper: float
    count: int
    mean_predicted: float
    observed_rate: float

    @property
    def gap(self) -> float:
        return self.observed_rate - self.mean_predicted


def calibration_table(
    probs: Sequence[Mapping[str, float]], outcomes: Sequence[str], n_bins: int = 10
) -> list[CalibrationBin]:
    """Reliability table over every (outcome, probability) pair.

    Well-calibrated means: of the forecasts you gave a 30% chance, about 30%
    happened.  A model can be sharp and badly calibrated, and a badly
    calibrated model destroys Kelly staking even when it ranks matches well.
    """
    p, y = _stack(probs, outcomes)
    flat_p, flat_y = p.ravel(), y.ravel()
    edges = np.linspace(0.0, 1.0, n_bins + 1)
    idx = np.clip(np.digitize(flat_p, edges[1:-1], right=False), 0, n_bins - 1)

    table: list[CalibrationBin] = []
    for b in range(n_bins):
        mask = idx == b
        n = int(mask.sum())
        if n == 0:
            continue
        table.append(
            CalibrationBin(
                lower=float(edges[b]), upper=float(edges[b + 1]), count=n,
                mean_predicted=float(flat_p[mask].mean()),
                observed_rate=float(flat_y[mask].mean()),
            )
        )
    return table


def expected_calibration_error(
    probs: Sequence[Mapping[str, float]], outcomes: Sequence[str], n_bins: int = 10
) -> float:
    """Count-weighted mean absolute calibration gap."""
    table = calibration_table(probs, outcomes, n_bins)
    total = sum(b.count for b in table)
    if not total:
        return float("nan")
    return sum(b.count * abs(b.gap) for b in table) / total


def score_all(
    probs: Sequence[Mapping[str, float]], outcomes: Sequence[str], n_bins: int = 10
) -> dict[str, float]:
    return {
        "n": float(len(outcomes)),
        "log_loss": log_loss(probs, outcomes),
        "brier": brier_score(probs, outcomes),
        "rps": ranked_probability_score(probs, outcomes),
        "ece": expected_calibration_error(probs, outcomes, n_bins),
    }


def skill_vs_reference(
    model: Mapping[str, float], reference: Mapping[str, float]
) -> dict[str, float]:
    """Model minus reference, where negative means the model is better.

    Also reports a normalised skill score for log loss, the fraction of the
    reference's loss that the model removes.
    """
    out = {f"d_{k}": model[k] - reference[k] for k in ("log_loss", "brier", "rps") if k in model}
    if reference.get("log_loss"):
        out["log_loss_skill"] = 1.0 - model["log_loss"] / reference["log_loss"]
    out["beats_reference"] = float(model.get("log_loss", math.inf) < reference.get("log_loss", -math.inf))
    return out
