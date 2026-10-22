"""
Calculator tools for the Nomad-style investment agent.

Each tool takes plain numbers, does real arithmetic, and returns JSON the model
can reason over. None of them call the network.

  scale_economics_shared     Are savings from scale given back to customers or kept?
  retention_quality          Does retention flatten out, and is it earned or imposed?
  unit_economics_persistence Are per-unit economics stable/improving across periods?
  destination_analysis       Where does reinvestment at a given return take the business?
  reverse_valuation          What growth does today's price imply? Expected return from a discount?
  robustness_ratio           Customer + employee gains per dollar kept by shareholders
  hidden_investment          Earning power before discretionary growth spending
  maturity_uplift            Profit growth embedded in young stores/cohorts as they mature
  dilution_risk              Value per share if equity must be raised at low prices
  moat_scorecard             Weighted Nomad-style score with weakest link and red flags
"""

from __future__ import annotations

import json
import math
from statistics import mean, pstdev
from typing import Any, Callable

# ──────────────────────────────────────────────────────────────────────
#  Small helpers
# ──────────────────────────────────────────────────────────────────────


def _slope(values: list[float]) -> float:
    """Least-squares slope per period."""
    n = len(values)
    if n < 2:
        return 0.0
    xs = range(n)
    x_bar = (n - 1) / 2
    y_bar = mean(values)
    num = sum((x - x_bar) * (y - y_bar) for x, y in zip(xs, values))
    den = sum((x - x_bar) ** 2 for x in xs)
    return num / den


def _cagr(first: float, last: float, periods: int) -> float | None:
    if first <= 0 or last <= 0 or periods <= 0:
        return None
    return (last / first) ** (1 / periods) - 1


def _cv(values: list[float]) -> float | None:
    """Coefficient of variation (volatility relative to the average)."""
    m = mean(values)
    if m == 0:
        return None
    return pstdev(values) / abs(m)


def _r(x: float | None, nd: int = 3) -> float | None:
    return None if x is None else round(x, nd)


# ──────────────────────────────────────────────────────────────────────
#  1. Scale economics shared
# ──────────────────────────────────────────────────────────────────────


def scale_economics_shared(inp: dict) -> dict:
    """
    periods: [{label, revenue, gross_margin_pct, opex_pct?, price_index?}]
    opex_pct = operating costs (excl. COGS) as % of revenue.
    price_index = average price customers pay (any base), optional.
    """
    periods = inp["periods"]
    if len(periods) < 2:
        raise ValueError("need at least two periods")

    first, last = periods[0], periods[-1]
    n = len(periods) - 1

    rev_cagr = _cagr(first["revenue"], last["revenue"], n)
    gm_change = last["gross_margin_pct"] - first["gross_margin_pct"]

    out: dict[str, Any] = {
        "periods": len(periods),
        "revenue_cagr_pct": _r(rev_cagr * 100 if rev_cagr is not None else None, 1),
        "gross_margin_change_pts": round(gm_change, 2),
    }

    opex_change = None
    if all("opex_pct" in p for p in (first, last)):
        opex_change = last["opex_pct"] - first["opex_pct"]
        out["opex_ratio_change_pts"] = round(opex_change, 2)
        # Scale savings = fall in the opex ratio. Share-back = how much of that
        # fall shows up as lower gross margin (i.e. lower prices to customers).
        savings = -opex_change
        if savings > 0.25:
            out["scale_savings_pts"] = round(savings, 2)
            out["share_back_ratio"] = round(max(0.0, -gm_change) / savings, 2)

    price_cagr = None
    if all("price_index" in p for p in (first, last)):
        price_cagr = _cagr(first["price_index"], last["price_index"], n)
        out["price_cagr_pct"] = _r(price_cagr * 100 if price_cagr is not None else None, 2)

    # Classification
    growing = rev_cagr is not None and rev_cagr > 0.03
    if opex_change is None:
        verdict = "insufficient data (add opex_pct per period to measure scale savings)"
    elif opex_change > -0.25:
        verdict = "no clear scale savings yet: operating cost ratio is not falling"
    elif gm_change <= 0.5 and (price_cagr is None or price_cagr <= 0.01):
        verdict = "SHARER: scale savings appear to be passed to customers (margins held flat or lower while costs fell)"
    elif price_cagr is not None and price_cagr > 0.03:
        verdict = "HARVESTER: margins rising alongside price increases; gains kept rather than shared"
    else:
        verdict = "KEEPER: scale savings mostly retained as margin; durable only if competitors can't match the cost base"

    out["verdict"] = verdict
    out["growing"] = growing
    out["note"] = (
        "Share-back ratio near 1 means most of the scale savings went to customers; "
        "near 0 means they were kept. Check that gross-margin moves are not caused by mix shifts."
    )
    return out


