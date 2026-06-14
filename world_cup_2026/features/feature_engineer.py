"""
Feature engineering for the XGBoost meta-model.

Research-backed feature set (ranked by importance from literature):

TIER 1 — Highest predictive value:
  xG_diff_recent    Market-calibrated goal expectancy difference
  elo_diff          Elo rating difference (Hvattum & Arntzen 2010)
  implied_prob_*    Market implied probabilities (devigged)

TIER 2 — Strong signal:
  attack_rating     Dixon-Coles attack parameter
  defense_rating    Dixon-Coles defense parameter
  form_gd_10        Goal differential last 10 internationals (time-decayed)
  squad_value_ratio Log ratio of squad market values

TIER 3 — Contextual:
  continental_home  Whether team plays in home confederation
  dc_lambda/mu      Dixon-Coles expected goals
  tournament_stage  Group stage vs knockout (affects draw likelihood)

TIER 4 — Refinement:
  shots_on_target_diff  Recent SoT differential
  possession_diff       Recent possession differential
  xg_over_actual        Whether team over/underperforms xG (regression signal)
"""

import numpy as np
import math
from world_cup_2026.config import (
    TEAM_ELO, SQUAD_VALUE_M, RECENT_FORM_GD, CONFEDERATION,
    HOST_CONFEDERATION, FORM_HALFLIFE_DAYS
)


def american_to_implied_prob(american_odds: int) -> float:
    """Convert American moneyline odds to implied probability (raw, includes vig)."""
    if american_odds > 0:
        return 100.0 / (american_odds + 100.0)
    else:
        return abs(american_odds) / (abs(american_odds) + 100.0)


def devig_multiplicative(probs: list[float]) -> list[float]:
    """
    Remove bookmaker vig using the multiplicative method.
    Most accurate method per research on sharp soccer markets (Shin 1993,
    Joseph et al. 2006). Scales each probability down proportionally.
    """
    total = sum(probs)
    return [p / total for p in probs]


def devig_power(probs: list[float], n: int = None) -> list[float]:
    """
    Power (Shin) method for vig removal. Slightly better for
    heavy favourite-longshot situations common in World Cup group stage.
    """
    if n is None:
        n = len(probs)
    # Binary search for power exponent k such that sum(p^k) = 1
    lo, hi = 0.5, 2.0
    for _ in range(50):
        mid = (lo + hi) / 2
        if sum(p ** mid for p in probs) > 1.0:
            lo = mid
        else:
            hi = mid
    k = (lo + hi) / 2
    devigged = [p ** k for p in probs]
    total = sum(devigged)
    return [p / total for p in devigged]


def closing_line_value(opening_prob: float, closing_prob: float) -> float:
    """
    Closing Line Value (CLV): measures how much the market moved toward a team.

    Positive = sharp money pushed the line in team's favor (bullish signal).
    Negative = line moved away (public/square money or fade by sharps).

    Research (Joseph et al. 2006, Power 2019): closing lines are the sharpest
    available probability estimate. If your model agrees with CLV direction,
    that's corroborating evidence. If it disagrees, investigate before betting.
    """
    return closing_prob - opening_prob


def xg_overperformance(actual_goals: float, xg: float) -> float:
    """
    Ratio of actual goals to xG over recent matches.
    > 1.0 = team outscoring xG (likely to regress down)
    < 1.0 = team underscoring xG (likely to regress up)
    Neutral at 1.0; bounded to avoid extreme values.
    """
    return min(max(actual_goals / max(xg, 0.1), 0.2), 3.0)


