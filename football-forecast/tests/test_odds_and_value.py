"""Overround removal, edge thresholds, Kelly staking and parlay correlation."""

from __future__ import annotations

import copy

import numpy as np
import pytest

from footy.dixoncoles import scoreline_matrix
from footy.markets import build_markets
from footy.odds import METHODS, margin_per_selection, overround, remove_overround
from footy.types import BookOdds
from footy.value import (
    ParlayLeg,
    ValueConfig,
    apply_bankroll_cap,
    evaluate_parlay,
    find_value_bets,
    kelly_stake,
)


class _Forecast:
    def __init__(self, matrix, home="Home FC", away="Away FC"):
        self.matrix = matrix
        self.home = home
        self.away = away
        self.competition = "EPL"


# --------------------------------------------------------------------------
# de-vigging
# --------------------------------------------------------------------------


@pytest.mark.parametrize("method", METHODS)
def test_devigged_probabilities_sum_to_one(method):
    result = remove_overround({"H": 1.53, "D": 4.20, "A": 6.50}, method=method)
    assert sum(result.probabilities.values()) == pytest.approx(1.0)
    assert all(0 < p < 1 for p in result.probabilities.values())


def test_overround_is_reported_correctly():
    book = {"H": 1.53, "D": 4.20, "A": 6.50}
    assert remove_overround(book).overround == pytest.approx(overround(book))
    assert overround(book) > 0


@pytest.mark.parametrize("method", METHODS)
def test_devigging_preserves_the_favourite_ordering(method):
    book = {"H": 1.53, "D": 4.20, "A": 6.50}
    probs = remove_overround(book, method=method).probabilities
    assert probs["H"] > probs["D"] > probs["A"]


def test_methods_agree_on_a_balanced_two_way_book():
    book = {"Over": 1.90, "Under": 1.95}
    values = [remove_overround(book, m).probabilities["Over"] for m in METHODS]
    assert max(values) - min(values) < 0.005


def test_multiplicative_overstates_the_longshot_relative_to_shin():
    """The reason shin is the default: proportional scaling puts too much of
    the margin on the favourite and too little on the longshot."""
    book = {"H": 1.25, "D": 6.00, "A": 12.00}
    shin = remove_overround(book, "shin").probabilities
    mult = remove_overround(book, "multiplicative").probabilities
    assert mult["A"] > shin["A"]
    assert mult["H"] < shin["H"]


def test_margin_is_spread_across_selections():
    margins = margin_per_selection({"H": 1.53, "D": 4.20, "A": 6.50})
    assert sum(margins.values()) == pytest.approx(overround({"H": 1.53, "D": 4.20, "A": 6.50}))


def test_a_book_with_no_margin_is_just_normalised():
    result = remove_overround({"H": 2.1, "A": 2.1})
    assert result.probabilities == {"H": pytest.approx(0.5), "A": pytest.approx(0.5)}
    assert result.overround < 0


def test_devig_rejects_a_single_selection():
    with pytest.raises(ValueError):
        remove_overround({"H": 2.0})


def test_devig_rejects_impossible_odds():
    with pytest.raises(ValueError):
        remove_overround({"H": 0.0, "A": 2.0})


# --------------------------------------------------------------------------
# Kelly
# --------------------------------------------------------------------------


def test_kelly_matches_the_textbook_formula_without_pushes():
    p, odds = 0.55, 2.10
    full, frac = kelly_stake(p, 1 - p, odds, fraction=1.0)
    assert full == pytest.approx((p * odds - 1) / (odds - 1))
    assert frac == pytest.approx(full)


def test_fractional_kelly_scales_the_stake():
    full, quarter = kelly_stake(0.55, 0.45, 2.10, fraction=0.25)
    _, half = kelly_stake(0.55, 0.45, 2.10, fraction=0.5)
    assert quarter == pytest.approx(full * 0.25)
    assert half == pytest.approx(full * 0.5)
    assert quarter < half < full


def test_kelly_is_zero_without_an_edge():
    assert kelly_stake(0.45, 0.55, 2.0)[0] == 0.0     # negative EV
    assert kelly_stake(0.50, 0.50, 2.0)[0] == 0.0     # exactly fair


def test_kelly_stake_is_capped():
    _, frac = kelly_stake(0.90, 0.10, 5.0, fraction=1.0, cap=0.05)
    assert frac == pytest.approx(0.05)


