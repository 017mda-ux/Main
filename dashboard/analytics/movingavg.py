"""Moving-average cross detection.

Reports three states worth a slot on the page: a cross that has just fired, a
cross that is closing and near, and a spread that has stretched to an extreme.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date

from ..config import MA_FAST, MA_PROXIMITY_PCT, MA_SLOW
from .series import TimeSeries


@dataclass
class MACross:
    key: str
    label: str
    fast: float
    slow: float
    fast_window: int
    slow_window: int
    gap_pct: float               # (fast - slow) / |slow| * 100
    state: str                   # golden | death | approaching | above | below
    direction: str               # closing | widening
    days_since_cross: int | None
    crossed_on: date | None
    price: float | None
    price_vs_slow_pct: float | None

    @property
    def fired(self) -> bool:
        return self.state in ("golden", "death")

    @property
    def headline(self) -> str:
        w = f"{self.fast_window}/{self.slow_window}"
        if self.state == "golden":
            return f"{self.label}: {w} golden cross"
        if self.state == "death":
            return f"{self.label}: {w} death cross"
        if self.state == "approaching":
            side = "above" if self.gap_pct > 0 else "below"
            return (f"{self.label}: {w} closing — fast {abs(self.gap_pct):.2f}% "
                    f"{side} slow")
        return f"{self.label}: fast {self.gap_pct:+.2f}% vs slow"


def ma_state(
    ts: TimeSeries,
    fast_window: int = MA_FAST,
    slow_window: int = MA_SLOW,
    proximity_pct: float = MA_PROXIMITY_PCT,
) -> MACross | None:
    """Classify where a series sits against its own moving averages."""
    if len(ts) < slow_window + 5:
        return None

    fast_ma = ts.sma(fast_window)
    slow_ma = ts.sma(slow_window)

    pairs = [
        (d, f, s)
        for d, f, s in zip(ts.dates, fast_ma, slow_ma)
        if f is not None and s is not None
    ]
    if len(pairs) < 5:
        return None

    _, f_now, s_now = pairs[-1]
    if s_now == 0:
        return None
    gap_pct = (f_now - s_now) / abs(s_now) * 100.0

    # Walk back to find the most recent sign change of (fast - slow).
    crossed_on: date | None = None
    days_since: int | None = None
    sign_now = 1 if f_now > s_now else -1
    for i in range(len(pairs) - 2, -1, -1):
        d, f, s = pairs[i]
        sign = 1 if f > s else -1
        if sign != sign_now:
            crossed_on = pairs[i + 1][0]
            days_since = len(pairs) - 1 - (i + 1)
            break

    _, f_prev, s_prev = pairs[-2]
    prev_gap = abs(f_prev - s_prev) / abs(s_prev) * 100.0 if s_prev else 0.0
    direction = "closing" if abs(gap_pct) < prev_gap else "widening"

    if days_since is not None and days_since <= 5:
        state = "golden" if sign_now > 0 else "death"
    elif abs(gap_pct) <= proximity_pct and direction == "closing":
        state = "approaching"
    else:
        state = "above" if sign_now > 0 else "below"

    price = ts.last
    price_vs_slow = (
        (price - s_now) / abs(s_now) * 100.0 if price is not None and s_now else None
    )

    return MACross(
        key=ts.key,
        label=ts.label or ts.key,
        fast=f_now,
        slow=s_now,
        fast_window=fast_window,
        slow_window=slow_window,
        gap_pct=gap_pct,
        state=state,
        direction=direction,
        days_since_cross=days_since,
        crossed_on=crossed_on,
        price=price,
        price_vs_slow_pct=price_vs_slow,
    )


def cross_salience(mc: MACross | None) -> float:
    """0–100 contribution of a moving-average state to a module's score."""
    if mc is None:
        return 0.0
    if mc.state in ("golden", "death"):
        # Freshest crosses matter most; decays over the first two weeks.
        age = mc.days_since_cross or 0
        return max(55.0, 95.0 - 4.0 * age)
    if mc.state == "approaching":
        # Closer and closing → higher.
        closeness = 1.0 - min(abs(mc.gap_pct) / MA_PROXIMITY_PCT, 1.0)
        return 30.0 + 40.0 * closeness
    # A stretched trend is mildly interesting.
    return min(abs(mc.gap_pct) * 2.0, 25.0)
