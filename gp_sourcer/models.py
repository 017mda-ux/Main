"""Data models and persistent JSON store for the GP sourcing pipeline."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from datetime import datetime
from pathlib import Path
from typing import List, Optional

PIPELINE_STAGES = ["prospect", "contacted", "meeting", "diligence", "committed", "passed"]

STATUS_COLORS = {
    "prospect": "dim white",
    "contacted": "cyan",
    "meeting": "yellow",
    "diligence": "blue",
    "committed": "bold green",
    "passed": "red",
}

STATUS_LABELS = {
    "prospect": "Prospect",
    "contacted": "Contacted",
    "meeting": "Meeting",
    "diligence": "Due Diligence",
    "committed": "Committed ✓",
    "passed": "Passed",
}


@dataclass
class GP:
    id: str
    name: str
    firm: str
    role: str
    focus_areas: List[str]
    stage: List[str]
    geography: List[str]
    fund_size_m: Optional[float]
    aum_m: Optional[float]
    portfolio_highlights: List[str]
    notable_exits: List[str]
    bio: str
    status: str = "prospect"
    notes: List[str] = field(default_factory=list)
    tags: List[str] = field(default_factory=list)
    linkedin: Optional[str] = None
    twitter: Optional[str] = None
    website: Optional[str] = None
    added_date: str = field(default_factory=lambda: datetime.now().strftime("%Y-%m-%d"))
    last_contacted: Optional[str] = None
    fit_score: Optional[int] = None


_GP_DEFAULTS = {
    "notes": [],
    "tags": [],
    "linkedin": None,
    "twitter": None,
    "website": None,
    "last_contacted": None,
    "fit_score": None,
    "aum_m": None,
    "status": "prospect",
}


class GPStore:
    """JSON-backed persistent store for the GP sourcing pipeline."""

    def __init__(self, path: str = "./data/gp_pipeline.json"):
        self.path = Path(path)
        self._gps: dict[str, GP] = {}
        self._load()

    def _load(self) -> None:
        if not self.path.exists():
            return
        try:
            raw = json.loads(self.path.read_text())
            for k, v in raw.items():
                for key, default in _GP_DEFAULTS.items():
                    v.setdefault(key, default)
                self._gps[k] = GP(**v)
        except Exception:
            self._gps = {}

    def save(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(json.dumps({k: asdict(v) for k, v in self._gps.items()}, indent=2))

    def add(self, gp: GP) -> None:
        self._gps[gp.id] = gp
        self.save()

    def get(self, gp_id: str) -> Optional[GP]:
        return self._gps.get(gp_id)

    def get_by_index(self, idx: int, filtered: Optional[List[GP]] = None) -> Optional[GP]:
        gps = filtered if filtered is not None else self.all()
        if 1 <= idx <= len(gps):
            return gps[idx - 1]
        return None

    def all(self) -> List[GP]:
        return list(self._gps.values())

    def update(self, gp: GP) -> None:
        self._gps[gp.id] = gp
        self.save()

    def filter(
        self,
        status: Optional[str] = None,
        stage: Optional[str] = None,
        sector: Optional[str] = None,
        search: Optional[str] = None,
    ) -> List[GP]:
        results = self.all()
        if status:
            results = [g for g in results if g.status == status]
        if stage:
            results = [g for g in results if any(stage.lower() in s.lower() for s in g.stage)]
        if sector:
            results = [g for g in results if any(sector.lower() in f.lower() for f in g.focus_areas)]
        if search:
            q = search.lower()
            results = [g for g in results if (
                q in g.name.lower()
                or q in g.firm.lower()
                or q in g.bio.lower()
                or any(q in t.lower() for t in g.tags)
                or any(q in f.lower() for f in g.focus_areas)
            )]
        return results

    def pipeline_stats(self) -> dict:
        stats = {s: 0 for s in PIPELINE_STAGES}
        for gp in self.all():
            if gp.status in stats:
                stats[gp.status] += 1
        stats["total"] = len(self._gps)
        return stats

    def is_empty(self) -> bool:
        return not self._gps
