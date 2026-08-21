"""Core data structures shared across the package.

Everything downstream (model, markets, value scan, backtest) speaks in terms of
:class:`Match` and :class:`BookOdds`.  Keeping them dumb and immutable makes the
pipeline easy to test with hand-built fixtures.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime
from typing import Iterable, Mapping, Optional

PREMIER_LEAGUE = "EPL"
LA_LIGA = "LaLiga"
CHAMPIONS_LEAGUE = "UCL"

SUPPORTED_COMPETITIONS = (PREMIER_LEAGUE, LA_LIGA, CHAMPIONS_LEAGUE)


def _as_date(value) -> date:
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    if isinstance(value, str):
        for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%d/%m/%y", "%Y/%m/%d"):
            try:
                return datetime.strptime(value.strip(), fmt).date()
            except ValueError:
                continue
        raise ValueError(f"unrecognised date format: {value!r}")
    raise TypeError(f"cannot interpret {value!r} as a date")


@dataclass(frozen=True)
class Match:
    """A single played (or scheduled) fixture.

    ``home_xg``/``away_xg`` are optional: Champions League and older seasons
    frequently lack expected-goals coverage, and the model falls back to raw
    goals on a per-match basis when they are absent.
    """

    date: date
    competition: str
    home: str
    away: str
    home_goals: Optional[int] = None
    away_goals: Optional[int] = None
    home_xg: Optional[float] = None
    away_xg: Optional[float] = None
    neutral: bool = False
    match_id: Optional[str] = None
    season: Optional[str] = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "date", _as_date(self.date))
        if self.match_id is None:
            ident = f"{self.date.isoformat()}:{self.competition}:{self.home}:{self.away}"
            object.__setattr__(self, "match_id", ident)

    @property
    def played(self) -> bool:
        return self.home_goals is not None and self.away_goals is not None

    @property
    def has_xg(self) -> bool:
        return self.home_xg is not None and self.away_xg is not None

    @property
    def result(self) -> str:
        """``H``, ``D`` or ``A``."""
        if not self.played:
            raise ValueError(f"{self.match_id} has no result yet")
        if self.home_goals > self.away_goals:
            return "H"
        if self.home_goals < self.away_goals:
            return "A"
        return "D"


@dataclass(frozen=True)
class OddsQuote:
    """One price from one bookmaker for one selection."""

    market: str
    selection: str
    odds: float
    bookmaker: str = "book"
    is_closing: bool = True

    def __post_init__(self) -> None:
        if self.odds <= 1.0:
            raise ValueError(
                f"decimal odds must exceed 1.0, got {self.odds} for "
                f"{self.market}/{self.selection}"
            )


@dataclass
class BookOdds:
    """All prices available for one match, grouped by market.

    A *market group* is a set of mutually exclusive, collectively exhaustive
    selections (``1X2`` -> H/D/A; ``ou_2.5`` -> Over/Under).  Grouping matters
    because the overround can only be stripped from a complete book.
    """

    match_id: str
    quotes: list[OddsQuote] = field(default_factory=list)
    kickoff: Optional[date] = None

    def add(self, market: str, selection: str, odds: float, **kw) -> "BookOdds":
        self.quotes.append(OddsQuote(market, selection, float(odds), **kw))
        return self

    def markets(self) -> dict[str, dict[str, float]]:
        out: dict[str, dict[str, float]] = {}
        for q in self.quotes:
            out.setdefault(q.market, {})[q.selection] = q.odds
        return out

    def get(self, market: str, selection: str) -> Optional[float]:
        for q in self.quotes:
            if q.market == market and q.selection == selection:
                return q.odds
        return None

    @classmethod
    def from_mapping(
        cls, match_id: str, mapping: Mapping[str, Mapping[str, float]], **kw
    ) -> "BookOdds":
        book = cls(match_id=match_id, **kw)
        for market, sels in mapping.items():
            for selection, odds in sels.items():
                book.add(market, selection, odds)
        return book


def date_range(matches: Iterable[Match]) -> tuple[Optional[date], Optional[date]]:
    dates = sorted(m.date for m in matches)
    if not dates:
        return None, None
    return dates[0], dates[-1]