# ──────────────────────────────────────────────────────────────────────
#  2. Retention quality
# ──────────────────────────────────────────────────────────────────────

EARNED_REASONS = {
    "product_improves", "lower_price", "trust", "habit", "community", "convenience", "quality",
    "fair_fixed_pricing", "word_of_mouth", "network_standard",
}
IMPOSED_REASONS = {"contract", "data_lock_in", "migration_pain", "bundling", "cancellation_friction", "regulatory", "no_alternative"}


def retention_quality(inp: dict) -> dict:
    """
    logo_retention_pct: % of a cohort still active at each period, starting at 100.
    revenue_retention_pct: optional, same cohort's revenue as % of period 0.
    retention_reasons: optional list of reasons customers stay (see EARNED/IMPOSED sets).
    revenue_from_price_increases_pct: optional share of revenue growth from price rises.
    """
    curve = [float(x) for x in inp["logo_retention_pct"]]
    if len(curve) < 3:
        raise ValueError("need at least three points on the retention curve")

    period_churn = [
        (1 - curve[i] / curve[i - 1]) * 100 if curve[i - 1] > 0 else 100.0
        for i in range(1, len(curve))
    ]
    early = period_churn[0]
    late = period_churn[-1]

    out: dict[str, Any] = {
        "period_churn_pct": [round(c, 2) for c in period_churn],
        "early_churn_pct": round(early, 2),
        "latest_churn_pct": round(late, 2),
    }

    # Does the curve flatten? Survivors churning much less than new customers is
    # the signature of a product people keep choosing.
    if late <= 0.5:
        shape = "flat: curve has levelled off; surviving customers are essentially permanent"
    elif late < early * 0.5:
        shape = "flattening: churn falls sharply with customer age (good sign)"
    elif late < early * 0.9:
        shape = "slowly flattening"
    else:
        shape = "not flattening: customers keep leaving at the same rate (weak)"
    out["curve_shape"] = shape

    if late > 0:
        out["implied_avg_remaining_life_periods"] = round(100 / late, 1)

    rev = inp.get("revenue_retention_pct")
    if rev:
        rev = [float(x) for x in rev]
        out["latest_net_revenue_retention_pct"] = rev[-1]
        out["revenue_smile"] = rev[-1] > 100
        if len(rev) >= 2 and len(curve) >= 2:
            out["revenue_per_surviving_customer_index"] = round(rev[-1] / curve[len(rev) - 1] * 100, 1)

    reasons = set(inp.get("retention_reasons") or [])
    if reasons:
        earned = reasons & EARNED_REASONS
        imposed = reasons & IMPOSED_REASONS
        total = len(earned) + len(imposed)
        out["earned_reasons"] = sorted(earned)
        out["imposed_reasons"] = sorted(imposed)
        out["unrecognised_reasons"] = sorted(reasons - EARNED_REASONS - IMPOSED_REASONS)
        if total:
            share = len(earned) / total
            out["want_to_stay_share"] = round(share, 2)
            out["loyalty_type"] = (
                "mostly earned (want-to-stay)" if share >= 2 / 3
                else "mixed" if share >= 1 / 3
                else "mostly imposed (have-to-stay): brittle if switching gets easier"
            )

    price_share = inp.get("revenue_from_price_increases_pct")
    if price_share is not None:
        out["price_driven_growth_flag"] = price_share > 50
        if price_share > 50:
            out["price_driven_growth_note"] = (
                "More than half of growth comes from price increases: check whether customers "
                "are getting more value or just paying more."
            )
    return out


# ──────────────────────────────────────────────────────────────────────
#  3. Unit economics persistence
# ──────────────────────────────────────────────────────────────────────

# For each metric: is higher better?
_UE_DIRECTION = {
    "contribution_margin_pct": True,
    "contribution_per_unit": True,
    "cac": False,
    "payback_months": False,
    "incremental_roic_pct": True,
    "arpu": True,
    "churn_pct": False,
    "gross_margin_pct": True,
    "marketing_pct_of_revenue": False,
}


