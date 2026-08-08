import math
import random

from kalshi_ev.calibration import CalibrationModel, brier_score, reliability_table


def _logit(p):
    return math.log(p / (1 - p))


def _sigmoid(z):
    return 1 / (1 + math.exp(-z))


def _synthetic(n, true_a, true_b, seed=7):
    """Markets price p, but the true probability is sigmoid(a + b*logit(p))."""
    rng = random.Random(seed)
    prices, outcomes = [], []
    for _ in range(n):
        p = rng.uniform(0.03, 0.97)
        q_true = _sigmoid(true_a + true_b * _logit(p))
        prices.append(p * 100)
        outcomes.append(1 if rng.random() < q_true else 0)
    return prices, outcomes


def test_recovers_overconfident_market():
    # b=0.6: longshots overpriced, favorites underpriced
    prices, outcomes = _synthetic(8000, true_a=0.0, true_b=0.6)
    model = CalibrationModel.fit(prices, outcomes)
    assert abs(model.a) < 0.15
    assert abs(model.b - 0.6) < 0.1


def test_recovers_calibrated_market():
    prices, outcomes = _synthetic(8000, true_a=0.0, true_b=1.0)
    model = CalibrationModel.fit(prices, outcomes)
    assert abs(model.b - 1.0) < 0.12


def test_model_beats_market_brier_when_biased():
    prices, outcomes = _synthetic(8000, true_a=0.0, true_b=0.6)
    model = CalibrationModel.fit(prices, outcomes)
    market = brier_score([p / 100 for p in prices], outcomes)
    fitted = brier_score([model.predict(p) for p in prices], outcomes)
    assert fitted < market


def test_predict_monotonic_and_bounded():
    model = CalibrationModel(a=0.1, b=0.7)
    qs = [model.predict(p) for p in range(1, 100)]
    assert all(0 < q < 1 for q in qs)
    assert all(b >= a for a, b in zip(qs, qs[1:]))


def test_save_load_roundtrip(tmp_path):
    model = CalibrationModel(a=-0.2, b=0.85, n_train=123)
    path = tmp_path / "model.json"
    model.save(path)
    loaded = CalibrationModel.load(path)
    assert loaded.a == model.a and loaded.b == model.b and loaded.n_train == 123


def test_fit_requires_enough_data():
    try:
        CalibrationModel.fit([50.0] * 5, [1, 0, 1, 0, 1])
        assert False, "should have raised"
    except ValueError:
        pass


def test_reliability_table_shape():
    prices, outcomes = _synthetic(2000, 0.0, 0.8)
    rows = reliability_table(prices, outcomes)
    assert 5 <= len(rows) <= 10
    total = sum(n for _, n, _, _ in rows)
    assert total == 2000
