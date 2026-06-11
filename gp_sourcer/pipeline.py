"""
Pipeline — lightweight JSON-backed kanban for fund opportunities.

Stages: radar -> initial_review -> soft_circle -> full_diligence -> committed | passed
Cards arrive from any module (deal feed, LP watch, talent signal, agent offering).
"""

from __future__ import annotations

import json
from datetime import date
from pathlib import Path

STAGES = ["radar", "initial_review", "soft_circle", "full_diligence", "committed", "passed"]

_STORE = Path(__file__).parent / "data" / "pipeline.json"


def _load() -> list[dict]:
    if _STORE.exists():
        return json.loads(_STORE.read_text())
    return []


def _save(cards: list[dict]) -> None:
    _STORE.parent.mkdir(exist_ok=True)
    _STORE.write_text(json.dumps(cards, indent=2))


def add_to_pipeline(
    fund_name: str,
    gp_name: str = "",
    strategy: str = "",
    size_usd: int | None = None,
    fund_number: int | None = None,
    source: str = "",                 # form_d | lp_watch | talent_signal | placement_agent | manual
    stage: str = "radar",
    conviction: str = "",             # high | medium | low
    note: str = "",
) -> dict:
    if stage not in STAGES:
        return {"error": f"Invalid stage '{stage}'. Valid: {STAGES}"}
    cards = _load()
    if any(c["fund_name"].lower() == fund_name.lower() for c in cards):
        return {"error": f"'{fund_name}' already in pipeline", "duplicate": True}
    card = {
        "fund_name": fund_name,
        "gp_name": gp_name,
        "strategy": strategy,
        "size_usd": size_usd,
        "fund_number": fund_number,
        "source": source,
        "stage": stage,
        "conviction": conviction,
        "note": note,
        "added": date.today().isoformat(),
        "last_action": date.today().isoformat(),
    }
    cards.append(card)
    _save(cards)
    return card


def move_stage(fund_name: str, new_stage: str, note: str = "") -> dict:
    if new_stage not in STAGES:
        return {"error": f"Invalid stage '{new_stage}'. Valid: {STAGES}"}
    cards = _load()
    for c in cards:
        if c["fund_name"].lower() == fund_name.lower():
            c["stage"] = new_stage
            c["last_action"] = date.today().isoformat()
            if note:
                c["note"] = (c["note"] + " | " if c["note"] else "") + note
            _save(cards)
            return c
    return {"error": f"'{fund_name}' not found in pipeline"}


def get_pipeline(stage: str | None = None) -> dict:
    """Return the board grouped by stage, or a single stage's cards."""
    cards = _load()
    if stage:
        return {stage: [c for c in cards if c["stage"] == stage]}
    return {s: [c for c in cards if c["stage"] == s] for s in STAGES}
