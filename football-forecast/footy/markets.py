"""Every market, derived from the one scoreline distribution.

Match odds, Asian handicaps, totals, both-teams-to-score and correct score are
all just different ways of summing the same matrix.  Deriving them from one
object rather than modelling each separately is what makes them internally
consistent: the over 2.5 price and the -1.5 handicap price can never disagree
about the same underlying match, and a same-match parlay can be priced exactly
rather than by assuming independence.

Each :class:`Selection` carries two weight matrices over scorelines --
``win_weights`` (fraction of stake that wins) and ``push_weights`` (fraction
returned).  Quarter-ball handicaps drop out of that representation naturally as
half-weights, and it gives :mod:`footy.value` an exact joint distribution to
work with when two legs come from the same match.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional, Sequence

import numpy as np

DEFAULT_TOTALS_LINES: tuple[float, ...] = (
    0.5, 1.5, 2.0, 2.25, 2.5, 2.75, 3.0, 3.25, 3.5, 4.5,
)
DEFAULT_HANDICAP_LINES: tuple[float, ...] = (
    -2.0, -1.75, -1.5, -1.25, -1.0, -0.75, -0.5, -0.25, 0.0,
    0.25, 0.5, 0.75, 1.0, 1.25, 1.5, 1.75, 2.0,
)


@dataclass
class Selection:
    """One bettable outcome, expressed as payoff weights over scorelines."""

    market: str
    name: str
    win_weights: np.ndarray = field(repr=False)
    push_weights: np.ndarray = field(repr=False)
    win_prob: float
    push_prob: float
    lose_prob: float

    @property
    def fair_odds(self) -> float:
        """Break-even decimal odds, accounting for pushes.

        Solves ``win_prob * (o - 1) - lose_prob = 0``.  For a market with no
        push this is the familiar ``1 / p``; with a push it correctly prices
        the returned stake rather than treating it as a loss.
        """
        if self.win_prob <= 0:
            return float("inf")
        return 1.0 + self.lose_prob / self.win_prob

    @property
    def fair_probability(self) -> float:
        """Win probability conditional on the bet not being pushed.

        This is the number to compare against a de-vigged market price, since a
        pushed bet is a non-event for both sides.
        """
        live = self.win_prob + self.lose_prob
        return self.win_prob / live if live > 0 else 0.0

    @property
    def has_push(self) -> bool:
        return self.push_prob > 1e-12

    def expected_value(self, odds: float) -> float:
        """Expected profit per unit staked at the given decimal odds."""
        return self.win_prob * (odds - 1.0) - self.lose_prob


def _probs(matrix: np.ndarray, win_w: np.ndarray, push_w: np.ndarray) -> tuple[float, float, float]:
    win = float((matrix * win_w).sum())
    push = float((matrix * push_w).sum())
    return win, push, max(0.0, 1.0 - win - push)


def _make(market: str, name: str, matrix: np.ndarray, win_w: np.ndarray,
          push_w: Optional[np.ndarray] = None) -> Selection:
    push_w = np.zeros_like(win_w) if push_w is None else push_w
    win, push, lose = _probs(matrix, win_w, push_w)
    return Selection(market, name, win_w, push_w, win, push, lose)


def goal_difference(n: int) -> np.ndarray:
    """``gd[i, j] = i - j`` over the scoreline grid."""
    idx = np.arange(n)
    return idx[:, None] - idx[None, :]


def goal_total(n: int) -> np.ndarray:
    idx = np.arange(n)
    return idx[:, None] + idx[None, :]


def _is_quarter(line: float) -> bool:
    return abs((abs(line) * 4) % 2 - 1) < 1e-9


def _threshold_weights(
    values: np.ndarray, line: float, direction: int
) -> tuple[np.ndarray, np.ndarray]:
    """Weights for "``values`` beats ``line``", handling quarter lines.

    ``direction`` is +1 for "above the line" (over, handicap win) and -1 for
    "below the line" (under).  Quarter lines split the stake across the two
    neighbouring half-lines, exactly as a bookmaker settles them.
    """
    if _is_quarter(line):
        lo_win, lo_push = _threshold_weights(values, line - 0.25, direction)
        hi_win, hi_push = _threshold_weights(values, line + 0.25, direction)
        return 0.5 * (lo_win + hi_win), 0.5 * (lo_push + hi_push)

    diff = direction * (values - line)
    win = (diff > 0).astype(float)
    push = np.isclose(diff, 0.0).astype(float)
    return win, push


def match_odds(matrix: np.ndarray) -> dict[str, Selection]:
    n = matrix.shape[0]
    gd = goal_difference(n)
    return {
        "H": _make("1X2", "H", matrix, (gd > 0).astype(float)),
        "D": _make("1X2", "D", matrix, (gd == 0).astype(float)),
        "A": _make("1X2", "A", matrix, (gd < 0).astype(float)),
    }


def double_chance(matrix: np.ndarray) -> dict[str, Selection]:
    n = matrix.shape[0]
    gd = goal_difference(n)
    return {
        "1X": _make("dc", "1X", matrix, (gd >= 0).astype(float)),
        "12": _make("dc", "12", matrix, (gd != 0).astype(float)),
        "X2": _make("dc", "X2", matrix, (gd <= 0).astype(float)),
    }


def draw_no_bet(matrix: np.ndarray) -> dict[str, Selection]:
    n = matrix.shape[0]
    gd = goal_difference(n)
    push = (gd == 0).astype(float)
    return {
        "Home": _make("dnb", "Home", matrix, (gd > 0).astype(float), push),
        "Away": _make("dnb", "Away", matrix, (gd < 0).astype(float), push),
    }


def asian_handicap(matrix: np.ndarray, line: float) -> dict[str, Selection]:
    """Handicap priced from the goal-difference distribution.

    ``line`` is stated from the home team's perspective, so ``-0.5`` means the
    home side gives away half a goal.  The away selection is the mirror image.
    """
    gd = goal_difference(matrix.shape[0]).astype(float)
    market = f"ah_{line:+g}"
    # Home wins when gd + line > 0, i.e. gd is above the threshold -line; the
    # quarter-ball split is driven by the threshold, so it must be passed as the
    # line rather than folded into the values.
    home_win, home_push = _threshold_weights(gd, -line, +1)
    away_win, away_push = _threshold_weights(gd, -line, -1)
    return {
        "Home": _make(market, "Home", matrix, home_win, home_push),
        "Away": _make(market, "Away", matrix, away_win, away_push),
    }


def totals(matrix: np.ndarray, line: float) -> dict[str, Selection]:
    """Over/under priced from the goals-total distribution."""
    tot = goal_total(matrix.shape[0]).astype(float)
    market = f"ou_{line:g}"
    over_win, over_push = _threshold_weights(tot, line, +1)
    under_win, under_push = _threshold_weights(tot, line, -1)
    return {
        "Over": _make(market, "Over", matrix, over_win, over_push),
        "Under": _make(market, "Under", matrix, under_win, under_push),
    }


def both_teams_to_score(matrix: np.ndarray) -> dict[str, Selection]:
    n = matrix.shape[0]
    idx = np.arange(n)
    both = ((idx[:, None] > 0) & (idx[None, :] > 0)).astype(float)
    return {
        "Yes": _make("btts", "Yes", matrix, both),
        "No": _make("btts", "No", matrix, 1.0 - both),
    }


def correct_score(matrix: np.ndarray, top_n: int = 10) -> dict[str, Selection]:
    flat = np.argsort(matrix, axis=None)[::-1][:top_n]
    out: dict[str, Selection] = {}
    for pos in flat:
        i, j = divmod(int(pos), matrix.shape[1])
        w = np.zeros_like(matrix)
        w[i, j] = 1.0
        out[f"{i}-{j}"] = _make("cs", f"{i}-{j}", matrix, w)
    return out


def build_markets(
    forecast,
    totals_lines: Sequence[float] = DEFAULT_TOTALS_LINES,
    handicap_lines: Sequence[float] = DEFAULT_HANDICAP_LINES,
    include_correct_score: int = 0,
) -> dict[str, dict[str, Selection]]:
    """Price the full board from one :class:`~footy.dixoncoles.ScorelineForecast`."""
    matrix = forecast.matrix
    board: dict[str, dict[str, Selection]] = {
        "1X2": match_odds(matrix),
        "dc": double_chance(matrix),
        "dnb": draw_no_bet(matrix),
        "btts": both_teams_to_score(matrix),
    }
    for line in totals_lines:
        board[f"ou_{line:g}"] = totals(matrix, line)
    for line in handicap_lines:
        board[f"ah_{line:+g}"] = asian_handicap(matrix, line)
    if include_correct_score:
        board["cs"] = correct_score(matrix, include_correct_score)
    return board


def fair_odds_board(board: dict[str, dict[str, Selection]]) -> dict[str, dict[str, float]]:
    return {
        market: {name: round(sel.fair_odds, 4) for name, sel in sels.items()}
        for market, sels in board.items()
    }


def find_selection(
    board: dict[str, dict[str, Selection]], market: str, selection: str
) -> Optional[Selection]:
    return board.get(market, {}).get(selection)


def consistency_check(board: dict[str, dict[str, Selection]], tol: float = 1e-9) -> list[str]:
    """Assert the internal coherence the shared-matrix design is supposed to buy.

    Returns a list of human-readable violations; empty means the board hangs
    together.  Worth running in tests and after any change to the market code.
    """
    problems: list[str] = []
    for market, sels in board.items():
        if market == "cs":
            continue
        total = sum(s.win_prob + s.push_prob / 2.0 for s in sels.values())
        # Double chance overlaps by design (1X + 12 + X2 = 2), so it is exempt;
        # everything else must partition the outcome space exactly once, with a
        # push counted half to each side.
        if market != "dc" and abs(total - 1.0) > 1e-6:
            problems.append(f"{market}: outcome weights sum to {total:.6f}, expected 1")

    one_x_two = board.get("1X2")
    if one_x_two:
        h, d, a = (one_x_two[k].win_prob for k in ("H", "D", "A"))
        checks = (
            ("ah_+0", "Home", h, "level handicap Home should equal 1X2 H"),
            ("ah_+0", "Away", a, "level handicap Away should equal 1X2 A"),
            ("ah_-0.5", "Home", h, "-0.5 handicap Home should equal 1X2 H"),
            ("ah_+0.5", "Away", a, "+0.5 handicap Away should equal 1X2 A"),
            ("dnb", "Home", h, "draw-no-bet Home should equal 1X2 H"),
            ("dc", "1X", h + d, "double chance 1X should equal 1X2 H + D"),
            ("dc", "X2", d + a, "double chance X2 should equal 1X2 D + A"),
            ("dc", "12", h + a, "double chance 12 should equal 1X2 H + A"),
        )
        for key, selection, expected, message in checks:
            sel = board.get(key, {}).get(selection)
            if sel is not None and abs(sel.win_prob - expected) > tol:
                problems.append(f"{message} ({sel.win_prob:.9f} vs {expected:.9f})")
    return problems
