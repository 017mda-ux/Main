"""
Synthetic training data generator for World Cup / international match history.

In production, replace with real data from:
  - football-data.co.uk (free CSV downloads)
  - football-data.org API (free tier, 10 competitions)
  - StatsBomb open data (38 competitions free, includes xG)
  - Kaggle: "International football results from 1872 to 2024" dataset

This module generates realistic synthetic data for demonstration and
unit testing. Real data integration hooks are included.
"""

import random
import math
import datetime
from world_cup_2026.config import TEAM_ELO, CONFEDERATION


def generate_synthetic_match(team_a: str, team_b: str,
                              match_date: datetime.date,
                              match_type: str = "qualifier",
                              neutral: bool = True,
                              elo_a: float = None, elo_b: float = None,
                              rng: random.Random = None) -> dict:
    """
    Generate a synthetic match result consistent with team Elo ratings.
    Uses Poisson model seeded from Elo difference.
    """
    if rng is None:
        rng = random.Random()

    elo_a = elo_a or TEAM_ELO.get(team_a, 1600)
    elo_b = elo_b or TEAM_ELO.get(team_b, 1600)
    elo_diff = elo_a - elo_b + (50 if not neutral else 0)

    strength_ratio = 10 ** (elo_diff / 800)
    lambda_ = max(1.35 * strength_ratio, 0.2)
    mu_ = max(1.05 / strength_ratio, 0.2)

    def poisson_sample(lam):
        L = math.exp(-lam)
        k, p = 0, 1.0
        while p > L:
            k += 1
            p *= rng.random()
        return k - 1

    home_goals = poisson_sample(lambda_)
    away_goals = poisson_sample(mu_)

    return {
        "date": match_date,
        "home_team": team_a,
        "away_team": team_b,
        "home_goals": home_goals,
        "away_goals": away_goals,
        "match_type": match_type,
        "neutral": neutral,
        "stage": "group" if match_type in ("friendly", "qualifier") else "knockout",
    }


def generate_training_dataset(n_matches: int = 2000,
                               start_year: int = 2018,
                               seed: int = 42) -> list[dict]:
    """
    Generate synthetic historical international match dataset.
    Teams are drawn from WC 2026 participants; Elo ratings drive outcomes.
    """
    rng = random.Random(seed)
    teams = list(TEAM_ELO.keys())
    match_types = ["friendly", "qualifier", "qualifier", "confederation", "world_cup"]
    matches = []

    current_date = datetime.date(start_year, 1, 1)
    for _ in range(n_matches):
        # ~8 international matches per day globally during FIFA windows
        current_date += datetime.timedelta(days=rng.randint(1, 3))
        if current_date > datetime.date(2026, 6, 1):
            break

        team_a, team_b = rng.sample(teams, 2)
        # Higher chance of confederation-internal matches (more realistic)
        if rng.random() < 0.6:
            same_conf = [t for t in teams if CONFEDERATION.get(t) == CONFEDERATION.get(team_a)]
            if len(same_conf) > 1:
                team_b = rng.choice([t for t in same_conf if t != team_a])

        match_type = rng.choices(
            match_types,
            weights=[0.3, 0.35, 0.35, 0.1, 0.05], k=1
        )[0]

        neutral = match_type in ("world_cup", "confederation") or rng.random() < 0.15
        match = generate_synthetic_match(
            team_a, team_b, current_date, match_type, neutral, rng=rng
        )
        matches.append(match)

    return matches


def load_from_csv(filepath: str) -> list[dict]:
    """
    Load real match data from football-data.co.uk CSV format.

    Expected columns: Date, HomeTeam, AwayTeam, FTHG, FTAG
    (FTHG = Full Time Home Goals, FTAG = Full Time Away Goals)

    Usage:
        matches = load_from_csv("path/to/international_results.csv")
    """
    import csv
    matches = []
    with open(filepath, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            try:
                matches.append({
                    "date": datetime.date.fromisoformat(row.get("Date", "2020-01-01")),
                    "home_team": row["HomeTeam"],
                    "away_team": row["AwayTeam"],
                    "home_goals": int(row.get("FTHG", row.get("home_score", 0))),
                    "away_goals": int(row.get("FTAG", row.get("away_score", 0))),
                    "match_type": row.get("match_type", "qualifier"),
                    "neutral": row.get("neutral", "True").lower() == "true",
                })
            except (KeyError, ValueError):
                continue
    return matches


def load_statsbomb_xg(team_name: str, n_recent: int = 20) -> dict:
    """
    Load xG stats from StatsBomb open data (requires statsbombpy).

    Returns:
      {'xg_for': float, 'xg_against': float, 'shots_ot': float}

    Usage:
        from statsbombpy import sb
        # Install: pip install statsbombpy
        matches = sb.matches(competition_id=43, season_id=106)  # WC 2022
    """
    try:
        from statsbombpy import sb
        # This is a stub — in production, filter by team and recent n matches
        return {"xg_for": 1.5, "xg_against": 0.9, "shots_ot": 5.2}
    except ImportError:
        return {"xg_for": 1.35, "xg_against": 1.05, "shots_ot": 4.5}


def get_current_odds_from_api(api_key: str = None,
                               sport: str = "soccer_fifa_world_cup",
                               region: str = "us",
                               market: str = "h2h") -> list[dict]:
    """
    Fetch live match odds from The Odds API (free tier: 500 requests/month).
    https://the-odds-api.com

    Returns list of match odds dicts.
    """
    import requests

    if not api_key:
        print("No API key provided. Set ODDS_API_KEY environment variable.")
        return []

    url = (f"https://api.the-odds-api.com/v4/sports/{sport}/odds/"
           f"?apiKey={api_key}&regions={region}&markets={market}&oddsFormat=american")
    try:
        resp = requests.get(url, timeout=10)
        resp.raise_for_status()
        return resp.json()
    except Exception as e:
        print(f"Odds API error: {e}")
        return []
