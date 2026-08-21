"""Market tests: internal consistency and correct handicap/total settlement."""

from __future__ import annotations

import pytest

from footy.dixoncoles import scoreline_matrix
from footy.markets import (
    DEFAULT_HANDICAP_LINES,
    DEFAULT_TOTALS_LINES,
    asian_handicap,
    both_teams_to_score,
    build_markets,
    consistency_check,
    correct_score,
    double_chance,
    draw_no_bet,
    match_odds,
    totals,
)


class _Forecast:
    def __init__(self, matrix):
        self.matrix = matrix
        self.home = "H"
        self.away = "A"
        self.competition = "EPL"


@pytest.fixture
def matrix():
    return scoreline_matrix(1.7, 1.15, -0.08, 13)


@pytest.fixture
def board(matrix):
    return build_markets(_Forecast(matrix))


def test_match_odds_sum_to_one(matrix):
    sels = match_odds(matrix)
    assert sum(s.win_prob for s in sels.values()) == pytest.approx(1.0)


def test_every_market_is_internally_consistent(board):
    assert consistency_check(board) == []


def test_consistency_check_actually_detects_an_inconsistent_board(board):
    """A check that can never fail is worse than no check at all."""
    import dataclasses

    board["dc"]["1X"] = dataclasses.replace(board["dc"]["1X"], win_prob=0.11)
    board["ah_+0"]["Home"] = dataclasses.replace(board["ah_+0"]["Home"], win_prob=0.99)
    problems = consistency_check(board)
    assert any("double chance 1X" in p for p in problems)
    assert any("level handicap Home" in p for p in problems)


def test_zero_handicap_equals_draw_no_bet(matrix):
    ah = asian_handicap(matrix, 0.0)
    dnb = draw_no_bet(matrix)
    for side in ("Home", "Away"):
        assert ah[side].win_prob == pytest.approx(dnb[side].win_prob)
        assert ah[side].push_prob == pytest.approx(dnb[side].push_prob)
        assert ah[side].fair_odds == pytest.approx(dnb[side].fair_odds)


def test_half_ball_handicap_equals_match_odds(matrix):
    ah = asian_handicap(matrix, -0.5)
    odds = match_odds(matrix)
    assert ah["Home"].win_prob == pytest.approx(odds["H"].win_prob)
    assert ah["Away"].win_prob == pytest.approx(odds["D"].win_prob + odds["A"].win_prob)
    assert not ah["Home"].has_push


def test_double_chance_agrees_with_match_odds(matrix):
    dc = double_chance(matrix)
    odds = match_odds(matrix)
    assert dc["1X"].win_prob == pytest.approx(odds["H"].win_prob + odds["D"].win_prob)
    assert dc["12"].win_prob == pytest.approx(odds["H"].win_prob + odds["A"].win_prob)
    assert dc["X2"].win_prob == pytest.approx(odds["D"].win_prob + odds["A"].win_prob)


@pytest.mark.parametrize("line", DEFAULT_HANDICAP_LINES)
def test_handicap_sides_are_complementary(matrix, line):
    ah = asian_handicap(matrix, line)
    home, away = ah["Home"], ah["Away"]
    total = home.win_prob + home.push_prob / 2 + away.win_prob + away.push_prob / 2
    assert total == pytest.approx(1.0)
    assert home.push_prob == pytest.approx(away.push_prob)


@pytest.mark.parametrize("line", DEFAULT_TOTALS_LINES)
def test_totals_sides_are_complementary(matrix, line):
    ou = totals(matrix, line)
    over, under = ou["Over"], ou["Under"]
    total = over.win_prob + over.push_prob / 2 + under.win_prob + under.push_prob / 2
    assert total == pytest.approx(1.0)


def test_integer_lines_push_and_half_lines_do_not(matrix):
    assert totals(matrix, 2.0)["Over"].has_push
    assert not totals(matrix, 2.5)["Over"].has_push
    assert asian_handicap(matrix, -1.0)["Home"].has_push
    assert not asian_handicap(matrix, -1.5)["Home"].has_push


def test_quarter_line_splits_stake_across_neighbouring_lines(matrix):
    """A -0.25 handicap is half at 0 and half at -0.5, and must price that way."""
    quarter = asian_handicap(matrix, -0.25)["Home"]
    zero = asian_handicap(matrix, 0.0)["Home"]
    half = asian_handicap(matrix, -0.5)["Home"]
    assert quarter.win_prob == pytest.approx(0.5 * (zero.win_prob + half.win_prob))
    assert quarter.push_prob == pytest.approx(0.5 * (zero.push_prob + half.push_prob))
    # -0.25 is a better handicap for the backer than -0.5 (half the stake is
    # refunded on a draw rather than lost), so it must command a shorter price;
    # a level handicap, which refunds the whole stake, is shorter still.
    assert zero.fair_odds < quarter.fair_odds < half.fair_odds


def test_quarter_total_settles_a_draw_on_the_line_correctly():
    """On Over 2.25 with exactly two goals, half the stake pushes and half loses."""
    matrix = scoreline_matrix(1.3, 1.3, 0.0, 13)
    over = totals(matrix, 2.25)["Over"]
    under = totals(matrix, 2.25)["Under"]
    # scoreline 1-1: total is 2, exactly on the lower half of the split
    assert over.win_weights[1, 1] == pytest.approx(0.0)
    assert over.push_weights[1, 1] == pytest.approx(0.5)
    assert under.win_weights[1, 1] == pytest.approx(0.5)
    assert under.push_weights[1, 1] == pytest.approx(0.5)


def test_fair_odds_account_for_pushes(matrix):
    """With a push, break-even odds are 1 + lose/win, not 1/win."""
    sel = totals(matrix, 3.0)["Over"]
    assert sel.has_push
    assert sel.fair_odds == pytest.approx(1.0 + sel.lose_prob / sel.win_prob)
    assert sel.fair_odds < 1.0 / sel.win_prob  # push protection makes it shorter
    assert sel.expected_value(sel.fair_odds) == pytest.approx(0.0, abs=1e-12)


def test_expected_value_is_zero_at_fair_odds_for_every_selection(board):
    for market, sels in board.items():
        for name, sel in sels.items():
            if sel.win_prob <= 0:
                continue
            assert sel.expected_value(sel.fair_odds) == pytest.approx(0.0, abs=1e-9), (
                f"{market}/{name}"
            )


def test_btts_matches_the_matrix(matrix):
    btts = both_teams_to_score(matrix)
    expected = float(matrix[1:, 1:].sum())
    assert btts["Yes"].win_prob == pytest.approx(expected)
    assert btts["No"].win_prob == pytest.approx(1.0 - expected)


def test_correct_score_returns_the_most_likely_scorelines(matrix):
    cs = correct_score(matrix, top_n=5)
    assert len(cs) == 5
    probs = [s.win_prob for s in cs.values()]
    assert probs == sorted(probs, reverse=True)
    top = max(cs.values(), key=lambda s: s.win_prob)
    assert top.win_prob == pytest.approx(matrix.max())


def test_totals_and_handicaps_never_disagree_about_the_same_match(matrix):
    """The point of the shared matrix: a stronger favourite must never price
    as a weaker one on a different market."""
    strong = scoreline_matrix(2.4, 0.8, -0.08, 13)
    weak = scoreline_matrix(1.4, 1.3, -0.08, 13)
    for line in (-1.5, -0.5, 0.5):
        assert (
            asian_handicap(strong, line)["Home"].win_prob
            > asian_handicap(weak, line)["Home"].win_prob
        )
    assert match_odds(strong)["H"].win_prob > match_odds(weak)["H"].win_prob