def unit_economics_persistence(inp: dict) -> dict:
    """
    series: {metric_name: [value per period, oldest first]}
    Known metrics get direction-aware verdicts; others are summarised neutrally.
    Optional ltv_inputs: {arpu, gross_margin_pct, churn_pct, cac} per period lists
    to compute LTV/CAC over time.
    """
    series: dict[str, list[float]] = inp["series"]
    results = {}
    for name, vals in series.items():
        vals = [float(v) for v in vals]
        if len(vals) < 2:
            results[name] = {"error": "need at least two periods"}
            continue
        s = _slope(vals)
        rel = s / abs(mean(vals)) if mean(vals) else 0.0
        higher_better = _UE_DIRECTION.get(name)
        if abs(rel) < 0.02:
            direction = "stable"
        elif (s > 0) == bool(higher_better):
            direction = "improving"
        else:
            direction = "deteriorating"
        if higher_better is None:
            direction = "rising" if s > 0 and abs(rel) >= 0.02 else "falling" if abs(rel) >= 0.02 else "stable"
        cv = _cv(vals)
        results[name] = {
            "first": vals[0],
            "last": vals[-1],
            "slope_per_period": round(s, 3),
            "relative_trend_pct_per_period": round(rel * 100, 1),
            "volatility_cv": _r(cv, 2),
            "direction": direction,
            "persistent": cv is not None and cv < 0.2,
        }

    ltv = inp.get("ltv_inputs")
    if ltv:
        arpu, gm, churn, cac = (ltv[k] for k in ("arpu", "gross_margin_pct", "churn_pct", "cac"))
        ratios = []
        for a, g, c, k in zip(arpu, gm, churn, cac):
            if c > 0 and k > 0:
                ratios.append(round(a * (g / 100) / (c / 100) / k, 2))
            else:
                ratios.append(None)
        results["ltv_to_cac"] = {"by_period": ratios}
        clean = [r for r in ratios if r is not None]
        if len(clean) >= 2:
            results["ltv_to_cac"]["direction"] = (
                "improving" if clean[-1] > clean[0] * 1.05
                else "deteriorating" if clean[-1] < clean[0] * 0.95
                else "stable"
            )

    worsening = [k for k, v in results.items() if isinstance(v, dict) and v.get("direction") == "deteriorating"]
    return {
        "metrics": results,
        "deteriorating": worsening,
        "summary": (
            "Unit economics holding or improving across the board"
            if not worsening
            else f"Watch: {', '.join(worsening)} getting worse"
        ),
    }


# ──────────────────────────────────────────────────────────────────────
#  4. Destination analysis
# ──────────────────────────────────────────────────────────────────────


def destination_analysis(inp: dict) -> dict:
    """
    Growth from reinvestment = reinvestment_rate x incremental_roic, capped by
    the market the business can realistically win.

    current_revenue, current_net_margin_pct, reinvestment_rate_pct (share of
    profit reinvested), incremental_roic_pct, years (default 10),
    tam (optional), max_share_pct (optional, default 30).
    """
    rev = float(inp["current_revenue"])
    margin = float(inp["current_net_margin_pct"]) / 100
    reinvest = float(inp["reinvestment_rate_pct"]) / 100
    roic = float(inp["incremental_roic_pct"]) / 100
    years = int(inp.get("years", 10))
    tam = inp.get("tam")
    max_share = float(inp.get("max_share_pct", 30)) / 100
    cap = float(tam) * max_share if tam else None

    # Sustainable growth of earnings from reinvestment (margin assumed constant,
    # so revenue grows at the same rate).
    g = reinvest * roic
    path = []
    r = rev
    capped_year = None
    for y in range(1, years + 1):
        r = r * (1 + g)
        if cap is not None and r >= cap:
            r = cap
            capped_year = capped_year or y
        path.append({"year": y, "revenue": round(r, 2), "earnings": round(r * margin, 2)})

    out = {
        "implied_growth_pct": round(g * 100, 2),
        "end_revenue": path[-1]["revenue"],
        "end_earnings": path[-1]["earnings"],
        "earnings_multiple_of_today": round(path[-1]["earnings"] / (rev * margin), 2) if margin > 0 else None,
        "path": path,
    }
    if cap is not None:
        out["revenue_ceiling"] = round(cap, 2)
        out["current_share_of_tam_pct"] = round(rev / float(tam) * 100, 2)
        out["hits_ceiling_in_year"] = capped_year
        if capped_year is None and g > 0:
            out["years_of_runway"] = round(math.log(cap / rev) / math.log(1 + g), 1) if cap > rev else 0
    out["note"] = (
        "This is an arithmetic sketch: growth only lasts while there are projects that earn the "
        "assumed return. Test lower ROIC and reinvestment rates."
    )
    return out


