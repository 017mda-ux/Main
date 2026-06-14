"""
Elo rating model for international soccer.

Based on:
- Elo (1978) original chess rating system
- Hvattum & Arntzen (2010): "Using ELO ratings for match result prediction in
  association football" - confirms Elo outperforms FIFA ranking
- Club Elo / World Football Elo (eloratings.net) methodology
- Expected score formula: E = 1 / (1 + 10^(-Δelo/400))

xG-Elo upgrade (Castellano et al. 2012, Caley 2015):
- Update Elo based on xG differential rather than actual scoreline
- Strips out finishing luck and goalkeeper variance from rating signal
- Particularly valuable in low-scoring sports where a 1-0 win tells you little
"""

import math
import datetime
from typing import Optional
from world_cup_2026.config import ELO_K, HOME_ADVANTAGE_ELO


def expected_score(elo_a: float, elo_b: float, home_advantage: float = 0) -> float:
    """
    Expected score (win probability) for team A vs team B.
    home_advantage: Elo points added for A when playing at home; 0 for neutral.
    Returns float in [0, 1] = P(A wins or draws weighted).
    """
    return 1.0 / (1.0 + 10 ** (-(elo_a + home_advantage - elo_b) / 400.0))


def wdl_probabilities(elo_a: float, elo_b: float, home_advantage: float = 0,
                      draw_rate: float = 0.26) -> tuple[float, float, float]:
    """
    Convert Elo expected score into Win / Draw / Loss probabilities.

    Draw rate of ~26% is empirically calibrated for international soccer.
    Research (Dixon & Coles 1997, Wheatcroft 2020) shows draws cluster around
    evenly matched teams (Δelo < 100) and fall off sharply for mismatches.

    Returns: (p_win_a, p_draw, p_win_b)
    """
    e = expected_score(elo_a, elo_b, home_advantage)
    elo_diff = abs(elo_a + home_advantage - elo_b)

    # Draw probability peaks at elo_diff=0 and decays with mismatch.
    # Calibrated to match observed international soccer draw rates.
    draw_factor = math.exp(-elo_diff / 350.0)
    p_draw = draw_rate * draw_factor

    # Residual split between win/loss proportional to expected score
    residual = 1.0 - p_draw
    p_win_a = e * residual
    p_win_b = (1.0 - e) * residual

    return p_win_a, p_draw, p_win_b


def update_elo(elo_a: float, elo_b: float, result: float,
               match_type: str = "qualifier",
               goal_diff: int = 0,
               home_a: bool = False) -> tuple[float, float]:
    """
    Update Elo ratings after a match.

    result: 1 = A wins, 0.5 = draw, 0 = B wins
    goal_diff: goal difference (used for goal-diff multiplier per eloratings.net)
    home_a: True if team A is the home team

    Goal difference multiplier (eloratings.net standard):
      1 goal: 1.0 | 2 goals: 1.5 | 3+ goals: (11 + goal_diff) / 8
    """
    k = ELO_K.get(match_type, 25)
    home_adv = HOME_ADVANTAGE_ELO if home_a else 0
    e_a = expected_score(elo_a, elo_b, home_adv)

    # Goal difference multiplier
    if goal_diff <= 1:
        gd_mult = 1.0
    elif goal_diff == 2:
        gd_mult = 1.5
    else:
        gd_mult = (11 + goal_diff) / 8.0

    delta = k * gd_mult * (result - e_a)
    return elo_a + delta, elo_b - delta


def update_elo_xg(elo_a: float, elo_b: float,
                   xg_a: float, xg_b: float,
                   match_type: str = "qualifier",
                   home_a: bool = False) -> tuple[float, float]:
    """
    xG-Elo: update ratings based on Expected Goals differential, not scoreline.

    Why: In soccer, a 1-0 win where the loser had 3.2 xG and hit the post twice
    contains almost no information about relative team strength. Updating on xG
    removes finishing luck and keeper variance from the rating signal.

    xG result encoding (mirrors scoreline Elo):
      xg_a > xg_b  → result = 1.0 (A "won" on xG)
      xg_a == xg_b → result = 0.5
      xg_a < xg_b  → result = 0.0

    Goal-diff multiplier applied to xG margin for proportional rating shifts.
    """
    k = ELO_K.get(match_type, 25)
    home_adv = HOME_ADVANTAGE_ELO if home_a else 0
    e_a = expected_score(elo_a, elo_b, home_adv)

    xg_margin = abs(xg_a - xg_b)
    if xg_margin <= 1.0:
        gd_mult = 1.0
    elif xg_margin <= 2.0:
        gd_mult = 1.5
    else:
        gd_mult = (11 + xg_margin) / 8.0

    if xg_a > xg_b:
        xg_result = 1.0
    elif xg_a < xg_b:
        xg_result = 0.0
    else:
        xg_result = 0.5

    delta = k * gd_mult * (xg_result - e_a)
    return elo_a + delta, elo_b - delta


