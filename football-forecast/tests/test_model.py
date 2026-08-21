"""Model tests: the likelihood, its gradient, and parameter recovery."""

from __future__ import annotations

import math
from datetime import date, timedelta

import numpy as np
import pytest
import scipy.optimize as so

from footy import dixoncoles as dc
from footy.dixoncoles import (
    DixonColesConfig,
    fit_dixon_coles,
    scoreline_matrix,
    time_weights,
)
from footy.types import Match


def _sampled_matches(lam, mu, rho, n=6000, seed=0):
    rng = np.random.default_rng(seed)
    matrix = scoreline_matrix(lam, mu, rho, 13)
    flat = matrix.ravel() / matrix.sum()
    picks = rng.choice(flat.size, size=n, p=flat)
    out = []
    for k, p in enumerate(picks):
        i, j = divmod(int(p), matrix.shape[1])
        out.append(
            Match(date=date(2021, 1, 1), competition="X", home="A", away="B",
                  home_goals=i, away_goals=j, match_id=str(k))
        )
    return out


def test_time_weights_halve_at_the_half_life():
    as_of = date(2024, 1, 1)
    dates = [as_of, as_of - timedelta(days=100), as_of - timedelta(days=200)]
    w = time_weights(dates, as_of, half_life_days=100)
    assert w[0] == pytest.approx(1.0)
    assert w[1] == pytest.approx(0.5)
    assert w[2] == pytest.approx(0.25)


def test_time_weights_disabled_when_half_life_is_none():
    as_of = date(2024, 1, 1)
    dates = [as_of - timedelta(days=d) for d in (0, 500, 5000)]
    assert np.allclose(time_weights(dates, as_of, None), 1.0)


def test_scoreline_matrix_normalises_and_applies_the_correction():
    matrix = scoreline_matrix(1.4, 1.1, -0.1, 13)
    assert matrix.sum() == pytest.approx(1.0)
    assert (matrix >= 0).all()

    plain = scoreline_matrix(1.4, 1.1, 0.0, 13)
    # Dixon-Coles found rho < 0: more low-scoring draws (0-0 and 1-1) and fewer
    # 1-0 / 0-1 results than independent Poissons predict.
    assert matrix[0, 0] > plain[0, 0]
    assert matrix[1, 1] > plain[1, 1]
    assert matrix[1, 0] < plain[1, 0]
    assert matrix[0, 1] < plain[0, 1]

    # And the correction only touches those four cells.
    assert matrix[3, 2] / plain[3, 2] == pytest.approx(matrix[4, 0] / plain[4, 0])


def test_scoreline_matrix_reduces_to_independent_poisson_at_rho_zero():
    lam, mu = 1.6, 1.2
    matrix = scoreline_matrix(lam, mu, 0.0, 20)
    idx = np.arange(20)
    from scipy.stats import poisson

    expected = np.outer(poisson.pmf(idx, lam), poisson.pmf(idx, mu))
    assert np.allclose(matrix, expected / expected.sum(), atol=1e-12)


def test_analytic_gradient_matches_finite_differences():
    """The gradient is hand-derived, including the tau correction, so it needs
    a real check -- a wrong gradient makes L-BFGS converge to the wrong place
    quietly."""
    from footy.data import generate_synthetic_dataset

    data = generate_synthetic_dataset(seasons=1, seed=3)
    matches = [m for m in data.matches if m.played][:400]

    captured = {}
    original = so.minimize

    def spy(fun, x0, **kw):
        captured["fun"], captured["x0"] = fun, x0
        return original(fun, x0, **kw)

    dc.minimize = spy
    try:
        fit_dixon_coles(matches, config=DixonColesConfig(half_life_days=200, xg_weight=0.6))
    finally:
        dc.minimize = original

    fun, x0 = captured["fun"], captured["x0"]
    rng = np.random.default_rng(0)
    x = x0 + rng.normal(0, 0.15, x0.shape)
    x[-1] = -0.08  # keep rho inside its bounds

    _, analytic = fun(x)
    eps = 1e-6
    numeric = np.empty_like(x)
    for i in range(len(x)):
        up, down = x.copy(), x.copy()
        up[i] += eps
        down[i] -= eps
        numeric[i] = (fun(up)[0] - fun(down)[0]) / (2 * eps)

    rel = np.abs(numeric - analytic) / np.maximum(1.0, np.abs(numeric))
    assert rel.max() < 1e-5, f"worst relative gradient error {rel.max():.2e}"


