"""Walk-forward backtesting against the closing line.

Two design decisions carry most of the weight here.

**Nothing leaks.**  For every match day the model is refitted using only
matches that finished strictly before it.  A model fitted on the full season
and then "tested" on part of it will look spectacular and lose money.

**The benchmark is the closing line, not the opener.**  Closing prices absorb
every steam move, team-news leak and sharp opinion in the market, and they are
the hardest thing in sports betting to beat.  Backtesting against openers
mostly measures how slow the bookmaker was on a Tuesday.  So the headline
output is not profit -- it is whether the model's forecasts score better than
the de-vigged *closing* market on the same matches.

Betting can be simulated at closing prices (the strict test) or at opening
prices (the realistic one).  Betting at the open makes closing line value
measurable, which is the fastest-converging read on edge there is; betting at
the close makes it identically zero by construction, so it is not reported
there.  Note that beating the close on forecast accuracy and earning positive
CLV are different claims -- a strategy can pass one and fail the other, which is
what happens when it beats sloppy openers without ever being better than the
market's final word.  :meth:`BacktestResult.verdict` separates them.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from datetime import date, timedelta
from typing import Mapping, Optional, Sequence

import numpy as np

from . import metrics
from .dixoncoles import DixonColesConfig, DixonColesModel, fit_dixon_coles
from .markets import Selection, build_markets
from .odds import remove_overround
from .types import BookOdds, Match
from .value import ValueBet, ValueConfig, apply_bankroll_cap, find_value_bets


@dataclass
class BacktestConfig:
    model: DixonColesConfig = field(default_factory=DixonColesConfig)
    value: ValueConfig = field(default_factory=ValueConfig)
    train_window_days: Optional[int] = 900
    min_train_matches: int = 250
    refit_every_days: int = 7
    bet_on: str = "closing"          # "closing" | "opening"
    bet_markets: tuple[str, ...] = ("1X2",)
    flat_stake: float = 1.0
    starting_bankroll: float = 1000.0
    warmup_days: int = 0

    def __post_init__(self) -> None:
        if self.bet_on not in {"closing", "opening"}:
            raise ValueError("bet_on must be 'closing' or 'opening'")


@dataclass
class BetRecord:
    date: date
    match_id: str
    home: str
    away: str
    competition: str
    market: str
    selection: str
    odds_taken: float
    closing_odds: Optional[float]
    model_prob: float
    market_prob: float
    edge: float
    ev: float
    stake_flat: float
    stake_kelly: float
    win_fraction: float
    push_fraction: float
    profit_per_unit: float
    bankroll_after: float

    @property
    def clv(self) -> Optional[float]:
        """Closing line value: how much better than the close you got, in price terms."""
        if not self.closing_odds:
            return None
        return self.odds_taken / self.closing_odds - 1.0

    @property
    def won(self) -> bool:
        return self.win_fraction > 0.5


@dataclass
class BacktestResult:
    model_metrics: dict[str, float]
    market_metrics: dict[str, float]
    skill: dict[str, float]
    calibration: list[metrics.CalibrationBin]
    market_calibration: list[metrics.CalibrationBin]
    bets: list[BetRecord]
    pnl: dict[str, float]
    clv: dict[str, float]
    n_matches_scored: int
    n_refits: int
    bankroll_curve: list[tuple[date, float]] = field(default_factory=list)

    @property
    def beat_the_close(self) -> bool:
        """Whether the model's forecasts scored better than the de-vigged close."""
        return bool(self.skill.get("beats_reference", 0.0))

    @property
    def positive_clv(self) -> bool:
        mean = self.clv.get("mean_clv", float("nan"))
        return bool(self.clv.get("measurable", 0.0)) and not math.isnan(mean) and mean > 0.0

    def verdict(self) -> list[str]:
        """The honest read on whether there is an edge here.

        Forecast accuracy against the close and closing line value are two
        different questions, and a strategy can pass one while failing the
        other -- typically when it beats sloppy opening prices without ever
        being better than the market's final word.
        """
        if not self.model_metrics:
            return ["nothing was scored: no match had both a forecast and a closing price"]

        if self.beat_the_close:
            head = [
                "MODEL BEATS THE CLOSING LINE",
                f"  its forecasts score {-self.skill['d_log_loss']:.4f} better on log loss than",
                "  the de-vigged closing market. That is the real result here.",
            ]
        else:
            head = [
                "model does NOT beat the closing line",
                f"  its forecasts score {self.skill['d_log_loss']:+.4f} on log loss against the",
                "  de-vigged close, so it is the less accurate of the two.",
            ]

        if not self.bets:
            return head

        if self.positive_clv:
            head += [
                "",
                f"  It did, however, take prices that beat the close by "
                f"{self.clv['mean_clv']:+.2%} on average",
                f"  ({self.clv['pct_positive_clv']:.0%} of bets). That is genuine edge over the prices",
                "  it actually got, which is a weaker claim than beating the close itself.",
            ]
        elif not self.beat_the_close:
            head += [
                "",
                "  Treat the profit below as variance until that changes.",
            ]
        return head

    def summary(self) -> str:
        lines = [
            f"matches scored : {self.n_matches_scored}   (refits: {self.n_refits})",
            "",
            f"{'metric':<12}{'model':>10}{'market':>10}{'delta':>10}",
            "-" * 42,
        ]
        for key in ("log_loss", "brier", "rps", "ece"):
            m, k = self.model_metrics.get(key), self.market_metrics.get(key)
            if m is None or k is None:
                continue
            lines.append(f"{key:<12}{m:>10.4f}{k:>10.4f}{m - k:>+10.4f}")
        lines += ["", *self.verdict(), ""]
        if self.bets:
            lines += [
                f"bets           : {self.pnl['n_bets']:.0f}",
                f"flat profit    : {self.pnl['flat_profit']:+.2f} u  "
                f"(ROI {self.pnl['flat_roi']:+.2%})",
                f"kelly bankroll : {self.pnl['final_bankroll']:.2f} "
                f"(from {self.pnl['starting_bankroll']:.2f}, "
                f"growth {self.pnl['kelly_growth']:+.2%})",
                f"strike rate    : {self.pnl['strike_rate']:.2%}",
                f"avg odds taken : {self.pnl['avg_odds']:.2f}",
            ]
            if not math.isnan(self.clv.get("mean_clv", float("nan"))):
                lines += [
                    f"mean CLV       : {self.clv['mean_clv']:+.2%} "
                    f"(beat the close on {self.clv['pct_positive_clv']:.1%} of bets)"
                ]
        else:
            lines.append("no bets cleared the thresholds")
        return "\n".join(lines)


