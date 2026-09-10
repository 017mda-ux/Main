"""Cross-asset ratios and the divergence test that decides when one matters.

The interesting event is rarely the ratio's level.  It is the ratio parting
company with the thing it normally tracks — copper/gold against the 10-year
being the canonical case.
"""

from __future__ import annotations

from dataclasses import dataclass

from ..config import Ratio
from .series import TimeSeries, align, correlation


def build_ratio(spec: Ratio, store: dict[str, TimeSeries]) -> TimeSeries | None:
    """Compute a ratio series from two stored series."""
    num, den = store.get(spec.numerator), store.get(spec.denominator)
    if not num or not den:
        return None

    dates, nv, dv = align(num, den)
    pairs = [
        (d, (n / d_) * spec.scale)
        for d, n, d_ in zip(dates, nv, dv)
        if d_ not in (0, None)
    ]
    if len(pairs) < 30:
        return None

    return TimeSeries.from_pairs(
        spec.key, pairs, unit="ratio", label=spec.label, source="derived",
    )


@dataclass
class Divergence:
    """How far a ratio has drifted from the series it normally tracks."""

    ratio_key: str
    versus_key: str
    ratio_last: float
    versus_last: float
    gap: float                # ratio_last - versus_last, on the scaled axis
    gap_z: float | None       # gap in std devs of its own trailing history
    correlation_1y: float | None
    correlation_5y: float | None
    regime_break: bool        # short-run correlation has flipped sign

    @property
    def implied_direction(self) -> str:
        """Which side the historical relationship says should move."""
        if self.gap > 0:
            return f"{self.versus_key} low vs {self.ratio_key}"
        return f"{self.versus_key} high vs {self.ratio_key}"


def divergence_score(
    ratio: TimeSeries,
    versus: TimeSeries,
    window_short: int = 252,
) -> tuple[float, Divergence | None]:
    """Score 0–100 for how notable a ratio-vs-benchmark gap currently is."""
    dates, rv, vv = align(ratio, versus)
    if len(dates) < 120:
        return 0.0, None

    gaps = [r - v for r, v in zip(rv, vv)]
    gap_now = gaps[-1]

    hist = gaps[-window_short * 2:] if len(gaps) > 60 else gaps
    mean = sum(hist) / len(hist)
    var = sum((g - mean) ** 2 for g in hist) / len(hist)
    sd = var ** 0.5
    gap_z = (gap_now - mean) / sd if sd > 0 else None

    corr_1y = correlation(rv[-window_short:], vv[-window_short:])
    corr_5y = correlation(rv, vv)

    regime_break = bool(
        corr_1y is not None
        and corr_5y is not None
        and corr_5y > 0.2
        and corr_1y < -0.1
    )

    div = Divergence(
        ratio_key=ratio.key,
        versus_key=versus.key,
        ratio_last=rv[-1],
        versus_last=vv[-1],
        gap=gap_now,
        gap_z=gap_z,
        correlation_1y=corr_1y,
        correlation_5y=corr_5y,
        regime_break=regime_break,
    )

    score = 0.0
    if gap_z is not None:
        score += min(abs(gap_z) * 28.0, 75.0)
    if regime_break:
        score += 25.0
    return min(score, 100.0), div
