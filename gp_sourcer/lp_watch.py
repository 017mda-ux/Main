"""
LP Watch — track the reference LPs whose commitments are quality signals.

The LP's named watch list: WashU St. Louis, CPPIB, Yale, Michigan,
UNC Management, SWIB, MIT IMC, SCS Financial.

Signals come from three places:
  1. IRS 990 filings (endowments)         -> irs_990.py
  2. Public pension disclosures (CPPIB, SWIB) -> press / board minutes
  3. Press coverage of fund closes naming the LP

This module stores the watch list, a signal log, and provides search
query generators for the agent's weekly sweep.
"""

from __future__ import annotations

import json
from datetime import date
from pathlib import Path

WATCHED_LPS: dict[str, dict] = {
    "washu": {
        "name": "Washington University in St. Louis (WUIMC)",
        "type": "endowment", "aum_bn": 13.5, "ein": "43-0653611",
        "disclosure": "IRS 990 Schedule D/R (lagged ~18mo)",
    },
    "cppib": {
        "name": "CPP Investments (CPPIB)",
        "type": "public_pension", "aum_bn": 700,
        "disclosure": "Quarterly transaction disclosures + press releases (cppinvestments.com)",
    },
    "yale": {
        "name": "Yale University Investments Office",
        "type": "endowment", "aum_bn": 41, "ein": "06-0646973",
        "disclosure": "IRS 990 + secondary-sale reporting (e.g. Project Gatsby)",
    },
    "michigan": {
        "name": "University of Michigan Investment Office",
        "type": "endowment", "aum_bn": 18, "ein": "38-6006309",
        "disclosure": "Monthly Regents agenda items disclose every new commitment",
    },
    "unc": {
        "name": "UNC Management Company",
        "type": "endowment", "aum_bn": 10, "ein": "56-1583594",
        "disclosure": "IRS 990; limited press",
    },
    "swib": {
        "name": "State of Wisconsin Investment Board (SWIB)",
        "type": "public_pension", "aum_bn": 156,
        "disclosure": "Public PE portfolio with per-fund commitments (swib.state.wi.us)",
    },
    "mitimco": {
        "name": "MIT Investment Management Company (MITIMCo)",
        "type": "endowment", "aum_bn": 24, "ein": "04-2103594",
        "disclosure": "IRS 990; known for early-manager seeding",
    },
    "scs": {
        "name": "SCS Financial (Focus Partners Wealth)",
        "type": "ofo_wealth", "aum_bn": 30,
        "disclosure": "No public disclosure — manual/network entry only",
    },
}

_STORE = Path(__file__).parent / "data" / "lp_signals.json"


def _load() -> list[dict]:
    if _STORE.exists():
        return json.loads(_STORE.read_text())
    return []


def _save(signals: list[dict]) -> None:
    _STORE.parent.mkdir(exist_ok=True)
    _STORE.write_text(json.dumps(signals, indent=2))


def log_lp_signal(
    lp_id: str,
    fund_name: str,
    gp_name: str = "",
    commitment_usd: int | None = None,
    source: str = "",
    signal_date: str = "",
    note: str = "",
) -> dict:
    """Record an observed LP commitment / signal."""
    if lp_id not in WATCHED_LPS:
        return {"error": f"Unknown LP id '{lp_id}'. Known: {sorted(WATCHED_LPS)}"}
    signals = _load()
    rec = {
        "lp_id": lp_id,
        "lp_name": WATCHED_LPS[lp_id]["name"],
        "fund_name": fund_name,
        "gp_name": gp_name,
        "commitment_usd": commitment_usd,
        "source": source,
        "signal_date": signal_date or date.today().isoformat(),
        "note": note,
    }
    signals.append(rec)
    _save(signals)
    return rec


def get_lp_signals(lp_id: str | None = None, limit: int = 50) -> list[dict]:
    """Return logged signals, newest first, optionally for one LP."""
    signals = _load()
    if lp_id:
        signals = [s for s in signals if s["lp_id"] == lp_id]
    return sorted(signals, key=lambda s: s["signal_date"], reverse=True)[:limit]


def lp_sweep_queries() -> list[dict]:
    """Web-search queries for the weekly LP sweep, one batch per LP."""
    queries = []
    for lp_id, lp in WATCHED_LPS.items():
        if lp_id == "scs":
            continue  # no public footprint to search
        short = lp["name"].split("(")[0].strip()
        queries.append({
            "lp_id": lp_id,
            "queries": [
                f'"{short}" commits private equity fund 2026',
                f'"{short}" limited partner new fund close',
                f'"{short}" venture capital commitment',
            ],
        })
    return queries
