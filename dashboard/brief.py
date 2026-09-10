"""Assemble a ranked brief from the collectors.

`build()` runs the full live pipeline and emits the same snapshot structure
that `render.py` consumes, so a rendered page is always reproducible from the
JSON that produced it.
"""

from __future__ import annotations

import json
from dataclasses import asdict, is_dataclass
from datetime import date, datetime
from pathlib import Path

from .analytics.movingavg import ma_state
from .analytics.ratios import build_ratio, divergence_score
from .analytics.salience import rank, score_event, score_ratio, score_series
from .analytics.series import TimeSeries
from .config import (
    MA_WATCH, RATIOS, SALIENCE, SERIES, SERIES_BY_KEY,
)
from .sources import feeds, fred, stooq, treasury_fiscal, treasury_rates
from .sources.http import HttpError

STATE_PATH = Path("./data/dashboard_state.json")


# ──────────────────────────────────────────────────────────────────────
#  Collection
# ──────────────────────────────────────────────────────────────────────

def collect_series(verbose: bool = False) -> tuple[dict[str, TimeSeries], list[str]]:
    """Fetch every configured series; return what succeeded plus failures."""
    store: dict[str, TimeSeries] = {}
    failed: list[str] = []

    for spec in SERIES:
        try:
            if spec.source == "fred":
                ts = fred.fetch(spec.source_id)
            elif spec.source == "stooq":
                ts = stooq.fetch(spec.source_id)
            else:
                continue
            ts.key = spec.key
            ts.label = spec.label
            ts.unit = spec.unit
            store[spec.key] = ts
            if verbose:
                print(f"  ok   {spec.key:<12} {len(ts):>5} obs  "
                      f"last {ts.last_date}")
        except HttpError as exc:
            failed.append(f"{spec.key}: {exc}")
            if verbose:
                print(f"  FAIL {spec.key:<12} {exc}")

    return store, failed


def collect_ratios(store: dict[str, TimeSeries]) -> dict[str, TimeSeries]:
    out: dict[str, TimeSeries] = {}
    for spec in RATIOS:
        ts = build_ratio(spec, store)
        if ts is not None:
            out[spec.key] = ts
    return out


# ──────────────────────────────────────────────────────────────────────
#  Scoring
# ──────────────────────────────────────────────────────────────────────

def build_signals(
    store: dict[str, TimeSeries],
    ratios: dict[str, TimeSeries],
    events: list[dict],
    today: date,
):
    """Score every candidate module."""
    signals = []

    crosses = {
        key: ma_state(ts)
        for key, ts in {**store, **ratios}.items()
        if key in MA_WATCH
    }

    for spec in SERIES:
        ts = store.get(spec.key)
        if ts:
            signals.append(score_series(spec, ts, crosses.get(spec.key)))

    for spec in RATIOS:
        ts = ratios.get(spec.key)
        if not ts:
            continue
        div, div_score = None, 0.0
        if spec.versus and spec.versus in store:
            div_score, div = divergence_score(ts, store[spec.versus])
        signals.append(score_ratio(
            spec.key, spec.label, ts, div, div_score, crosses.get(spec.key),
        ))

    for ev in events:
        when = ev["date"]
        if isinstance(when, str):
            when = datetime.strptime(when, "%Y-%m-%d").date()
        signals.append(score_event(
            ev["key"], ev["label"], when, today,
            ev.get("weight", 1.0), ev.get("note", ""),
        ))

    return signals


# ──────────────────────────────────────────────────────────────────────
#  Run history (so the page rotates)
# ──────────────────────────────────────────────────────────────────────

def load_state() -> dict:
    if STATE_PATH.exists():
        try:
            return json.loads(STATE_PATH.read_text())
        except json.JSONDecodeError:
            pass
    return {"runs": []}


def save_state(state: dict, leaders: list[str]) -> None:
    state.setdefault("runs", []).insert(
        0, {"at": datetime.now().isoformat(timespec="seconds"), "leaders": leaders}
    )
    state["runs"] = state["runs"][:10]
    STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
    STATE_PATH.write_text(json.dumps(state, indent=2))


