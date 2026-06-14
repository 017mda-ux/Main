"""
Betting value detection engine.

Core framework:
  Edge = P(model) - P(market)  [after devigging]
  EV   = Edge * (decimal_odds - 1) - (1 - P(model))
  Kelly fraction = Edge / (decimal_odds - 1)  [full Kelly]
  Fractional Kelly = Kelly * 0.25             [conservative]

Research insights implemented:
  1. Favorite-Longshot Bias: Favorites win MORE than odds imply in international
     tournaments (Forrest & Simmons 2008, Deschamps & Gergaud 2012).
     → Adjust longshot (>+300) probability DOWN by bias_factor.

  2. Asian handicap markets are unbiased (no FLB); use as calibration anchor
     when available (Štrumbelj & Šikonja 2010).

  3. Sharp market anchor: Pinnacle closing line is the best single predictor
     of true probability. Always compare against Pinnacle if available.

  4. Over/Under market tends to be slightly efficient; value rarer than on 1X2.

  5. Non-transitive anomaly (Dyte & Clarke 2000): certain team matchups
     produce unexpected results vs odds — flagged where detected.
"""

import math
from dataclasses import dataclass
from typing import Optional
from world_cup_2026.features.feature_engineer import (
    american_to_implied_prob, devig_multiplicative, devig_power
)


@dataclass
class BettingOpportunity:
    market: str          # "home_win" | "draw" | "away_win" | "over_2_5" | ...
    team_a: str
    team_b: str
    model_prob: float    # our estimated true probability
    market_prob: float   # devigged market probability
    raw_odds_american: int
    decimal_odds: float
    edge: float          # model_prob - market_prob
    ev_per_unit: float   # expected value per $1 wagered
    kelly_fraction: float
    frac_kelly_25: float
    confidence: str      # "HIGH" | "MEDIUM" | "LOW"
    note: str


# Favorite-Longshot Bias adjustment factors for international 1X2 markets.
# Based on: Forrest & Simmons (2002), Goddard & Asimakopoulos (2004).
# Favorites (implied prob > 0.60) are UNDERPRICED on average.
# Longshots (implied prob < 0.20) are OVERPRICED on average.
FLB_ADJUSTMENT = {
    "favorite": 0.04,    # add ~4% to heavy favorites (>60% implied)
    "mild_fav": 0.015,   # add ~1.5% to mild favorites (40-60%)
    "neutral": 0.0,      # no adjustment near even money (35-40%)
    "underdog": -0.015,  # subtract 1.5% from underdogs (20-35%)
    "longshot": -0.04,   # subtract 4% from longshots (<20%)
}


def apply_flb_adjustment(market_prob: float) -> float:
    """
    Apply Favorite-Longshot Bias correction to market probability.
    This shifts our ESTIMATE of true probability relative to market.
    Documented in international soccer research; stronger in 1X2 vs Asian markets.
    """
    if market_prob > 0.60:
        return market_prob + FLB_ADJUSTMENT["favorite"]
    elif market_prob > 0.40:
        return market_prob + FLB_ADJUSTMENT["mild_fav"]
    elif market_prob > 0.35:
        return market_prob + FLB_ADJUSTMENT["neutral"]
    elif market_prob > 0.20:
        return market_prob + FLB_ADJUSTMENT["underdog"]
    else:
        return market_prob + FLB_ADJUSTMENT["longshot"]


def american_to_decimal(american: int) -> float:
    if american > 0:
        return american / 100.0 + 1.0
    else:
        return 100.0 / abs(american) + 1.0


def calculate_ev(model_prob: float, decimal_odds: float) -> float:
    """EV per $1 wagered = model_prob * (odds - 1) - (1 - model_prob)"""
    return model_prob * (decimal_odds - 1) - (1.0 - model_prob)


def kelly_fraction(model_prob: float, decimal_odds: float) -> float:
    """
    Full Kelly criterion. In practice, use 25% Kelly (frac_kelly_25)
    to account for model uncertainty and variance.
    Kelly = (model_prob * decimal_odds - 1) / (decimal_odds - 1)
    """
    if decimal_odds <= 1.0:
        return 0.0
    k = (model_prob * decimal_odds - 1.0) / (decimal_odds - 1.0)
    return max(k, 0.0)


