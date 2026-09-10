"""CLI:  python -m dashboard <command>

  build    collect from source, rank, render          (needs network egress)
  render   render an existing snapshot JSON to HTML   (offline)
  probe    report which sources this machine can read
  rank     print the ranking table without rendering
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import date
from pathlib import Path

from . import brief, render as renderer
from .config import FEEDS, SERIES
from .sources.http import HttpError, get

DEFAULT_OUT = Path("./data/dashboard.html")
DEFAULT_SNAPSHOT = Path("./data/snapshot.json")


def cmd_build(args) -> int:
    events = []
    if args.calendar and Path(args.calendar).exists():
        events = json.loads(Path(args.calendar).read_text())

    snap = brief.build(events=events, verbose=not args.quiet)

    snap_path = Path(args.snapshot or DEFAULT_SNAPSHOT)
    snap_path.parent.mkdir(parents=True, exist_ok=True)
    snap_path.write_text(json.dumps(snap, indent=2, default=str))

    out = renderer.write(snap, args.out or DEFAULT_OUT)
    print(f"\nsnapshot → {snap_path}")
    print(f"page     → {out}")
    if snap.get("failures"):
        print(f"\n{len(snap['failures'])} source(s) failed:")
        for f in snap["failures"]:
            print(f"  {f}")
    return 0


def cmd_render(args) -> int:
    snap = renderer.load(args.snapshot)
    out = renderer.write(snap, args.out or DEFAULT_OUT)
    print(f"page → {out}  ({len(snap.get('modules', []))} modules)")
    return 0


def cmd_probe(args) -> int:
    """Check reachability before a build, so failures are legible."""
    targets = [
        ("FRED", "https://fred.stlouisfed.org/graph/fredgraph.csv?id=DGS10"),
        ("Treasury curve",
         "https://home.treasury.gov/resource-center/data-chart-center/"
         "interest-rates/pages/xml?data=daily_treasury_yield_curve"
         f"&field_tdr_date_value={date.today().year}"),
        ("Treasury FiscalData",
         "https://api.fiscaldata.treasury.gov/services/api/fiscal_service/"
         "v2/accounting/od/debt_to_penny?page%5Bsize%5D=1"),
        ("BLS", "https://api.bls.gov/publicAPI/v1/timeseries/data/CUUR0000SA0"),
        ("Stooq", "https://stooq.com/q/d/l/?s=%5Espx&i=d"),
    ] + [(f"feed: {k}", v) for k, v in FEEDS.items()]

    ok = 0
    for name, url in targets:
        try:
            body = get(url, ttl=0, retries=1, timeout=15)
            print(f"  ok    {name:<24} {len(body):>9,} bytes")
            ok += 1
        except HttpError as exc:
            reason = str(exc).split(": ", 1)[-1][:60]
            print(f"  BLOCK {name:<24} {reason}")

    print(f"\n{ok}/{len(targets)} reachable")
    if ok < len(targets):
        print("Blocked sources are skipped at build time; the page marks "
              "anything it could not read.")
    return 0 if ok else 1


def cmd_rank(args) -> int:
    store, failed = brief.collect_series(verbose=False)
    ratios = brief.collect_ratios(store)
    signals = brief.build_signals(store, ratios, [], date.today())
    signals.sort(key=lambda s: s.score, reverse=True)

    print(f"{'score':>6}  {'module':<30} {'bucket':<12} why")
    print("-" * 100)
    for s in signals:
        mark = "*" if s.score >= 25 else " "
        print(f"{s.score:6.1f}{mark} {s.label:<30} {s.bucket:<12} "
              f"{s.top_reason[:44]}")
    print(f"\n{sum(1 for s in signals if s.score >= 25)} would clear the floor "
          f"({len(SERIES)} series tracked, {len(failed)} failed)")
    return 0


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="dashboard", description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest="cmd", required=True)

    b = sub.add_parser("build", help="collect, rank and render")
    b.add_argument("--out", help=f"HTML output (default {DEFAULT_OUT})")
    b.add_argument("--snapshot", help=f"snapshot JSON (default {DEFAULT_SNAPSHOT})")
    b.add_argument("--calendar", help="JSON file of upcoming releases")
    b.add_argument("--quiet", action="store_true")
    b.set_defaults(fn=cmd_build)

    r = sub.add_parser("render", help="render a snapshot to HTML")
    r.add_argument("snapshot")
    r.add_argument("--out", help=f"HTML output (default {DEFAULT_OUT})")
    r.set_defaults(fn=cmd_render)

    pr = sub.add_parser("probe", help="check which sources are reachable")
    pr.set_defaults(fn=cmd_probe)

    rk = sub.add_parser("rank", help="print the ranking table only")
    rk.set_defaults(fn=cmd_rank)

    args = p.parse_args(argv)
    return args.fn(args)


if __name__ == "__main__":
    sys.exit(main())
