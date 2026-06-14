"""
World Cup 2026 Betting Model — Main Interface
=============================================
Research-backed hybrid model combining:
  1. Dixon-Coles Bivariate Poisson  (Dixon & Coles 1997)
  2. Elo Rating System              (Hvattum & Arntzen 2010)
  3. XGBoost Meta-Model             (Bunker & Thabtah 2019)
  4. Favorite-Longshot Bias Adj.    (Forrest & Simmons 2002)
  5. Monte Carlo Simulation         (50,000 iterations)

Usage:
    python -m world_cup_2026.main predict --home Spain --away Brazil
    python -m world_cup_2026.main simulate --sims 50000
    python -m world_cup_2026.main group --group H
    python -m world_cup_2026.main value --home Spain --away Brazil --h-odds -200 --d-odds +260 --a-odds +550
"""

import sys
import argparse
import random
import math
from pprint import pprint

from world_cup_2026.config import (
    WC2026_GROUPS, TEAM_ELO, OUTRIGHT_WINNER_ODDS_AMERICAN,
    SQUAD_VALUE_M, RECENT_FORM_GD
)
from world_cup_2026.models.dixon_coles import predict_match, score_matrix
from world_cup_2026.models.elo_model import wdl_probabilities
from world_cup_2026.models.xgboost_model import SoccerXGBModel, blend_predictions
from world_cup_2026.features.feature_engineer import build_match_features
from world_cup_2026.betting.odds_engine import (
    evaluate_1x2_market, evaluate_ou_market, format_opportunity,
    american_to_implied_prob, devig_power
)
from world_cup_2026.analysis.monte_carlo import run_simulation, print_tournament_odds
from world_cup_2026.data.synthetic_training_data import generate_training_dataset


def build_dc_params_from_elo() -> dict:
    """
    Bootstrap Dixon-Coles attack/defense parameters from Elo ratings.
    Used when no historical match CSV is available.
    Elo → attack/defense via log-linear scaling calibrated to international averages.
    """
    avg_elo = sum(TEAM_ELO.values()) / len(TEAM_ELO)
    team_params = {}
    for team, elo in TEAM_ELO.items():
        # Scale factor: each 200 Elo = ~+/- 15% in attack/defense
        strength = 10 ** ((elo - avg_elo) / 1200)
        # Top teams have better attack AND better defense (lower = better defense)
        team_params[team] = {
            "attack": round(strength * 1.05, 4),
            "defense": round(1.0 / (strength * 0.95), 4),  # lower defense = harder to score against
        }
    return {"team_params": team_params, "rho": -0.134}