def build_elo_ratings_xg(match_history: list[dict],
                          initial_ratings: dict[str, float],
                          verbose: bool = False) -> dict[str, float]:
    """
    Build xG-Elo ratings by replaying match history using xG differentials.

    Matches without xg_home / xg_away fall back to actual scoreline.
    In production, feed StatsBomb or Opta xG data for each match.
    """
    ratings = dict(initial_ratings)

    for match in sorted(match_history, key=lambda x: x["date"]):
        home = match["home_team"]
        away = match["away_team"]
        mtype = match.get("match_type", "qualifier")
        neutral = match.get("neutral", False)

        if home not in ratings:
            ratings[home] = 1500
        if away not in ratings:
            ratings[away] = 1500

        home_adv = not neutral

        # Use xG if available, fall back to actual goals
        if "xg_home" in match and "xg_away" in match:
            new_home, new_away = update_elo_xg(
                ratings[home], ratings[away],
                match["xg_home"], match["xg_away"],
                mtype, home_adv
            )
        else:
            hg, ag = match["home_goals"], match["away_goals"]
            result = 1.0 if hg > ag else (0.5 if hg == ag else 0.0)
            gd = abs(hg - ag)
            new_home, new_away = update_elo(
                ratings[home], ratings[away], result, mtype, gd, home_adv
            )

        ratings[home] = new_home
        ratings[away] = new_away

        if verbose:
            xg_str = (f"xG {match.get('xg_home', '?'):.1f}-{match.get('xg_away', '?'):.1f}"
                      if "xg_home" in match else
                      f"{match['home_goals']}-{match['away_goals']}")
            print(f"{match['date']} {home} {xg_str} {away} | "
                  f"{home}: {new_home:.0f}, {away}: {new_away:.0f}")

    return ratings


def elo_win_probability_table(elo_diffs: list[float]) -> dict:
    """
    Pre-compute win probabilities for a range of Elo differences.
    Useful for calibration validation.
    """
    return {
        diff: {
            "p_win": round(1 / (1 + 10 ** (-diff / 400)), 4),
            "p_win_wdl": round(wdl_probabilities(1800 + diff, 1800)[0], 4),
            "p_draw": round(wdl_probabilities(1800 + diff, 1800)[1], 4),
        }
        for diff in elo_diffs
    }


def build_elo_ratings(match_history: list[dict], initial_ratings: dict[str, float],
                      verbose: bool = False) -> dict[str, float]:
    """
    Replay historical matches to build current Elo ratings.

    match_history: list of dicts with keys:
      date, home_team, away_team, home_goals, away_goals, match_type, neutral
    initial_ratings: starting Elo per team
    """
    ratings = dict(initial_ratings)

    for match in sorted(match_history, key=lambda x: x["date"]):
        home = match["home_team"]
        away = match["away_team"]
        hg = match["home_goals"]
        ag = match["away_goals"]
        mtype = match.get("match_type", "qualifier")
        neutral = match.get("neutral", False)

        if home not in ratings:
            ratings[home] = 1500
        if away not in ratings:
            ratings[away] = 1500

        # No home advantage at neutral venues
        home_adv = not neutral

        if hg > ag:
            result, gd = 1.0, hg - ag
        elif hg < ag:
            result, gd = 0.0, ag - hg
        else:
            result, gd = 0.5, 0

        new_home, new_away = update_elo(
            ratings[home], ratings[away], result, mtype, gd, home_adv
        )
        ratings[home] = new_home
        ratings[away] = new_away

        if verbose:
            print(f"{match['date']} {home} {hg}-{ag} {away} | "
                  f"{home}: {new_home:.0f}, {away}: {new_away:.0f}")

    return ratings