# ──────────────────────────────────────────────────────────────────────
#  Entry point
# ──────────────────────────────────────────────────────────────────────

def build(events: list[dict] | None = None, verbose: bool = True) -> dict:
    """Run the whole pipeline and return a snapshot dict."""
    today = date.today()
    if verbose:
        print("Collecting series…")
    store, failed = collect_series(verbose)
    ratios = collect_ratios(store)

    if verbose:
        print(f"Collected {len(store)} series, {len(ratios)} ratios, "
              f"{len(failed)} failures")

    signals = build_signals(store, ratios, events or [], today)

    state = load_state()
    previous = [r.get("leaders", []) for r in state.get("runs", [])]
    ranked = rank(signals, previous)

    if verbose:
        print(f"\n{len(ranked)} of {len(signals)} modules cleared the floor:")
        for s in ranked:
            print(f"  {s.score:5.1f}  {s.label:<28} {s.top_reason}")

    save_state(state, [s.key for s in ranked[:5]])

    snapshot = {
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "as_of": today.isoformat(),
        "failures": failed,
        "modules": [_signal_json(s) for s in ranked],
        "curve": _curve_json(),
        "fiscal": _fiscal_json(),
        "feed": _feed_json(),
    }
    return snapshot


def _signal_json(sig) -> dict:
    ts: TimeSeries | None = sig.payload.get("series")
    cross = sig.payload.get("cross")
    out = {
        "key": sig.key,
        "label": sig.label,
        "bucket": sig.bucket,
        "score": round(sig.score, 1),
        "components": {k: round(v, 1) for k, v in sig.components.items()},
        "reasons": sig.reasons,
    }
    if ts:
        spec = SERIES_BY_KEY.get(sig.key)
        out["last"] = ts.last
        out["last_date"] = ts.last_date.isoformat() if ts.last_date else None
        out["change_1d"] = ts.change(1)
        out["change_5d"] = ts.change(5)
        out["pct_change_1d"] = ts.pct_change(1)
        out["percentile"] = ts.percentile(spec.window if spec else 504)
        out["source"] = ts.source
        out["unit"] = ts.unit
        # A year of daily observations is enough for a sparkline.
        tail = ts.tail(252)
        out["spark"] = [round(v, 6) for v in tail.values]
        out["spark_dates"] = [d.isoformat() for d in tail.dates]
    if cross is not None:
        out["cross"] = asdict(cross) if is_dataclass(cross) else None
        if out["cross"]:
            for k in ("crossed_on",):
                v = out["cross"].get(k)
                out["cross"][k] = v.isoformat() if isinstance(v, date) else v
    return out


def _curve_json() -> dict:
    try:
        rows = treasury_rates.fetch_curve()
        if not rows:
            return {}
        return {
            "latest": {k: (v.isoformat() if isinstance(v, date) else v)
                       for k, v in rows[-1].items()},
            "change_1d": treasury_rates.curve_change(rows, 1),
            "change_5d": treasury_rates.curve_change(rows, 5),
            "change_21d": treasury_rates.curve_change(rows, 21),
            "source": "U.S. Treasury, Daily Par Yield Curve",
        }
    except HttpError:
        return {}


def _fiscal_json() -> dict:
    out: dict = {}
    for name, fn in (
        ("cash_balance", treasury_fiscal.operating_cash_balance),
        ("deficit", treasury_fiscal.monthly_deficit),
        ("auctions", treasury_fiscal.auction_results),
        ("interest", treasury_fiscal.interest_expense),
    ):
        try:
            rows = fn()
            out[name] = [
                {k: (v.isoformat() if isinstance(v, date) else v)
                 for k, v in r.items()}
                for r in rows[:24]
            ]
        except HttpError:
            out[name] = []
    return out


def _feed_json() -> dict:
    try:
        items = feeds.collect()
    except HttpError:
        return {"items": []}
    return {
        "items": [
            {
                "title": i.title,
                "link": i.link,
                "published": i.published.isoformat() if i.published else None,
                "source": i.source,
                "speakers": i.speakers,
                "tags": i.tags,
                "score": i.score,
                "summary": i.summary[:280],
            }
            for i in items[:40]
        ]
    }