def full_match_prediction(team_a: str, team_b: str,
                           dc_params: dict = None,
                           odds_1x2: dict = None,
                           ou_odds: dict = None,
                           stage: str = "group",
                           verbose: bool = True) -> dict:
    """
    Run the complete prediction pipeline for one match.

    Returns dict with:
      - Dixon-Coles WDL + O/U probabilities
      - Elo-based probabilities
      - Blended (ensemble) probabilities
      - Value bet detection vs provided odds
    """
    if dc_params is None:
        dc_params = build_dc_params_from_elo()

    # ── Dixon-Coles prediction ─────────────────────────────────────────────
    dc_pred = predict_match(team_a, team_b, dc_params["team_params"],
                            neutral=True, rho=dc_params.get("rho", -0.134))

    # ── Elo-based WDL ─────────────────────────────────────────────────────
    elo_a = TEAM_ELO.get(team_a, 1600)
    elo_b = TEAM_ELO.get(team_b, 1600)
    elo_p_win, elo_p_draw, elo_p_loss = wdl_probabilities(elo_a, elo_b)

    # ── Ensemble blend (45% DC + 55% Elo as stand-in for XGBoost) ────────
    blended_win, blended_draw, blended_loss = blend_predictions(
        (dc_pred["p_home_win"], dc_pred["p_draw"], dc_pred["p_away_win"]),
        (elo_p_win, elo_p_draw, elo_p_loss),
        dc_weight=0.55,
    )

    result = {
        "match": f"{team_a} vs {team_b}",
        "stage": stage,
        "model_probabilities": {
            "p_win_A": round(blended_win, 4),
            "p_draw": round(blended_draw, 4),
            "p_win_B": round(blended_loss, 4),
        },
        "dixon_coles": {
            "lambda (xG_A)": dc_pred["lambda"],
            "mu (xG_B)": dc_pred["mu"],
            "expected_total_goals": dc_pred["expected_total_goals"],
            "most_likely_score": dc_pred["most_likely_score"],
            "p_win_A": dc_pred["p_home_win"],
            "p_draw": dc_pred["p_draw"],
            "p_win_B": dc_pred["p_away_win"],
            "p_over_1_5": dc_pred["p_over_1_5"],
            "p_over_2_5": dc_pred["p_over_2_5"],
            "p_over_3_5": dc_pred["p_over_3_5"],
            "p_btts": dc_pred["p_btts"],
        },
        "elo": {
            "elo_A": elo_a, "elo_B": elo_b,
            "elo_diff": elo_a - elo_b,
            "p_win_A": round(elo_p_win, 4),
            "p_draw": round(elo_p_draw, 4),
            "p_win_B": round(elo_p_loss, 4),
        },
    }

    # ── Value detection ────────────────────────────────────────────────────
    if odds_1x2:
        model_p = {"home": blended_win, "draw": blended_draw, "away": blended_loss}
        value_bets = evaluate_1x2_market(team_a, team_b, model_p, odds_1x2)
        result["value_bets_1x2"] = [vars(o) for o in value_bets]

    if ou_odds:
        ou_value = evaluate_ou_market(
            team_a, team_b,
            model_p_over=dc_pred["p_over_2_5"],
            odds_over=ou_odds.get("over", -115),
            odds_under=ou_odds.get("under", -105),
            line=2.5,
        )
        result["value_bets_ou"] = [vars(o) for o in ou_value]

    if verbose:
        _print_prediction(result, team_a, team_b, odds_1x2, ou_odds)

    return result


def _print_prediction(result: dict, team_a: str, team_b: str,
                       odds_1x2: dict = None, ou_odds: dict = None):
    """Pretty-print the full match prediction."""
    sep = "═" * 60
    print(f"\n{sep}")
    print(f"  ⚽  {team_a.upper()}  vs  {team_b.upper()}")
    print(f"  Stage: {result['stage'].upper()} | Venue: Neutral")
    print(sep)

    p = result["model_probabilities"]
    dc = result["dixon_coles"]
    elo = result["elo"]

    print(f"\n{'BLENDED MODEL PROBABILITIES':}")
    print(f"  {team_a} Win:  {p['p_win_A']:>6.1%}  │  Draw: {p['p_draw']:>6.1%}  │  {team_b} Win: {p['p_win_B']:>6.1%}")

    print(f"\n{'DIXON-COLES (Bivariate Poisson)':}")
    print(f"  xG {team_a}: {dc['lambda (xG_A)']:.3f}  │  xG {team_b}: {dc['mu (xG_B)']:.3f}")
    print(f"  Most likely score: {dc['most_likely_score']}  │  Exp. total: {dc['expected_total_goals']:.2f}")
    print(f"  Over 1.5: {dc['p_over_1_5']:.1%}  │  Over 2.5: {dc['p_over_2_5']:.1%}  │  Over 3.5: {dc['p_over_3_5']:.1%}")
    print(f"  BTTS: {dc['p_btts']:.1%}")

    print(f"\n{'ELO RATINGS':}")
    print(f"  {team_a}: {elo['elo_A']}  │  {team_b}: {elo['elo_B']}  │  Diff: {elo['elo_diff']:+d}")

    if odds_1x2:
        raw_h = american_to_implied_prob(odds_1x2["home"])
        raw_d = american_to_implied_prob(odds_1x2["draw"])
        raw_a = american_to_implied_prob(odds_1x2["away"])
        mkt_h, mkt_d, mkt_a = devig_power([raw_h, raw_d, raw_a])
        vig = round((raw_h + raw_d + raw_a - 1) * 100, 2)
        print(f"\n{'MARKET ODDS (devigged)':}")
        print(f"  Home {odds_1x2['home']:+d} → {mkt_h:.1%}  │  "
              f"Draw {odds_1x2['draw']:+d} → {mkt_d:.1%}  │  "
              f"Away {odds_1x2['away']:+d} → {mkt_a:.1%}  │  Vig: {vig:.1f}%")

    if result.get("value_bets_1x2"):
        print(f"\n{'VALUE BETS DETECTED (1X2)':}")
        from world_cup_2026.betting.odds_engine import BettingOpportunity
        for b in result["value_bets_1x2"]:
            opp = BettingOpportunity(**b)
            print(format_opportunity(opp))

    if result.get("value_bets_ou"):
        print(f"\n{'VALUE BETS DETECTED (O/U)':}")
        from world_cup_2026.betting.odds_engine import BettingOpportunity
        for b in result["value_bets_ou"]:
            opp = BettingOpportunity(**b)
            print(format_opportunity(opp))

    print(f"\n{sep}")


