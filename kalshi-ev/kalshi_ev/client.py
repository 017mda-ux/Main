"""Minimal client for Kalshi's public (unauthenticated) trade API v2.

Market data — markets, events, series, orderbooks, trades, candlesticks —
requires no API key. Order placement is intentionally not implemented:
this toolkit finds and sizes edges; execute manually (or wire in the
authenticated API yourself once you trust the numbers on paper).

Docs: https://docs.kalshi.com/  (base https://api.elections.kalshi.com/trade-api/v2)
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any, Dict, Iterator, List, Optional, Tuple

import requests

PROD_BASE = "https://api.elections.kalshi.com/trade-api/v2"
DEMO_BASE = "https://demo-api.kalshi.co/trade-api/v2"


class KalshiPublicClient:
    def __init__(self, base_url: str = PROD_BASE, timeout: float = 15.0,
                 max_retries: int = 4, throttle_s: float = 0.15):
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.max_retries = max_retries
        self.throttle_s = throttle_s
        self.session = requests.Session()
        self.session.headers["User-Agent"] = "kalshi-ev/0.1 (research)"

    # ── low level ────────────────────────────────────────────────────

    def _get(self, path: str, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        url = f"{self.base_url}{path}"
        delay = 1.0
        for attempt in range(self.max_retries + 1):
            resp = self.session.get(url, params=params, timeout=self.timeout)
            if resp.status_code in (429, 500, 502, 503, 504) and attempt < self.max_retries:
                time.sleep(delay)
                delay *= 2
                continue
            resp.raise_for_status()
            return resp.json()
        raise RuntimeError("unreachable")

    def _paged(self, path: str, key: str, params: Optional[Dict[str, Any]] = None,
               limit_total: Optional[int] = None) -> Iterator[Dict[str, Any]]:
        params = dict(params or {})
        params.setdefault("limit", 200)
        seen = 0
        while True:
            data = self._get(path, params)
            items = data.get(key) or []
            for item in items:
                yield item
                seen += 1
                if limit_total is not None and seen >= limit_total:
                    return
            cursor = data.get("cursor")
            if not cursor or not items:
                return
            params["cursor"] = cursor
            time.sleep(self.throttle_s)

    # ── endpoints ────────────────────────────────────────────────────

    def exchange_status(self) -> Dict[str, Any]:
        return self._get("/exchange/status")

    def get_market(self, ticker: str) -> Dict[str, Any]:
        return self._get(f"/markets/{ticker}")["market"]

    def get_markets(self, status: Optional[str] = None, series_ticker: Optional[str] = None,
                    event_ticker: Optional[str] = None,
                    limit_total: Optional[int] = None,
                    min_close_ts: Optional[int] = None,
                    max_close_ts: Optional[int] = None) -> Iterator[Dict[str, Any]]:
        params: Dict[str, Any] = {}
        if status:
            params["status"] = status
        if series_ticker:
            params["series_ticker"] = series_ticker
        if event_ticker:
            params["event_ticker"] = event_ticker
        if min_close_ts:
            params["min_close_ts"] = min_close_ts
        if max_close_ts:
            params["max_close_ts"] = max_close_ts
        return self._paged("/markets", "markets", params, limit_total)

    def get_event(self, event_ticker: str, with_nested_markets: bool = True) -> Dict[str, Any]:
        data = self._get(f"/events/{event_ticker}",
                         {"with_nested_markets": str(with_nested_markets).lower()})
        return data["event"]

    def get_events(self, status: Optional[str] = None, series_ticker: Optional[str] = None,
                   limit_total: Optional[int] = None,
                   with_nested_markets: bool = True) -> Iterator[Dict[str, Any]]:
        params: Dict[str, Any] = {"with_nested_markets": str(with_nested_markets).lower()}
        if status:
            params["status"] = status
        if series_ticker:
            params["series_ticker"] = series_ticker
        return self._paged("/events", "events", params, limit_total)

    def get_orderbook(self, ticker: str, depth: int = 8) -> "Orderbook":
        data = self._get(f"/markets/{ticker}/orderbook", {"depth": depth})
        return Orderbook.from_api(ticker, data.get("orderbook") or {})

    def get_candlesticks(self, series_ticker: str, market_ticker: str,
                         start_ts: int, end_ts: int,
                         period_interval_minutes: int = 60) -> List[Dict[str, Any]]:
        data = self._get(
            f"/series/{series_ticker}/markets/{market_ticker}/candlesticks",
            {"start_ts": start_ts, "end_ts": end_ts,
             "period_interval": period_interval_minutes},
        )
        return data.get("candlesticks") or []


# ── orderbook view ───────────────────────────────────────────────────
#
# The API returns resting *bids* on each side:
#   {"yes": [[price, qty], ...], "no": [[price, qty], ...]}
# A YES ask does not exist as such — buying YES at x means someone was
# bidding NO at 100 - x. So: best_yes_ask = 100 - best_no_bid.


@dataclass
class Orderbook:
    ticker: str
    yes_bids: List[Tuple[int, int]] = field(default_factory=list)  # (price, qty), best first
    no_bids: List[Tuple[int, int]] = field(default_factory=list)

    @classmethod
    def from_api(cls, ticker: str, raw: Dict[str, Any]) -> "Orderbook":
        def norm(levels) -> List[Tuple[int, int]]:
            out = [(int(p), int(q)) for p, q in (levels or [])]
            return sorted(out, key=lambda t: -t[0])  # highest bid first
        return cls(ticker, norm(raw.get("yes")), norm(raw.get("no")))

    @property
    def best_yes_bid(self) -> Optional[int]:
        return self.yes_bids[0][0] if self.yes_bids else None

    @property
    def best_no_bid(self) -> Optional[int]:
        return self.no_bids[0][0] if self.no_bids else None

    @property
    def best_yes_ask(self) -> Optional[int]:
        return 100 - self.no_bids[0][0] if self.no_bids else None

    @property
    def best_no_ask(self) -> Optional[int]:
        return 100 - self.yes_bids[0][0] if self.yes_bids else None

    @property
    def yes_ask_qty(self) -> int:
        return self.no_bids[0][1] if self.no_bids else 0

    @property
    def no_ask_qty(self) -> int:
        return self.yes_bids[0][1] if self.yes_bids else 0

    @property
    def mid_cents(self) -> Optional[float]:
        bid, ask = self.best_yes_bid, self.best_yes_ask
        if bid is None and ask is None:
            return None
        if bid is None:
            return float(ask)
        if ask is None:
            return float(bid)
        return (bid + ask) / 2.0

    @property
    def spread_cents(self) -> Optional[int]:
        if self.best_yes_bid is None or self.best_yes_ask is None:
            return None
        return self.best_yes_ask - self.best_yes_bid
