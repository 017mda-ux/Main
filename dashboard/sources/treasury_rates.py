"""Treasury daily par yield curve, read straight from home.treasury.gov.

FRED carries the same numbers with a lag; this is the primary publication and
is what the page cites for curve levels.
"""

from __future__ import annotations

import re
from datetime import date, datetime
from xml.etree import ElementTree as ET

from .http import HttpError, get

XML = ("https://home.treasury.gov/resource-center/data-chart-center/"
       "interest-rates/pages/xml?data=daily_treasury_yield_curve"
       "&field_tdr_date_value={year}")

NS = {
    "a": "http://www.w3.org/2005/Atom",
    "m": "http://schemas.microsoft.com/ado/2007/08/dataservices/metadata",
    "d": "http://schemas.microsoft.com/ado/2007/08/dataservices",
}

TENORS = {
    "BC_1MONTH": "1m", "BC_2MONTH": "2m", "BC_3MONTH": "3m",
    "BC_4MONTH": "4m", "BC_6MONTH": "6m", "BC_1YEAR": "1y",
    "BC_2YEAR": "2y", "BC_3YEAR": "3y", "BC_5YEAR": "5y",
    "BC_7YEAR": "7y", "BC_10YEAR": "10y", "BC_20YEAR": "20y",
    "BC_30YEAR": "30y",
}

ORDER = ["1m", "2m", "3m", "4m", "6m", "1y", "2y", "3y", "5y", "7y",
         "10y", "20y", "30y"]


def fetch_curve(year: int | None = None, **kw) -> list[dict]:
    """Return [{'date': date, '1m': float, ...}] for the requested year."""
    year = year or date.today().year
    raw = get(XML.format(year=year), **kw)

    try:
        root = ET.fromstring(raw)
    except ET.ParseError as exc:
        raise HttpError(f"Treasury curve {year}: {exc}") from exc

    rows: list[dict] = []
    for entry in root.findall(".//a:entry", NS):
        props = entry.find(".//m:properties", NS)
        if props is None:
            continue
        row: dict = {}
        for el in props:
            tag = re.sub(r"^\{.*\}", "", el.tag)
            if tag == "NEW_DATE" and el.text:
                try:
                    row["date"] = datetime.strptime(
                        el.text[:10], "%Y-%m-%d").date()
                except ValueError:
                    pass
            elif tag in TENORS and el.text:
                try:
                    row[TENORS[tag]] = float(el.text)
                except ValueError:
                    pass
        if "date" in row:
            rows.append(row)

    rows.sort(key=lambda r: r["date"])
    return rows


def latest_curve(**kw) -> dict | None:
    """Most recent published curve, falling back to last year in early January."""
    rows = fetch_curve(**kw)
    if not rows:
        rows = fetch_curve(year=date.today().year - 1, **kw)
    return rows[-1] if rows else None


def curve_change(rows: list[dict], back: int = 1) -> dict[str, float]:
    """Change in basis points per tenor over `back` publication days."""
    if len(rows) <= back:
        return {}
    now, then = rows[-1], rows[-1 - back]
    out: dict[str, float] = {}
    for t in ORDER:
        if t in now and t in then:
            out[t] = (now[t] - then[t]) * 100.0
    return out
