"""Loading match data and odds.

Two real-world shapes are supported out of the box:

* **football-data.co.uk** season CSVs (``E0.csv`` for the Premier League,
  ``SP1.csv`` for La Liga) -- results plus a wide block of bookmaker prices,
  including the ``*C*`` closing columns that the backtester wants.
* A **generic CSV** with a user-supplied column mapping, for xG feeds
  (Understat, FBref exports) or any private dataset.

Plus :func:`generate_synthetic_dataset`, which simulates leagues *and* a
bookmaker from a known ground truth.  That makes the whole pipeline runnable
with no network access, gives the tests something honest to assert against, and
lets you sanity-check the backtester on a world where you know whether an edge
actually exists.
"""

from __future__ import annotations

import csv
import math
import re
from dataclasses import dataclass, field
from datetime import date, timedelta
from pathlib import Path
from typing import Iterable, Mapping, Optional, Sequence

import numpy as np

from .types import (
    CHAMPIONS_LEAGUE,
    LA_LIGA,
    PREMIER_LEAGUE,
    BookOdds,
    Match,
    _as_date,
)

# --------------------------------------------------------------------------
# Team-name normalisation
# --------------------------------------------------------------------------

TEAM_ALIASES: dict[str, str] = {
    # England
    "man united": "Manchester United",
    "man utd": "Manchester United",
    "manchester utd": "Manchester United",
    "man city": "Manchester City",
    "spurs": "Tottenham",
    "tottenham hotspur": "Tottenham",
    "wolves": "Wolverhampton Wanderers",
    "wolverhampton": "Wolverhampton Wanderers",
    "newcastle utd": "Newcastle United",
    "newcastle": "Newcastle United",
    "nott'm forest": "Nottingham Forest",
    "nottm forest": "Nottingham Forest",
    "sheffield weds": "Sheffield Wednesday",
    "sheffield utd": "Sheffield United",
    "west brom": "West Bromwich Albion",
    "west ham": "West Ham United",
    "brighton": "Brighton & Hove Albion",
    "leicester": "Leicester City",
    "leeds": "Leeds United",
    "norwich": "Norwich City",
    "stoke": "Stoke City",
    "swansea": "Swansea City",
    "cardiff": "Cardiff City",
    "hull": "Hull City",
    "birmingham": "Birmingham City",
    # Spain
    "ath madrid": "Atletico Madrid",
    "atletico": "Atletico Madrid",
    "atlético madrid": "Atletico Madrid",
    "ath bilbao": "Athletic Club",
    "athletic bilbao": "Athletic Club",
    "sociedad": "Real Sociedad",
    "espanol": "Espanyol",
    "betis": "Real Betis",
    "vallecano": "Rayo Vallecano",
    "la coruna": "Deportivo La Coruna",
    "celta": "Celta Vigo",
    "barcelona": "Barcelona",
    "fc barcelona": "Barcelona",
    "real madrid cf": "Real Madrid",
    # Europe
    "bayern munich": "Bayern Munich",
    "bayern münchen": "Bayern Munich",
    "fc bayern munich": "Bayern Munich",
    "paris sg": "Paris Saint-Germain",
    "psg": "Paris Saint-Germain",
    "inter": "Inter Milan",
    "internazionale": "Inter Milan",
    "ac milan": "Milan",
    "sporting cp": "Sporting Lisbon",
    "dortmund": "Borussia Dortmund",
    "bayer leverkusen": "Bayer Leverkusen",
}

_SUFFIX_NOISE = re.compile(r"\b(fc|cf|afc|sc|ac|ss|us|club)\b", re.IGNORECASE)


def normalise_team(name: str) -> str:
    """Canonicalise a team name so odds feeds and xG feeds join cleanly.

    Name mismatches are the single most common source of silent data loss when
    stitching an xG source onto an odds source, so this runs on every load.
    """
    if name is None:
        raise ValueError("team name is required")
    cleaned = " ".join(str(name).replace(".", " ").split()).strip()
    key = cleaned.lower()
    if key in TEAM_ALIASES:
        return TEAM_ALIASES[key]
    stripped = " ".join(_SUFFIX_NOISE.sub(" ", key).split())
    if stripped in TEAM_ALIASES:
        return TEAM_ALIASES[stripped]
    return cleaned


# --------------------------------------------------------------------------
# football-data.co.uk
# --------------------------------------------------------------------------

FOOTBALL_DATA_COMPETITIONS = {"E0": PREMIER_LEAGUE, "SP1": LA_LIGA}