# ──────────────────────────────────────────────────────────────────────
#  5. Reverse valuation
# ──────────────────────────────────────────────────────────────────────


def _dcf_value(fcf0: float, g: float, years: int, r: float, tg: float) -> float:
    pv = 0.0
    fcf = fcf0
    for t in range(1, years + 1):
        fcf *= 1 + g
        pv += fcf / (1 + r) ** t
    terminal = fcf * (1 + tg) / (r - tg)
    return pv + terminal / (1 + r) ** years


def reverse_valuation(inp: dict) -> dict:
    """
    What annual free-cash-flow growth for `years` is needed to justify the price?

    market_cap (or enterprise value), owner_earnings (normalised free cash flow),
    discount_rate_pct (default 9), terminal_growth_pct (default 3), years (default 10).
    """
    price = float(inp["market_cap"])
    fcf0 = float(inp["owner_earnings"])
    r = float(inp.get("discount_rate_pct", 9)) / 100
    tg = float(inp.get("terminal_growth_pct", 3)) / 100
    years = int(inp.get("years", 10))
    if r <= tg:
        raise ValueError("discount rate must exceed terminal growth")
    if fcf0 <= 0:
        raise ValueError("owner_earnings must be positive for a reverse DCF")

    lo, hi = -0.5, 1.5
    for _ in range(200):
        mid = (lo + hi) / 2
        if _dcf_value(fcf0, mid, years, r, tg) < price:
            lo = mid
        else:
            hi = mid
    implied = (lo + hi) / 2

    out = {
        "owner_earnings_yield_pct": round(fcf0 / price * 100, 2),
        "implied_annual_growth_pct": round(implied * 100, 2),
        "years": years,
        "discount_rate_pct": r * 100,
        "terminal_growth_pct": tg * 100,
        "value_at_0pct_growth": round(_dcf_value(fcf0, 0.0, years, r, tg), 2),
        "note": (
            "Prices are a language: compare the implied growth with your destination analysis. "
            "If the business can plausibly beat it by a wide margin, patience may be paid."
        ),
    }

    # Nomad's "typical purchase" arithmetic (December 2003): buy at a discount to
    # value, let value compound, and assume price converges on value after N years.
    value = inp.get("your_value_estimate")
    if value:
        g = float(inp.get("value_growth_pct", 10)) / 100
        n = int(inp.get("years_to_converge", 5))
        future_value = float(value) * (1 + g) ** n
        out["price_to_value_cents"] = round(price / float(value) * 100, 1)
        out["expected_annual_return_pct"] = round(((future_value / price) ** (1 / n) - 1) * 100, 1)
        out["expected_return_if_value_flat_pct"] = round(((float(value) / price) ** (1 / n) - 1) * 100, 1)
        out["expected_return_assumptions"] = {"value_growth_pct": g * 100, "years_to_converge": n}
    return out


# ──────────────────────────────────────────────────────────────────────
#  6. Robustness ratio (Nomad, "Measuring the Moat", May 2005)
# ──────────────────────────────────────────────────────────────────────


def robustness_ratio(inp: dict) -> dict:
    """
    How the gains of scale are split. (customer savings + employee premium)
    divided by profit kept for shareholders. Nomad estimated Costco ~5:1, Geico ~1:1.

    periods: [{label?, customer_savings, shareholder_profit, employee_premium?}]
    All in the same currency and period length.
    """
    periods = inp["periods"]
    if not periods:
        raise ValueError("need at least one period")
    rows = []
    for p in periods:
        cust = float(p["customer_savings"])
        emp = float(p.get("employee_premium", 0))
        sh = float(p["shareholder_profit"])
        if sh <= 0:
            raise ValueError("shareholder_profit must be positive")
        total = cust + emp + sh
        rows.append({
            "label": p.get("label"),
            "robustness_ratio": round((cust + emp) / sh, 2),
            "customer_share_pct": round(cust / total * 100, 1),
            "employee_share_pct": round(emp / total * 100, 1),
            "shareholder_share_pct": round(sh / total * 100, 1),
        })

    latest = rows[-1]["robustness_ratio"]
    out: dict[str, Any] = {
        "by_period": rows,
        "latest_ratio": latest,
        "reading": (
            "very wide moat: rivals must give up large sums to match (Costco-like)" if latest >= 4
            else "wide moat (between Geico and Costco)" if latest >= 2
            else "fair split, roughly Geico-like" if latest >= 0.8
            else "shareholders take most of the gains: check whether rivals can undercut"
        ),
    }
    if len(rows) >= 2:
        first = rows[0]["robustness_ratio"]
        change = latest - first
        out["trend"] = (
            "rising: more of the gains going to customers (moat widening)" if change > 0.1 * first
            else "falling: shifting toward shareholders, watch for harvesting" if change < -0.1 * first
            else "stable"
        )
    out["note"] = (
        "Most useful where customers buy on price. A falling ratio is not always bad: a maturing "
        "firm can reasonably keep more, but 'too much, and the moat is drained'."
    )
    return out