def simulate_all(n_sims: int = 50000, seed: int = 42) -> dict:
    """Run full Monte Carlo tournament simulation."""
    print(f"\n⚽ World Cup 2026 Monte Carlo Simulation ({n_sims:,} runs)")
    print("Building DC parameters from Elo ratings...")
    dc_params = build_dc_params_from_elo()

    print("Running simulations...")
    probs = run_simulation(n_sims=n_sims, dc_params=dc_params, seed=seed)

    print("\n" + "═" * 72)
    print("  WORLD CUP 2026 PROJECTED PROBABILITIES")
    print("═" * 72)
    print_tournament_odds(probs, top_n=24)

    # Compare model vs market for outright winner
    print("\n" + "═" * 72)
    print("  MODEL vs MARKET — OUTRIGHT WINNER VALUE")
    print("═" * 72)
    print(f"{'TEAM':<20} {'Model Win%':>10} {'Market Win%':>12} {'Edge':>8} {'Market Odds':>12}")
    print("─" * 64)

    for team, p in list(probs.items())[:20]:
        model_win = p.get("winner", 0)
        mkt_odds = OUTRIGHT_WINNER_ODDS_AMERICAN.get(team, 10000)
        mkt_win = american_to_implied_prob(mkt_odds)
        edge = model_win - mkt_win
        edge_str = f"{edge:+.1%}"
        flag = " ◄ VALUE" if edge > 0.01 else (" ✗ AVOID" if edge < -0.02 else "")
        print(f"{team:<20} {model_win:>9.1%}  {mkt_win:>11.1%}  {edge_str:>8}{flag}")

    return probs


def simulate_group(group_letter: str, n_sims: int = 100000) -> None:
    """Simulate a single group's outcomes."""
    group_letter = group_letter.upper()
    if group_letter not in WC2026_GROUPS:
        print(f"Group {group_letter} not found. Available: {list(WC2026_GROUPS.keys())}")
        return

    teams = WC2026_GROUPS[group_letter]
    dc_params = build_dc_params_from_elo()
    print(f"\n⚽ Group {group_letter}: {' | '.join(teams)}")
    print(f"Running {n_sims:,} simulations...\n")

    from world_cup_2026.analysis.monte_carlo import simulate_group as _sim_group
    from collections import Counter

    first_counts = Counter()
    second_counts = Counter()
    third_counts = Counter()
    fourth_counts = Counter()
    rng = random.Random(42)

    for _ in range(n_sims):
        standings = _sim_group(teams, dc_params, rng=random.Random(rng.randint(0, 2**31)))
        first_counts[standings[0]["team"]] += 1
        second_counts[standings[1]["team"]] += 1
        third_counts[standings[2]["team"]] += 1
        fourth_counts[standings[3]["team"]] += 1

    print(f"{'TEAM':<20} {'Win Group':>10} {'2nd':>8} {'3rd':>8} {'4th (Out)':>10}")
    print("─" * 60)
    for team in teams:
        p1 = first_counts[team] / n_sims
        p2 = second_counts[team] / n_sims
        p3 = third_counts[team] / n_sims
        p4 = fourth_counts[team] / n_sims
        print(f"{team:<20} {p1:>9.1%}  {p2:>7.1%}  {p3:>7.1%}  {p4:>9.1%}")


