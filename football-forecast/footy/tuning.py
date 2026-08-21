"""Tuning the half-life and the xG/goals blend.

Both are genuine free parameters, and both are usually set by folklore ("half a
season", "just use xG").  They are cheap to choose properly: walk forward
through the data, score out-of-sample forecasts with a proper scoring rule, and
take the grid point that minimises it.

Tuning targets log loss rather than profit on purpose.  Profit over a few
hundred bets is far too noisy to rank configurations, and optimising it
directly is an efficient way to fit the noise.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import timedelta
from typing import Optional, Sequence

import numpy as np

from . import metrics
from .dixoncoles import DixonColesConfig, fit_dixon_coles
from .types import Match

DEFAULT_HALF_LIVES: tuple[float, ...] = (60.0, 90.0, 120.0, 180.0, 250.0, 365.0, 550.0)
DEFAULT_XG_WEIGHTS: tuple[float, ...] = (0.0, 0.25, 0.5, 0.75, 1.0)


@dataclass
class GridPoint:
    half_life_days: float
    xg_weight: float
    log_loss: float
    brier: float
    rps: float
    n_scored: int

    def as_row(self) -> dict[str, float]:
        return {
            "half_life": self.half_life_days,
            "xg_weight": self.xg_weight,
            "log_loss": round(self.log_loss, 5),
            "brier": round(self.brier, 5),
            "rps": round(self.rps, 5),
            "n": self.n_scored,
        }


@dataclass
class TuningResult:
    best: GridPoint
    grid: list[GridPoint] = field(default_factory=list)
    criterion: str = "log_loss"

    @property
    def best_config_kwargs(self) -> dict[str, float]:
        return {"half_life_days": self.best.half_life_days, "xg_weight": self.best.xg_weight}

    def table(self) -> str:
        header = f"{'half_life':>10}{'xg_w':>7}{'log_loss':>11}{'brier':>9}{'rps':>9}{'n':>7}"
        rows = [header, "-" * len(header)]
        for gp in sorted(self.grid, key=lambda g: getattr(g, self.criterion)):
            marker = " *" if gp is self.best else ""
            rows.append(
                f"{gp.half_life_days:>10.0f}{gp.xg_weight:>7.2f}{gp.log_loss:>11.5f}"
                f"{gp.brier:>9.5f}{gp.rps:>9.5f}{gp.n_scored:>7d}{marker}"
            )
        return "\n".join(rows)


def walk_forward_score(
    matches: Sequence[Match],
    config: DixonColesConfig,
    train_window_days: Optional[int] = 900,
    min_train_matches: int = 250,
    refit_every_days: int = 14,
    warmup_days: int = 0,
) -> dict[str, float]:
    """Score out-of-sample 1X2 forecasts with no odds involved.

    This measures the model alone: whether the parameters describe football,
    not whether they beat a bookmaker.  Tune here, then check the market
    comparison in :func:`footy.backtest.run_backtest`.
    """
    played = sorted((m for m in matches if m.played), key=lambda m: m.date)
    if not played:
        raise ValueError("no played matches supplied")

    probs: list[dict[str, float]] = []
    outcomes: list[str] = []
    model = None
    last_fit = None
    start_after = played[0].date + timedelta(days=warmup_days)

    by_date: dict = {}
    for m in played:
        by_date.setdefault(m.date, []).append(m)

    for day in sorted(by_date):
        if day <= start_after:
            continue
        history = [m for m in played if m.date < day]
        if train_window_days:
            history = [m for m in history if m.date >= day - timedelta(days=train_window_days)]
        if len(history) < min_train_matches:
            continue
        if model is None or last_fit is None or (day - last_fit).days >= refit_every_days:
            try:
                model = fit_dixon_coles(history, as_of=day, config=config)
            except (ValueError, FloatingPointError):
                continue
            last_fit = day

        for match in by_date[day]:
            try:
                forecast = model.predict_match(match)
            except KeyError:
                continue
            probs.append(forecast.outcome_probabilities())
            outcomes.append(match.result)

    if not outcomes:
        raise ValueError(
            "nothing was scored -- the training window never filled; lower "
            "min_train_matches or supply more history"
        )
    return metrics.score_all(probs, outcomes)


def tune(
    matches: Sequence[Match],
    half_lives: Sequence[float] = DEFAULT_HALF_LIVES,
    xg_weights: Sequence[float] = DEFAULT_XG_WEIGHTS,
    base_config: Optional[DixonColesConfig] = None,
    criterion: str = "log_loss",
    **walk_kwargs,
) -> TuningResult:
    """Grid-search half-life and xG blend against out-of-sample score."""
    if criterion not in {"log_loss", "brier", "rps"}:
        raise ValueError("criterion must be one of log_loss, brier, rps")
    base = base_config or DixonColesConfig()

    grid: list[GridPoint] = []
    for hl in half_lives:
        for w in xg_weights:
            cfg = DixonColesConfig(
                **{**base.__dict__, "half_life_days": float(hl), "xg_weight": float(w)}
            )
            try:
                scores = walk_forward_score(matches, cfg, **walk_kwargs)
            except ValueError:
                continue
            grid.append(
                GridPoint(
                    half_life_days=float(hl), xg_weight=float(w),
                    log_loss=scores["log_loss"], brier=scores["brier"],
                    rps=scores["rps"], n_scored=int(scores["n"]),
                )
            )

    if not grid:
        raise ValueError("no grid point could be evaluated")
    best = min(grid, key=lambda g: getattr(g, criterion))
    return TuningResult(best=best, grid=grid, criterion=criterion)


def sensitivity(result: TuningResult, criterion: Optional[str] = None) -> dict[str, float]:
    """How much the criterion actually moves across the grid.

    If the spread is tiny the choice barely matters and a mid-range default is
    fine; if it is large, the parameter is doing real work and is worth
    re-tuning as data accumulates.
    """
    key = criterion or result.criterion
    values = np.array([getattr(g, key) for g in result.grid])
    return {
        "best": float(values.min()),
        "worst": float(values.max()),
        "spread": float(values.max() - values.min()),
        "relative_spread": float((values.max() - values.min()) / values.min()) if values.min() else float("nan"),
    }