#: ``(home, draw, away)`` column triples, closing prices first.
_1X2_COLUMNS: Sequence[tuple[str, str, str, bool]] = (
    ("PSCH", "PSCD", "PSCA", True),      # Pinnacle closing -- sharpest available
    ("B365CH", "B365CD", "B365CA", True),
    ("AvgCH", "AvgCD", "AvgCA", True),   # market average closing
    ("MaxCH", "MaxCD", "MaxCA", True),
    ("PSH", "PSD", "PSA", False),
    ("B365H", "B365D", "B365A", False),
    ("AvgH", "AvgD", "AvgA", False),
)

_OU_COLUMNS: Sequence[tuple[str, str, str, bool]] = (
    ("P>2.5C", "P<2.5C", "2.5", True),
    ("B365>2.5C", "B365<2.5C", "2.5", True),
    ("Avg>2.5C", "Avg<2.5C", "2.5", True),
    ("B365>2.5", "B365<2.5", "2.5", False),
)

_AH_COLUMNS: Sequence[tuple[str, str, str, bool]] = (
    ("AHCh", "PCAHH", "PCAHA", True),
    ("AHCh", "B365CAHH", "B365CAHA", True),
    ("AHh", "B365AHH", "B365AHA", False),
)


def _f(row: Mapping[str, str], key: str) -> Optional[float]:
    raw = row.get(key)
    if raw is None or str(raw).strip() == "":
        return None
    try:
        return float(raw)
    except ValueError:
        return None


def load_football_data_csv(
    path: str | Path,
    competition: Optional[str] = None,
    season: Optional[str] = None,
) -> tuple[list[Match], list[BookOdds]]:
    """Read one football-data.co.uk season CSV.

    Returns matches and their odds books.  Where both closing and opening
    prices exist, both are recorded and tagged, because the backtester needs to
    tell them apart -- the closing line is the benchmark, the opener is not.
    """
    path = Path(path)
    if competition is None:
        competition = FOOTBALL_DATA_COMPETITIONS.get(path.stem, path.stem)

    matches: list[Match] = []
    books: list[BookOdds] = []
    with path.open(newline="", encoding="utf-8-sig", errors="replace") as fh:
        for row in csv.DictReader(fh):
            if not row.get("HomeTeam") or not row.get("Date"):
                continue
            hg, ag = _f(row, "FTHG"), _f(row, "FTAG")
            match = Match(
                date=_as_date(row["Date"]),
                competition=competition,
                home=normalise_team(row["HomeTeam"]),
                away=normalise_team(row["AwayTeam"]),
                home_goals=int(hg) if hg is not None else None,
                away_goals=int(ag) if ag is not None else None,
                season=season,
            )
            matches.append(match)
            books.append(_odds_from_football_data_row(row, match))
    return matches, books


def _odds_from_football_data_row(row: Mapping[str, str], match: Match) -> BookOdds:
    book = BookOdds(match_id=match.match_id, kickoff=match.date)
    for h_col, d_col, a_col, closing in _1X2_COLUMNS:
        h, d, a = _f(row, h_col), _f(row, d_col), _f(row, a_col)
        if None in (h, d, a):
            continue
        maker = h_col.replace("CH", "").replace("H", "") or "book"
        for sel, price in (("H", h), ("D", d), ("A", a)):
            book.add("1X2", sel, price, bookmaker=maker, is_closing=closing)
        break  # first available triple wins; closing is listed first

    for over_col, under_col, line, closing in _OU_COLUMNS:
        o, u = _f(row, over_col), _f(row, under_col)
        if None in (o, u):
            continue
        book.add(f"ou_{line}", "Over", o, is_closing=closing)
        book.add(f"ou_{line}", "Under", u, is_closing=closing)
        break

    for line_col, home_col, away_col, closing in _AH_COLUMNS:
        line, h, a = _f(row, line_col), _f(row, home_col), _f(row, away_col)
        if None in (line, h, a):
            continue
        book.add(f"ah_{line:+g}", "Home", h, is_closing=closing)
        book.add(f"ah_{line:+g}", "Away", a, is_closing=closing)
        break
    return book


# --------------------------------------------------------------------------
# Generic / xG CSVs
# --------------------------------------------------------------------------

DEFAULT_COLUMN_MAP = {
    "date": "date",
    "competition": "competition",
    "home": "home",
    "away": "away",
    "home_goals": "home_goals",
    "away_goals": "away_goals",
    "home_xg": "home_xg",
    "away_xg": "away_xg",
    "neutral": "neutral",
}


