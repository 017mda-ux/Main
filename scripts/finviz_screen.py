#!/usr/bin/env python3
"""
Finviz first pass -> own 10-year return maths -> ranked odds of 15% a year.

Finviz supplies raw data only. The return model and ranking are ours:
  expected 10y annual return = solve IRR for: buy at today's price, receive free cash flow
  (yield = 1 / P/FCF) growing at a haircut of analysts' 5-year EPS growth for 5 years, half that
  for the next 5, then sell at a capped exit multiple.
  odds of 15% = normal approximation around that estimate (10-year error ~6 points a year).

    python scripts/finviz_screen.py                 # default quality filters
    python scripts/finviz_screen.py --max-pages 5   # fewer requests
Output: knowledge/screens/finviz_<date>.csv and a printed top-30 table.
Personal research use; requests are spaced out to be polite to the site.
"""

from __future__ import annotations

import argparse
import csv
import datetime as dt
import math
import time
from pathlib import Path

import requests
from bs4 import BeautifulSoup

BASE = "https://finviz.com/screener.ashx"
# First-order filters (Nomad-flavoured, quantitative only):
#   mid cap and up, ROE > 15%, analysts' 5y EPS growth > 10%, debt/equity < 1, P/FCF < 50
FILTERS = "cap_midover,fa_roe_o15,fa_estltgrowth_o10,fa_debteq_u1,fa_pfcf_u50"
VIEWS = {"valuation": 121, "financial": 161}
HEADERS = {"User-Agent": "Mozilla/5.0 (personal research)"}
OUT = Path(__file__).resolve().parent.parent / "knowledge" / "screens"


def parse_table(html: str) -> list[dict]:
    """Find the results table (the one whose header row starts with No./Ticker) and return dict rows."""
    soup = BeautifulSoup(html, "html.parser")
    for table in soup.find_all("table"):
        rows = table.find_all("tr")
        if not rows:
            continue
        headers = [c.get_text(strip=True) for c in rows[0].find_all(["th", "td"])]
        if "Ticker" not in headers or len(headers) < 5:
            continue
        out = []
        for r in rows[1:]:
            cells = [c.get_text(strip=True) for c in r.find_all("td")]
            if len(cells) == len(headers):
                out.append(dict(zip(headers, cells)))
        if out:
            return out
    return []


def num(s: str | None) -> float | None:
    if s in (None, "", "-"):
        return None
    s = s.replace(",", "").replace("%", "")
    mult = {"B": 1e3, "M": 1, "K": 1e-3}.get(s[-1], None)
    try:
        return float(s[:-1]) * mult if mult else float(s)
    except ValueError:
        return None


def fetch_view(view: int, max_pages: int, delay: float) -> dict[str, dict]:
    rows: dict[str, dict] = {}
    for page in range(max_pages):
        r = requests.get(BASE, params={"v": view, "f": FILTERS, "r": 1 + 20 * page},
                         headers=HEADERS, timeout=30)
        r.raise_for_status()
        batch = parse_table(r.text)
        new = [b for b in batch if b["Ticker"] not in rows]
        for b in new:
            rows[b["Ticker"]] = b
        if len(batch) < 20 or not new:
            break
        time.sleep(delay)
    return rows


# ── own return model ────────────────────────────────────────────────

def irr(cfs: list[float]) -> float:
    lo, hi = -0.9, 2.0
    for _ in range(200):
        mid = (lo + hi) / 2
        npv = sum(c / (1 + mid) ** t for t, c in enumerate(cfs))
        lo, hi = (mid, hi) if npv > 0 else (lo, mid)
    return (lo + hi) / 2


def expected_return(p_fcf: float, eps_5y: float, haircut: float = 0.7, exit_cap: float = 25) -> float:
    g1 = min(eps_5y / 100 * haircut, 0.30)
    g2 = max(g1 / 2, 0.04)
    e, flows = 1 / p_fcf, []
    for y in range(1, 11):
        e *= 1 + (g1 if y <= 5 else g2)
        flows.append(e)
    exit_mult = min(p_fcf, exit_cap)
    return irr([-1.0] + flows[:-1] + [flows[-1] * (1 + exit_mult)])


def odds_of_15(r: float, error: float = 0.06) -> float:
    return 0.5 * (1 + math.erf((r - 0.15) / (error * math.sqrt(2))))


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--max-pages", type=int, default=25)
    ap.add_argument("--delay", type=float, default=2.0)
    args = ap.parse_args()

    val = fetch_view(VIEWS["valuation"], args.max_pages, args.delay)
    fin = fetch_view(VIEWS["financial"], args.max_pages, args.delay)
    print(f"Finviz returned {len(val)} companies passing the first-order filters")

    results = []
    for t, v in val.items():
        f = fin.get(t, {})
        p_fcf, g = num(v.get("P/FCF")), num(v.get("EPS next 5Y"))
        if not p_fcf or p_fcf <= 0 or g is None:
            continue
        r = expected_return(p_fcf, g)
        results.append({
            "ticker": t, "p_fcf": p_fcf, "fcf_yield_pct": round(100 / p_fcf, 1),
            "eps_next_5y_pct": g, "roe_pct": num(f.get("ROE")), "roi_pct": num(f.get("ROI")),
            "gross_margin_pct": num(f.get("Gross M")), "oper_margin_pct": num(f.get("Oper M")),
            "debt_eq": num(f.get("Debt/Eq")), "sales_past_5y_pct": num(v.get("Sales past 5Y")),
            "exp_10y_return_pct": round(r * 100, 1), "odds_15_pct": round(odds_of_15(r) * 100),
        })
    results.sort(key=lambda x: -x["odds_15_pct"])

    OUT.mkdir(parents=True, exist_ok=True)
    path = OUT / f"finviz_{dt.date.today()}.csv"
    if results:
        with path.open("w", newline="") as fh:
            w = csv.DictWriter(fh, fieldnames=list(results[0]))
            w.writeheader()
            w.writerows(results)
    print(f"{'ticker':8}{'FCF yld':>8}{'EPS 5y':>8}{'ROE':>7}{'GM':>6}{'exp 10y':>9}{'P(15%)':>8}")
    for x in results[:30]:
        print(f"{x['ticker']:8}{x['fcf_yield_pct']:7.1f}%{x['eps_next_5y_pct']:7.1f}%"
              f"{(x['roe_pct'] or 0):6.0f}%{(x['gross_margin_pct'] or 0):5.0f}%"
              f"{x['exp_10y_return_pct']:8.1f}%{x['odds_15_pct']:7}%")
    print(f"\nSaved {len(results)} rows to {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
