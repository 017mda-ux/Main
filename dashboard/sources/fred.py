"""FRED (Federal Reserve Bank of St. Louis).

Uses the public `fredgraph.csv` endpoint, which serves full history without an
API key.  Anything FRED redistributes carries its originating agency — Treasury
for the constant-maturity curve, BLS for prices, ICE for OAS — recorded in
`ORIGIN` so the page can attribute correctly.
"""

from __future__ import annotations

import csv
import io
from datetime import date, datetime

from ..analytics.series import TimeSeries
from .http import HttpError, get

BASE = "https://fred.stlouisfed.org/graph/fredgraph.csv"

ORIGIN = {
    "DGS": "U.S. Treasury (constant maturity)",
    "DFII": "U.S. Treasury (TIPS)",
    "T10Y": "Federal Reserve Board / Treasury",
    "T5YIFR": "Federal Reserve Board",
    "EFFR": "Federal Reserve Bank of New York",
    "SOFR": "Federal Reserve Bank of New York",
    "IORB": "Federal Reserve Board",
    "RRPONTSYD": "Federal Reserve Bank of New York",
    "WALCL": "Federal Reserve Board (H.4.1)",
    "WTREGEN": "U.S. Treasury (Daily Treasury Statement)",
    "BAML": "ICE BofA index, via FRED",
    "DEX": "Federal Reserve Board (H.10)",
    "DTWEXBGS": "Federal Reserve Board (H.10)",
    "VIXCLS": "Cboe",
    "DCOIL": "U.S. EIA",
    "PCEPILFE": "U.S. BEA",
    "RSAFS": "U.S. Census Bureau",
}


def attribution(series_id: str) -> str:
    for prefix, name in ORIGIN.items():
        if series_id.startswith(prefix):
            return name
    return "FRED"


def fetch(series_id: str, *, start: str = "2015-01-01", **kw) -> TimeSeries:
    """Download one FRED series as a TimeSeries."""
    url = f"{BASE}?id={series_id}&cosd={start}"
    raw = get(url, **kw)

    reader = csv.reader(io.StringIO(raw))
    header = next(reader, None)
    if not header or len(header) < 2:
        raise HttpError(f"FRED {series_id}: unexpected CSV header {header!r}")

    pairs: list[tuple[date, float | None]] = []
    for row in reader:
        if len(row) < 2:
            continue
        try:
            d = datetime.strptime(row[0].strip(), "%Y-%m-%d").date()
        except ValueError:
            continue
        val = row[1].strip()
        if val in (".", "", "NA"):
            continue          # FRED marks holidays and gaps with a period
        try:
            pairs.append((d, float(val)))
        except ValueError:
            continue

    return TimeSeries.from_pairs(
        series_id, pairs, label=series_id, source=attribution(series_id),
    )


def fetch_many(ids: list[str], **kw) -> dict[str, TimeSeries]:
    """Fetch several series, skipping any that fail rather than aborting."""
    out: dict[str, TimeSeries] = {}
    for sid in ids:
        try:
            out[sid] = fetch(sid, **kw)
        except HttpError:
            continue
    return out
