"""
Fundraise Cycle Forecaster — predict who is in market now or coming back.

Model (per the LP's assumptions):
  - Buyout GPs raise every 3 years; venture and growth every 2
  - If a GP has 2+ known closes, the observed cadence overrides the default
  - GPs pre-market ~6 months before launch, so the "in market" window opens
    at: last_close + cycle - 6 months

Status:
  in_market_now  - window already open (predicted raising today)
  imminent       - window opens within 12 months
  monitor        - window opens later

Verification path: predictions are hypotheses — confirm with
form_d_manager_history (a new Form D filing = confirmed in market).
"""

from __future__ import annotations

from datetime import date, timedelta

CYCLE_YEARS = {"buyout": 3, "venture": 2, "growth": 2, "credit": 3, "real_assets": 3}
PREMARKET_MONTHS = 6

# Known fund-close history. close dates verified in-session unless
# confidence is "memory" (verify before acting).
GP_FUND_HISTORY: list[dict] = [
    # --- Verified this session (2026 press / Dakota) ---
    {"gp": "Seven Hills Capital", "strategy": "buyout", "confidence": "verified",
     "funds": [{"name": "Fund I", "close": "2024-02-01", "size_usd": 125_000_000},
               {"name": "Fund II", "close": "2026-02-27", "size_usd": 235_000_000}],
     "note": "Healthcare LMM; Pacenote exclusive agent; Fund II oversubscribed in <3mo"},
    {"gp": "Palm Peak Capital", "strategy": "buyout", "confidence": "verified",
     "funds": [{"name": "Fund I", "close": "2026-02-19", "size_usd": 374_000_000}],
     "note": "Sun Capital spinout; LMM industrials"},
    {"gp": "KKR (North America flagship)", "strategy": "buyout", "confidence": "verified",
     "funds": [{"name": "North America Fund XIII", "close": "2022-04-01", "size_usd": 19_000_000_000},
               {"name": "North America Fund XIV", "close": "2026-05-01", "size_usd": 23_000_000_000}]},
    {"gp": "26North Partners", "strategy": "buyout", "confidence": "verified",
     "funds": [{"name": "Debut PE Fund", "close": "2026-05-01", "size_usd": 5_900_000_000}],
     "note": "Josh Harris (ex-Apollo) spinout"},
    {"gp": "EQT (BPEA Asia)", "strategy": "buyout", "confidence": "verified",
     "funds": [{"name": "BPEA VIII", "close": "2022-09-01", "size_usd": 11_200_000_000},
               {"name": "BPEA IX", "close": "2026-04-01", "size_usd": 15_600_000_000}]},
    {"gp": "Court Square Capital", "strategy": "buyout", "confidence": "verified",
     "funds": [{"name": "Fund V", "close": "2026-04-01", "size_usd": 3_800_000_000}]},
    {"gp": "OceanSound Partners", "strategy": "buyout", "confidence": "verified",
     "funds": [{"name": "Fund II", "close": "2023-08-01", "size_usd": 1_490_000_000},
               {"name": "Fund III", "close": "2026-04-01", "size_usd": 3_400_000_000}],
     "note": "Defense / government technology"},
    {"gp": "Bain Capital (Asia)", "strategy": "buyout", "confidence": "verified",
     "funds": [{"name": "Asia Fund V", "close": "2023-02-01", "size_usd": 7_100_000_000},
               {"name": "Asia Fund VI", "close": "2026-05-01", "size_usd": 10_500_000_000}]},
    {"gp": "THL Partners", "strategy": "buyout", "confidence": "verified",
     "funds": [{"name": "Fund IX", "close": "2021-11-01", "size_usd": 5_600_000_000},
               {"name": "Fund X", "close": "2026-05-01", "size_usd": 6_350_000_000}]},
    {"gp": "Apollo (Hybrid Value)", "strategy": "buyout", "confidence": "verified",
     "funds": [{"name": "Hybrid Value Fund II", "close": "2022-06-01", "size_usd": 4_600_000_000},
               {"name": "Hybrid Value Fund III", "close": "2026-05-01", "size_usd": 6_500_000_000}]},
    {"gp": "Lightspeed Venture Partners", "strategy": "venture", "confidence": "verified",
     "funds": [{"name": "Select V + flagship (combined)", "close": "2022-07-01", "size_usd": 7_100_000_000},
               {"name": "2025 fund family", "close": "2025-12-15", "size_usd": 9_000_000_000}]},
    {"gp": "Andreessen Horowitz (crypto)", "strategy": "venture", "confidence": "verified",
     "funds": [{"name": "Crypto Fund IV", "close": "2022-05-01", "size_usd": 4_500_000_000},
               {"name": "Crypto Fund V", "close": "2026-05-05", "size_usd": 2_200_000_000}]},
    {"gp": "Earlybird Venture Capital", "strategy": "venture", "confidence": "verified",
     "funds": [{"name": "Fund VIII (largest ever)", "close": "2026-05-01", "size_usd": 378_000_000}]},
    {"gp": "Eclipse Ventures", "strategy": "venture", "confidence": "verified",
     "funds": [{"name": "Physical economy funds", "close": "2026-04-01", "size_usd": 1_310_000_000}]},
    {"gp": "Knox Lane (TPG Growth spinout)", "strategy": "growth", "confidence": "verified",
     "funds": [{"name": "Fund I", "close": "2022-03-01", "size_usd": 610_000_000},
               {"name": "Fund II", "close": "2024-12-01", "size_usd": 1_000_000_000}]},
    # --- Memory-based vintages (verify via form_d_manager_history before acting) ---
    {"gp": "Insight Partners", "strategy": "growth", "confidence": "memory",
     "funds": [{"name": "Fund XII", "close": "2022-02-01", "size_usd": 20_000_000_000},
               {"name": "Fund XIII", "close": "2025-01-01", "size_usd": 12_500_000_000}]},
    {"gp": "GTCR", "strategy": "buyout", "confidence": "memory",
     "funds": [{"name": "Fund XIII", "close": "2020-11-01", "size_usd": 7_500_000_000},
               {"name": "Fund XIV", "close": "2023-07-01", "size_usd": 11_500_000_000}],
     "note": "Flagship XV not yet announced, but actively raising: mid-cap fund II "
             "($3B target) + Strategic Growth II closed $3.6B Feb 2025 (Buyouts/Bloomberg)"},
    {"gp": "Clayton Dubilier & Rice", "strategy": "buyout", "confidence": "memory",
     "funds": [{"name": "Fund XI", "close": "2020-01-01", "size_usd": 16_000_000_000},
               {"name": "Fund XII", "close": "2023-08-01", "size_usd": 26_000_000_000}]},
    {"gp": "Warburg Pincus", "strategy": "buyout", "confidence": "memory",
     "funds": [{"name": "Global Growth", "close": "2018-12-01", "size_usd": 14_800_000_000},
               {"name": "Global Growth 14", "close": "2023-10-01", "size_usd": 17_300_000_000}]},
    {"gp": "Permira", "strategy": "buyout", "confidence": "verified",
     "funds": [{"name": "Fund VII", "close": "2019-10-01", "size_usd": 12_100_000_000},
               {"name": "Fund VIII", "close": "2023-03-01", "size_usd": 18_000_000_000}],
     "note": "CONFIRMED IN MARKET: Permira IX launched Jul 2025, €17B target (FN London)"},
    {"gp": "Genstar Capital", "strategy": "buyout", "confidence": "memory",
     "funds": [{"name": "Fund X", "close": "2021-04-01", "size_usd": 10_200_000_000},
               {"name": "Fund XI", "close": "2023-04-01", "size_usd": 12_600_000_000}]},
    {"gp": "Vista Equity Partners", "strategy": "buyout", "confidence": "memory",
     "funds": [{"name": "Fund VII", "close": "2019-09-01", "size_usd": 16_000_000_000},
               {"name": "Fund VIII", "close": "2024-04-01", "size_usd": 20_000_000_000}]},
    {"gp": "Bessemer Venture Partners", "strategy": "venture", "confidence": "memory",
     "funds": [{"name": "Fund XI", "close": "2021-02-01", "size_usd": 3_300_000_000},
               {"name": "Fund XII", "close": "2024-05-01", "size_usd": 3_850_000_000}]},
    {"gp": "TA Associates", "strategy": "growth", "confidence": "memory",
     "funds": [{"name": "Fund XIV", "close": "2021-06-01", "size_usd": 12_500_000_000},
               {"name": "Fund XV", "close": "2023-06-01", "size_usd": 16_500_000_000}]},
    {"gp": "Summit Partners", "strategy": "growth", "confidence": "memory",
     "funds": [{"name": "Growth Equity X", "close": "2019-09-01", "size_usd": 4_900_000_000},
               {"name": "Growth Equity XI", "close": "2021-12-01", "size_usd": 8_350_000_000}]},
]


