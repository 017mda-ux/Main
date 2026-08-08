"""Market calibration model (favorite-longshot correction).

The single most robust, documented inefficiency in prediction markets is
miscalibration at the extremes: longshots tend to trade above their true
probability and near-certainties below it (fee structure and lottery
preference both push this way). If that holds in the data, prices need to
be *shrunk* or *stretched* in log-odds space before they are treated as
probabilities.

We fit a two-parameter Platt-style map on settled markets:

    q = sigmoid( a + b * logit(p) )

where p is the market price (as a probability) at some fixed horizon
before settlement and q is the calibrated probability. b < 1 means the
market is overconfident (longshot bias exists → fade the extremes);
b > 1 means underconfident (buy the favorites). a captures any
systematic yes/no skew.

The fit is a plain 2-parameter logistic regression, solved by
Newton-Raphson — no dependencies needed.

Everything here is honest only if the input prices come from *before*
settlement was knowable (see data.py, which snapshots prices at a fixed
horizon via candlesticks — never use last_price of a settled market, it
is ~0 or ~100 by construction).
"""

from __future__ import annotations

import json
import math
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, List, Sequence, Tuple

_EPS = 0.005  # clip prices into [0.5c, 99.5c] as probabilities


def _logit(p: float) -> float:
    p = min(max(p, _EPS), 1.0 - _EPS)
    return math.log(p / (1.0 - p))


def _sigmoid(z: float) -> float:
    if z >= 0:
        return 1.0 / (1.0 + math.exp(-z))
    ez = math.exp(z)
    return ez / (1.0 + ez)


@dataclass
class CalibrationModel:
    a: float = 0.0
    b: float = 1.0
    n_train: int = 0

    def predict(self, price_cents: float) -> float:
        """Calibrated probability of yes, given a market price in cents."""
        return _sigmoid(self.a + self.b * _logit(price_cents / 100.0))

    # ── fitting ──────────────────────────────────────────────────────

    @classmethod
    def fit(cls, prices_cents: Sequence[float], outcomes: Sequence[int],
            max_iter: int = 100, ridge: float = 1e-6) -> "CalibrationModel":
        """Maximum-likelihood fit of (a, b) on (price, outcome) pairs.
        ``outcomes`` are 1 for yes settlements, 0 for no."""
        xs = [_logit(p / 100.0) for p in prices_cents]
        ys = list(outcomes)
        if len(xs) != len(ys) or len(xs) < 10:
            raise ValueError("need at least 10 (price, outcome) pairs")

        a, b = 0.0, 1.0
        for _ in range(max_iter):
            g0 = g1 = 0.0
            h00 = h01 = h11 = 0.0
            for x, y in zip(xs, ys):
                mu = _sigmoid(a + b * x)
                w = mu * (1.0 - mu)
                r = y - mu
                g0 += r
                g1 += r * x
                h00 += w
                h01 += w * x
                h11 += w * x * x
            h00 += ridge
            h11 += ridge
            det = h00 * h11 - h01 * h01
            if det <= 0:
                break
            da = (h11 * g0 - h01 * g1) / det
            db = (-h01 * g0 + h00 * g1) / det
            a += da
            b += db
            if abs(da) + abs(db) < 1e-10:
                break
        return cls(a=a, b=b, n_train=len(xs))

    # ── persistence ──────────────────────────────────────────────────

    def save(self, path: str | Path) -> None:
        Path(path).write_text(json.dumps(
            {"a": self.a, "b": self.b, "n_train": self.n_train}, indent=2))

    @classmethod
    def load(cls, path: str | Path) -> "CalibrationModel":
        d = json.loads(Path(path).read_text())
        return cls(a=d["a"], b=d["b"], n_train=d.get("n_train", 0))


# ── diagnostics ──────────────────────────────────────────────────────

def brier_score(probs: Iterable[float], outcomes: Iterable[int]) -> float:
    pairs = list(zip(probs, outcomes))
    if not pairs:
        return float("nan")
    return sum((p - y) ** 2 for p, y in pairs) / len(pairs)


def reliability_table(prices_cents: Sequence[float], outcomes: Sequence[int],
                      n_bins: int = 10) -> List[Tuple[str, int, float, float]]:
    """(bin label, count, mean price, empirical yes rate) per price decile.
    The gap between the last two columns is the raw edge before fees."""
    rows = []
    for i in range(n_bins):
        lo, hi = 100.0 * i / n_bins, 100.0 * (i + 1) / n_bins
        bucket = [(p, y) for p, y in zip(prices_cents, outcomes) if lo <= p < hi]
        if not bucket:
            continue
        mean_p = sum(p for p, _ in bucket) / len(bucket)
        rate = sum(y for _, y in bucket) / len(bucket)
        rows.append((f"{int(lo)}-{int(hi)}c", len(bucket), mean_p, rate * 100.0))
    return rows
