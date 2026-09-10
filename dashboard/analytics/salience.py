"""Ranking: what has earned a slot on today's page.

The brief is filtered, not templated.  Every candidate module produces a
`Signal` with a 0–100 score built from independent components; anything under
the floor is dropped, buckets are capped so one asset class cannot crowd out
the rest, and modules that led recent runs are decayed so the page rotates.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date

from ..config import SALIENCE, SalienceConfig, Series
from .movingavg import MACross, cross_salience
from .ratios import Divergence
from .series import TimeSeries


@dataclass
class Signal:
    """One candidate module, with its score decomposed for display."""

    key: str
    label: str
    bucket: str
    score: float
    components: dict[str, float] = field(default_factory=dict)
    # Human-readable reasons, most important first — these become the
    # "why this is here" line under each module heading.
    reasons: list[str] = field(default_factory=list)
    payload: dict = field(default_factory=dict)

    @property
    def lead(self) -> bool:
        return self.score >= SALIENCE.lead_floor

    @property
    def top_reason(self) -> str:
        return self.reasons[0] if self.reasons else ""


def _fmt(value: float, unit: str, decimals: int = 2) -> str:
    if unit == "bp":
        return f"{value * 100:,.0f}bp" if abs(value) < 25 else f"{value:,.0f}bp"
    if unit == "usd":
        return f"${value:,.{decimals}f}"
    if unit == "pct":
        return f"{value:.{decimals}f}%"
    return f"{value:,.{decimals}f}"


def score_series(
    spec: Series,
    ts: TimeSeries,
    cross: MACross | None = None,
    cfg: SalienceConfig = SALIENCE,
) -> Signal:
    """Score a tracked series on move size, level extremity, trend and cross."""
    comps: dict[str, float] = {}
    reasons: list[str] = []

    # --- size of the latest move -----------------------------------------
    z = ts.zscore(1, spec.window)
    if z is not None:
        comps["move"] = min(abs(z) / max(spec.z_notable, 0.1) * 45.0, 100.0)
        if abs(z) >= spec.z_notable:
            chg = ts.change(1)
            direction = "up" if (chg or 0) > 0 else "down"
            reasons.append(
                f"{direction} {abs(z):.1f}σ on the day"
                + (f" ({_fmt(chg, spec.unit, spec.decimals)})" if chg is not None else "")
            )

    # --- how extreme the level is ----------------------------------------
    pct = ts.percentile(spec.window)
    if pct is not None:
        edge = max(pct, 100.0 - pct)          # 50 → middle, 100 → at an extreme
        if edge >= 100.0 - spec.extreme_pctile:
            comps["level"] = (edge - 50.0) * 2.0
            direction = "high" if pct > 50 else "low"
            since = ts.extreme_since("high" if direction == "high" else "low")
            years = round(spec.window / 252, 1)
            if since is None:
                reasons.append(f"highest in the {years}y sample"
                               if direction == "high"
                               else f"lowest in the {years}y sample")
            else:
                reasons.append(f"{direction}est since {since:%b %Y}")
        else:
            comps["level"] = max(edge - 50.0, 0.0)

    # --- persistent run ---------------------------------------------------
    streak = ts.streak()
    if abs(streak) >= 4:
        comps["streak"] = min(abs(streak) * 8.0, 50.0)
        word = "gains" if streak > 0 else "declines"
        reasons.append(f"{abs(streak)} straight sessions of {word}")

    # --- moving-average state --------------------------------------------
    cs = cross_salience(cross)
    if cs > 0:
        comps["cross"] = cs
        if cross is not None and cross.state in ("golden", "death", "approaching"):
            reasons.append(cross.headline)

    score = _combine(comps, cfg)
    return Signal(
        key=spec.key,
        label=spec.label,
        bucket=spec.bucket,
        score=score,
        components=comps,
        reasons=reasons,
        payload={"series": ts, "cross": cross, "spec": spec},
    )


def score_ratio(
    key: str,
    label: str,
    ts: TimeSeries,
    div: Divergence | None,
    div_score: float,
    cross: MACross | None = None,
    cfg: SalienceConfig = SALIENCE,
) -> Signal:
    """Score a derived ratio, weighted toward divergence from its benchmark."""
    comps: dict[str, float] = {}
    reasons: list[str] = []

    if div_score > 0:
        comps["divergence"] = div_score
    if div is not None:
        if div.gap_z is not None and abs(div.gap_z) >= 1.5:
            reasons.append(
                f"gap to {div.versus_key} is {abs(div.gap_z):.1f}σ wide — "
                f"{div.implied_direction}"
            )
        if div.regime_break:
            reasons.append(
                f"1y correlation {div.correlation_1y:+.2f} against "
                f"{div.correlation_5y:+.2f} over the full sample — "
                "the usual relationship has inverted"
            )

    z = ts.zscore(1, 504)
    if z is not None:
        comps["move"] = min(abs(z) / 1.5 * 40.0, 90.0)
        if abs(z) >= 1.5:
            reasons.append(f"ratio moved {abs(z):.1f}σ on the day")

    cs = cross_salience(cross)
    if cs > 0:
        comps["cross"] = cs
        if cross is not None and cross.fired:
            reasons.append(cross.headline)

    pct = ts.percentile(504)
    if pct is not None:
        edge = max(pct, 100.0 - pct)
        comps["level"] = max(edge - 50.0, 0.0)

    return Signal(
        key=key,
        label=label,
        bucket="ratio",
        score=_combine(comps, cfg),
        components=comps,
        reasons=reasons,
        payload={"series": ts, "divergence": div, "cross": cross},
    )


def score_event(
    key: str,
    label: str,
    when: date,
    today: date,
    weight: float = 1.0,
    note: str = "",
    cfg: SalienceConfig = SALIENCE,
) -> Signal:
    """Score a scheduled catalyst by how close it is."""
    days = (when - today).days
    if days < 0:
        return Signal(key, label, "event", 0.0)
    # Same-day and next-day events dominate; decays out to about three weeks.
    proximity = max(0.0, 100.0 - 6.5 * days)
    comps = {"event": proximity * weight}
    reasons = []
    if days == 0:
        reasons.append(f"releases today")
    elif days == 1:
        reasons.append("releases tomorrow")
    else:
        reasons.append(f"in {days} days")
    if note:
        reasons.append(note)
    return Signal(key, label, "event", _combine(comps, cfg), comps, reasons,
                  {"when": when, "days": days})


def _combine(comps: dict[str, float], cfg: SalienceConfig) -> float:
    """Weighted quadratic blend.

    A module with one very strong reason should outrank one with several weak
    ones, so components combine as a weighted root-sum-square rather than a
    mean — but the result is capped so nothing runs away.
    """
    weights = {
        "move": cfg.w_move,
        "level": cfg.w_level,
        "cross": cfg.w_cross,
        "surprise": cfg.w_surprise,
        "event": cfg.w_event,
        "divergence": cfg.w_divergence,
        "streak": cfg.w_streak,
    }
    if not comps:
        return 0.0
    total = sum((weights.get(k, 1.0) * v) ** 2 for k, v in comps.items())
    return min(total ** 0.5, 100.0)


def rank(
    signals: list[Signal],
    previous_leaders: list[list[str]] | None = None,
    cfg: SalienceConfig = SALIENCE,
) -> list[Signal]:
    """Filter, decay repeats, cap per bucket, and order the page.

    `previous_leaders` is the keys that led each of the last few runs, most
    recent first — used so the brief does not open on the same module every
    day when nothing has changed.
    """
    decayed: list[Signal] = []
    for s in signals:
        adj = s.score
        if previous_leaders:
            for age, leaders in enumerate(previous_leaders[: cfg.repeat_lookback]):
                if s.key in leaders:
                    # Most recent appearance decays hardest.
                    factor = cfg.repeat_decay ** (cfg.repeat_lookback - age)
                    adj *= factor
                    break
        if adj >= cfg.floor:
            s.score = adj
            decayed.append(s)

    decayed.sort(key=lambda s: s.score, reverse=True)

    out: list[Signal] = []
    per_bucket: dict[str, int] = {}
    for s in decayed:
        n = per_bucket.get(s.bucket, 0)
        if n >= cfg.max_per_bucket:
            continue
        per_bucket[s.bucket] = n + 1
        out.append(s)
        if len(out) >= cfg.max_modules:
            break
    return out