def test_kelly_accounts_for_push_probability():
    """A push is not a loss, so a pushable bet supports a larger stake than the
    same win probability would imply if the rest were losses."""
    with_push, _ = kelly_stake(0.50, 0.30, 2.2, fraction=1.0)   # 20% push
    without, _ = kelly_stake(0.50, 0.50, 2.2, fraction=1.0)
    assert with_push > without


# --------------------------------------------------------------------------
# value detection
# --------------------------------------------------------------------------


def _board_and_book(model_matrix, prices):
    board = build_markets(_Forecast(model_matrix))
    book = BookOdds.from_mapping("m1", prices)
    return board, book


def test_no_bet_when_the_book_agrees_with_the_model():
    matrix = scoreline_matrix(1.5, 1.2, -0.06, 13)
    board = build_markets(_Forecast(matrix))
    fair = {k: 1.0 / s.fair_probability for k, s in board["1X2"].items()}
    vigged = {k: o / 1.05 for k, o in fair.items()}  # book adds margin
    board, book = _board_and_book(matrix, {"1X2": vigged})
    assert find_value_bets(board, book, ValueConfig()) == []


def test_bet_is_flagged_when_the_book_is_wrong():
    matrix = scoreline_matrix(1.9, 0.9, -0.06, 13)
    board = build_markets(_Forecast(matrix))
    # Price the away side far too generously.
    prices = {"H": 1.60, "D": 4.00, "A": 12.0}
    _, book = _board_and_book(matrix, {"1X2": prices})
    bets = find_value_bets(board, book, ValueConfig(min_ev=0.02, min_prob_edge=0.01))
    assert [b.selection for b in bets] == ["A"]
    bet = bets[0]
    assert bet.ev > 0.02 and bet.edge > 0.01
    assert bet.stake > 0
    assert bet.model_prob > bet.market_prob


def test_thresholds_actually_gate_marginal_edges():
    """A positive edge is not enough -- that is the whole point of the threshold."""
    matrix = scoreline_matrix(1.6, 1.2, -0.06, 13)
    board = build_markets(_Forecast(matrix))
    fair = {k: 1.0 / s.fair_probability for k, s in board["1X2"].items()}
    # A book that is 1% generous on the draw: real, but far too thin to bet.
    prices = dict(fair)
    prices["D"] = fair["D"] * 1.01
    _, book = _board_and_book(matrix, {"1X2": prices})

    assert find_value_bets(board, book, ValueConfig(min_ev=0.03, min_prob_edge=0.02)) == []
    loose = find_value_bets(board, book, ValueConfig(min_ev=0.0, min_prob_edge=0.0))
    assert any(b.selection == "D" for b in loose)


def test_partial_books_are_skipped_rather_than_guessed():
    """De-vigging half a market would invent an edge, so it must not happen."""
    matrix = scoreline_matrix(1.6, 1.2, -0.06, 13)
    board = build_markets(_Forecast(matrix))
    book = BookOdds.from_mapping("m1", {"1X2": {"A": 20.0}})
    assert find_value_bets(board, book, ValueConfig(min_ev=0.0, min_prob_edge=0.0)) == []


def test_very_high_overround_books_are_ignored():
    matrix = scoreline_matrix(1.6, 1.2, -0.06, 13)
    board = build_markets(_Forecast(matrix))
    greedy = {"1X2": {"H": 1.4, "D": 3.0, "A": 3.4}}   # ~20% overround
    book = BookOdds.from_mapping("m1", greedy)
    assert find_value_bets(board, book, ValueConfig(max_overround=0.08, min_ev=0.0)) == []


def test_bankroll_cap_scales_a_whole_slate_down():
    matrix = scoreline_matrix(1.9, 0.9, -0.06, 13)
    board = build_markets(_Forecast(matrix))
    _, book = _board_and_book(matrix, {"1X2": {"H": 1.60, "D": 4.00, "A": 12.0}})
    cfg = ValueConfig(min_ev=0.0, min_prob_edge=0.0, bankroll=1000, max_total_stake_fraction=0.02)
    found = find_value_bets(board, book, cfg)
    bets = [copy.deepcopy(b) for _ in range(5) for b in found]  # a busy Saturday
    before = sum(b.stake for b in bets)
    apply_bankroll_cap(bets, cfg)
    after = sum(b.stake for b in bets)
    assert before > 20.0
    assert after == pytest.approx(20.0)


def test_value_config_rejects_a_silly_kelly_fraction():
    with pytest.raises(ValueError):
        ValueConfig(kelly_fraction=0.0)
    with pytest.raises(ValueError):
        ValueConfig(kelly_fraction=1.5)