# ──────────────────────────────────────────────────────────────────────
#  7. Hidden investment: earnings before discretionary growth spending
# ──────────────────────────────────────────────────────────────────────


def hidden_investment(inp: dict) -> dict:
    """
    Nomad's Amazon exercise (December 2006): reported free cash flow is after growth
    spending that is expensed (marketing, R&D, subsidies, price cuts). Add back the
    discretionary part to see what the business could earn as a "cash cow".

    reported_fcf, discretionary_growth_spend (pre-tax, beyond what maintains the
    business), tax_rate_pct (default 25), cash_cow_multiple (default 15),
    market_cap (optional), net_cash (optional, can be negative for net debt).
    """
    fcf = float(inp["reported_fcf"])
    spend = float(inp["discretionary_growth_spend"])
    tax = float(inp.get("tax_rate_pct", 25)) / 100
    mult = float(inp.get("cash_cow_multiple", 15))
    net_cash = float(inp.get("net_cash", 0))

    cash_cow_fcf = fcf + spend * (1 - tax)
    cash_cow_value = cash_cow_fcf * mult + net_cash
    out: dict[str, Any] = {
        "cash_cow_fcf": round(cash_cow_fcf, 2),
        "growth_spend_after_tax": round(spend * (1 - tax), 2),
        "hidden_share_of_earning_power_pct": round(spend * (1 - tax) / cash_cow_fcf * 100, 1) if cash_cow_fcf else None,
        "cash_cow_value": round(cash_cow_value, 2),
    }
    mc = inp.get("market_cap")
    if mc:
        mc = float(mc)
        out["market_cap"] = mc
        out["market_value_of_growth"] = round(mc - cash_cow_value, 2)
        out["reading"] = (
            "market is paying little or nothing for the growth spending" if mc <= cash_cow_value * 1.1
            else "market is paying a premium for growth: check the destination justifies it"
        )
    out["note"] = (
        "Only count spending the company could stop without damaging the existing business. "
        "Be conservative: this is a judgement, not an accounting figure."
    )
    return out


# ──────────────────────────────────────────────────────────────────────
#  8. Maturity uplift (Costco store-age analysis, December 2004)
# ──────────────────────────────────────────────────────────────────────


def maturity_uplift(inp: dict) -> dict:
    """
    cohorts: [{label, assets_or_cost, current_return_pct}] — stores, regions, customer
    cohorts or contracts grouped by age. mature_return_pct: return the youngest cohorts
    should reach once mature (default = best cohort's return).
    """
    cohorts = inp["cohorts"]
    if len(cohorts) < 2:
        raise ValueError("need at least two cohorts")
    assets = [float(c["assets_or_cost"]) for c in cohorts]
    rets = [float(c["current_return_pct"]) / 100 for c in cohorts]
    target = float(inp.get("mature_return_pct", max(rets) * 100)) / 100

    profit_now = sum(a * r for a, r in zip(assets, rets))
    profit_mature = sum(a * max(r, target) for a, r in zip(assets, rets))
    total_assets = sum(assets)
    out = {
        "blended_return_now_pct": round(profit_now / total_assets * 100, 2),
        "blended_return_at_maturity_pct": round(profit_mature / total_assets * 100, 2),
        "embedded_profit_uplift_pct": round((profit_mature / profit_now - 1) * 100, 1) if profit_now > 0 else None,
        "share_of_assets_below_target_pct": round(
            sum(a for a, r in zip(assets, rets) if r < target) / total_assets * 100, 1),
        "note": (
            "Profit growth already 'in the ground' before any new units are added. Check that "
            "young cohorts are on the same path as old ones did at the same age."
        ),
    }
    years = inp.get("years_to_mature")
    if years and out["embedded_profit_uplift_pct"] is not None:
        out["implied_annual_growth_from_maturity_pct"] = round(
            ((profit_mature / profit_now) ** (1 / int(years)) - 1) * 100, 2)
    return out


