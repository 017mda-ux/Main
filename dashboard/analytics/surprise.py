"""Scoring economic prints against consensus.

Consensus is not available from an official source, so it is supplied by the
caller (from the release calendar file) and always carried through to the page
with its provenance attached.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from statistics import pstdev


@dataclass
class Surprise:
    key: str
    label: str
    released_on: date
    actual: float
    consensus: float | None
    prior: float | None
    prior_revised: float | None
    unit: str = ""
    consensus_source: str = ""

    @property
    def miss(self) -> float | None:
        if self.consensus is None:
            return None
        return self.actual - self.consensus

    @property
    def revision(self) -> float | None:
        if self.prior is None or self.prior_revised is None:
            return None
        return self.prior_revised - self.prior

    def z(self, history: list[float] | None = None) -> float | None:
        """Miss expressed in std devs of past misses for the same release."""
        m = self.miss
        if m is None:
            return None
        if not history or len(history) < 6:
            return None
        sd = pstdev(history)
        return m / sd if sd > 0 else None

    @property
    def direction(self) -> str:
        m = self.miss
        if m is None:
            return "inline"
        if abs(m) < 1e-9:
            return "inline"
        return "beat" if m > 0 else "miss"


def surprise_salience(s: Surprise, history: list[float] | None = None,
                      weight: float = 1.0) -> float:
    """0–100 contribution of a data surprise, scaled by the release's weight."""
    z = s.z(history)
    if z is None:
        # No surprise distribution — fall back to a proportional miss.
        m, c = s.miss, s.consensus
        if m is None or not c:
            return 0.0
        rel = abs(m) / max(abs(c), 1e-6)
        return min(rel * 100.0, 60.0) * weight
    base = min(abs(z) * 30.0, 90.0)
    if s.revision is not None and abs(s.revision) > 0:
        base += 10.0
    return min(base * weight, 100.0)
