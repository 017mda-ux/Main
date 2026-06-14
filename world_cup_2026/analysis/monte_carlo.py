"""
Monte Carlo tournament simulation for World Cup 2026.

Methodology:
  - Simulate all 104 matches (48-team format: 12 groups of 4, then R32 → Final)
  - Each simulation draws match outcomes from Dixon-Coles probabilities
  - 50,000 iterations (reduces sampling error to < 0.3% per probability)
  - Tracks: group advancement, knockout progression, tournament winner
  - Conditions on real results as they happen (live in-tournament updating)

Group advancement rules (WC 2026 format):
  - Top 2 in each group advance automatically (24 teams)
  - 8 best 3rd-place finishers also advance (8 teams) → R32 total = 32 teams

Tiebreakers (in order):
  1. Points  2. Goal difference  3. Goals scored  4. Head-to-head
"""

import random
import math
from collections import defaultdict
from typing import Optional
from tqdm import tqdm

from world_cup_2026.config import WC2026_GROUPS, TEAM_ELO
from world_cup_2026.models.dixon_coles import predict_match, score_matrix, wdl_from_matrix
from world_cup_2026.models.elo_model import wdl_probabilities


# Pre-computed CDF cache: (team_a, team_b) → (flat_cdf, n_cols)
_MATCH_CDF_CACHE: dict = {}


def _get_match_cdf(team_a: str, team_b: str, dc_params: dict,
                   neutral: bool = True) -> tuple[list, int]:
    """Cache Dixon-Coles CDFs so each matchup is computed once, not per sim."""
    key = (team_a, team_b, neutral)
    if key not in _MATCH_CDF_CACHE:
        pred = predict_match(team_a, team_b, dc_params["team_params"],
                             neutral=neutral, rho=dc_params.get("rho", -0.134))
        mat = pred["score_matrix"]
        n_cols = len(mat[0])
        flat = [mat[i][j] for i in range(len(mat)) for j in range(n_cols)]
        cdf = []
        cumsum = 0.0
        for p in flat:
            cumsum += p
            cdf.append(cumsum)
        _MATCH_CDF_CACHE[key] = (cdf, n_cols)
    return _MATCH_CDF_CACHE[key]


def simulate_match(team_a: str, team_b: str,
                   dc_params: dict = None,
                   elo_ratings: dict = None,
                   neutral: bool = True,
                   rng: random.Random = None) -> tuple[int, int]:
    """
    Simulate a single match; returns (goals_a, goals_b).
    Uses Dixon-Coles score distribution if dc_params available (with CDF caching),
    else falls back to Elo-derived Poisson.
    """
    if rng is None:
        rng = random.Random()

    if dc_params:
        cdf, n_cols = _get_match_cdf(team_a, team_b, dc_params, neutral)
        r = rng.random()
        # Binary search is faster than linear scan for large CDFs
        import bisect
        idx = bisect.bisect_left(cdf, r)
        idx = min(idx, len(cdf) - 1)
        goals_a, goals_b = divmod(idx, n_cols)
        return goals_a, goals_b
    else:
        # Elo-derived Poisson (simpler fallback)
        elo = elo_ratings or TEAM_ELO
        elo_a = elo.get(team_a, 1600)
        elo_b = elo.get(team_b, 1600)
        elo_diff = elo_a - elo_b
        lambda_ = 1.35 * (10 ** (elo_diff / 800))  # attack proxy
        mu_ = 1.05 * (10 ** (-elo_diff / 800))     # defense proxy
        goals_a = _poisson_sample(lambda_, rng)
        goals_b = _poisson_sample(mu_, rng)
        return goals_a, goals_b


def _poisson_sample(lam: float, rng: random.Random) -> int:
    """Knuth algorithm for Poisson sampling."""
    L = math.exp(-lam)
    k, p = 0, 1.0
    while p > L:
        k += 1
        p *= rng.random()
    return k - 1


def simulate_group(teams: list[str],
                   dc_params: dict = None,
                   elo_ratings: dict = None,
                   fixed_results: dict = None,
                   rng: random.Random = None) -> list[dict]:
    """
    Simulate a full group of 4 teams (6 matches round-robin).
    fixed_results: dict of {(team_a, team_b): (goals_a, goals_b)} for played matches.

    Returns list of team standings sorted by points, GD, GF.
    """
    if rng is None:
        rng = random.Random()

    stats = {t: {"pts": 0, "gf": 0, "ga": 0, "gd": 0, "matches": 0} for t in teams}

    for i, team_a in enumerate(teams):
        for team_b in teams[i + 1:]:
            # Check if match already played
            key = (team_a, team_b)
            rev_key = (team_b, team_a)

            if fixed_results and key in fixed_results:
                ga, gb = fixed_results[key]
            elif fixed_results and rev_key in fixed_results:
                gb, ga = fixed_results[rev_key]
            else:
                ga, gb = simulate_match(team_a, team_b, dc_params, elo_ratings,
                                        neutral=True, rng=rng)

            # Update stats
            for team, gf, gc in [(team_a, ga, gb), (team_b, gb, ga)]:
                stats[team]["gf"] += gf
                stats[team]["ga"] += gc
                stats[team]["gd"] += gf - gc
                stats[team]["matches"] += 1

            if ga > gb:
                stats[team_a]["pts"] += 3
            elif ga == gb:
                stats[team_a]["pts"] += 1
                stats[team_b]["pts"] += 1
            else:
                stats[team_b]["pts"] += 3

    # Sort by pts, then GD, then GF
    standings = sorted(
        [{"team": t, **stats[t]} for t in teams],
        key=lambda x: (x["pts"], x["gd"], x["gf"]),
        reverse=True
    )
    return standings


