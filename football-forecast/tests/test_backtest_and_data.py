"""Backtest mechanics, scoring rules, tuning and data loading."""

from __future__ import annotations

import csv
from datetime import date

import numpy as np
import pytest

from footy import metrics
from footy.backtest import BacktestConfig, filter_book, run_backtest
from footy.data import (
    attach_xg,
    coverage_report,
    generate_synthetic_dataset,
    load_football_data_csv,
    load_matches_csv,
    normalise_team,
    write_matches_csv,
)
from footy.dixoncoles import DixonColesConfig
from footy.tuning import tune, walk_forward_score
from footy.types import BookOdds, Match
from footy.value import ValueConfig


# --------------------------------------------------------------------------
# scoring rules
# --------------------------------------------------------------------------


def test_perfect_forecast_scores_zero():
    probs = [{"H": 1.0, "D": 0.0, "A": 0.0}, {"H": 0.0, "D": 0.0, "A": 1.0}]
    assert metrics.brier_score(probs, ["H", "A"]) == pytest.approx(0.0, abs=1e-12)
    assert metrics.log_loss(probs, ["H", "A"]) == pytest.approx(0.0, abs=1e-12)
    assert metrics.ranked_probability_score(probs, ["H", "A"]) == pytest.approx(0.0, abs=1e-12)


def test_uninformative_forecast_scores_the_known_constant():
    probs = [{"H": 1 / 3, "D": 1 / 3, "A": 1 / 3}] * 100
    outcomes = ["H", "D", "A"] * 33 + ["H"]
    assert metrics.brier_score(probs, outcomes) == pytest.approx(2 / 3, abs=1e-9)
    assert metrics.log_loss(probs, outcomes) == pytest.approx(np.log(3), abs=1e-9)


def test_rps_punishes_a_reversed_result_more_than_a_draw():
    """H-D-A is an ordered scale, which is exactly what RPS is for."""
    forecast = [{"H": 0.7, "D": 0.2, "A": 0.1}]
    near_miss = metrics.ranked_probability_score(forecast, ["D"])
    far_miss = metrics.ranked_probability_score(forecast, ["A"])
    assert far_miss > near_miss


def test_log_loss_punishes_confident_mistakes():
    cautious = metrics.log_loss([{"H": 0.5, "D": 0.3, "A": 0.2}], ["A"])
    reckless = metrics.log_loss([{"H": 0.95, "D": 0.03, "A": 0.02}], ["A"])
    assert reckless > cautious


def test_calibration_table_detects_a_biased_forecast():
    probs = [{"H": 0.8, "D": 0.1, "A": 0.1}] * 100
    outcomes = ["H"] * 50 + ["A"] * 50           # claimed 80%, delivered 50%
    table = metrics.calibration_table(probs, outcomes)
    high = [b for b in table if b.lower >= 0.8][0]
    assert high.gap < -0.2
    assert metrics.expected_calibration_error(probs, outcomes) > 0.1


def test_calibration_is_flat_for_an_honest_forecast():
    rng = np.random.default_rng(0)
    probs, outcomes = [], []
    for _ in range(4000):
        p = float(rng.uniform(0.15, 0.7))
        rest = 1.0 - p
        row = {"H": p, "D": rest * 0.5, "A": rest * 0.5}
        probs.append(row)
        outcomes.append(rng.choice(["H", "D", "A"], p=[row["H"], row["D"], row["A"]]))
    assert metrics.expected_calibration_error(probs, outcomes) < 0.03


def test_skill_vs_reference_reports_the_right_direction():
    better = {"log_loss": 0.95, "brier": 0.55, "rps": 0.19}
    worse = {"log_loss": 1.00, "brier": 0.58, "rps": 0.20}
    skill = metrics.skill_vs_reference(better, worse)
    assert skill["d_log_loss"] < 0
    assert skill["log_loss_skill"] > 0
    assert skill["beats_reference"] == 1.0
    assert metrics.skill_vs_reference(worse, better)["beats_reference"] == 0.0


