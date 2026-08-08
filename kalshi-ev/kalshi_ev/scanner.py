"""Live opportunity scanners: structural arbs, calibration edges, weather EV.

Each scanner returns plain dataclasses; the CLI renders them. Nothing
here places orders.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from typing import Dict, List, Optional

from .arbitrage import ArbOpportunity, scan_event
from .calibration import CalibrationModel
from .client import KalshiPublicClient, Orderbook
from .ev import TradeDecision, evaluate_market
from .fees import STANDARD_RATE
from .weather import (NWSClient, STATIONS, market_yes_probability,
                      sigma_for_lead)


@dataclass
class EdgeOpportunity:
    ticker: str
    title: str
    source: str            # "calibration" | "weather"
    decision: TradeDecision
    liquidity: int         # contracts available at the ask
    note: str = ""


def _books_for_event(client: KalshiPublicClient, event: dict) -> Dict[str, Orderbook]:
    books: Dict[str, Orderbook] = {}
    for market in event.get("markets") or []:
        ticker = market.get("ticker")
        if not ticker or market.get("status") not in (None, "active", "open"):
            continue
        try:
            books[ticker] = client.get_orderbook(ticker)
        except Exception:
            continue
    return books


def scan_arbitrage(client: KalshiPublicClient, series_tickers: Optional[List[str]] = None,
                   max_events: int = 50, min_profit_cents: float = 1.0,
                   rate: float = STANDARD_RATE) -> List[ArbOpportunity]:
    """Scan open events (optionally restricted to series) for structural arbs."""
    out: List[ArbOpportunity] = []
    series_list = series_tickers or [None]
    for series in series_list:
        for event in client.get_events(status="open", series_ticker=series,
                                       limit_total=max_events):
            books = _books_for_event(client, event)
            if not books:
                continue
            out.extend(scan_event(event, books, rate=rate,
                                  min_profit_cents=min_profit_cents))
    out.sort(key=lambda o: -o.profit_cents * max(o.max_units, 0))
    return out


def scan_calibration_edges(client: KalshiPublicClient, model: CalibrationModel,
                           series_tickers: Optional[List[str]] = None,
                           max_events: int = 50, min_ev_cents: float = 3.0,
                           min_liquidity: int = 10,
                           rate: float = STANDARD_RATE) -> List[EdgeOpportunity]:
    """Reprice open markets through the fitted calibration curve and flag
    asks that are cheap relative to the calibrated probability.

    Only meaningful if the model was fitted on comparable markets at a
    comparable horizon — a curve fitted on daily weather markets says
    nothing about elections."""
    out: List[EdgeOpportunity] = []
    series_list = series_tickers or [None]
    for series in series_list:
        for event in client.get_events(status="open", series_ticker=series,
                                       limit_total=max_events):
            for market in event.get("markets") or []:
                ticker = market.get("ticker")
                if not ticker:
                    continue
                try:
                    book = client.get_orderbook(ticker)
                except Exception:
                    continue
                mid = book.mid_cents
                if mid is None or not (1 <= mid <= 99):
                    continue
                q = model.predict(mid)
                decision = evaluate_market(q, book.best_yes_ask, book.best_no_ask,
                                           rate=rate, min_ev_cents=min_ev_cents)
                if decision is None:
                    continue
                liquidity = (book.yes_ask_qty if decision.side == "yes"
                             else book.no_ask_qty)
                if liquidity < min_liquidity:
                    continue
                out.append(EdgeOpportunity(
                    ticker=ticker, title=market.get("title", ""),
                    source="calibration", decision=decision, liquidity=liquidity,
                    note=f"mid={mid:.0f}c -> q={q:.3f}",
                ))
    out.sort(key=lambda o: -o.decision.ev_cents)
    return out


def scan_weather(client: KalshiPublicClient, nws: NWSClient,
                 series_tickers: Optional[List[str]] = None,
                 min_ev_cents: float = 3.0, min_liquidity: int = 5,
                 bias_degf: float = 0.0,
                 rate: float = STANDARD_RATE) -> List[EdgeOpportunity]:
    """Price open daily-high markets from the NWS point forecast and flag
    asks that are cheap relative to the Normal(forecast, sigma) model."""
    out: List[EdgeOpportunity] = []
    for series, station in STATIONS.items():
        if series_tickers and series not in series_tickers:
            continue
        try:
            forecasts = {f.target_date: f for f in
                         nws.daily_highs(station["lat"], station["lon"])}
        except Exception as exc:
            print(f"  ! NWS fetch failed for {series} ({station['name']}): {exc}")
            continue

        for event in client.get_events(status="open", series_ticker=series,
                                       limit_total=10):
            target = _event_target_date(event)
            fc = forecasts.get(target) if target else None
            if fc is None:
                continue
            mu = fc.high_degf + bias_degf
            sigma = sigma_for_lead(fc.lead_days)
            for market in event.get("markets") or []:
                ticker = market.get("ticker")
                if not ticker:
                    continue
                try:
                    q = market_yes_probability(market, mu, sigma)
                except (ValueError, TypeError):
                    continue
                try:
                    book = client.get_orderbook(ticker)
                except Exception:
                    continue
                decision = evaluate_market(q, book.best_yes_ask, book.best_no_ask,
                                           rate=rate, min_ev_cents=min_ev_cents)
                if decision is None:
                    continue
                liquidity = (book.yes_ask_qty if decision.side == "yes"
                             else book.no_ask_qty)
                if liquidity < min_liquidity:
                    continue
                out.append(EdgeOpportunity(
                    ticker=ticker, title=market.get("title") or market.get("subtitle", ""),
                    source="weather", decision=decision, liquidity=liquidity,
                    note=(f"{station['name']}: forecast {fc.high_degf:.0f}F "
                          f"(lead {fc.lead_days}d, sigma {sigma:.1f}) -> q={q:.3f}"),
                ))
    out.sort(key=lambda o: -o.decision.ev_cents)
    return out


def _event_target_date(event: dict) -> Optional[date]:
    """Kalshi daily event tickers end in -YYMMMDD (e.g. KXHIGHNY-25AUG08)."""
    ticker = event.get("event_ticker", "")
    tail = ticker.rsplit("-", 1)[-1]
    try:
        return datetime.strptime(tail, "%y%b%d").date()
    except ValueError:
        pass
    # fall back to the earliest market close date
    for market in event.get("markets") or []:
        raw = market.get("close_time")
        if raw:
            try:
                return datetime.fromisoformat(str(raw).replace("Z", "+00:00")).date()
            except ValueError:
                continue
    return None