# --------------------------------------------------------------------------
# parlays
# --------------------------------------------------------------------------


def _parlay_fixtures():
    matrix = scoreline_matrix(1.8, 1.0, -0.06, 13)
    forecast = _Forecast(matrix)
    board = build_markets(forecast)
    return {"m1": board}, {"m1": forecast}


def test_same_match_legs_are_priced_jointly_not_multiplied():
    boards, forecasts = _parlay_fixtures()
    legs = [ParlayLeg("m1", "1X2", "H", 2.0), ParlayLeg("m1", "ou_2.5", "Over", 1.9)]
    result = evaluate_parlay(legs, boards, forecasts)

    assert result.priced
    assert result.joint_prob != pytest.approx(result.naive_independent_prob)
    # A home win and goals reinforce each other, so the true joint is higher.
    assert result.correlation_factor > 1.0
    assert result.correlated_groups and len(result.correlated_groups[0]) == 2
    assert any("same match" in w for w in result.warnings)


def test_joint_probability_matches_a_direct_matrix_calculation():
    boards, forecasts = _parlay_fixtures()
    matrix = forecasts["m1"].matrix
    legs = [ParlayLeg("m1", "1X2", "H", 2.0), ParlayLeg("m1", "btts", "Yes", 1.9)]
    result = evaluate_parlay(legs, boards, forecasts)

    gd = np.arange(matrix.shape[0])[:, None] - np.arange(matrix.shape[1])[None, :]
    both = np.zeros_like(matrix)
    both[1:, 1:] = 1.0
    expected = float((matrix * (gd > 0) * both).sum())
    assert result.joint_prob == pytest.approx(expected)


def test_mutually_exclusive_same_match_legs_have_zero_joint_probability():
    """Home win *and* away win cannot both happen; naive multiplication would
    happily quote it as a live bet."""
    boards, forecasts = _parlay_fixtures()
    legs = [ParlayLeg("m1", "1X2", "H", 2.0), ParlayLeg("m1", "1X2", "A", 4.0)]
    result = evaluate_parlay(legs, boards, forecasts)
    assert result.joint_prob == pytest.approx(0.0)
    assert result.naive_independent_prob > 0.05   # what the naive answer would be
    assert result.ev == pytest.approx(-1.0)


def test_reject_mode_refuses_to_price_correlated_legs():
    boards, forecasts = _parlay_fixtures()
    legs = [ParlayLeg("m1", "1X2", "H", 2.0), ParlayLeg("m1", "ou_2.5", "Over", 1.9)]
    result = evaluate_parlay(legs, boards, forecasts, on_correlation="reject")
    assert not result.priced
    assert np.isnan(result.joint_prob)
    assert any("refused" in w for w in result.warnings)


def test_different_matches_are_treated_as_independent():
    boards, forecasts = _parlay_fixtures()
    other = _Forecast(scoreline_matrix(1.2, 1.4, -0.06, 13), "C", "D")
    boards["m2"] = build_markets(other)
    forecasts["m2"] = other

    legs = [ParlayLeg("m1", "1X2", "H", 2.0), ParlayLeg("m2", "1X2", "A", 2.4)]
    result = evaluate_parlay(legs, boards, forecasts)
    assert result.joint_prob == pytest.approx(result.naive_independent_prob)
    assert result.correlation_factor == pytest.approx(1.0)
    assert not result.correlated_groups


def test_correlated_legs_are_refused_without_a_scoreline_matrix():
    boards, _ = _parlay_fixtures()
    legs = [ParlayLeg("m1", "1X2", "H", 2.0), ParlayLeg("m1", "btts", "Yes", 1.9)]
    result = evaluate_parlay(legs, boards, {}, on_correlation="exact")
    assert not result.priced
    assert any("no scoreline matrix" in w for w in result.warnings)


def test_parlay_combined_odds_are_the_product_of_the_legs():
    boards, forecasts = _parlay_fixtures()
    legs = [ParlayLeg("m1", "1X2", "H", 2.0), ParlayLeg("m1", "ou_2.5", "Over", 1.9)]
    result = evaluate_parlay(legs, boards, forecasts)
    assert result.combined_odds == pytest.approx(3.8)


def test_parlay_needs_at_least_one_leg():
    boards, forecasts = _parlay_fixtures()
    with pytest.raises(ValueError):
        evaluate_parlay([], boards, forecasts)