def filter_book(book: BookOdds, closing: bool) -> BookOdds:
    """Keep only closing (or only opening) quotes, preferring complete markets."""
    quotes = [q for q in book.quotes if q.is_closing == closing]
    return BookOdds(match_id=book.match_id, quotes=quotes, kickoff=book.kickoff)


def _settle(sel: Selection, match: Match) -> tuple[float, float]:
    """Win/push fractions for a selection given the actual scoreline."""
    n = sel.win_weights.shape[0]
    i = min(int(match.home_goals), n - 1)
    j = min(int(match.away_goals), n - 1)
    return float(sel.win_weights[i, j]), float(sel.push_weights[i, j])


def run_backtest(
    matches: Sequence[Match],
    odds: Mapping[str, BookOdds],
    config: Optional[BacktestConfig] = None,
) -> BacktestResult:
    """Refit-and-predict forward through time, scoring every match with a book."""
    config = config or BacktestConfig()
    played = sorted((m for m in matches if m.played), key=lambda m: m.date)
    if not played:
        raise ValueError("no played matches supplied")

    model_probs: list[dict[str, float]] = []
    market_probs: list[dict[str, float]] = []
    results: list[str] = []
    bets: list[BetRecord] = []
    bankroll = config.starting_bankroll
    curve: list[tuple[date, float]] = []

    model: Optional[DixonColesModel] = None
    last_fit: Optional[date] = None
    n_refits = 0

    all_dates = sorted({m.date for m in played})
    start_after = played[0].date + timedelta(days=config.warmup_days)
    by_date: dict[date, list[Match]] = {}
    for m in played:
        by_date.setdefault(m.date, []).append(m)

    for day in all_dates:
        if day <= start_after:
            continue
        history = [m for m in played if m.date < day]
        if config.train_window_days:
            cutoff = day - timedelta(days=config.train_window_days)
            history = [m for m in history if m.date >= cutoff]
        if len(history) < config.min_train_matches:
            continue

        if model is None or last_fit is None or (day - last_fit).days >= config.refit_every_days:
            try:
                model = fit_dixon_coles(history, as_of=day, config=config.model)
            except (ValueError, FloatingPointError):
                continue
            last_fit, n_refits = day, n_refits + 1

        day_bets: list[tuple[ValueBet, Match, Selection, Optional[float]]] = []
        for match in by_date[day]:
            book = odds.get(match.match_id)
            if book is None:
                continue
            try:
                forecast = model.predict_match(match)
            except KeyError:
                continue  # a team the training window has never seen

            board = build_markets(forecast)
            closing = filter_book(book, closing=True)
            betting_book = closing if config.bet_on == "closing" else filter_book(book, closing=False)

            # --- scoring: model vs the de-vigged closing line -----------------
            closing_1x2 = closing.markets().get("1X2")
            if closing_1x2 and len(closing_1x2) == 3:
                try:
                    devig = remove_overround(closing_1x2, method=config.value.devig_method)
                except ValueError:
                    devig = None
                if devig is not None:
                    model_probs.append(forecast.outcome_probabilities())
                    market_probs.append(devig.probabilities)
                    results.append(match.result)

            # --- betting -----------------------------------------------------
            if not betting_book.quotes:
                continue
            scoped = {k: v for k, v in board.items() if k in config.bet_markets}
            value_cfg = ValueConfig(**{**config.value.__dict__, "bankroll": bankroll})
            found = find_value_bets(scoped, betting_book, value_cfg, forecast=forecast)
            for bet in found:
                sel = board[bet.market][bet.selection]
                close_price = closing.get(bet.market, bet.selection)
                day_bets.append((bet, match, sel, close_price))

        if not day_bets:
            curve.append((day, bankroll))
            continue

        # Size the whole slate together, then settle it together.
        slate = [b for b, _, _, _ in day_bets]
        apply_bankroll_cap(slate, ValueConfig(**{**config.value.__dict__, "bankroll": bankroll}))

        day_pnl = 0.0
        for bet, match, sel, close_price in day_bets:
            win_f, push_f = _settle(sel, match)
            lose_f = max(0.0, 1.0 - win_f - push_f)
            ppu = win_f * (bet.odds - 1.0) - lose_f
            day_pnl += ppu * bet.stake
            bets.append(
                BetRecord(
                    date=day, match_id=match.match_id, home=match.home, away=match.away,
                    competition=match.competition, market=bet.market, selection=bet.selection,
                    odds_taken=bet.odds, closing_odds=close_price,
                    model_prob=bet.model_prob, market_prob=bet.market_prob,
                    edge=bet.edge, ev=bet.ev, stake_flat=config.flat_stake,
                    stake_kelly=bet.stake, win_fraction=win_f, push_fraction=push_f,
                    profit_per_unit=ppu, bankroll_after=0.0,
                )
            )
        bankroll = max(0.0, bankroll + day_pnl)
        for rec in bets[-len(day_bets):]:
            rec.bankroll_after = bankroll
        curve.append((day, bankroll))

    return _assemble(config, model_probs, market_probs, results, bets, bankroll, curve, n_refits)


