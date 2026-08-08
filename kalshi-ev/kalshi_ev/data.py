"""Historical snapshot collection for calibration and backtesting.

The trap to avoid: a settled market's ``last_price`` is ~0 or ~100 by
construction (the market converged as the outcome became known), so
fitting calibration on it "proves" the market is perfectly calibrated.
Useless. What we want is the price *while the outcome was still
uncertain*.

So for each settled market we pull hourly candlesticks and record the
price ``horizon_hours`` before close. Each snapshot is one JSONL row:

    {"ticker", "event_ticker", "series_ticker", "price_cents",
     "outcome" (1 yes / 0 no), "close_ts", "horizon_hours"}

Collect once (network), then calibrate/backtest offline as often as you
like.
"""

from __future__ import annotations

import json
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Dict, Iterator, List, Optional

from .client import KalshiPublicClient


@dataclass
class Snapshot:
    ticker: str
    event_ticker: str
    series_ticker: str
    price_cents: float
    outcome: int
    close_ts: int
    horizon_hours: int


def _parse_close_ts(market: Dict[str, Any]) -> Optional[int]:
    raw = market.get("close_time")
    if raw is None:
        return None
    if isinstance(raw, (int, float)):
        return int(raw)
    from datetime import datetime
    try:
        return int(datetime.fromisoformat(str(raw).replace("Z", "+00:00")).timestamp())
    except ValueError:
        return None


def _candle_price_cents(candle: Dict[str, Any]) -> Optional[float]:
    """Best available close price from a candlestick: bid/ask midpoint if
    both sides quoted, else the last-trade close."""
    yes_bid = (candle.get("yes_bid") or {}).get("close")
    yes_ask = (candle.get("yes_ask") or {}).get("close")
    if yes_bid and yes_ask and 0 < yes_bid < 100 and 0 < yes_ask < 100:
        return (yes_bid + yes_ask) / 2.0
    price = (candle.get("price") or {}).get("close")
    if price and 0 < price < 100:
        return float(price)
    return None


def collect_snapshots(client: KalshiPublicClient, series_tickers: List[str],
                      horizon_hours: int = 24, max_markets_per_series: int = 400,
                      out_path: str | Path = "data/snapshots.jsonl",
                      verbose: bool = True) -> int:
    """Snapshot settled markets of the given series at ``horizon_hours``
    before close. Appends to ``out_path``, skipping tickers already there.
    Returns the number of new snapshots written."""
    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    seen = {s.ticker for s in load_snapshots(out_path)} if out_path.exists() else set()

    written = 0
    with out_path.open("a") as fh:
        for series in series_tickers:
            for market in client.get_markets(status="settled", series_ticker=series,
                                             limit_total=max_markets_per_series):
                ticker = market.get("ticker")
                result = market.get("result")
                close_ts = _parse_close_ts(market)
                if not ticker or ticker in seen or result not in ("yes", "no") or not close_ts:
                    continue

                target_ts = close_ts - horizon_hours * 3600
                candles = client.get_candlesticks(
                    series, ticker,
                    start_ts=target_ts - 6 * 3600, end_ts=target_ts + 3600,
                    period_interval_minutes=60,
                )
                price = None
                for candle in reversed(candles):  # latest candle at/before target
                    if candle.get("end_period_ts", 0) <= target_ts + 3600:
                        price = _candle_price_cents(candle)
                        if price is not None:
                            break
                if price is None:
                    continue

                snap = Snapshot(
                    ticker=ticker,
                    event_ticker=market.get("event_ticker", ""),
                    series_ticker=series,
                    price_cents=price,
                    outcome=1 if result == "yes" else 0,
                    close_ts=close_ts,
                    horizon_hours=horizon_hours,
                )
                fh.write(json.dumps(asdict(snap)) + "\n")
                seen.add(ticker)
                written += 1
                if verbose and written % 25 == 0:
                    print(f"  {written} snapshots... (last: {ticker} @ {price:.0f}c -> {result})")
                time.sleep(client.throttle_s)
    return written


def load_snapshots(path: str | Path) -> List[Snapshot]:
    out: List[Snapshot] = []
    p = Path(path)
    if not p.exists():
        return out
    for line in p.read_text().splitlines():
        line = line.strip()
        if not line:
            continue
        d = json.loads(line)
        out.append(Snapshot(**d))
    return out