def load_matches_csv(
    path: str | Path,
    column_map: Optional[Mapping[str, str]] = None,
    competition: Optional[str] = None,
) -> list[Match]:
    """Read a match CSV using a column mapping (``field -> csv column``)."""
    cmap = dict(DEFAULT_COLUMN_MAP)
    if column_map:
        cmap.update(column_map)

    out: list[Match] = []
    with Path(path).open(newline="", encoding="utf-8-sig", errors="replace") as fh:
        for row in csv.DictReader(fh):
            comp = competition or row.get(cmap["competition"]) or "unknown"
            hg, ag = _f(row, cmap["home_goals"]), _f(row, cmap["away_goals"])
            neutral_raw = str(row.get(cmap["neutral"], "")).strip().lower()
            out.append(
                Match(
                    date=_as_date(row[cmap["date"]]),
                    competition=comp,
                    home=normalise_team(row[cmap["home"]]),
                    away=normalise_team(row[cmap["away"]]),
                    home_goals=int(hg) if hg is not None else None,
                    away_goals=int(ag) if ag is not None else None,
                    home_xg=_f(row, cmap["home_xg"]),
                    away_xg=_f(row, cmap["away_xg"]),
                    neutral=neutral_raw in {"1", "true", "yes", "y"},
                )
            )
    return out


def attach_xg(
    matches: Sequence[Match], xg_matches: Sequence[Match], date_tolerance_days: int = 2
) -> tuple[list[Match], list[Match]]:
    """Join an xG feed onto results by ``(home, away)`` within a date window.

    Returns ``(merged, unmatched_xg)``.  The unmatched list is deliberately
    surfaced rather than swallowed -- a long tail there almost always means a
    team-name alias is missing, and silently fitting on half your xG is worse
    than not using xG at all.
    """
    index: dict[tuple[str, str], list[Match]] = {}
    for x in xg_matches:
        index.setdefault((x.home, x.away), []).append(x)

    merged: list[Match] = []
    used: set[int] = set()
    for m in matches:
        best, best_gap = None, None
        for cand in index.get((m.home, m.away), []):
            if id(cand) in used:
                continue
            gap = abs((cand.date - m.date).days)
            if gap <= date_tolerance_days and (best_gap is None or gap < best_gap):
                best, best_gap = cand, gap
        if best is not None and best.has_xg:
            used.add(id(best))
            merged.append(
                Match(
                    date=m.date, competition=m.competition, home=m.home, away=m.away,
                    home_goals=m.home_goals, away_goals=m.away_goals,
                    home_xg=best.home_xg, away_xg=best.away_xg,
                    neutral=m.neutral, match_id=m.match_id, season=m.season,
                )
            )
        else:
            merged.append(m)

    unmatched = [x for x in xg_matches if id(x) not in used]
    return merged, unmatched


def coverage_report(matches: Sequence[Match]) -> dict[str, dict[str, float]]:
    """Per-competition match counts and xG coverage -- run this before trusting a fit."""
    out: dict[str, dict[str, float]] = {}
    for m in matches:
        row = out.setdefault(m.competition, {"matches": 0, "played": 0, "with_xg": 0})
        row["matches"] += 1
        row["played"] += int(m.played)
        row["with_xg"] += int(m.has_xg)
    for row in out.values():
        row["xg_coverage"] = row["with_xg"] / row["played"] if row["played"] else 0.0
    return out


# --------------------------------------------------------------------------
# Synthetic world
# --------------------------------------------------------------------------


