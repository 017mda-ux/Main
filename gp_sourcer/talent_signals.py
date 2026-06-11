"""
Talent Signals — spinout detection and senior departure tracking.

Two signal types:
  1. departure  - partner/MD/VP leaves a watched firm (LinkedIn status change,
                  press coverage, "former X partner" mentions)
  2. spinout    - a new firm registers (IAPD/Form D) led by alumni of a
                  watched firm — the actual investable event

Detection paths:
  - Weekly web search per watched firm (query generators below)
  - New IAPD registrations cross-checked against alumni keywords
  - Form D filings where key persons' bios mention a watched firm
"""

from __future__ import annotations

import json
from datetime import date
from pathlib import Path

# Firms whose alumni historically launch fundable spinouts.
WATCHED_FIRMS: list[str] = [
    # Mega/large buyout
    "KKR", "Blackstone", "Carlyle", "Apollo Global Management", "TPG",
    "Warburg Pincus", "Bain Capital", "Advent International", "Hellman & Friedman",
    # Tech / mid buyout
    "Vista Equity Partners", "Thoma Bravo", "Francisco Partners", "Silver Lake",
    # Growth
    "General Atlantic", "Insight Partners", "Summit Partners", "TA Associates",
    # Venture
    "Sequoia Capital", "Accel", "Andreessen Horowitz", "Benchmark",
    "Lightspeed Venture Partners", "NEA", "Bessemer Venture Partners",
    "Founders Fund", "General Catalyst",
]

SENIOR_TITLES = ["Partner", "Managing Director", "Principal", "Vice President",
                 "Managing Partner", "General Partner", "Co-Founder"]

_STORE = Path(__file__).parent / "data" / "talent_signals.json"


def _load() -> list[dict]:
    if _STORE.exists():
        return json.loads(_STORE.read_text())
    return []


def _save(signals: list[dict]) -> None:
    _STORE.parent.mkdir(exist_ok=True)
    _STORE.write_text(json.dumps(signals, indent=2))


def log_talent_signal(
    person: str,
    prior_firm: str,
    prior_title: str = "",
    signal_type: str = "departure",       # "departure" | "spinout"
    new_firm: str = "",
    evidence: str = "",
    signal_date: str = "",
    status: str = "watching",             # "watching" | "spinout_confirmed" | "joined_competitor" | "closed"
) -> dict:
    """Record a departure or spinout signal."""
    signals = _load()
    rec = {
        "person": person,
        "prior_firm": prior_firm,
        "prior_title": prior_title,
        "signal_type": signal_type,
        "new_firm": new_firm,
        "evidence": evidence,
        "signal_date": signal_date or date.today().isoformat(),
        "status": status,
    }
    signals.append(rec)
    _save(signals)
    return rec


def get_talent_signals(signal_type: str | None = None, limit: int = 50) -> list[dict]:
    signals = _load()
    if signal_type:
        signals = [s for s in signals if s["signal_type"] == signal_type]
    return sorted(signals, key=lambda s: s["signal_date"], reverse=True)[:limit]


def departure_sweep_queries(firms: list[str] | None = None) -> list[dict]:
    """
    Web-search queries for the weekly departure sweep. LinkedIn itself can't be
    scraped, but departures surface fast in trade press and "joins/launches"
    announcements; LinkedIn status changes get reported within days.
    """
    out = []
    for firm in firms or WATCHED_FIRMS:
        out.append({
            "firm": firm,
            "queries": [
                f'"former {firm}" partner OR "managing director" launches fund 2026',
                f'"{firm}" partner departs OR leaves OR exits 2026',
                f'"previously at {firm}" new firm Form D',
                f'"{firm}" alumni spinout fund first close',
            ],
        })
    return out


def spinout_check_queries(person: str, prior_firm: str) -> list[str]:
    """Once a departure is logged, these confirm whether a fund is forming."""
    return [
        f'"{person}" new fund OR new firm OR launches',
        f'"{person}" Form D site:sec.gov',
        f'"{person}" "{prior_firm}" spinout fundraising',
        f'"{person}" registered investment adviser',
    ]
