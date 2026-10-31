#!/usr/bin/env python3
"""
Build a stock universe from sources reachable via GitHub, then run our 10-year return screen.

Sources (refreshed daily by their maintainers):
  * rreichel3/US-Stock-Symbols  - every NASDAQ/NYSE/AMEX listing: price, market cap, sector, country
  * fcesterbics/Data_Stock      - ~480 large US companies: FCF, ROE, margins, growth, debt (via Yahoo)

    python scripts/build_universe.py            # download, merge, screen
    python scripts/build_universe.py --top 40

Outputs (git-ignored): knowledge/data_raw/*, knowledge/screens/universe_<date>.csv
The return model is ours (see expected_return); the sources supply raw numbers only.
"""

from __future__ import annotations

import argparse
import csv
import datetime as dt
import json
import math
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parent.parent / "knowledge"
RAW, OUT = ROOT / "data_raw", ROOT / "screens"
GH = "https://raw.githubusercontent.com"
SYMBOLS = {x: f"{GH}/rreichel3/US-Stock-Symbols/main/{x}/{x}_full_tickers.json" for x in ("nasdaq", "nyse", "amex")}
CYCLICAL_SECTORS = {"Energy", "Basic Materials", "Utilities", "Real Estate"}
FUNDAMENTALS = f"{GH}/fcesterbics/Data_Stock/main/Stock_Screener_PRO.csv"


def fetch(url: str, dest: Path) -> Path:
    r = requests.get(url, timeout=60)
    r.raise_for_status()
    dest.write_bytes(r.content)
    return dest


def f(x) -> float | None:
    try:
        v = float(x)
        return v if math.isfinite(v) else None
    except (TypeError, ValueError):
        return None


def irr(cfs: list[float]) -> float:
    lo, hi = -0.9, 2.0
    for _ in range(200):
        mid = (lo + hi) / 2
        npv = sum(c / (1 + mid) ** t for t, c in enumerate(cfs))
        lo, hi = (mid, hi) if npv > 0 else (lo, mid)
    return (lo + hi) / 2


def expected_return(fcf_yield: float, growth: float, exit_mult: float) -> float:
    """Buy at 1, get FCF yield growing at `growth` for 5 yrs then half that (min 3%), exit at multiple."""
    g1, g2 = growth, max(growth / 2, 0.03)
    e, flows = fcf_yield, []
    for y in range(1, 11):
        e *= 1 + (g1 if y <= 5 else g2)
        flows.append(e)
    return irr([-1.0] + flows[:-1] + [flows[-1] * (1 + exit_mult)])


def odds_of_15(r: float, error: float = 0.06) -> float:
    return 0.5 * (1 + math.erf((r - 0.15) / (error * math.sqrt(2))))


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--top", type=int, default=30)
    args = ap.parse_args()
    RAW.mkdir(parents=True, exist_ok=True)
    OUT.mkdir(parents=True, exist_ok=True)

    universe = {}
    for ex, url in SYMBOLS.items():
        for r in json.loads(fetch(url, RAW / f"{ex}.json").read_text()):
            universe[r["symbol"]] = {"exchange": ex, **r}
    fund = {r["ticker"]: r for r in csv.DictReader(fetch(FUNDAMENTALS, RAW / "fundamentals.csv").open())}
    print(f"Universe: {len(universe)} listed stocks; fundamentals for {len(fund)}")

    rows = []
    for t, fr in fund.items():
        mcap, fcf = f(fr.get("marketCap")), f(fr.get("freeCashflow"))
        if not mcap or not fcf or fcf <= 0:
            continue
        roe, opm = f(fr.get("returnOnEquity")), f(fr.get("operatingMargins"))
        de = f(fr.get("debtToEquity"))  # Yahoo reports this in percent
        cagr, yoy, pe = f(fr.get("revenue_cagr")), f(fr.get("revenueGrowth")), f(fr.get("trailingPE"))
        g_hist = [g for g in (cagr, yoy) if g is not None]
        if not g_hist:
            continue
        boom = max(g_hist) > 0.40                         # cyclical upswing, assume it fades
        growth = max(0.0, min(0.7 * min(g_hist), 0.08 if boom else 0.20))
        # Owner earnings: the lower of FCF and 1.3x net income, to strip one-off cash swings
        y = fcf / mcap
        if pe and pe > 0:
            y = min(y, 1.3 / pe)
        else:
            y *= 0.7
        cyclical = (fr.get("sector") in CYCLICAL_SECTORS) or boom
        exit_mult = max(12.0, min(1 / y, 25.0)) if y > 0 else 12.0
        r = expected_return(y, growth, exit_mult)
        quality = (roe is not None and roe > 0.15) + (opm is not None and opm > 0.15) + (de is not None and de < 150)
        rows.append({
            "ticker": t, "name": fr.get("shortName"), "sector": fr.get("sector"),
            "mcap_bn": round(mcap / 1e9, 1), "fcf_yield_pct": round(y * 100, 1),
            "growth_used_pct": round(growth * 100, 1), "roe_pct": round(roe * 100) if roe is not None else None,
            "op_margin_pct": round(opm * 100) if opm is not None else None, "debt_eq_pct": de,
            "quality_checks_3": quality, "cyclical_or_peak": cyclical, "exp_10y_pct": round(r * 100, 1), "odds_15_pct": round(odds_of_15(r) * 100),
        })
    rows.sort(key=lambda x: (-x["odds_15_pct"], -x["quality_checks_3"]))
    path = OUT / f"universe_{dt.date.today()}.csv"
    with path.open("w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)

    print(f"{'ticker':7}{'name':26}{'mcap$bn':>8}{'FCFyld':>7}{'grow':>6}{'ROE':>5}{'OpM':>5}{'Q':>3}{'exp10y':>8}{'P15':>5}")
    durable = [r for r in rows if r["quality_checks_3"] >= 2 and not r["cyclical_or_peak"]]
    print(f"Durable (non-cyclical, 2+ quality checks): {len(durable)} of {len(rows)}")
    for x in durable[: args.top]:
        print(f"{x['ticker']:7}{(x['name'] or '')[:25]:26}{x['mcap_bn']:8.0f}{x['fcf_yield_pct']:6.1f}%"
              f"{x['growth_used_pct']:5.1f}%{(x['roe_pct'] or 0):4}%{(x['op_margin_pct'] or 0):4}%"
              f"{x['quality_checks_3']:3}{x['exp_10y_pct']:7.1f}%{x['odds_15_pct']:4}%")
    print(f"\nSaved {len(rows)} screened rows to {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
