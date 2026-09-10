"""A minimal date-indexed float series with the statistics the brief needs.

Deliberately dependency-free: the collectors run in constrained environments
where numpy/pandas may not be installed, and none of this is hot-path.
"""

from __future__ import annotations

import math
from bisect import bisect_left
from dataclasses import dataclass
from datetime import date
from statistics import fmean, pstdev
from typing import Iterable, Sequence


@dataclass
class TimeSeries:
    """Ascending-by-date observations.  Missing values are dropped at parse."""

    key: str
    dates: list[date]
    values: list[float]
    unit: str = "pct"
    label: str = ""
    source: str = ""

    # ---- construction ---------------------------------------------------

    @classmethod
    def from_pairs(
        cls,
        key: str,
        pairs: Iterable[tuple[date, float | None]],
        **kw,
    ) -> "TimeSeries":
        clean = [(d, v) for d, v in pairs if v is not None and not math.isnan(v)]
        clean.sort(key=lambda p: p[0])
        return cls(key, [d for d, _ in clean], [v for _, v in clean], **kw)

    def __len__(self) -> int:
        return len(self.values)

    def __bool__(self) -> bool:
        return bool(self.values)

    # ---- access ---------------------------------------------------------

    @property
    def last(self) -> float | None:
        return self.values[-1] if self.values else None

    @property
    def last_date(self) -> date | None:
        return self.dates[-1] if self.dates else None

    def prior(self, n: int = 1) -> float | None:
        """Value n observations back from the latest."""
        idx = len(self.values) - 1 - n
        return self.values[idx] if idx >= 0 else None

    def asof(self, when: date) -> float | None:
        """Last value at or before `when`."""
        i = bisect_left(self.dates, when)
        if i < len(self.dates) and self.dates[i] == when:
            return self.values[i]
        return self.values[i - 1] if i > 0 else None

    def tail(self, n: int) -> "TimeSeries":
        return TimeSeries(
            self.key, self.dates[-n:], self.values[-n:],
            self.unit, self.label, self.source,
        )

    # ---- differences ----------------------------------------------------

    def change(self, n: int = 1) -> float | None:
        """Absolute change over n observations."""
        p, c = self.prior(n), self.last
        return None if p is None or c is None else c - p

    def pct_change(self, n: int = 1) -> float | None:
        p, c = self.prior(n), self.last
        if p is None or c is None or p == 0:
            return None
        return (c / p - 1.0) * 100.0

    def diffs(self, window: int | None = None) -> list[float]:
        vals = self.values if window is None else self.values[-(window + 1):]
        return [b - a for a, b in zip(vals, vals[1:])]

    # ---- distribution ---------------------------------------------------

    def vol(self, window: int = 252) -> float | None:
        """Standard deviation of first differences — the unit of 'a big move'."""
        d = self.diffs(window)
        if len(d) < 20:
            return None
        s = pstdev(d)
        return s if s > 0 else None

    def zscore(self, n: int = 1, window: int = 252) -> float | None:
        """Today's move expressed in trailing daily standard deviations."""
        chg, sigma = self.change(n), self.vol(window)
        if chg is None or sigma is None:
            return None
        return chg / (sigma * math.sqrt(max(n, 1)))

    def percentile(self, window: int = 504) -> float | None:
        """Where the current level sits in its trailing window, 0–100.

        Ties count as half, so a series with no dispersion lands at the middle
        rather than reading as an all-time low — which would otherwise push
        dead series to the top of the page.
        """
        vals = self.values[-window:]
        if len(vals) < 30 or self.last is None:
            return None
        if max(vals) == min(vals):
            return None          # no dispersion, no information
        below = sum(1 for v in vals if v < self.last)
        ties = sum(1 for v in vals if v == self.last)
        return 100.0 * (below + 0.5 * ties) / len(vals)

    def extreme_since(self, direction: str = "high") -> date | None:
        """Date of the last observation more extreme than the current one.

        Returns None when the current print is the most extreme on record,
        which the renderer reports as 'highest in the sample'.
        """
        cur = self.last
        if cur is None:
            return None
        for d, v in zip(reversed(self.dates[:-1]), reversed(self.values[:-1])):
            if (direction == "high" and v > cur) or (direction == "low" and v < cur):
                return d
        return None

    def streak(self) -> int:
        """Consecutive same-direction observations, signed."""
        d = self.diffs()
        if not d:
            return 0
        sign = 1 if d[-1] > 0 else -1 if d[-1] < 0 else 0
        if sign == 0:
            return 0
        n = 0
        for x in reversed(d):
            if (x > 0 and sign > 0) or (x < 0 and sign < 0):
                n += 1
            else:
                break
        return n * sign

    def sma(self, window: int) -> list[float | None]:
        """Simple moving average aligned to `self.dates`."""
        out: list[float | None] = []
        acc = 0.0
        for i, v in enumerate(self.values):
            acc += v
            if i >= window:
                acc -= self.values[i - window]
            out.append(acc / window if i >= window - 1 else None)
        return out

    def normalized(self, base: float = 100.0) -> list[float]:
        """Index the series to `base` at its first observation."""
        if not self.values or self.values[0] == 0:
            return list(self.values)
        f = base / self.values[0]
        return [v * f for v in self.values]


def align(a: TimeSeries, b: TimeSeries) -> tuple[list[date], list[float], list[float]]:
    """Inner-join two series on date."""
    idx = {d: v for d, v in zip(a.dates, a.values)}
    dates, av, bv = [], [], []
    for d, v in zip(b.dates, b.values):
        if d in idx:
            dates.append(d)
            av.append(idx[d])
            bv.append(v)
    return dates, av, bv


def correlation(xs: Sequence[float], ys: Sequence[float]) -> float | None:
    """Pearson correlation; None when undefined."""
    if len(xs) < 10 or len(xs) != len(ys):
        return None
    mx, my = fmean(xs), fmean(ys)
    num = sum((x - mx) * (y - my) for x, y in zip(xs, ys))
    dx = math.sqrt(sum((x - mx) ** 2 for x in xs))
    dy = math.sqrt(sum((y - my) ** 2 for y in ys))
    if dx == 0 or dy == 0:
        return None
    return num / (dx * dy)