# ──────────────────────────────────────────────────────────────────────
#  9. Dilution risk (MBIA, June 2008)
# ──────────────────────────────────────────────────────────────────────


def dilution_risk(inp: dict) -> dict:
    """
    value_before (equity value before any losses), shares_outstanding, capital_needed
    (losses the new money must cover), your_purchase_price, and raise_prices to test.
    """
    value = float(inp["value_before"])
    shares = float(inp["shares_outstanding"])
    need = float(inp["capital_needed"])
    buy = float(inp["your_purchase_price"])
    prices = inp.get("raise_prices") or [buy, buy / 2, buy / 5]

    scenarios = []
    for p in prices:
        p = float(p)
        if p <= 0:
            continue
        new_shares = need / p
        # The cash raised covers the losses, so total equity is back to value_before,
        # now spread over more shares.
        vps = value / (shares + new_shares)
        scenarios.append({
            "raise_price": round(p, 4),
            "new_shares": round(new_shares, 2),
            "value_per_share_after": round(vps, 4),
            "your_price_as_cents_per_dollar": round(buy / vps * 100, 1),
        })
    return {
        "value_per_share_before": round(value / shares, 4),
        "value_per_share_after_losses_no_dilution": round((value - need) / shares, 4),
        "scenarios": scenarios,
        "note": (
            "The lower the price new equity is sold at, the faster value per share falls. "
            "A cheap stock that may need capital is only cheap if you can say what it is worth per share."
        ),
    }


# ──────────────────────────────────────────────────────────────────────
#  10. Scorecard
# ──────────────────────────────────────────────────────────────────────

SCORECARD_WEIGHTS = {
    "scale_economics_shared": 0.18,
    "earned_retention": 0.14,
    "customer_delight": 0.14,
    "unit_economics_persistence": 0.12,
    "management_character": 0.12,
    "reinvestment_runway": 0.10,
    "many_small_advantages": 0.10,
    "pricing_restraint": 0.05,
    "resilience": 0.05,
}

RED_FLAGS = {
    "growth_from_price_hikes": "Most growth comes from raising prices, not adding value",
    "rising_take_rate": "Take rate or fees keep rising faster than value delivered",
    "rented_distribution": "Growth depends on another platform's ads, store or model",
    "subsidised_unit_economics": "Unit economics only work with subsidies or cheap capital",
    "dark_patterns": "Retention relies on cancellation friction or hidden fees",
    "customer_concentration": "A few customers make up a large share of revenue",
    "short_term_incentives": "Management paid on short-term targets",
    "heavy_leverage": "Debt that could force bad decisions in a downturn",
    "dilution_risk": "May need to issue equity at low prices",
    "one_big_thing": "Advantage rests on a single patent, licence or product",
    "windfall_misallocation": "Windfall profits spent on capacity or acquisitions away from the core",
    "promotional_management": "Heavy guidance, hype or advertising standing in for product quality",
    "candour_problem": "Mistakes explained away rather than owned and fixed",
}


def moat_scorecard(inp: dict) -> dict:
    """
    scores: {dimension: 0-5} for each key in SCORECARD_WEIGHTS.
    red_flags: optional list of keys from RED_FLAGS.
    """
    scores = inp["scores"]
    missing = [k for k in SCORECARD_WEIGHTS if k not in scores]
    for k, v in scores.items():
        if k not in SCORECARD_WEIGHTS:
            raise ValueError(f"unknown dimension '{k}'")
        if not 0 <= float(v) <= 5:
            raise ValueError(f"score for '{k}' must be 0-5")

    used = {k: w for k, w in SCORECARD_WEIGHTS.items() if k in scores}
    total_w = sum(used.values())
    weighted = sum(float(scores[k]) * w for k, w in used.items()) / total_w if total_w else 0
    pct = weighted / 5 * 100

    flags = [f for f in (inp.get("red_flags") or []) if f in RED_FLAGS]
    penalty = 5 * len(flags)
    adjusted = max(0.0, pct - penalty)

    weakest = min(used, key=lambda k: float(scores[k])) if used else None
    grade = (
        "Exceptional (rare, Nomad-style compounder)" if adjusted >= 80
        else "Strong" if adjusted >= 65
        else "Average" if adjusted >= 50
        else "Weak"
    )
    return {
        "weighted_score_pct": round(pct, 1),
        "red_flag_penalty_pts": penalty,
        "adjusted_score_pct": round(adjusted, 1),
        "grade": grade,
        "weakest_link": weakest,
        "red_flags": {f: RED_FLAGS[f] for f in flags},
        "unscored_dimensions": missing,
        "weights": SCORECARD_WEIGHTS,
    }


