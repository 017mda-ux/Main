"""NWS-forecast-based probabilities for Kalshi daily high-temperature markets.

Why weather: Kalshi's temperature markets settle on objective, well-
forecast quantities (the official NWS climate report high at a specific
station). The National Weather Service publishes point forecasts free of
charge, and decades of verification data pin down forecast error
distributions tightly. Retail flow on these markets is largely vibes; a
disciplined Normal(forecast, sigma_by_lead_time) model priced against
the orderbook is one of the few places a small trader can plausibly be
the informed side.

Model: actual_high ~ Normal(nws_forecast + bias, sigma(lead_days)),
with bucket probabilities from the Normal CDF with a +-0.5 degF
continuity correction (settlement temps are integers).

The default sigmas below are seeded from published NWS MOS/NBM
verification (MAE ~= 2-3 degF at 1-3 days out; sigma ~= MAE * 1.25 for a
Normal). They are starting points, not gospel: re-estimate them per
station from your own collected forecast-vs-settlement history, and
raise them if in doubt — overstated confidence is the failure mode that
loses money.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from datetime import date, datetime
from typing import Any, Dict, List, Optional

import requests

# sigma of (actual - forecast) in degF, keyed by forecast lead in days
DEFAULT_SIGMA_BY_LEAD = {0: 2.0, 1: 2.6, 2: 3.3, 3: 4.0, 4: 4.7, 5: 5.4, 6: 6.0, 7: 6.5}
DEFAULT_BIAS_DEGF = 0.0

# Kalshi daily-high series -> approximate station coordinates
STATIONS: Dict[str, Dict[str, Any]] = {
    "KXHIGHNY":   {"name": "NYC (Central Park)",      "lat": 40.7789, "lon": -73.9692},
    "KXHIGHCHI":  {"name": "Chicago (Midway)",        "lat": 41.7842, "lon": -87.7553},
    "KXHIGHMIA":  {"name": "Miami (Intl Airport)",    "lat": 25.7906, "lon": -80.3164},
    "KXHIGHAUS":  {"name": "Austin (Camp Mabry)",     "lat": 30.3208, "lon": -97.7604},
    "KXHIGHDEN":  {"name": "Denver (Intl Airport)",   "lat": 39.8467, "lon": -104.6564},
    "KXHIGHPHIL": {"name": "Philadelphia (Intl)",     "lat": 39.8683, "lon": -75.2311},
    "KXHIGHLAX":  {"name": "Los Angeles (LAX)",       "lat": 33.9382, "lon": -118.3866},
}


def _phi(z: float) -> float:
    """Standard normal CDF."""
    return 0.5 * (1.0 + math.erf(z / math.sqrt(2.0)))


def _is_integerish(x: float) -> bool:
    return abs(x - round(x)) < 1e-9


def bucket_probability(mu: float, sigma: float, strike_type: str,
                       floor_strike: Optional[float] = None,
                       cap_strike: Optional[float] = None) -> float:
    """P(market settles YES) for a temperature bucket under
    high ~ Normal(mu, sigma), with continuity correction for integer strikes.

    Kalshi semantics: "between" is floor <= T <= cap (inclusive);
    "greater" is T > floor (strict); "less" is T < cap (strict).
    """
    if sigma <= 0:
        raise ValueError("sigma must be positive")

    def cdf(x: float) -> float:
        return _phi((x - mu) / sigma)

    if strike_type == "between":
        if floor_strike is None or cap_strike is None:
            raise ValueError("between requires floor and cap")
        lo = floor_strike - 0.5 if _is_integerish(floor_strike) else floor_strike
        hi = cap_strike + 0.5 if _is_integerish(cap_strike) else cap_strike
        return max(0.0, cdf(hi) - cdf(lo))
    if strike_type == "greater":
        if floor_strike is None:
            raise ValueError("greater requires floor")
        # strict: integer floor F means T >= F + 1
        lo = floor_strike + 0.5 if _is_integerish(floor_strike) else floor_strike
        return 1.0 - cdf(lo)
    if strike_type == "less":
        if cap_strike is None:
            raise ValueError("less requires cap")
        hi = cap_strike - 0.5 if _is_integerish(cap_strike) else cap_strike
        return cdf(hi)
    raise ValueError(f"unknown strike_type: {strike_type}")


def market_yes_probability(market: Dict[str, Any], mu: float, sigma: float) -> float:
    """Bucket probability from a Kalshi market dict (uses strike fields)."""
    return bucket_probability(
        mu, sigma,
        strike_type=market.get("strike_type", "between"),
        floor_strike=market.get("floor_strike"),
        cap_strike=market.get("cap_strike"),
    )


# ── NWS client ───────────────────────────────────────────────────────


@dataclass
class Forecast:
    target_date: date
    high_degf: float
    lead_days: int


class NWSClient:
    """Thin client for api.weather.gov (free, no key; requires a UA header)."""

    def __init__(self, timeout: float = 15.0):
        self.session = requests.Session()
        self.session.headers["User-Agent"] = "kalshi-ev/0.1 (research; contact via repo)"
        self.timeout = timeout

    def _get(self, url: str) -> Dict[str, Any]:
        resp = self.session.get(url, timeout=self.timeout)
        resp.raise_for_status()
        return resp.json()

    def daily_highs(self, lat: float, lon: float) -> List[Forecast]:
        """Forecast daytime highs for the next ~7 days at a point."""
        point = self._get(f"https://api.weather.gov/points/{lat:.4f},{lon:.4f}")
        forecast_url = point["properties"]["forecast"]
        periods = self._get(forecast_url)["properties"]["periods"]
        today = datetime.now().astimezone().date()
        out: List[Forecast] = []
        for period in periods:
            if not period.get("isDaytime"):
                continue
            when = datetime.fromisoformat(period["startTime"]).date()
            out.append(Forecast(
                target_date=when,
                high_degf=float(period["temperature"]),
                lead_days=max(0, (when - today).days),
            ))
        return out

    def high_for_date(self, lat: float, lon: float, target: date) -> Optional[Forecast]:
        for fc in self.daily_highs(lat, lon):
            if fc.target_date == target:
                return fc
        return None


def sigma_for_lead(lead_days: int,
                   table: Dict[int, float] = DEFAULT_SIGMA_BY_LEAD) -> float:
    if lead_days in table:
        return table[lead_days]
    return table[max(table)]