def build_match_features(team_a: str, team_b: str,
                         elo_ratings: dict = None,
                         dc_params: dict = None,
                         match_odds_1x2: dict = None,
                         opening_odds_1x2: dict = None,
                         xg_stats: dict = None,
                         xg_overperf: dict = None,
                         neutral: bool = True,
                         tournament_stage: str = "group") -> dict:
    """
    Build the full feature vector for one match (team_a vs team_b).

    Parameters
    ----------
    team_a: str  — "home" or attacking side
    team_b: str  — "away" side
    elo_ratings: dict  — current Elo ratings, defaults to TEAM_ELO
    dc_params: dict  — Dixon-Coles attack/defense params
    match_odds_1x2: dict  — {'home': american_odds, 'draw': ..., 'away': ...}
    xg_stats: dict  — {'team': {'xg_for': float, 'xg_against': float, 'shots_ot': float}}
    neutral: bool  — World Cup group matches are neutral venue
    tournament_stage: str  — 'group' | 'r32' | 'r16' | 'qf' | 'sf' | 'final'

    Returns dict of features (all floats).
    """
    elo = elo_ratings or TEAM_ELO
    elo_a = elo.get(team_a, 1600)
    elo_b = elo.get(team_b, 1600)
    elo_diff = elo_a - elo_b

    # Elo win probability (no home advantage for neutral WC venues)
    e_a = 1.0 / (1.0 + 10 ** (-elo_diff / 400.0))
    e_b = 1.0 - e_a

    # Squad value (log ratio captures relative depth)
    val_a = SQUAD_VALUE_M.get(team_a, 100)
    val_b = SQUAD_VALUE_M.get(team_b, 100)
    squad_value_log_ratio = math.log(max(val_a, 1) / max(val_b, 1))

    # Recent form (goal differential last 10 matches, time-decayed)
    form_a = RECENT_FORM_GD.get(team_a, 0)
    form_b = RECENT_FORM_GD.get(team_b, 0)
    form_diff = form_a - form_b

    # Continental advantage (host confederation = CONCACAF for WC 2026)
    conf_a = CONFEDERATION.get(team_a, "OTHER")
    conf_b = CONFEDERATION.get(team_b, "OTHER")
    continent_adv_a = 1.0 if conf_a == HOST_CONFEDERATION else 0.0
    continent_adv_b = 1.0 if conf_b == HOST_CONFEDERATION else 0.0
    continent_adv_diff = continent_adv_a - continent_adv_b

    # Tournament stage encoding (knockout stages have fewer draws in regulation
    # due to extra time, but group stage has more draws)
    stage_map = {"group": 0, "r32": 1, "r16": 2, "qf": 3, "sf": 4, "final": 5}
    stage_encoded = stage_map.get(tournament_stage, 0)
    is_knockout = int(stage_encoded > 0)

    # Dixon-Coles expected goals
    dc_lambda, dc_mu = 1.35, 1.05  # defaults
    dc_attack_diff = 0.0
    dc_defense_diff = 0.0
    if dc_params:
        params = dc_params.get("team_params", {})
        pa = params.get(team_a, {"attack": 1.0, "defense": 1.0})
        pb = params.get(team_b, {"attack": 1.0, "defense": 1.0})
        home_adv = 1.0 if neutral else 1.1
        dc_lambda = pa["attack"] * pb["defense"] * 1.35 * home_adv
        dc_mu = pb["attack"] * pa["defense"] * 1.05
        dc_attack_diff = pa["attack"] - pb["attack"]
        dc_defense_diff = pa["defense"] - pb["defense"]

    dc_expected_total = dc_lambda + dc_mu
    dc_expected_diff = dc_lambda - dc_mu

    # xG stats (rolling average from recent matches)
    xg_for_a = xg_against_a = 1.35
    xg_for_b = xg_against_b = 1.05
    shots_ot_diff = 0.0
    if xg_stats:
        if team_a in xg_stats:
            xg_for_a = xg_stats[team_a].get("xg_for", 1.35)
            xg_against_a = xg_stats[team_a].get("xg_against", 1.05)
            shots_ot_a = xg_stats[team_a].get("shots_ot", 4.5)
        else:
            shots_ot_a = 4.5
        if team_b in xg_stats:
            xg_for_b = xg_stats[team_b].get("xg_for", 1.05)
            xg_against_b = xg_stats[team_b].get("xg_against", 1.35)
            shots_ot_b = xg_stats[team_b].get("shots_ot", 3.5)
        else:
            shots_ot_b = 3.5
        shots_ot_diff = shots_ot_a - shots_ot_b

    xg_net_a = xg_for_a - xg_against_a
    xg_net_b = xg_for_b - xg_against_b
    xg_net_diff = xg_net_a - xg_net_b
    xg_total = xg_for_a + xg_for_b  # proxy for O/U line

    # Closing Line Value — sharp money direction
    clv_a = clv_draw = clv_b = 0.0
    if opening_odds_1x2 and match_odds_1x2:
        raw_open = [
            american_to_implied_prob(opening_odds_1x2.get("home", -110)),
            american_to_implied_prob(opening_odds_1x2.get("draw", 250)),
            american_to_implied_prob(opening_odds_1x2.get("away", 300)),
        ]
        raw_close = [
            american_to_implied_prob(match_odds_1x2.get("home", -110)),
            american_to_implied_prob(match_odds_1x2.get("draw", 250)),
            american_to_implied_prob(match_odds_1x2.get("away", 300)),
        ]
        open_dv = devig_power(raw_open)
        close_dv = devig_power(raw_close)
        clv_a = closing_line_value(open_dv[0], close_dv[0])
        clv_draw = closing_line_value(open_dv[1], close_dv[1])
        clv_b = closing_line_value(open_dv[2], close_dv[2])

    # Market implied probabilities (devigged)
    mkt_p_win = mkt_p_draw = mkt_p_loss = None
    mkt_edge_a = mkt_edge_draw = mkt_edge_b = 0.0

    if match_odds_1x2:
        raw_p_home = american_to_implied_prob(match_odds_1x2.get("home", -110))
        raw_p_draw = american_to_implied_prob(match_odds_1x2.get("draw", 250))
        raw_p_away = american_to_implied_prob(match_odds_1x2.get("away", 300))

        # Power method is better for 3-way markets per research on soccer odds
        mkt_p_win, mkt_p_draw, mkt_p_loss = devig_power(
            [raw_p_home, raw_p_draw, raw_p_away]
        )
        # Market-Elo edge = our estimate - market estimate
        p_win_elo, p_draw_elo, p_loss_elo = _elo_wdl(elo_a, elo_b)
        mkt_edge_a = p_win_elo - mkt_p_win
        mkt_edge_draw = p_draw_elo - mkt_p_draw
        mkt_edge_b = p_loss_elo - mkt_p_loss
    else:
        mkt_p_win, mkt_p_draw, mkt_p_loss = _elo_wdl(elo_a, elo_b)

    return {
        # Tier 1 — Highest predictive power
        "elo_diff": elo_diff,
        "elo_win_prob_a": round(e_a, 4),
        "mkt_implied_win_a": round(mkt_p_win, 4),
        "mkt_implied_draw": round(mkt_p_draw, 4),
        "mkt_implied_win_b": round(mkt_p_loss, 4),

        # Tier 2 — Strong signal
        "dc_lambda": round(dc_lambda, 4),
        "dc_mu": round(dc_mu, 4),
        "dc_expected_total": round(dc_expected_total, 4),
        "dc_expected_diff": round(dc_expected_diff, 4),
        "dc_attack_diff": round(dc_attack_diff, 4),
        "dc_defense_diff": round(dc_defense_diff, 4),
        "xg_net_diff": round(xg_net_diff, 4),
        "xg_total_proxy": round(xg_total, 4),
        "squad_value_log_ratio": round(squad_value_log_ratio, 4),
        "form_gd_diff": round(form_diff, 4),

        # Tier 3 — Contextual
        "continent_adv_diff": round(continent_adv_diff, 4),
        "is_knockout": is_knockout,
        "stage_encoded": stage_encoded,
        "neutral_venue": int(neutral),

        # Tier 4 — Refinement
        "shots_ot_diff": round(shots_ot_diff, 4),
        "mkt_edge_a": round(mkt_edge_a, 4),
        "mkt_edge_b": round(mkt_edge_b, 4),

        # CLV — line movement (requires opening odds; zero if not provided)
        "clv_a": round(clv_a, 4),
        "clv_draw": round(clv_draw, 4),
        "clv_b": round(clv_b, 4),

        # xG overperformance — regression-to-mean signal (1.0 = neutral)
        "xg_overperf_a": round(xg_overperf.get(team_a, 1.0) if xg_overperf else 1.0, 4),
        "xg_overperf_b": round(xg_overperf.get(team_b, 1.0) if xg_overperf else 1.0, 4),

        # Meta
        "team_a": team_a,
        "team_b": team_b,
    }


def _elo_wdl(elo_a: float, elo_b: float) -> tuple[float, float, float]:
    """Quick WDL from Elo without importing the full module."""
    import math
    elo_diff = elo_a - elo_b
    e = 1.0 / (1.0 + 10 ** (-elo_diff / 400.0))
    draw_factor = math.exp(-abs(elo_diff) / 350.0)
    p_draw = 0.26 * draw_factor
    residual = 1.0 - p_draw
    return e * residual, p_draw, (1.0 - e) * residual