def main():
    parser = argparse.ArgumentParser(
        description="World Cup 2026 Betting Model",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    subparsers = parser.add_subparsers(dest="command")

    # Predict a match
    pred_p = subparsers.add_parser("predict", help="Predict a single match")
    pred_p.add_argument("--home", required=True, help="Team A name")
    pred_p.add_argument("--away", required=True, help="Team B name")
    pred_p.add_argument("--stage", default="group",
                        choices=["group", "r32", "r16", "qf", "sf", "final"])
    pred_p.add_argument("--h-odds", type=int, help="Home win American odds e.g. -150")
    pred_p.add_argument("--d-odds", type=int, help="Draw American odds e.g. +260")
    pred_p.add_argument("--a-odds", type=int, help="Away win American odds e.g. +380")
    pred_p.add_argument("--over-odds", type=int, help="Over 2.5 goals American odds")
    pred_p.add_argument("--under-odds", type=int, help="Under 2.5 goals American odds")

    # Simulate tournament
    sim_p = subparsers.add_parser("simulate", help="Run full tournament simulation")
    sim_p.add_argument("--sims", type=int, default=50000, help="Number of simulations")
    sim_p.add_argument("--seed", type=int, default=42)

    # Simulate a group
    grp_p = subparsers.add_parser("group", help="Simulate a group stage")
    grp_p.add_argument("--group", required=True, help="Group letter e.g. H")
    grp_p.add_argument("--sims", type=int, default=100000)

    # Demo mode
    subparsers.add_parser("demo", help="Run demo predictions for key WC 2026 matchups")

    args = parser.parse_args()

    if args.command == "predict":
        odds_1x2 = None
        if args.h_odds and args.d_odds and args.a_odds:
            odds_1x2 = {"home": args.h_odds, "draw": args.d_odds, "away": args.a_odds}
        ou_odds = None
        if args.over_odds and args.under_odds:
            ou_odds = {"over": args.over_odds, "under": args.under_odds}
        full_match_prediction(args.home, args.away,
                              odds_1x2=odds_1x2, ou_odds=ou_odds, stage=args.stage)

    elif args.command == "simulate":
        simulate_all(n_sims=args.sims, seed=args.seed)

    elif args.command == "group":
        simulate_group(args.group, n_sims=args.sims)

    elif args.command == "demo":
        _run_demo()

    else:
        _run_demo()


def _run_demo():
    """Run a showcase of model predictions on key WC 2026 matchups."""
    print("\n" + "═" * 60)
    print("  WORLD CUP 2026 BETTING MODEL — DEMO")
    print("  Research-backed: xG + Elo + Dixon-Coles + FLB Adj.")
    print("═" * 60)

    dc_params = build_dc_params_from_elo()

    # Key group-stage matchups
    matchups = [
        {
            "home": "Spain", "away": "Uruguay", "stage": "group",
            "odds": {"home": -200, "draw": +300, "away": +550},
            "ou": {"over": -120, "under": +100},
        },
        {
            "home": "France", "away": "Belgium", "stage": "group",
            "odds": {"home": -160, "draw": +280, "away": +430},
            "ou": {"over": -135, "under": +115},
        },
        {
            "home": "Brazil", "away": "Mexico", "stage": "group",
            "odds": {"home": -220, "draw": +330, "away": +600},
            "ou": {"over": -125, "under": +105},
        },
        {
            "home": "Argentina", "away": "Algeria", "stage": "group",
            "odds": {"home": -350, "draw": +380, "away": +900},
            "ou": {"over": -150, "under": +125},
        },
        {
            "home": "USA", "away": "Panama", "stage": "group",
            "odds": {"home": -180, "draw": +290, "away": +480},
            "ou": {"over": -110, "under": -110},
        },
        {
            "home": "Germany", "away": "Netherlands", "stage": "group",
            "odds": {"home": -115, "draw": +260, "away": +300},
            "ou": {"over": -140, "under": +120},
        },
    ]

    for m in matchups:
        full_match_prediction(
            m["home"], m["away"],
            dc_params=dc_params,
            odds_1x2=m.get("odds"),
            ou_odds=m.get("ou"),
            stage=m.get("stage", "group"),
        )

    # Run quick group simulations for Groups H and J
    print("\n\nQUICK GROUP SIMULATIONS (10,000 runs each)\n")
    simulate_group("H", n_sims=10000)
    print()
    simulate_group("J", n_sims=10000)

    # Full tournament simulation (quick version)
    print("\n\nFULL TOURNAMENT SIMULATION (10,000 runs)\n")
    simulate_all(n_sims=10000)


if __name__ == "__main__":
    main()
