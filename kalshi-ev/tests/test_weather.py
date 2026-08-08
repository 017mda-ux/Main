import math

from kalshi_ev.weather import bucket_probability, market_yes_probability, sigma_for_lead


def test_partition_sums_to_one():
    """An exhaustive bucket set — 'less than 35', '35-36', ..., 'greater
    than 42' — must have probabilities summing to exactly 1 under the
    continuity-corrected model."""
    mu, sigma = 38.2, 3.0
    buckets = [
        ("less", None, 35.0),        # T <= 34
        ("between", 35.0, 36.0),
        ("between", 37.0, 38.0),
        ("between", 39.0, 40.0),
        ("between", 41.0, 42.0),
        ("greater", 42.0, None),     # T >= 43
    ]
    total = sum(bucket_probability(mu, sigma, st, lo, hi) for st, lo, hi in buckets)
    assert math.isclose(total, 1.0, abs_tol=1e-9)


def test_between_centered_bucket_is_most_likely():
    mu, sigma = 78.0, 2.5
    center = bucket_probability(mu, sigma, "between", 77.0, 79.0)
    off = bucket_probability(mu, sigma, "between", 83.0, 85.0)
    # P(76.5 < X < 79.5) with sigma 2.5 = Phi(0.6) - Phi(-0.6) ~= 0.4515
    assert math.isclose(center, 0.4515, abs_tol=0.001)
    assert center > 10 * off


def test_greater_less_complement():
    mu, sigma = 60.0, 3.0
    # T <= 59 and T >= 60 partition the integers at the 59/60 boundary
    p_less = bucket_probability(mu, sigma, "less", cap_strike=60.0)     # T < 60
    p_greater = bucket_probability(mu, sigma, "greater", floor_strike=59.0)  # T > 59
    assert math.isclose(p_less + p_greater, 1.0, abs_tol=1e-9)


def test_non_integer_strikes_skip_continuity():
    mu, sigma = 50.0, 2.0
    # strike exactly at the mean: strictly greater than 49.5 => ~0.5987 with
    # no correction (Kalshi uses half-point strikes to avoid ties)
    p = bucket_probability(mu, sigma, "greater", floor_strike=49.5)
    assert math.isclose(p, 1 - 0.4013, abs_tol=0.001)


def test_market_dict_wrapper():
    market = {"strike_type": "between", "floor_strike": 70.0, "cap_strike": 72.0}
    p = market_yes_probability(market, mu=71.0, sigma=2.0)
    assert 0.4 < p < 0.65


def test_sigma_table_monotone_and_extends():
    assert sigma_for_lead(0) < sigma_for_lead(3) < sigma_for_lead(7)
    assert sigma_for_lead(30) == sigma_for_lead(7)  # clamps at max lead


def test_bad_inputs_raise():
    for bad in (
        lambda: bucket_probability(70, 0, "between", 60, 65),
        lambda: bucket_probability(70, 2, "between", None, 65),
        lambda: bucket_probability(70, 2, "wat", 60, 65),
    ):
        try:
            bad()
            assert False, "should have raised"
        except ValueError:
            pass
