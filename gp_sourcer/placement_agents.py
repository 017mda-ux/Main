"""
Placement Agent Tracker — offerings in market via reputable agents.

Watched agents per the LP's list (Shannon, Pacenote, Acalyx, Lazard)
plus the standard institutional set. Offerings enter via:
  1. Manual entry (teaser received) — the common path; agents don't publish
  2. Weekly web sweep — mandate announcements, "X retains Y" coverage
"""

from __future__ import annotations

import json
from datetime import date
from pathlib import Path

WATCHED_AGENTS: dict[str, dict] = {
    "shannon": {"name": "Shannon Advisors", "tier": "watch"},
    "pacenote": {"name": "Pacenote Capital", "tier": "watch",
                 "note": "Known for emerging-manager and spinout mandates"},
    "acalyx": {"name": "Acalyx Advisors", "tier": "watch",
               "note": "Emerging/first-time fund specialist"},
    "lazard": {"name": "Lazard Private Capital Advisory", "tier": "bulge"},
    "parkhill": {"name": "Park Hill (PJT Partners)", "tier": "bulge"},
    "evercore": {"name": "Evercore Private Funds Group", "tier": "bulge"},
    "campbell_lutyens": {"name": "Campbell Lutyens", "tier": "bulge"},
    "rede": {"name": "Rede Partners", "tier": "mid"},
    "mvision": {"name": "MVision", "tier": "mid"},
    "asante": {"name": "Asante Capital", "tier": "mid"},
}

_STORE = Path(__file__).parent / "data" / "agent_offerings.json"


def _load() -> list[dict]:
    if _STORE.exists():
        return json.loads(_STORE.read_text())
    return []


def _save(offerings: list[dict]) -> None:
    _STORE.parent.mkdir(exist_ok=True)
    _STORE.write_text(json.dumps(offerings, indent=2))


def log_offering(
    agent_id: str,
    fund_name: str,
    gp_name: str = "",
    strategy: str = "",                 # buyout | growth | venture | credit | real_assets
    target_usd: int | None = None,
    expected_close: str = "",
    received_date: str = "",
    status: str = "teaser_received",    # teaser_received | reviewing | meeting_set | passed | progressed
    note: str = "",
) -> dict:
    """Record a placement-agent offering (typically from a received teaser)."""
    if agent_id not in WATCHED_AGENTS:
        return {"error": f"Unknown agent id '{agent_id}'. Known: {sorted(WATCHED_AGENTS)}"}
    offerings = _load()
    rec = {
        "agent_id": agent_id,
        "agent_name": WATCHED_AGENTS[agent_id]["name"],
        "fund_name": fund_name,
        "gp_name": gp_name,
        "strategy": strategy,
        "target_usd": target_usd,
        "expected_close": expected_close,
        "received_date": received_date or date.today().isoformat(),
        "status": status,
        "note": note,
    }
    offerings.append(rec)
    _save(offerings)
    return rec


def get_offerings(agent_id: str | None = None, status: str | None = None,
                  limit: int = 50) -> list[dict]:
    offerings = _load()
    if agent_id:
        offerings = [o for o in offerings if o["agent_id"] == agent_id]
    if status:
        offerings = [o for o in offerings if o["status"] == status]
    return sorted(offerings, key=lambda o: o["received_date"], reverse=True)[:limit]


def agent_sweep_queries() -> list[dict]:
    """Web-search queries for the weekly placement-agent sweep."""
    out = []
    for agent_id, agent in WATCHED_AGENTS.items():
        out.append({
            "agent_id": agent_id,
            "queries": [
                f'"{agent["name"]}" placement agent fund mandate 2026',
                f'"{agent["name"]}" retained fundraising',
            ],
        })
    return out