def _third_place_score(standing: dict) -> tuple:
    """Scoring key for comparing 3rd-place finishers."""
    return (standing["pts"], standing["gd"], standing["gf"])


def simulate_tournament(dc_params: dict = None,
                         elo_ratings: dict = None,
                         fixed_results: dict = None,
                         groups: dict = None,
                         rng: random.Random = None) -> dict:
    """
    Simulate a complete WC 2026 tournament.
    Returns dict: {team: reached_stage} where stage ∈
    {group, r32, r16, qf, sf, final, winner}
    """
    if rng is None:
        rng = random.Random()
    if groups is None:
        groups = WC2026_GROUPS
    if fixed_results is None:
        fixed_results = {}

    results = {t: "group" for group in groups.values() for t in group}
    qualifiers = []  # 32 teams for R32
    third_place_finishers = []

    # ── Group Stage ──────────────────────────────────────────────────────────
    for group_name, teams in groups.items():
        # Filter fixed results for this group
        group_fixed = {k: v for k, v in fixed_results.items()
                       if k[0] in teams and k[1] in teams}
        standings = simulate_group(teams, dc_params, elo_ratings,
                                   group_fixed, rng)

        # 1st and 2nd advance
        for rank, s in enumerate(standings):
            if rank < 2:
                qualifiers.append({"team": s["team"], "group": group_name,
                                   "rank": rank + 1, **s})
                results[s["team"]] = "r32"
            elif rank == 2:
                third_place_finishers.append(
                    {"team": s["team"], "group": group_name, "rank": 3, **s}
                )

    # Best 8 third-place finishers also advance
    third_place_finishers.sort(key=_third_place_score, reverse=True)
    for s in third_place_finishers[:8]:
        qualifiers.append(s)
        results[s["team"]] = "r32"

    # ── Knockout Rounds ───────────────────────────────────────────────────────
    current_round = [q["team"] for q in qualifiers]
    stage_names = {32: "r32", 16: "r16", 8: "qf", 4: "sf", 2: "final"}

    while len(current_round) > 1:
        stage = stage_names.get(len(current_round), "knockout")
        next_round = []
        # Pair up sequentially (simplified; real WC bracket is structured)
        random.shuffle(current_round)  # simplified seeding
        for i in range(0, len(current_round), 2):
            if i + 1 >= len(current_round):
                next_round.append(current_round[i])
                continue
            team_a = current_round[i]
            team_b = current_round[i + 1]
            ga, gb = simulate_match(team_a, team_b, dc_params, elo_ratings,
                                    neutral=True, rng=rng)
            if ga == gb:
                # Knockout: extra time + pens → 50/50 after draw (simplified)
                winner = rng.choice([team_a, team_b])
            else:
                winner = team_a if ga > gb else team_b

            loser = team_b if winner == team_a else team_a
            results[winner] = stage
            next_round.append(winner)

        current_round = next_round

    if current_round:
        results[current_round[0]] = "winner"

    return results


def run_simulation(n_sims: int = 50000,
                   dc_params: dict = None,
                   elo_ratings: dict = None,
                   fixed_results: dict = None,
                   groups: dict = None,
                   seed: int = 42) -> dict:
    """
    Run n_sims Monte Carlo simulations. Returns tournament probabilities.

    Returns:
      {team: {stage: probability, ...}}
    """
    rng = random.Random(seed)
    stage_order = ["group", "r32", "r16", "qf", "sf", "final", "winner"]
    stage_counts = defaultdict(lambda: defaultdict(int))

    for _ in tqdm(range(n_sims), desc="Simulating WC 2026", unit="sim"):
        result = simulate_tournament(dc_params, elo_ratings,
                                     fixed_results, groups,
                                     random.Random(rng.randint(0, 2**31)))
        for team, stage in result.items():
            # Count reaching each stage (stage = best stage reached)
            reached_idx = stage_order.index(stage)
            for s in stage_order[:reached_idx + 1]:
                stage_counts[team][s] += 1

    # Convert to probabilities
    probs = {}
    for team, counts in stage_counts.items():
        probs[team] = {
            stage: round(counts.get(stage, 0) / n_sims, 4)
            for stage in stage_order
        }

    return dict(sorted(probs.items(),
                        key=lambda x: x[1].get("winner", 0), reverse=True))


def print_tournament_odds(probs: dict, top_n: int = 20):
    """Print tournament odds in a clean table with implied American odds."""
    header = (f"{'TEAM':<20} {'Win%':>6} {'Final%':>7} {'SF%':>6} "
              f"{'QF%':>6} {'R16%':>6} {'Impl.Odds':>10}")
    print(header)
    print("─" * len(header))
    for team, p in list(probs.items())[:top_n]:
        win_p = p.get("winner", 0)
        final_p = p.get("final", 0)
        sf_p = p.get("sf", 0)
        qf_p = p.get("qf", 0)
        r16_p = p.get("r16", 0)
        if win_p > 0:
            american = int(round(100 / win_p - 100))
            odds_str = f"+{american}" if american >= 0 else str(american)
        else:
            odds_str = "N/A"
        print(f"{team:<20} {win_p:>5.1%}  {final_p:>6.1%}  {sf_p:>5.1%}  "
              f"{qf_p:>5.1%}  {r16_p:>5.1%}  {odds_str:>10}")