def _parse(d: str) -> date:
    return date.fromisoformat(d)


def _observed_cycle_years(funds: list[dict]) -> float | None:
    """Average years between consecutive closes, if 2+ closes known."""
    closes = sorted(_parse(f["close"]) for f in funds)
    if len(closes) < 2:
        return None
    gaps = [(b - a).days / 365.25 for a, b in zip(closes, closes[1:])]
    return sum(gaps) / len(gaps)


def forecast_gp(record: dict, today: date | None = None) -> dict:
    """Predict the next raise window for one GP record."""
    today = today or date.today()
    funds = sorted(record["funds"], key=lambda f: f["close"])
    last = funds[-1]
    last_close = _parse(last["close"])

    observed = _observed_cycle_years(funds)
    default = CYCLE_YEARS.get(record["strategy"], 3)
    cycle = observed if observed is not None else float(default)

    next_close_due = last_close + timedelta(days=int(cycle * 365.25))
    window_opens = next_close_due - timedelta(days=int(PREMARKET_MONTHS * 30.4))

    if today >= window_opens:
        status = "in_market_now"
    elif (window_opens - today).days <= 365:
        status = "imminent"
    else:
        status = "monitor"

    # naive next-size guess: last size * observed growth (capped 2x), else last size
    growth = 1.0
    if len(funds) >= 2 and funds[-2].get("size_usd") and last.get("size_usd"):
        growth = min(last["size_usd"] / funds[-2]["size_usd"], 2.0)
    est_next_size = int(last["size_usd"] * growth) if last.get("size_usd") else None

    return {
        "gp": record["gp"],
        "strategy": record["strategy"],
        "last_fund": last["name"],
        "last_close": last["close"],
        "last_size_usd": last.get("size_usd"),
        "cycle_years": round(cycle, 1),
        "cycle_basis": "observed" if observed is not None else f"assumed ({default}y {record['strategy']})",
        "window_opens": window_opens.isoformat(),
        "next_close_due": next_close_due.isoformat(),
        "status": status,
        "est_next_size_usd": est_next_size,
        "confidence": record.get("confidence", "verified"),
        "note": record.get("note", ""),
        "verify_with": f'form_d_manager_history(manager_name="{record["gp"].split(" (")[0]}")',
    }


def forecast_market(
    status: str | None = None,          # "in_market_now" | "imminent" | "monitor"
    strategy: str | None = None,
    records: list[dict] | None = None,
    today: date | None = None,
) -> dict:
    """Forecast across the GP registry, soonest window first."""
    rows = [forecast_gp(r, today) for r in (records or GP_FUND_HISTORY)]
    if status:
        rows = [r for r in rows if r["status"] == status]
    if strategy:
        rows = [r for r in rows if r["strategy"] == strategy]
    rows.sort(key=lambda r: r["window_opens"])
    return {
        "as_of": (today or date.today()).isoformat(),
        "counts": {
            "in_market_now": sum(1 for r in rows if r["status"] == "in_market_now"),
            "imminent": sum(1 for r in rows if r["status"] == "imminent"),
            "monitor": sum(1 for r in rows if r["status"] == "monitor"),
        },
        "forecasts": rows,
        "model": "buyout/credit/real_assets 3y, venture/growth 2y; observed cadence "
                 "overrides when 2+ closes known; window opens 6mo before predicted close",
    }