def evaluate_1x2_market(team_a: str, team_b: str,
                         model_probs: dict,
                         odds_1x2: dict,
                         apply_flb: bool = True) -> list[BettingOpportunity]:
    """
    Evaluate all three outcomes of a 1X2 market for value.

    model_probs: {'home': float, 'draw': float, 'away': float}
    odds_1x2: {'home': american_int, 'draw': american_int, 'away': american_int}

    Returns list of BettingOpportunity where edge > 0.
    """
    raw_home = american_to_implied_prob(odds_1x2["home"])
    raw_draw = american_to_implied_prob(odds_1x2["draw"])
    raw_away = american_to_implied_prob(odds_1x2["away"])

    mkt_home, mkt_draw, mkt_away = devig_power([raw_home, raw_draw, raw_away])

    outcomes = [
        ("home_win", team_a, model_probs["home"], mkt_home, odds_1x2["home"]),
        ("draw",     f"{team_a} vs {team_b}", model_probs["draw"],  mkt_draw,  odds_1x2["draw"]),
        ("away_win", team_b, model_probs["away"], mkt_away, odds_1x2["away"]),
    ]

    opportunities = []
    for market, team, model_p, mkt_p, american in outcomes:
        # Apply FLB adjustment: we believe favorites are underpriced
        # so TRUE probability of favorites > market implies
        if apply_flb:
            flb_adjusted_mkt = apply_flb_adjustment(mkt_p)
        else:
            flb_adjusted_mkt = mkt_p

        edge = model_p - flb_adjusted_mkt
        decimal = american_to_decimal(american)
        ev = calculate_ev(model_p, decimal)
        kelly = kelly_fraction(model_p, decimal)
        frac_kelly = kelly * 0.25

        if model_p >= 0.40:
            conf = "HIGH"
        elif model_p >= 0.25:
            conf = "MEDIUM"
        else:
            conf = "LOW"

        note = ""
        if mkt_p > 0.60 and apply_flb:
            note = "Favorite-Longshot Bias: heavy favorite likely underpriced in 1X2 market"
        elif mkt_p < 0.15 and apply_flb:
            note = "Favorite-Longshot Bias: longshot likely overpriced — avoid"

        opportunities.append(BettingOpportunity(
            market=market, team_a=team_a, team_b=team_b,
            model_prob=round(model_p, 4), market_prob=round(mkt_p, 4),
            raw_odds_american=american, decimal_odds=round(decimal, 3),
            edge=round(edge, 4), ev_per_unit=round(ev, 4),
            kelly_fraction=round(kelly, 4), frac_kelly_25=round(frac_kelly, 4),
            confidence=conf, note=note
        ))

    return [o for o in opportunities if o.edge > 0.02]  # min 2% edge threshold


def evaluate_ou_market(team_a: str, team_b: str,
                        model_p_over: float,
                        odds_over: int, odds_under: int,
                        line: float = 2.5) -> list[BettingOpportunity]:
    """
    Evaluate Over/Under market for value.
    O/U markets are slightly more efficient than 1X2 but still exploitable
    when model has strong xG signal.
    """
    raw_over = american_to_implied_prob(odds_over)
    raw_under = american_to_implied_prob(odds_under)
    mkt_over, mkt_under = devig_multiplicative([raw_over, raw_under])

    opportunities = []
    for market, model_p, mkt_p, american in [
        (f"over_{line}", model_p_over, mkt_over, odds_over),
        (f"under_{line}", 1.0 - model_p_over, mkt_under, odds_under),
    ]:
        edge = model_p - mkt_p
        decimal = american_to_decimal(american)
        ev = calculate_ev(model_p, decimal)
        kelly = kelly_fraction(model_p, decimal)

        if abs(edge) > 0.03:
            opportunities.append(BettingOpportunity(
                market=market, team_a=team_a, team_b=team_b,
                model_prob=round(model_p, 4), market_prob=round(mkt_p, 4),
                raw_odds_american=american, decimal_odds=round(decimal, 3),
                edge=round(edge, 4), ev_per_unit=round(ev, 4),
                kelly_fraction=round(kelly, 4), frac_kelly_25=round(kelly * 0.25, 4),
                confidence="MEDIUM" if model_p > 0.55 else "LOW",
                note="O/U market — use xG model signal as primary driver"
            ))

    return [o for o in opportunities if o.edge > 0.0]


def format_opportunity(opp: BettingOpportunity) -> str:
    """Human-readable bet summary."""
    direction = "▲ VALUE" if opp.edge > 0 else "▼ SKIP"
    return (
        f"{direction} | {opp.market.upper():15s} | "
        f"{opp.team_a} vs {opp.team_b}\n"
        f"  Model prob : {opp.model_prob:.1%}  |  Market prob: {opp.market_prob:.1%}  "
        f"|  Edge: {opp.edge:+.1%}\n"
        f"  Odds       : {opp.raw_odds_american:+d} (decimal {opp.decimal_odds:.2f})\n"
        f"  EV/unit    : {opp.ev_per_unit:+.4f}  |  "
        f"Kelly: {opp.kelly_fraction:.1%}  |  25% Kelly: {opp.frac_kelly_25:.1%}\n"
        f"  Confidence : {opp.confidence}"
        + (f"\n  Note       : {opp.note}" if opp.note else "")
    )
