"""BLS public API (v2 with a registration key, v1 without).

Used for CPI, payrolls and earnings so the page cites BLS directly rather than
a redistributor.  Set BLS_API_KEY for the higher v2 limits.
"""

from __future__ import annotations

import json
import os
from datetime import date

from .http import HttpError, get

V1 = "https://api.bls.gov/publicAPI/v1/timeseries/data/"
V2 = "https://api.bls.gov/publicAPI/v2/timeseries/data/"

MONTH = {f"M{i:02d}": i for i in range(1, 13)}


def fetch(series_ids: list[str], start_year: int, end_year: int,
          **kw) -> dict[str, list[dict]]:
    """Return {series_id: [{'date':, 'value':, 'period':}, ...]} ascending."""
    key = os.getenv("BLS_API_KEY")
    payload = {
        "seriesid": series_ids,
        "startyear": str(start_year),
        "endyear": str(end_year),
    }
    if key:
        payload["registrationkey"] = key
        payload["calculations"] = True

    raw = get(
        V2 if key else V1,
        body=json.dumps(payload).encode(),
        headers={"Content-Type": "application/json"},
        **kw,
    )
    try:
        data = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise HttpError(f"BLS: invalid JSON ({exc})") from exc

    if data.get("status") != "REQUEST_SUCCEEDED":
        raise HttpError(f"BLS: {data.get('status')} {data.get('message')}")

    out: dict[str, list[dict]] = {}
    for series in data.get("Results", {}).get("series", []):
        sid = series.get("seriesID", "")
        rows = []
        for item in series.get("data", []):
            period = item.get("period", "")
            if period not in MONTH:
                continue          # skip annual averages
            try:
                d = date(int(item["year"]), MONTH[period], 1)
                v = float(item["value"])
            except (ValueError, KeyError):
                continue
            rows.append({"date": d, "value": v, "period": period,
                         "footnotes": item.get("footnotes", [])})
        rows.sort(key=lambda r: r["date"])
        out[sid] = rows
    return out


def yoy(rows: list[dict]) -> float | None:
    """Year-over-year percent change from a monthly index series."""
    if len(rows) < 13:
        return None
    now, then = rows[-1]["value"], rows[-13]["value"]
    return None if then == 0 else (now / then - 1.0) * 100.0


def mom(rows: list[dict]) -> float | None:
    if len(rows) < 2:
        return None
    now, then = rows[-1]["value"], rows[-2]["value"]
    return None if then == 0 else (now / then - 1.0) * 100.0
