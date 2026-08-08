import math

from kalshi_ev.fees import fee_cents, fee_cents_exact, effective_cost_cents
from kalshi_ev.ev import ev_yes_cents, ev_no_cents, kelly_fraction, evaluate_market


def test_fee_exact_at_50c():
    # 0.07 * 0.5 * 0.5 = 1.75 cents
    assert math.isclose(fee_cents_exact(50), 1.75)


def test_fee_rounds_up_per_order():
    assert fee_cents(50, 1) == 2          # 1.75 -> 2
    assert fee_cents(10, 1) == 1          # 0.63 -> 1
    assert fee_cents(50, 100) == 175      # exact multiple stays
    assert fee_cents(10, 100) == 63


def test_fee_symmetric_and_peaks_at_50():
    assert math.isclose(fee_cents_exact(30), fee_cents_exact(70))
    assert fee_cents_exact(50) > fee_cents_exact(49) > fee_cents_exact(10)


def test_ev_yes_zero_at_fair_price_plus_fee():
    # q = effective cost / 100 -> EV exactly zero
    q = effective_cost_cents(40) / 100.0
    assert math.isclose(ev_yes_cents(q, 40), 0.0, abs_tol=1e-9)


def test_ev_no_complements_yes():
    # buying NO at (100 - p) with prob 1-q mirrors YES at p with q
    assert math.isclose(ev_no_cents(0.3, 60), ev_yes_cents(0.7, 60))


def test_kelly_zero_when_no_edge():
    assert kelly_fraction(0.5, cost_cents=55.0) == 0.0
    assert kelly_fraction(0.4, cost_cents=100.0) == 0.0


def test_kelly_known_value():
    # cost 50c, payout 100c => even odds (b=1); q=0.6 => f* = 2q-1 = 0.2
    assert math.isclose(kelly_fraction(0.6, 50.0), 0.2)


def test_evaluate_market_picks_correct_side():
    # model says 80% yes, but yes asks 60c: strong yes edge
    d = evaluate_market(0.8, yes_ask_cents=60, no_ask_cents=42, min_ev_cents=2.0)
    assert d is not None and d.side == "yes"
    assert d.ev_cents > 15

    # model says 20% yes, no asks 60c: strong no edge
    d = evaluate_market(0.2, yes_ask_cents=42, no_ask_cents=60, min_ev_cents=2.0)
    assert d is not None and d.side == "no"


def test_evaluate_market_respects_threshold():
    # fair market: 50/50 with 51c asks both sides -> negative EV after fees
    assert evaluate_market(0.5, 51, 51, min_ev_cents=2.0) is None


def test_stake_contracts_caps_fraction():
    d = evaluate_market(0.9, yes_ask_cents=50, no_ask_cents=None, min_ev_cents=1.0)
    assert d is not None
    # bankroll $1000; max_fraction 5% -> at most $50 / 50c = 100 contracts
    assert d.stake_contracts(100_000, kelly_multiplier=1.0, max_fraction=0.05) == 100
    # tiny kelly multiplier shrinks it
    assert d.stake_contracts(100_000, kelly_multiplier=0.01, max_fraction=0.05) < 100
