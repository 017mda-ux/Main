import math
import random

import pytest

from kalshi_ev.backtest import run_backtest
from kalshi_ev.data import Snapshot


def _logit(p):
    return math.log(p / (1 - p))


def _sigmoid(z):
    return 1 / (1 + math.exp(-z))


def _snapshots(n, true_b, seed=11):
    """Synthetic settled markets: price p, true prob sigmoid(b*logit(p)).
    true_b < 1 simulates a market with strong favorite-longshot bias."""
    rng = random.Random(seed)
    out = []
    for i in range(n):
        p = rng.uniform(0.05, 0.95)
        q = _sigmoid(true_b * _logit(p))
        out.append(Snapshot(
            ticker=f"SYN-{i}", event_ticker=f"EVT-{i // 5}", series_ticker="SYN",
            price_cents=p * 100, outcome=1 if rng.random() < q else 0,
            close_ts=1_700_000_000 + i * 3600, horizon_hours=24,
        ))
    return out


def test_accounting_identity():
    result = run_backtest(_snapshots(2000, true_b=0.55), bankroll_cents=100_000)
    assert math.isclose(sum(t.pnl_cents for t in result.trades), result.pnl_cents)
    assert math.isclose(100_000 + result.pnl_cents, result.final_bankroll_cents)
    assert result.n_wins <= result.n_trades
    assert result.n_train + result.n_test == result.n_snapshots


def test_profitable_on_heavily_biased_market():
    # b=0.55 is a much bigger miscalibration than reality; the point is
    # that the engine converts a real probability edge into positive P&L.
    result = run_backtest(_snapshots(3000, true_b=0.55), bankroll_cents=100_000,
                          min_ev_cents=3.0, slippage_cents=2)
    assert result.n_trades > 50
    assert result.pnl_cents > 0
    assert result.model_brier < result.market_brier  # out of sample


def test_no_trades_on_calibrated_market_with_threshold():
    # a fair market plus fees, slippage, and a 3c EV floor should trade
    # rarely-to-never and certainly not print big profits
    result = run_backtest(_snapshots(2000, true_b=1.0), bankroll_cents=100_000,
                          min_ev_cents=3.0, slippage_cents=2)
    assert result.n_trades < 100  # fitted b hovers near 1; few false edges


def test_requires_minimum_data():
    with pytest.raises(ValueError):
        run_backtest(_snapshots(20, true_b=0.8))


def test_walk_forward_split_is_chronological():
    snaps = _snapshots(500, true_b=0.7)
    random.Random(3).shuffle(snaps)  # engine must re-sort internally
    result = run_backtest(snaps, bankroll_cents=100_000)
    assert result.n_train == 300 and result.n_test == 200