def test_scoring_rejects_mismatched_input():
    with pytest.raises(ValueError):
        metrics.log_loss([{"H": 1.0}], ["H", "A"])
    with pytest.raises(ValueError):
        metrics.log_loss([], [])


# --------------------------------------------------------------------------
# backtest
# --------------------------------------------------------------------------


@pytest.fixture(scope="module")
def dataset():
    return generate_synthetic_dataset(seasons=3, seed=11)


@pytest.fixture(scope="module")
def result(dataset):
    cfg = BacktestConfig(
        model=DixonColesConfig(half_life_days=180, xg_weight=0.5),
        value=ValueConfig(min_ev=0.05, min_prob_edge=0.03),
        refit_every_days=21, min_train_matches=300, bet_on="opening",
    )
    return run_backtest(dataset.matches, dataset.odds, cfg)


def test_backtest_scores_a_meaningful_number_of_matches(result):
    assert result.n_matches_scored > 1500
    assert result.n_refits > 10


def test_backtest_reports_both_model_and_market_scores(result):
    for key in ("log_loss", "brier", "rps", "ece"):
        assert key in result.model_metrics
        assert key in result.market_metrics
    assert result.skill["d_log_loss"] == pytest.approx(
        result.model_metrics["log_loss"] - result.market_metrics["log_loss"]
    )


def test_model_forecasts_are_in_the_right_ballpark(result):
    """Sanity floor: better than an uninformative forecast, worse than perfect."""
    assert 0.85 < result.model_metrics["log_loss"] < np.log(3)
    assert result.model_metrics["ece"] < 0.06


def test_the_simulated_closing_line_is_hard_to_beat(result):
    """The synthetic bookmaker prices near-truth, so the honest verdict is that
    the model does not beat it.  If this ever flips, suspect a leak."""
    assert not result.beat_the_close


def test_summary_states_the_verdict(result):
    text = result.summary()
    assert "closing line" in text
    assert "log_loss" in text


def test_clv_is_measured_when_betting_at_opening_prices(result):
    assert result.clv["measurable"] == 1.0
    if result.bets:
        assert not np.isnan(result.clv["mean_clv"])


def test_clv_is_not_reported_when_betting_at_the_close(dataset):
    cfg = BacktestConfig(
        model=DixonColesConfig(half_life_days=180, xg_weight=0.5),
        value=ValueConfig(min_ev=0.08, min_prob_edge=0.05),
        refit_every_days=45, min_train_matches=300, bet_on="closing",
    )
    res = run_backtest(dataset.matches, dataset.odds, cfg)
    assert res.clv["measurable"] == 0.0
    assert np.isnan(res.clv["mean_clv"])


def test_bets_are_settled_against_the_real_scoreline(dataset):
    cfg = BacktestConfig(
        model=DixonColesConfig(half_life_days=180, xg_weight=0.5),
        value=ValueConfig(min_ev=0.05, min_prob_edge=0.03),
        refit_every_days=45, min_train_matches=300,
    )
    res = run_backtest(dataset.matches, dataset.odds, cfg)
    by_id = {m.match_id: m for m in dataset.matches}
    for bet in res.bets[:50]:
        match = by_id[bet.match_id]
        if bet.market == "1X2":
            won = match.result == bet.selection
            assert bet.win_fraction == pytest.approx(1.0 if won else 0.0)
            expected = (bet.odds_taken - 1.0) if won else -1.0
            assert bet.profit_per_unit == pytest.approx(expected)


def test_stricter_thresholds_never_produce_more_bets(dataset):
    def n_bets(min_ev):
        cfg = BacktestConfig(
            model=DixonColesConfig(half_life_days=180, xg_weight=0.5),
            value=ValueConfig(min_ev=min_ev, min_prob_edge=0.02),
            refit_every_days=45, min_train_matches=300,
        )
        return run_backtest(dataset.matches, dataset.odds, cfg).pnl["n_bets"]

    assert n_bets(0.15) <= n_bets(0.03)