def _assemble(
    config: BacktestConfig,
    model_probs: list[dict[str, float]],
    market_probs: list[dict[str, float]],
    results: list[str],
    bets: list[BetRecord],
    bankroll: float,
    curve: list[tuple[date, float]],
    n_refits: int,
) -> BacktestResult:
    if results:
        model_metrics = metrics.score_all(model_probs, results)
        market_metrics = metrics.score_all(market_probs, results)
        skill = metrics.skill_vs_reference(model_metrics, market_metrics)
        calib = metrics.calibration_table(model_probs, results)
        market_calib = metrics.calibration_table(market_probs, results)
    else:
        model_metrics = market_metrics = {}
        skill, calib, market_calib = {}, [], []

    flat_profit = sum(b.profit_per_unit * b.stake_flat for b in bets)
    flat_turnover = sum(b.stake_flat for b in bets)
    kelly_turnover = sum(b.stake_kelly for b in bets)
    wins = sum(1 for b in bets if b.won)

    pnl = {
        "n_bets": float(len(bets)),
        "flat_profit": flat_profit,
        "flat_turnover": flat_turnover,
        "flat_roi": flat_profit / flat_turnover if flat_turnover else 0.0,
        "kelly_turnover": kelly_turnover,
        "starting_bankroll": config.starting_bankroll,
        "final_bankroll": bankroll,
        "kelly_growth": (bankroll / config.starting_bankroll - 1.0) if config.starting_bankroll else 0.0,
        "strike_rate": wins / len(bets) if bets else 0.0,
        "avg_odds": float(np.mean([b.odds_taken for b in bets])) if bets else 0.0,
        "avg_edge": float(np.mean([b.edge for b in bets])) if bets else 0.0,
        "max_drawdown": _max_drawdown([v for _, v in curve]),
    }

    # CLV is only meaningful when the bet was struck at a price other than the
    # close; betting at closing odds makes it identically zero by construction.
    clv_values = (
        [b.clv for b in bets if b.clv is not None] if config.bet_on == "opening" else []
    )
    clv = {
        "n": float(len(clv_values)),
        "mean_clv": float(np.mean(clv_values)) if clv_values else float("nan"),
        "median_clv": float(np.median(clv_values)) if clv_values else float("nan"),
        "pct_positive_clv": float(np.mean([v > 0 for v in clv_values])) if clv_values else float("nan"),
        "measurable": float(config.bet_on == "opening"),
    }

    return BacktestResult(
        model_metrics=model_metrics, market_metrics=market_metrics, skill=skill,
        calibration=calib, market_calibration=market_calib, bets=bets, pnl=pnl, clv=clv,
        n_matches_scored=len(results), n_refits=n_refits, bankroll_curve=curve,
    )


def _max_drawdown(values: Sequence[float]) -> float:
    if not values:
        return 0.0
    peak, worst = values[0], 0.0
    for v in values:
        peak = max(peak, v)
        if peak > 0:
            worst = min(worst, v / peak - 1.0)
    return worst
