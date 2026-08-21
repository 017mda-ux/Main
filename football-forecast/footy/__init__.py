"""Football match forecasting and value betting.

A time-weighted Dixon-Coles model for the Premier League, La Liga and the
Champions League, a scoreline matrix that generates every market consistently,
overround removal, thresholded value detection with fractional Kelly staking,
and a walk-forward backtest scored against the closing line.

Quick start::

    from footy import generate_synthetic_dataset, fit_dixon_coles, build_markets

    data = generate_synthetic_dataset(seasons=2)
    model = fit_dixon_coles(data.matches)
    forecast = model.predict("EPL 01", "EPL 02", "EPL")
    board = build_markets(forecast)
    print(forecast.outcome_probabilities())
"""

from .backtest import BacktestConfig, BacktestResult, BetRecord, run_backtest
from .data import (
    SyntheticDataset,
    attach_xg,
    coverage_report,
    generate_synthetic_dataset,
    load_football_data_csv,
    load_matches_csv,
    normalise_team,
    write_matches_csv,
)
from .dixoncoles import (
    DixonColesConfig,
    DixonColesModel,
    ScorelineForecast,
    fit_dixon_coles,
    scoreline_matrix,
    time_weights,
)
from .markets import (
    Selection,
    asian_handicap,
    both_teams_to_score,
    build_markets,
    consistency_check,
    correct_score,
    double_chance,
    draw_no_bet,
    fair_odds_board,
    match_odds,
    totals,
)
from .metrics import (
    brier_score,
    calibration_table,
    expected_calibration_error,
    log_loss,
    ranked_probability_score,
    score_all,
    skill_vs_reference,
)
from .odds import DevigResult, devig_book, margin_per_selection, overround, remove_overround
from .tuning import TuningResult, tune, walk_forward_score
from .types import (
    CHAMPIONS_LEAGUE,
    LA_LIGA,
    PREMIER_LEAGUE,
    BookOdds,
    Match,
    OddsQuote,
)
from .value import (
    ParlayEvaluation,
    ParlayLeg,
    ValueBet,
    ValueConfig,
    apply_bankroll_cap,
    evaluate_parlay,
    find_value_bets,
    kelly_stake,
)

__version__ = "0.1.0"

__all__ = [
    "PREMIER_LEAGUE", "LA_LIGA", "CHAMPIONS_LEAGUE",
    "Match", "BookOdds", "OddsQuote",
    "DixonColesConfig", "DixonColesModel", "ScorelineForecast",
    "fit_dixon_coles", "scoreline_matrix", "time_weights",
    "Selection", "build_markets", "match_odds", "asian_handicap", "totals",
    "double_chance", "draw_no_bet", "both_teams_to_score", "correct_score",
    "fair_odds_board", "consistency_check",
    "DevigResult", "remove_overround", "devig_book", "overround", "margin_per_selection",
    "ValueConfig", "ValueBet", "find_value_bets", "kelly_stake", "apply_bankroll_cap",
    "ParlayLeg", "ParlayEvaluation", "evaluate_parlay",
    "BacktestConfig", "BacktestResult", "BetRecord", "run_backtest",
    "brier_score", "log_loss", "ranked_probability_score", "calibration_table",
    "expected_calibration_error", "score_all", "skill_vs_reference",
    "tune", "TuningResult", "walk_forward_score",
    "generate_synthetic_dataset", "SyntheticDataset", "load_football_data_csv",
    "load_matches_csv", "attach_xg", "coverage_report", "normalise_team",
    "write_matches_csv",
    "__version__",
]