def test_backtest_never_trains_on_the_future(dataset):
    """The load-bearing property of the whole exercise."""
    from footy.dixoncoles import fit_dixon_coles

    matches = sorted((m for m in dataset.matches if m.played), key=lambda m: m.date)
    cutoff = matches[len(matches) // 2].date
    history = [m for m in matches if m.date < cutoff]
    model = fit_dixon_coles(history, as_of=cutoff, config=DixonColesConfig())
    assert model.as_of == cutoff
    assert model.n_matches == len(history)
    assert all(m.date < cutoff for m in history)


def test_filter_book_separates_opening_and_closing_quotes(dataset):
    book = next(iter(dataset.odds.values()))
    closing = filter_book(book, closing=True)
    opening = filter_book(book, closing=False)
    assert all(q.is_closing for q in closing.quotes)
    assert not any(q.is_closing for q in opening.quotes)
    assert len(closing.quotes) + len(opening.quotes) == len(book.quotes)


def test_backtest_needs_played_matches():
    with pytest.raises(ValueError):
        run_backtest([], {})


# --------------------------------------------------------------------------
# tuning
# --------------------------------------------------------------------------


def test_walk_forward_score_is_out_of_sample(dataset):
    scores = walk_forward_score(
        dataset.matches,
        DixonColesConfig(half_life_days=180, xg_weight=0.5),
        refit_every_days=45, min_train_matches=300,
    )
    assert 0.85 < scores["log_loss"] < np.log(3)
    assert scores["n"] > 1000


def test_tuning_prefers_a_finite_half_life_when_strength_drifts(dataset):
    """Team strength follows a random walk in the simulator, so forgetting old
    matches must beat remembering everything."""
    result = tune(
        dataset.matches, half_lives=(120.0, 1e9), xg_weights=(0.5,),
        refit_every_days=45, min_train_matches=300,
    )
    assert result.best.half_life_days == 120.0


def test_tuning_prefers_a_blend_over_either_pure_signal(dataset):
    """xG is a less noisy but incomplete signal; the mix should beat both ends."""
    result = tune(
        dataset.matches, half_lives=(180.0,), xg_weights=(0.0, 0.5, 1.0),
        refit_every_days=45, min_train_matches=300,
    )
    by_weight = {g.xg_weight: g.log_loss for g in result.grid}
    assert by_weight[0.5] < by_weight[0.0]
    assert by_weight[0.5] < by_weight[1.0]
    assert result.best.xg_weight == 0.5


def test_tuning_rejects_an_unknown_criterion(dataset):
    with pytest.raises(ValueError):
        tune(dataset.matches, criterion="profit")


# --------------------------------------------------------------------------
# data
# --------------------------------------------------------------------------


@pytest.mark.parametrize(
    "raw,expected",
    [
        ("Man United", "Manchester United"),
        ("man utd", "Manchester United"),
        ("Spurs", "Tottenham"),
        ("Ath Madrid", "Atletico Madrid"),
        ("Ath Bilbao", "Athletic Club"),
        ("  Arsenal  ", "Arsenal"),
        ("Paris SG", "Paris Saint-Germain"),
    ],
)
def test_team_names_are_normalised(raw, expected):
    assert normalise_team(raw) == expected


def test_normalise_team_rejects_none():
    with pytest.raises(ValueError):
        normalise_team(None)


def test_match_derives_its_own_identity_and_result():
    m = Match(date="2024-03-01", competition="EPL", home="Arsenal", away="Chelsea",
              home_goals=2, away_goals=1)
    assert m.date == date(2024, 3, 1)
    assert m.result == "H"
    assert m.played and not m.has_xg
    assert "Arsenal" in m.match_id


def test_match_parses_the_football_data_date_format():
    assert Match(date="01/03/2024", competition="EPL", home="A", away="B").date == date(2024, 3, 1)


def test_unplayed_match_has_no_result():
    m = Match(date="2024-03-01", competition="EPL", home="A", away="B")
    assert not m.played
    with pytest.raises(ValueError):
        _ = m.result


def test_odds_quote_rejects_impossible_prices():
    with pytest.raises(ValueError):
        BookOdds("m").add("1X2", "H", 0.95)


def test_football_data_csv_round_trip(tmp_path):
    path = tmp_path / "E0.csv"
    with path.open("w", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["Date", "HomeTeam", "AwayTeam", "FTHG", "FTAG",
                    "PSCH", "PSCD", "PSCA", "B365H", "B365D", "B365A",
                    "B365>2.5C", "B365<2.5C"])
        w.writerow(["01/03/2024", "Man United", "Spurs", "2", "1",
                    "2.10", "3.50", "3.60", "2.05", "3.40", "3.70", "1.90", "1.95"])

    matches, books = load_football_data_csv(path)
    assert len(matches) == 1
    assert matches[0].home == "Manchester United"
    assert matches[0].away == "Tottenham"
    assert matches[0].result == "H"

    book = books[0]
    one_x_two = book.markets()["1X2"]
    assert one_x_two["H"] == 2.10          # closing Pinnacle preferred over B365 opener
    assert all(q.is_closing for q in book.quotes if q.market == "1X2")
    assert book.markets()["ou_2.5"]["Over"] == 1.90


def test_generic_csv_round_trip(tmp_path):
    data = generate_synthetic_dataset(seasons=1, seed=2)
    path = write_matches_csv(data.matches[:50], tmp_path / "m.csv")
    loaded = load_matches_csv(path)
    assert len(loaded) == 50
    assert loaded[0].home == data.matches[0].home
    assert loaded[0].home_xg == pytest.approx(data.matches[0].home_xg)
    assert loaded[0].date == data.matches[0].date


def test_attach_xg_joins_and_reports_what_it_could_not_match():
    results = [
        Match(date=date(2024, 3, 1), competition="EPL", home="Arsenal", away="Chelsea",
              home_goals=2, away_goals=1),
        Match(date=date(2024, 3, 2), competition="EPL", home="Everton", away="Fulham",
              home_goals=0, away_goals=0),
    ]
    xg_feed = [
        Match(date=date(2024, 3, 1), competition="EPL", home="Arsenal", away="Chelsea",
              home_goals=2, away_goals=1, home_xg=1.8, away_xg=0.9),
        Match(date=date(2024, 3, 5), competition="EPL", home="Nobody", away="Nowhere",
              home_goals=1, away_goals=1, home_xg=1.0, away_xg=1.0),
    ]
    merged, unmatched = attach_xg(results, xg_feed)
    assert merged[0].has_xg and merged[0].home_xg == 1.8
    assert not merged[1].has_xg
    assert [m.home for m in unmatched] == ["Nobody"]


def test_coverage_report_counts_xg(dataset):
    report = coverage_report(dataset.matches)
    assert set(report) == {"EPL", "LaLiga", "UCL"}
    assert all(row["xg_coverage"] == pytest.approx(1.0) for row in report.values())


def test_synthetic_dataset_is_internally_coherent(dataset):
    assert len(dataset.matches) > 2000
    assert all(m.match_id in dataset.odds for m in dataset.matches)
    assert all(m.played and m.has_xg for m in dataset.matches)
    assert {m.competition for m in dataset.matches} == {"EPL", "LaLiga", "UCL"}
    assert any(m.neutral for m in dataset.matches)


def test_synthetic_strengths_actually_drift(dataset):
    team = next(iter(dataset.attack_paths))
    path = dataset.attack_paths[team]
    assert path.std() > 0.05
    first, last = dataset.matches[0].date, dataset.matches[-1].date
    assert dataset.attack_at(team, first) != dataset.attack_at(team, last)


def test_synthetic_odds_carry_a_realistic_margin(dataset):
    from footy.odds import overround

    book = next(iter(dataset.odds.values()))
    closing = {q.selection: q.odds for q in book.quotes if q.market == "1X2" and q.is_closing}
    assert 0.0 < overround(closing) < 0.25