# ──────────────────────────────────────────────────────────────────────
#  Tool definitions for the Claude API
# ──────────────────────────────────────────────────────────────────────

_num = {"type": "number"}
_num_list = {"type": "array", "items": {"type": "number"}}

TOOL_DEFINITIONS: list[dict] = [
    {
        "name": "scale_economics_shared",
        "description": (
            "Test whether a company passes savings from scale back to customers (lower prices, "
            "flat margins while operating costs fall) or keeps them (rising margins, price hikes). "
            "Give at least two periods, oldest first."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "periods": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "label": {"type": "string"},
                            "revenue": _num,
                            "gross_margin_pct": _num,
                            "opex_pct": {"type": "number", "description": "Operating costs excl. COGS as % of revenue"},
                            "price_index": {"type": "number", "description": "Average price paid, any base"},
                        },
                        "required": ["revenue", "gross_margin_pct"],
                    },
                }
            },
            "required": ["periods"],
        },
    },
    {
        "name": "retention_quality",
        "description": (
            "Analyse a cohort retention curve: does churn fall as customers age, is revenue "
            "retention above 100%, and are the reasons customers stay earned (product_improves, "
            "lower_price, trust, habit, community, convenience, quality) or imposed (contract, "
            "data_lock_in, migration_pain, bundling, cancellation_friction, regulatory, no_alternative)?"
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "logo_retention_pct": {**_num_list, "description": "% of cohort still active each period, starting at 100"},
                "revenue_retention_pct": {**_num_list, "description": "Cohort revenue as % of period 0"},
                "retention_reasons": {"type": "array", "items": {"type": "string"}},
                "revenue_from_price_increases_pct": _num,
            },
            "required": ["logo_retention_pct"],
        },
    },
    {
        "name": "unit_economics_persistence",
        "description": (
            "Check whether per-unit economics are stable, improving or getting worse across periods. "
            "Known metrics: contribution_margin_pct, contribution_per_unit, cac, payback_months, "
            "incremental_roic_pct, arpu, churn_pct, gross_margin_pct, marketing_pct_of_revenue. "
            "Optionally pass ltv_inputs to track LTV/CAC over time."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "series": {
                    "type": "object",
                    "description": "metric name -> list of values per period, oldest first",
                    "additionalProperties": _num_list,
                },
                "ltv_inputs": {
                    "type": "object",
                    "properties": {
                        "arpu": _num_list,
                        "gross_margin_pct": _num_list,
                        "churn_pct": _num_list,
                        "cac": _num_list,
                    },
                    "required": ["arpu", "gross_margin_pct", "churn_pct", "cac"],
                },
            },
            "required": ["series"],
        },
    },
    {
        "name": "destination_analysis",
        "description": (
            "Project where the business could be in N years if it reinvests a share of profit at a "
            "given incremental return, optionally capped by a realistic share of its market."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "current_revenue": _num,
                "current_net_margin_pct": _num,
                "reinvestment_rate_pct": _num,
                "incremental_roic_pct": _num,
                "years": {"type": "integer"},
                "tam": _num,
                "max_share_pct": _num,
            },
            "required": ["current_revenue", "current_net_margin_pct", "reinvestment_rate_pct", "incremental_roic_pct"],
        },
    },
    {
        "name": "reverse_valuation",
        "description": (
            "Reverse DCF: solve for the annual free-cash-flow growth the current market value implies."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "market_cap": _num,
                "owner_earnings": {"type": "number", "description": "Normalised annual free cash flow"},
                "discount_rate_pct": _num,
                "terminal_growth_pct": _num,
                "years": {"type": "integer"},
                "your_value_estimate": {"type": "number", "description": "Your estimate of what the business is worth today"},
                "value_growth_pct": {"type": "number", "description": "Annual growth in value (default 10)"},
                "years_to_converge": {"type": "integer", "description": "Years for price to reach value (default 5)"},
            },
            "required": ["market_cap", "owner_earnings"],
        },
    },
    {
        "name": "robustness_ratio",
        "description": (
            "Nomad's robustness ratio: (customer savings vs alternatives + employee pay premium) "
            "divided by profit kept for shareholders. Costco was ~5:1, Geico ~1:1. Give one or more "
            "periods to see whether the split is shifting toward customers or shareholders."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "periods": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "label": {"type": "string"},
                            "customer_savings": _num,
                            "employee_premium": _num,
                            "shareholder_profit": _num,
                        },
                        "required": ["customer_savings", "shareholder_profit"],
                    },
                }
            },
            "required": ["periods"],
        },
    },
    {
        "name": "hidden_investment",
        "description": (
            "Add back discretionary growth spending (marketing, R&D, subsidies, price cuts beyond "
            "maintenance) to reported free cash flow to estimate 'cash cow' earning power, and compare "
            "with market value to see what the market pays for growth."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "reported_fcf": _num,
                "discretionary_growth_spend": _num,
                "tax_rate_pct": _num,
                "cash_cow_multiple": _num,
                "market_cap": _num,
                "net_cash": _num,
            },
            "required": ["reported_fcf", "discretionary_growth_spend"],
        },
    },
    {
        "name": "maturity_uplift",
        "description": (
            "Estimate profit growth already embedded in young units (stores, regions, customer cohorts, "
            "contracts) as they mature to the returns of older ones."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "cohorts": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "label": {"type": "string"},
                            "assets_or_cost": _num,
                            "current_return_pct": _num,
                        },
                        "required": ["assets_or_cost", "current_return_pct"],
                    },
                },
                "mature_return_pct": _num,
                "years_to_mature": {"type": "integer"},
            },
            "required": ["cohorts"],
        },
    },
    {
        "name": "dilution_risk",
        "description": (
            "Show how value per share falls if a company must raise equity to cover losses, at "
            "different issue prices, and what your purchase price really paid per dollar of value."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "value_before": _num,
                "shares_outstanding": _num,
                "capital_needed": _num,
                "your_purchase_price": _num,
                "raise_prices": _num_list,
            },
            "required": ["value_before", "shares_outstanding", "capital_needed", "your_purchase_price"],
        },
    },
    {
        "name": "moat_scorecard",
        "description": (
            "Combine 0-5 scores on: " + ", ".join(SCORECARD_WEIGHTS)
            + " into a weighted grade, name the weakest link, and apply red-flag penalties. "
            "Red flags: " + ", ".join(RED_FLAGS) + "."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "scores": {
                    "type": "object",
                    "properties": {k: {"type": "number", "minimum": 0, "maximum": 5} for k in SCORECARD_WEIGHTS},
                },
                "red_flags": {"type": "array", "items": {"type": "string", "enum": list(RED_FLAGS)}},
            },
            "required": ["scores"],
        },
    },
]

