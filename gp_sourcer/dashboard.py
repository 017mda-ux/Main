"""
Dashboard — renders the full LP sourcing view as terminal/markdown output.

Run:  python -m gp_sourcer.dashboard
"""

from __future__ import annotations

from .deal_feed import build_deal_feed
from .fundraise_cycle import forecast_market
from .lp_watch import WATCHED_LPS, get_lp_signals
from .pipeline import get_pipeline
from .placement_agents import get_offerings
from .talent_signals import get_talent_signals

_FIT_BADGE = {
    "in_mandate": "IN MANDATE",
    "size_unknown": "SIZE TBC",
    "near_mandate": "NEAR MANDATE",
    "outside_mandate": "OUTSIDE",
}


def _fmt_usd(n: int | None) -> str:
    if n is None:
        return "Undisclosed"
    if n >= 1_000_000_000:
        return f"${n / 1e9:.1f}B"
    return f"${n / 1e6:.0f}M"


def render_deal_feed(strategy: str | None = None, emerging_only: bool = False,
                     include_outside_mandate: bool = False) -> str:
    feed = build_deal_feed(strategy=strategy, emerging_only=emerging_only,
                           include_outside_mandate=include_outside_mandate)
    s = feed["summary"]
    lines = [
        "=" * 78,
        "  DEAL FLOW FEED" + (f"  ·  strategy={strategy}" if strategy else "")
        + ("  ·  EMERGING ONLY" if emerging_only else ""),
        f"  {s['total']} funds  ·  {s['emerging']} emerging (Fund I-III)  ·  "
        f"{s['in_mandate_or_pending']} in-mandate/pending  ·  source: {feed['data_source']}",
        "=" * 78,
    ]
    for c in feed["cards"]:
        em = "  *EMERGING*" if c["emerging"] else ""
        fn = f"Fund {c['fund_number']}" if c["fund_number"] else "Fund # unknown"
        lines += [
            "",
            f"  {c['fund_name']}",
            f"  {c['gp_name']}  ·  [{_FIT_BADGE[c['fit']]}]  ·  "
            f"{(c['band_label'] or c['strategy'].title())}  ·  {fn}{em}",
            f"  {c['description']}",
            f"  Size: {_fmt_usd(c.get('size_usd'))}  ·  Filed: {c.get('file_date', '?')}  ·  {c['source']}",
        ]
        for fl in c["flags"]:
            lines.append(f"    - {fl}")
    return "\n".join(lines)


def render_lp_watch() -> str:
    lines = ["=" * 78, "  LP WATCH — reference LP activity", "=" * 78]
    for lp_id, lp in WATCHED_LPS.items():
        sigs = get_lp_signals(lp_id, limit=3)
        lines += ["", f"  {lp['name']}  (${lp['aum_bn']}B {lp['type'].replace('_', ' ')})"]
        if sigs:
            for s in sigs:
                amt = f" — {_fmt_usd(s['commitment_usd'])}" if s["commitment_usd"] else ""
                lines.append(f"    {s['signal_date']}  {s['fund_name']}{amt}  [{s['source']}]")
        else:
            lines.append(f"    No logged signals  ·  disclosure: {lp['disclosure']}")
    return "\n".join(lines)


def render_talent_signals() -> str:
    lines = ["=" * 78, "  TALENT SIGNALS — departures & spinouts", "=" * 78]
    sigs = get_talent_signals(limit=20)
    if not sigs:
        lines.append("  No signals logged yet — run the weekly departure sweep.")
    for s in sigs:
        kind = "SPINOUT" if s["signal_type"] == "spinout" else "DEPARTURE"
        nf = f" -> {s['new_firm']}" if s["new_firm"] else ""
        lines += [
            "",
            f"  [{kind}]  {s['person']}  ·  ex-{s['prior_firm']} ({s['prior_title']}){nf}",
            f"    {s['signal_date']}  ·  status: {s['status']}  ·  {s['evidence']}",
        ]
    return "\n".join(lines)


def render_agent_offerings() -> str:
    lines = ["=" * 78, "  PLACEMENT AGENT OFFERINGS", "=" * 78]
    offerings = get_offerings(limit=20)
    if not offerings:
        lines.append("  No offerings logged — add teasers as they arrive.")
    for o in offerings:
        tgt = f"  ·  target {_fmt_usd(o['target_usd'])}" if o["target_usd"] else ""
        lines += [
            "",
            f"  {o['fund_name']}  ({o['gp_name']})",
            f"    via {o['agent_name']}  ·  {o['strategy']}{tgt}  ·  "
            f"close {o['expected_close'] or 'TBD'}  ·  status: {o['status']}",
        ]
        if o["note"]:
            lines.append(f"    note: {o['note']}")
    return "\n".join(lines)


_STATUS_LABEL = {
    "in_market_now": "IN MARKET NOW",
    "imminent": "IMMINENT (<12mo)",
    "monitor": "MONITOR",
}


def render_reup_radar(strategy: str | None = None) -> str:
    fc = forecast_market(strategy=strategy)
    c = fc["counts"]
    lines = [
        "=" * 78,
        "  RE-UP RADAR — predicted fundraise windows"
        + (f"  ·  strategy={strategy}" if strategy else ""),
        f"  as of {fc['as_of']}  ·  {c['in_market_now']} in market now  ·  "
        f"{c['imminent']} imminent  ·  {c['monitor']} monitor",
        f"  model: {fc['model']}",
        "=" * 78,
    ]
    for r in fc["forecasts"]:
        if r["status"] == "monitor":
            continue
        est = f"  ·  est. next size ~{_fmt_usd(r['est_next_size_usd'])}" if r["est_next_size_usd"] else ""
        conf = "  ·  UNVERIFIED VINTAGE DATA" if r["confidence"] == "memory" else ""
        lines += [
            "",
            f"  [{_STATUS_LABEL[r['status']]}]  {r['gp']}  ·  {r['strategy']}",
            f"    Last: {r['last_fund']} closed {r['last_close']} at {_fmt_usd(r['last_size_usd'])}",
            f"    Cycle: {r['cycle_years']}y ({r['cycle_basis']})  ·  window opens "
            f"{r['window_opens']}  ·  close due ~{r['next_close_due']}{est}{conf}",
        ]
        if r["note"]:
            lines.append(f"    note: {r['note']}")
        lines.append(f"    verify: {r['verify_with']}")
    return "\n".join(lines)


def render_pipeline() -> str:
    lines = ["=" * 78, "  PIPELINE", "=" * 78]
    board = get_pipeline()
    for stage, cards in board.items():
        if not cards:
            continue
        lines.append(f"\n  {stage.upper().replace('_', ' ')} ({len(cards)})")
        for c in cards:
            fn = f" Fund {c['fund_number']}" if c["fund_number"] else ""
            cv = f"  ·  conviction: {c['conviction']}" if c["conviction"] else ""
            lines.append(f"    {c['fund_name']}{fn}  ·  {c['strategy']}  ·  "
                         f"{_fmt_usd(c['size_usd'])}  ·  via {c['source']}{cv}")
    if all(not v for v in board.values()):
        lines.append("  Empty — add funds from the deal feed.")
    return "\n".join(lines)


def render_dashboard() -> str:
    return "\n\n".join([
        render_deal_feed(include_outside_mandate=False),
        render_reup_radar(),
        render_lp_watch(),
        render_talent_signals(),
        render_agent_offerings(),
        render_pipeline(),
    ])


if __name__ == "__main__":
    print(render_dashboard())