@pytest.mark.parametrize("true_rho", [-0.15, -0.06, 0.0, 0.10])
def test_recovers_rho_and_rates(true_rho):
    matches = _sampled_matches(1.5, 1.1, true_rho, n=20000, seed=1)
    model = fit_dixon_coles(
        matches, config=DixonColesConfig(half_life_days=None, xg_weight=0.0, ridge=0.0)
    )
    assert model.rho == pytest.approx(true_rho, abs=0.02)
    lam, mu = model.rates("A", "B", "X")
    assert lam == pytest.approx(1.5, abs=0.05)
    assert mu == pytest.approx(1.1, abs=0.05)


def test_recovers_team_strengths_from_simulated_seasons():
    from footy.data import generate_synthetic_dataset

    data = generate_synthetic_dataset(seasons=3, seed=11, strength_drift=0.0)
    model = fit_dixon_coles(
        data.matches, config=DixonColesConfig(half_life_days=None, xg_weight=0.0)
    )
    teams = model.teams
    true_a = np.array([data.true_attack[t] for t in teams])
    fit_a = np.array([model.attack[t] for t in teams])
    true_d = np.array([data.true_defence[t] for t in teams])
    fit_d = np.array([model.defence[t] for t in teams])

    assert np.corrcoef(true_a, fit_a)[0, 1] > 0.85
    assert np.corrcoef(true_d, fit_d)[0, 1] > 0.85
    assert model.home_advantage("EPL") == pytest.approx(data.true_hfa, abs=0.08)


def test_attack_and_defence_are_identified_at_mean_zero():
    from footy.data import generate_synthetic_dataset

    data = generate_synthetic_dataset(seasons=1, seed=4)
    model = fit_dixon_coles(data.matches)
    assert sum(model.attack.values()) == pytest.approx(0.0, abs=1e-8)
    assert sum(model.defence.values()) == pytest.approx(0.0, abs=1e-8)


def test_xg_weight_zero_matches_a_pure_goals_fit():
    """xg_weight=0 must reduce exactly to textbook Dixon-Coles, whatever xG says."""
    from footy.data import generate_synthetic_dataset

    data = generate_synthetic_dataset(seasons=1, seed=6)
    stripped = [
        Match(date=m.date, competition=m.competition, home=m.home, away=m.away,
              home_goals=m.home_goals, away_goals=m.away_goals,
              neutral=m.neutral, match_id=m.match_id)
        for m in data.matches
    ]
    cfg = DixonColesConfig(xg_weight=0.0, half_life_days=200)
    with_xg = fit_dixon_coles(data.matches, config=cfg)
    without = fit_dixon_coles(stripped, config=cfg)
    assert with_xg.log_likelihood == pytest.approx(without.log_likelihood, rel=1e-9)
    for team in with_xg.teams:
        assert with_xg.attack[team] == pytest.approx(without.attack[team], abs=1e-6)


def test_missing_xg_falls_back_to_goals_per_match():
    """A match with no xG must not silently contribute zeros to the fit."""
    from footy.dixoncoles import _blend_targets

    played = Match(date=date(2023, 1, 1), competition="X", home="A", away="B",
                   home_goals=3, away_goals=1)
    with_xg = Match(date=date(2023, 1, 1), competition="X", home="A", away="B",
                    home_goals=3, away_goals=1, home_xg=2.0, away_xg=0.5)
    home, away = _blend_targets([played, with_xg], xg_weight=1.0)
    assert home[0] == 3.0 and away[0] == 1.0   # fell back to goals
    assert home[1] == 2.0 and away[1] == 0.5   # used xG


def test_unknown_team_raises_unless_allowed():
    from footy.data import generate_synthetic_dataset

    data = generate_synthetic_dataset(seasons=1, seed=8)
    model = fit_dixon_coles(data.matches)
    with pytest.raises(KeyError):
        model.predict("Nobody FC", "EPL 01", "EPL")

    model.config.allow_unknown_teams = True
    forecast = model.predict("Nobody FC", "EPL 01", "EPL")
    assert forecast.matrix.sum() == pytest.approx(1.0)


def test_neutral_venue_removes_home_advantage():
    from footy.data import generate_synthetic_dataset

    data = generate_synthetic_dataset(seasons=1, seed=9)
    model = fit_dixon_coles(data.matches)
    home_lam, _ = model.rates("EPL 01", "EPL 02", "EPL", neutral=False)
    neutral_lam, _ = model.rates("EPL 01", "EPL 02", "EPL", neutral=True)
    assert neutral_lam < home_lam
    assert math.log(home_lam / neutral_lam) == pytest.approx(model.home_advantage("EPL"), abs=1e-9)


def test_fit_rejects_empty_input():
    with pytest.raises(ValueError):
        fit_dixon_coles([])


def test_config_validates_its_inputs():
    with pytest.raises(ValueError):
        DixonColesConfig(xg_weight=1.5)
    with pytest.raises(ValueError):
        DixonColesConfig(half_life_days=-10)