_DISPATCH: dict[str, Callable[[dict], dict]] = {
    "scale_economics_shared": scale_economics_shared,
    "retention_quality": retention_quality,
    "unit_economics_persistence": unit_economics_persistence,
    "destination_analysis": destination_analysis,
    "reverse_valuation": reverse_valuation,
    "robustness_ratio": robustness_ratio,
    "hidden_investment": hidden_investment,
    "maturity_uplift": maturity_uplift,
    "dilution_risk": dilution_risk,
    "moat_scorecard": moat_scorecard,
}

_REQUIRED = {t["name"]: t["input_schema"].get("required", []) for t in TOOL_DEFINITIONS}


def execute_tool(name: str, tool_input: Any) -> tuple[str, bool]:
    """Run a tool. Returns (result_json, is_error)."""
    fn = _DISPATCH.get(name)
    if fn is None:
        return json.dumps({"error": f"unknown tool '{name}'"}), True
    if not isinstance(tool_input, dict):
        return json.dumps({"INVALID_JSON": str(tool_input)}), True
    missing = [k for k in _REQUIRED[name] if k not in tool_input]
    if missing:
        return json.dumps({"error": f"missing required fields: {missing}"}), True
    try:
        return json.dumps(fn(tool_input), indent=2), False
    except (ValueError, TypeError, KeyError, ZeroDivisionError) as exc:
        return json.dumps({"error": f"{type(exc).__name__}: {exc}"}), True
