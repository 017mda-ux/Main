import json

import pytest

from nomad import tools
from nomad.agent import load_system_prompt


def test_sharer_detected():
    out = tools.scale_economies_shared({"periods": [
        {"revenue": 100, "gross_margin_pct": 13.0, "opex_pct": 10.0, "price_index": 100},
        {"revenue": 160, "gross_margin_pct": 12.5, "opex_pct": 8.5, "price_index": 99},
    ]})
    assert out["verdict"].startswith("SHARER")
    assert out["share_back_ratio"] == pytest.approx(0.33, abs=0.01)


def test_harvester_detected():
    out = tools.scale_economies_shared({"periods": [
        {"revenue": 100, "gross_margin_pct": 60, "opex_pct": 40, "price_index": 100},
        {"revenue": 140, "gross_margin_pct": 66, "opex_pct": 35, "price_index": 125},
    ]})
    assert out["verdict"].startswith("HARVESTER")


def test_retention_flattening_and_loyalty():
    out = tools.retention_quality({
        "logo_retention_pct": [100, 70, 60, 56, 54],
        "revenue_retention_pct": [100, 85, 90, 98, 108],
        "retention_reasons": ["habit", "product_improves", "contract"],
    })
    assert "flattening" in out["curve_shape"]
    assert out["revenue_smile"] is True
    assert out["loyalty_type"].startswith("mostly earned")


def test_retention_not_flattening():
    out = tools.retention_quality({"logo_retention_pct": [100, 80, 64, 51.2]})
    assert out["curve_shape"].startswith("not flattening")


def test_unit_economics_direction():
    out = tools.unit_economics_persistence({
        "series": {"cac": [100, 120, 150, 190], "contribution_margin_pct": [30, 30.2, 29.9, 30.1]},
        "ltv_inputs": {"arpu": [100, 100], "gross_margin_pct": [50, 50], "churn_pct": [10, 10], "cac": [100, 200]},
    })
    assert out["metrics"]["cac"]["direction"] == "deteriorating"
    assert out["metrics"]["contribution_margin_pct"]["direction"] == "stable"
    assert out["metrics"]["ltv_to_cac"]["by_period"] == [5.0, 2.5]
    assert "cac" in out["deteriorating"]


def test_destination_capped_by_tam():
    out = tools.destination_analysis({
        "current_revenue": 100, "current_net_margin_pct": 10,
        "reinvestment_rate_pct": 100, "incremental_roic_pct": 30,
        "years": 10, "tam": 1000, "max_share_pct": 30,
    })
    assert out["implied_growth_pct"] == 30
    assert out["end_revenue"] == 300
    assert out["hits_ceiling_in_year"] == 5


def test_reverse_valuation_round_trip():
    fcf, r, tg = 10.0, 0.09, 0.03
    price = tools._dcf_value(fcf, 0.12, 10, r, tg)
    out = tools.reverse_valuation({"market_cap": price, "owner_earnings": fcf})
    assert out["implied_annual_growth_pct"] == pytest.approx(12.0, abs=0.01)


def test_scorecard_weakest_link_and_flags():
    scores = {k: 5 for k in tools.SCORECARD_WEIGHTS}
    scores["pricing_restraint"] = 1
    out = tools.moat_scorecard({"scores": scores, "red_flags": ["rising_take_rate"]})
    assert out["weakest_link"] == "pricing_restraint"
    assert out["red_flag_penalty_pts"] == 5
    assert out["adjusted_score_pct"] < out["weighted_score_pct"]


def test_execute_tool_errors_are_flagged():
    res, err = tools.execute_tool("reverse_valuation", {"market_cap": 1})
    assert err and "missing" in json.loads(res)["error"]
    res, err = tools.execute_tool("nope", {})
    assert err
    res, err = tools.execute_tool("moat_scorecard", {"scores": {"bogus": 3}})
    assert err


def test_tool_names_match_dispatch():
    assert {t["name"] for t in tools.TOOL_DEFINITIONS} == set(tools._DISPATCH)


def test_system_prompt_loads_without_front_matter():
    prompt = load_system_prompt()
    assert not prompt.startswith("---")
    assert "Scale economies shared" in prompt
