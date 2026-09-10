"""Stooq end-of-day CSV — index, futures and metals levels.

Exchange data (equity indices, metals, vol) is not published by a government
agency, so it comes from a market source.  FRED is preferred where it carries
the same series; this fills the gaps.
"""

from __future__ import annotations

import csv
import io
from datetime import date, datetime

from ..analytics.series import TimeSeries
from .http import HttpError, get

DAILY = "https://stooq.com/q/d/l/?s={symbol}&i=d"

LABELS = {
    "^spx": "S&P 500", "^ndx": "Nasdaq 100", "^dji": "Dow Jones",
    "^vix": "VIX", "^move": "MOVE",
    "xauusd": "Gold", "xagusd": "Silver",
    "hg.f": "Copper", "cl.f": "WTI crude", "cb.f": "Brent crude",
}


def fetch(symbol: str, **kw) -> TimeSeries:
    """Download a Stooq daily series (close prices)."""
    raw = get(DAILY.format(symbol=symbol), **kw)
    reader = csv.DictReader(io.StringIO(raw))
    if not reader.fieldnames or "Close" not in reader.fieldnames:
        raise HttpError(f"Stooq {symbol}: unexpected columns {reader.fieldnames!r}")

    pairs: list[tuple[date, float | None]] = []
    for row in reader:
        try:
            d = datetime.strptime(row["Date"], "%Y-%m-%d").date()
            pairs.append((d, float(row["Close"])))
        except (ValueError, TypeError, KeyError):
            continue

    return TimeSeries.from_pairs(
        symbol, pairs, unit="index",
        label=LABELS.get(symbol, symbol), source="Stooq (end of day)",
    )
