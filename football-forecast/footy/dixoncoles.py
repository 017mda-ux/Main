"""Time-weighted Dixon-Coles model, fitted by maximum likelihood.

The model
---------
For a match between home ``i`` and away ``j`` in competition ``c``::

    log lambda = level[c] + hfa[c] * (venue is not neutral) + attack[i] - defence[j]
    log mu     = level[c]                                   + attack[j] - defence[i]

Goals are Poisson around those rates, with the Dixon-Coles ``tau`` correction
applied to the four low-scoring cells to capture the well-known dependence
between 0-0/1-0/0-1/1-1 outcomes that independent Poissons get wrong.

Each match contributes with weight ``phi = exp(-xi * age_in_days)`` where
``xi = ln(2) / half_life_days``, so the half-life is the single knob that
controls how quickly form is forgotten.  It is a tunable parameter, not a
constant -- see :mod:`footy.tuning`.

Fitting on expected goals
-------------------------
``xg_weight`` blends expected goals with actual goals::

    target = xg_weight * xg + (1 - xg_weight) * goals

``xg_weight=1.0`` fits attack/defence purely on xG, ``0.0`` reduces exactly to
textbook Dixon-Coles on raw goals, and anything between tests the mix.  Because
the blended target is continuous, the Poisson kernel is evaluated in its
continuous form (``x log L - L - lgamma(x+1)``), which is the usual
quasi-likelihood treatment.  The ``tau`` correction is a property of *real*
scorelines, so it is always evaluated against the observed integer score
regardless of the blend.  Matches with no xG coverage silently fall back to
actual goals.

Identifiability
---------------
``attack`` and ``defence`` are each pinned to mean zero by a quadratic penalty;
the overall scoring level lives in ``level[c]``.  Both parameter blocks are also
ridge-shrunk toward zero, which keeps teams with a handful of matches (a common
situation in the Champions League) from acquiring absurd strengths.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from datetime import date
from typing import Iterable, Optional, Sequence

import numpy as np
from scipy.optimize import minimize
from scipy.special import gammaln

from .types import Match

TAU_FLOOR = 1e-9
RHO_BOUNDS = (-0.45, 0.45)


@dataclass
class DixonColesConfig:
    """Everything tunable about the fit."""

    half_life_days: float = 180.0
    xg_weight: float = 0.7
    ridge: float = 0.02
    max_goals: int = 12
    per_competition_hfa: bool = True
    neutral_kills_hfa: bool = True
    competition_weights: dict[str, float] = field(default_factory=dict)
    allow_unknown_teams: bool = False
    min_matches_per_team: int = 1

    def __post_init__(self) -> None:
        if not 0.0 <= self.xg_weight <= 1.0:
            raise ValueError("xg_weight must lie in [0, 1]")
        if self.half_life_days is not None and self.half_life_days <= 0:
            raise ValueError("half_life_days must be positive (or None for no decay)")
        if self.ridge < 0:
            raise ValueError("ridge must be non-negative")


def time_weights(
    match_dates: Sequence[date], as_of: date, half_life_days: Optional[float]
) -> np.ndarray:
    """Exponential decay on match age, normalised so the newest match weighs 1."""
    ages = np.array([(as_of - d).days for d in match_dates], dtype=float)
    ages = np.maximum(ages, 0.0)
    if half_life_days is None or not np.isfinite(half_life_days):
        return np.ones_like(ages)
    xi = math.log(2.0) / float(half_life_days)
    return np.exp(-xi * ages)


def _blend_targets(matches: Sequence[Match], xg_weight: float) -> tuple[np.ndarray, np.ndarray]:
    """Blend xG with goals, falling back to goals where xG is missing."""
    home = np.empty(len(matches))
    away = np.empty(len(matches))
    for k, m in enumerate(matches):
        w = xg_weight if m.has_xg else 0.0
        home[k] = w * (m.home_xg or 0.0) + (1.0 - w) * m.home_goals
        away[k] = w * (m.away_xg or 0.0) + (1.0 - w) * m.away_goals
    return home, away


@dataclass
class ScorelineForecast:
    """The single distribution every market is derived from."""

    home: str
    away: str
    competition: str
    home_rate: float
    away_rate: float
    rho: float
    matrix: np.ndarray  # matrix[i, j] = P(home scores i, away scores j)

    @property
    def max_goals(self) -> int:
        return self.matrix.shape[0] - 1

    def expected_goals(self) -> tuple[float, float]:
        idx = np.arange(self.matrix.shape[0])
        return float(idx @ self.matrix.sum(axis=1)), float(idx @ self.matrix.sum(axis=0))

    def outcome_probabilities(self) -> dict[str, float]:
        home = float(np.tril(self.matrix, -1).sum())
        draw = float(np.trace(self.matrix))
        away = float(np.triu(self.matrix, 1).sum())
        return {"H": home, "D": draw, "A": away}


@dataclass
class DixonColesModel:
    """A fitted model.  Immutable in spirit -- refit to move it forward in time."""

    attack: dict[str, float]
    defence: dict[str, float]
    level: dict[str, float]
    hfa: dict[str, float]
    rho: float
    config: DixonColesConfig
    as_of: date
    n_matches: int
    effective_matches: float
    log_likelihood: float
    converged: bool
    match_counts: dict[str, int] = field(default_factory=dict)

    # ---- introspection -------------------------------------------------
    @property
    def teams(self) -> list[str]:
        return sorted(self.attack)

    def home_advantage(self, competition: str) -> float:
        if competition in self.hfa:
            return self.hfa[competition]
        return self.hfa.get("__global__", next(iter(self.hfa.values()), 0.0))

    def team_strength(self) -> dict[str, dict[str, float]]:
        """Attack/defence/net ratings, sorted best-first by net rating."""
        rows = {
            t: {
                "attack": self.attack[t],
                "defence": self.defence[t],
                "net": self.attack[t] + self.defence[t],
                "matches": self.match_counts.get(t, 0),
            }
            for t in self.attack
        }
        return dict(sorted(rows.items(), key=lambda kv: -kv[1]["net"]))

    # ---- prediction ----------------------------------------------------
    def _lookup(self, team: str, which: str) -> float:
        table = self.attack if which == "attack" else self.defence
        if team in table:
            return table[team]
        if self.config.allow_unknown_teams:
            return 0.0
        raise KeyError(
            f"unknown team {team!r}; pass allow_unknown_teams=True to treat it as "
            "competition-average"
        )

    def rates(self, home: str, away: str, competition: str, neutral: bool = False) -> tuple[float, float]:
        level = self.level.get(competition)
        if level is None:
            if not self.config.allow_unknown_teams:
                raise KeyError(f"model was not fitted on competition {competition!r}")
            level = float(np.mean(list(self.level.values()))) if self.level else 0.0
        hfa = 0.0 if (neutral and self.config.neutral_kills_hfa) else self.home_advantage(competition)
        log_lam = level + hfa + self._lookup(home, "attack") - self._lookup(away, "defence")
        log_mu = level + self._lookup(away, "attack") - self._lookup(home, "defence")
        return math.exp(log_lam), math.exp(log_mu)

    def predict(
        self,
        home: str,
        away: str,
        competition: str,
        neutral: bool = False,
        max_goals: Optional[int] = None,
    ) -> ScorelineForecast:
        """Full scoreline matrix.  Every market in :mod:`footy.markets` reads
        from this one object, which is what keeps the markets consistent."""
        lam, mu = self.rates(home, away, competition, neutral=neutral)
        n = (max_goals if max_goals is not None else self.config.max_goals) + 1
        matrix = scoreline_matrix(lam, mu, self.rho, n_goals=n)
        return ScorelineForecast(home, away, competition, lam, mu, self.rho, matrix)

    def predict_match(self, match: Match, max_goals: Optional[int] = None) -> ScorelineForecast:
        return self.predict(
            match.home, match.away, match.competition, neutral=match.neutral, max_goals=max_goals
        )


def scoreline_matrix(lam: float, mu: float, rho: float, n_goals: int = 13) -> np.ndarray:
    """Dixon-Coles corrected scoreline distribution, truncated and renormalised."""
    idx = np.arange(n_goals)
    log_home = idx * math.log(lam) - lam - gammaln(idx + 1)
    log_away = idx * math.log(mu) - mu - gammaln(idx + 1)
    matrix = np.exp(log_home[:, None] + log_away[None, :])

    if n_goals >= 2:
        matrix[0, 0] *= 1.0 - lam * mu * rho
        matrix[0, 1] *= 1.0 + lam * rho
        matrix[1, 0] *= 1.0 + mu * rho
        matrix[1, 1] *= 1.0 - rho

    matrix = np.clip(matrix, 0.0, None)
    total = matrix.sum()
    if total <= 0:
        raise FloatingPointError("degenerate scoreline matrix")
    return matrix / total


# ---------------------------------------------------------------------------
# Fitting
# ---------------------------------------------------------------------------


def _tau_terms(gx: np.ndarray, gy: np.ndarray, lam: np.ndarray, mu: np.ndarray, rho: float):
    """tau and its partials, vectorised over matches."""
    tau = np.ones_like(lam)
    d_lam = np.zeros_like(lam)
    d_mu = np.zeros_like(lam)
    d_rho = np.zeros_like(lam)

    m00 = (gx == 0) & (gy == 0)
    m01 = (gx == 0) & (gy == 1)
    m10 = (gx == 1) & (gy == 0)
    m11 = (gx == 1) & (gy == 1)

    tau[m00] = 1.0 - lam[m00] * mu[m00] * rho
    d_lam[m00] = -mu[m00] * rho
    d_mu[m00] = -lam[m00] * rho
    d_rho[m00] = -lam[m00] * mu[m00]

    tau[m01] = 1.0 + lam[m01] * rho
    d_lam[m01] = rho
    d_rho[m01] = lam[m01]

    tau[m10] = 1.0 + mu[m10] * rho
    d_mu[m10] = rho
    d_rho[m10] = mu[m10]

    tau[m11] = 1.0 - rho
    d_rho[m11] = -1.0

    # Guard the log: if a parameter excursion pushes tau non-positive, floor it
    # and flatten its gradient so the optimiser is simply repelled from there.
    bad = tau < TAU_FLOOR
    if bad.any():
        tau = np.where(bad, TAU_FLOOR, tau)
        d_lam = np.where(bad, 0.0, d_lam)
        d_mu = np.where(bad, 0.0, d_mu)
        d_rho = np.where(bad, 0.0, d_rho)
    return tau, d_lam, d_mu, d_rho


def fit_dixon_coles(
    matches: Iterable[Match],
    as_of: Optional[date] = None,
    config: Optional[DixonColesConfig] = None,
) -> DixonColesModel:
    """Maximum-likelihood fit with time decay, xG blending and ridge shrinkage."""
    config = config or DixonColesConfig()
    played = [m for m in matches if m.played]
    if not played:
        raise ValueError("no played matches to fit on")

    if as_of is None:
        as_of = max(m.date for m in played)
    played = [m for m in played if m.date <= as_of]
    if not played:
        raise ValueError(f"no matches on or before as_of={as_of}")

    teams = sorted({m.home for m in played} | {m.away for m in played})
    comps = sorted({m.competition for m in played})
    t_idx = {t: i for i, t in enumerate(teams)}
    c_idx = {c: i for i, c in enumerate(comps)}
    n_t, n_c = len(teams), len(comps)

    home_i = np.array([t_idx[m.home] for m in played])
    away_i = np.array([t_idx[m.away] for m in played])
    comp_i = np.array([c_idx[m.competition] for m in played])
    gx = np.array([m.home_goals for m in played], dtype=float)
    gy = np.array([m.away_goals for m in played], dtype=float)
    x, y = _blend_targets(played, config.xg_weight)

    phi = time_weights([m.date for m in played], as_of, config.half_life_days)
    if config.competition_weights:
        phi = phi * np.array(
            [config.competition_weights.get(m.competition, 1.0) for m in played]
        )
    hfa_on = np.array(
        [0.0 if (m.neutral and config.neutral_kills_hfa) else 1.0 for m in played]
    )
    hfa_i = comp_i if config.per_competition_hfa else np.zeros(len(played), dtype=int)
    n_h = n_c if config.per_competition_hfa else 1

    counts: dict[str, int] = {}
    for m in played:
        counts[m.home] = counts.get(m.home, 0) + 1
        counts[m.away] = counts.get(m.away, 0) + 1
    thin = [t for t, c in counts.items() if c < config.min_matches_per_team]
    if thin:
        raise ValueError(
            f"{len(thin)} team(s) have fewer than {config.min_matches_per_team} matches: "
            f"{sorted(thin)[:5]}"
        )

    # Parameter layout: attack | defence | level | hfa | rho
    sl_att = slice(0, n_t)
    sl_def = slice(n_t, 2 * n_t)
    sl_lvl = slice(2 * n_t, 2 * n_t + n_c)
    sl_hfa = slice(2 * n_t + n_c, 2 * n_t + n_c + n_h)
    n_par = 2 * n_t + n_c + n_h + 1

    lgx = gammaln(x + 1.0) + gammaln(y + 1.0)
    centring = 10.0 * float(phi.sum()) / max(n_t, 1)  # scale-free sum-to-zero penalty

    def unpack(p: np.ndarray):
        return p[sl_att], p[sl_def], p[sl_lvl], p[sl_hfa], float(p[-1])

    def objective(p: np.ndarray) -> tuple[float, np.ndarray]:
        att, dfn, lvl, hfa, rho = unpack(p)
        log_lam = lvl[comp_i] + hfa[hfa_i] * hfa_on + att[home_i] - dfn[away_i]
        log_mu = lvl[comp_i] + att[away_i] - dfn[home_i]
        log_lam = np.clip(log_lam, -12.0, 4.0)
        log_mu = np.clip(log_mu, -12.0, 4.0)
        lam, mu = np.exp(log_lam), np.exp(log_mu)

        tau, dt_lam, dt_mu, dt_rho = _tau_terms(gx, gy, lam, mu, rho)
        ll_k = np.log(tau) + x * log_lam - lam + y * log_mu - mu - lgx
        ll = float(phi @ ll_k)

        # d/dlambda then chain to d/dlog(lambda)
        g_lam = (dt_lam / tau + x / lam - 1.0) * lam * phi
        g_mu = (dt_mu / tau + y / mu - 1.0) * mu * phi

        g = np.zeros(n_par)
        g[sl_att] = np.bincount(home_i, g_lam, n_t) + np.bincount(away_i, g_mu, n_t)
        g[sl_def] = -np.bincount(away_i, g_lam, n_t) - np.bincount(home_i, g_mu, n_t)
        g[sl_lvl] = np.bincount(comp_i, g_lam + g_mu, n_c)
        g[sl_hfa] = np.bincount(hfa_i, g_lam * hfa_on, n_h)
        g[-1] = float(np.sum(phi * dt_rho / tau))

        # Penalties: sum-to-zero on both blocks, plus ridge shrinkage.
        sa, sd = float(att.sum()), float(dfn.sum())
        pen = centring * (sa**2 + sd**2)
        pen += config.ridge * float(phi.sum()) * (float(att @ att) + float(dfn @ dfn))
        g[sl_att] -= 2.0 * centring * sa + 2.0 * config.ridge * float(phi.sum()) * att
        g[sl_def] -= 2.0 * centring * sd + 2.0 * config.ridge * float(phi.sum()) * dfn

        return -(ll - pen), -g

    x0 = np.zeros(n_par)
    mean_goals = float(np.average((x + y) / 2.0, weights=phi))
    x0[sl_lvl] = math.log(max(mean_goals, 0.05))
    x0[sl_hfa] = 0.25
    x0[-1] = -0.05

    bounds = [(None, None)] * (n_par - 1) + [RHO_BOUNDS]
    res = minimize(
        objective, x0, jac=True, method="L-BFGS-B", bounds=bounds,
        options={"maxiter": 2000, "ftol": 1e-11, "gtol": 1e-8},
    )

    att, dfn, lvl, hfa, rho = unpack(res.x)
    att = att - att.mean()
    dfn = dfn - dfn.mean()

    hfa_map = (
        {c: float(hfa[c_idx[c]]) for c in comps}
        if config.per_competition_hfa
        else {"__global__": float(hfa[0])}
    )

    return DixonColesModel(
        attack={t: float(att[i]) for t, i in t_idx.items()},
        defence={t: float(dfn[i]) for t, i in t_idx.items()},
        level={c: float(lvl[i]) for c, i in c_idx.items()},
        hfa=hfa_map,
        rho=float(rho),
        config=config,
        as_of=as_of,
        n_matches=len(played),
        effective_matches=float(phi.sum()),
        log_likelihood=-float(res.fun),
        converged=bool(res.success),
        match_counts=counts,
    )