@dataclass
class SyntheticDataset:
    """Simulated matches plus the ground truth that generated them.

    Team strengths follow a random walk, so form is genuinely time-varying and
    the half-life parameter has real work to do.  ``attack_at``/``defence_at``
    recover the true strength on any given date, which makes it possible to
    compute the irreducible score floor and check how close a fit gets to it.
    """

    matches: list[Match]
    odds: dict[str, BookOdds]
    true_hfa: float
    true_rho: float
    true_level: dict[str, float]
    start: date
    attack_paths: dict[str, np.ndarray] = field(default_factory=dict)
    defence_paths: dict[str, np.ndarray] = field(default_factory=dict)

    def week_index(self, day: date) -> int:
        weeks = max(0, (day - self.start).days // 7)
        n = len(next(iter(self.attack_paths.values()))) if self.attack_paths else 1
        return min(weeks, n - 1)

    def attack_at(self, team: str, day: date) -> float:
        return float(self.attack_paths[team][self.week_index(day)])

    def defence_at(self, team: str, day: date) -> float:
        return float(self.defence_paths[team][self.week_index(day)])

    def true_rates(self, match: Match) -> tuple[float, float]:
        """The rates that actually generated this match."""
        level = self.true_level[match.competition]
        hfa = 0.0 if match.neutral else self.true_hfa
        lam = math.exp(
            level + hfa + self.attack_at(match.home, match.date)
            - self.defence_at(match.away, match.date)
        )
        mu = math.exp(
            level + self.attack_at(match.away, match.date)
            - self.defence_at(match.home, match.date)
        )
        return lam, mu

    @property
    def true_attack(self) -> dict[str, float]:
        """Time-averaged attack strength, for coarse comparisons against a fit."""
        return {t: float(np.mean(p)) for t, p in self.attack_paths.items()}

    @property
    def true_defence(self) -> dict[str, float]:
        return {t: float(np.mean(p)) for t, p in self.defence_paths.items()}


def _sample_scoreline(rng: np.random.Generator, lam: float, mu: float, rho: float) -> tuple[int, int]:
    from .dixoncoles import scoreline_matrix

    matrix = scoreline_matrix(lam, mu, rho, n_goals=11)
    flat = matrix.ravel()
    pick = rng.choice(flat.size, p=flat / flat.sum())
    return int(pick // matrix.shape[1]), int(pick % matrix.shape[1])


def _round_robin(teams: Sequence[str]) -> list[tuple[str, str]]:
    """Double round-robin fixture list (each pair home and away)."""
    return [(h, a) for h in teams for a in teams if h != a]


def generate_synthetic_dataset(
    seasons: int = 3,
    start: date = date(2021, 8, 1),
    seed: int = 7,
    n_epl: int = 20,
    n_laliga: int = 20,
    book_noise: float = 0.10,
    closing_noise: float = 0.05,
    overround: float = 1.06,
    xg_dispersion: float = 3.0,
    strength_drift: float = 0.022,
) -> SyntheticDataset:
    """Simulate leagues, a Champions League, and a bookmaker with a known truth.

    Team strengths follow a weekly random walk of size ``strength_drift``, so
    form genuinely decays and a finite half-life is genuinely the right answer.
    The bookmaker prices the *true* probabilities perturbed by noise, then adds
    an overround; closing prices carry less noise than openers, which is what
    makes the closing line the hard benchmark it is in reality.

    Note that this simulated bookmaker is *much* sharper than a real one -- it
    knows the true model and only jitters it.  Treat a backtest here as a test
    of the machinery, not as evidence that a strategy works.
    """
    rng = np.random.default_rng(seed)
    epl = [f"EPL {i + 1:02d}" for i in range(n_epl)]
    laliga = [f"LAL {i + 1:02d}" for i in range(n_laliga)]
    teams = epl + laliga

    n_weeks = seasons * 53 + 4
    attack_paths: dict[str, np.ndarray] = {}
    defence_paths: dict[str, np.ndarray] = {}
    for t in teams:
        a0, d0 = float(rng.normal(0, 0.32)), float(rng.normal(0, 0.28))
        attack_paths[t] = a0 + np.concatenate(
            [[0.0], np.cumsum(rng.normal(0, strength_drift, n_weeks - 1))]
        )
        defence_paths[t] = d0 + np.concatenate(
            [[0.0], np.cumsum(rng.normal(0, strength_drift, n_weeks - 1))]
        )
    # Centre each week so the overall scoring level stays in ``level``.
    a_stack = np.vstack([attack_paths[t] for t in teams])
    d_stack = np.vstack([defence_paths[t] for t in teams])
    a_stack -= a_stack.mean(axis=0, keepdims=True)
    d_stack -= d_stack.mean(axis=0, keepdims=True)
    for i, t in enumerate(teams):
        attack_paths[t], defence_paths[t] = a_stack[i], d_stack[i]

    level = {PREMIER_LEAGUE: math.log(1.38), LA_LIGA: math.log(1.30), CHAMPIONS_LEAGUE: math.log(1.34)}
    hfa, rho = 0.26, -0.06

    matches: list[Match] = []
    books: dict[str, BookOdds] = {}

    def week_of(day: date) -> int:
        return min(max(0, (day - start).days // 7), n_weeks - 1)

    def emit(day: date, comp: str, home: str, away: str, neutral: bool = False) -> None:
        w = week_of(day)
        lam = math.exp(
            level[comp] + (0.0 if neutral else hfa) + attack_paths[home][w] - defence_paths[away][w]
        )
        mu = math.exp(level[comp] + attack_paths[away][w] - defence_paths[home][w])
        hg, ag = _sample_scoreline(rng, lam, mu, rho)

        # xG: unbiased, noisy observation of the underlying rate.
        hxg = float(rng.gamma(xg_dispersion, lam / xg_dispersion))
        axg = float(rng.gamma(xg_dispersion, mu / xg_dispersion))

        match = Match(
            date=day, competition=comp, home=home, away=away,
            home_goals=hg, away_goals=ag, home_xg=round(hxg, 2), away_xg=round(axg, 2),
            neutral=neutral,
        )
        matches.append(match)
        books[match.match_id] = _synthetic_book(
            rng, match, lam, mu, rho, book_noise, closing_noise, overround
        )

    day = start
    for _ in range(seasons):
        season_start = day
        for comp, roster in ((PREMIER_LEAGUE, epl), (LA_LIGA, laliga)):
            fixtures = _round_robin(roster)
            rng.shuffle(fixtures)  # type: ignore[arg-type]
            per_round = max(len(roster) // 2, 1)
            for k in range(0, len(fixtures), per_round):
                match_day = season_start + timedelta(days=(k // per_round) * 7)
                for home, away in fixtures[k : k + per_round]:
                    emit(match_day, comp, home, away)

        # Champions League: the strongest sides from both leagues, which is what
        # links the two league scales into one parameter space.
        w0 = week_of(season_start)
        strength = {t: attack_paths[t][w0] + defence_paths[t][w0] for t in teams}
        ucl = sorted(epl, key=lambda t: -strength[t])[:8] + sorted(laliga, key=lambda t: -strength[t])[:8]
        ucl_fixtures = _round_robin(ucl)
        rng.shuffle(ucl_fixtures)  # type: ignore[arg-type]
        for n, (home, away) in enumerate(ucl_fixtures[:96]):
            emit(season_start + timedelta(days=21 + (n // 8) * 21), CHAMPIONS_LEAGUE, home, away)
        emit(season_start + timedelta(days=290), CHAMPIONS_LEAGUE, ucl[0], ucl[1], neutral=True)

        day = season_start + timedelta(days=365)

    matches.sort(key=lambda m: (m.date, m.competition, m.home))
    return SyntheticDataset(
        matches=matches, odds=books, true_hfa=hfa, true_rho=rho, true_level=level,
        start=start, attack_paths=attack_paths, defence_paths=defence_paths,
    )


def _synthetic_book(
    rng: np.random.Generator,
    match: Match,
    lam: float,
    mu: float,
    rho: float,
    book_noise: float,
    closing_noise: float,
    overround: float,
) -> BookOdds:
    from .dixoncoles import scoreline_matrix
    from .markets import build_markets

    matrix = scoreline_matrix(lam, mu, rho, n_goals=13)
    truth = {
        "H": float(np.tril(matrix, -1).sum()),
        "D": float(np.trace(matrix)),
        "A": float(np.triu(matrix, 1).sum()),
    }

    book = BookOdds(match_id=match.match_id, kickoff=match.date)
    for tag, noise, closing in (("open", book_noise, False), ("close", closing_noise, True)):
        probs = np.array([truth["H"], truth["D"], truth["A"]])
        probs = np.clip(probs * np.exp(rng.normal(0, noise, 3)), 1e-4, None)
        probs /= probs.sum()
        for sel, p in zip(("H", "D", "A"), probs):
            book.add("1X2", sel, _price(p, overround), bookmaker=tag, is_closing=closing)

    # Totals and one handicap line, priced off the same simulated matrix so the
    # synthetic bookmaker is at least internally coherent.
    markets = build_markets(
        _ForecastShim(matrix), totals_lines=(2.5,), handicap_lines=(-0.5,)
    )
    for key, sels in markets.items():
        if key == "1X2":
            continue
        for name, sel in sels.items():
            live = sel.win_prob + sel.lose_prob
            if live <= 0:
                continue
            p = np.clip((sel.win_prob / live) * math.exp(rng.normal(0, closing_noise)), 1e-4, 0.999)
            book.add(key, name, _price(p, math.sqrt(overround)), is_closing=True)
    return book


def _price(prob: float, vig: float, floor: float = 1.01) -> float:
    """Decimal price for a probability, floored the way a real book floors it."""
    return round(max(floor, 1.0 / (float(prob) * vig)), 3)


class _ForecastShim:
    """Minimal duck-type of :class:`ScorelineForecast` for the synthetic book."""

    def __init__(self, matrix: np.ndarray) -> None:
        self.matrix = matrix
        self.home = self.away = self.competition = ""


def write_matches_csv(matches: Iterable[Match], path: str | Path) -> Path:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.writer(fh)
        writer.writerow(
            ["date", "competition", "home", "away", "home_goals", "away_goals",
             "home_xg", "away_xg", "neutral"]
        )
        for m in matches:
            writer.writerow(
                [m.date.isoformat(), m.competition, m.home, m.away, m.home_goals,
                 m.away_goals, m.home_xg, m.away_xg, int(m.neutral)]
            )
    return path
