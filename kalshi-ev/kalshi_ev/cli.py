"""Command-line interface. Run as `python -m kalshi_ev <command>`."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from .backtest import run_backtest
from .calibration import CalibrationModel, brier_score, reliability_table
from .client import DEMO_BASE, PROD_BASE, KalshiPublicClient
from .data import collect_snapshots, load_snapshots
from .scanner import scan_arbitrage, scan_calibration_edges, scan_weather
from .weather import NWSClient, STATIONS

console = Console()

DISCLAIMER = (
    "[dim]Research tool, not investment advice. Backtested or theoretical EV "
    "does not guarantee live profits. Paper-trade first; never bet money you "
    "can't lose.[/dim]"
)


def _client(args) -> KalshiPublicClient:
    return KalshiPublicClient(base_url=DEMO_BASE if args.demo else PROD_BASE)


# ── commands ─────────────────────────────────────────────────────────


def cmd_status(args):
    status = _client(args).exchange_status()
    console.print(Panel.fit(f"Exchange status: {status}", border_style="cyan"))


def cmd_arbs(args):
    client = _client(args)
    console.print("[cyan]Scanning open events for structural arbitrage…[/cyan]")
    opportunities = scan_arbitrage(
        client, series_tickers=args.series, max_events=args.max_events,
        min_profit_cents=args.min_profit)
    if not opportunities:
        console.print("[yellow]No structural arbs found[/yellow] — expected on a "
                      "liquid exchange; they appear briefly and mostly in "
                      "thin, multi-bucket events.")
        return
    table = Table(title="Structural arbitrage opportunities")
    for col in ("kind", "event", "legs", "cost¢", "payout¢", "profit¢/unit", "max units"):
        table.add_column(col)
    for o in opportunities:
        table.add_row(o.kind, o.event_ticker, str(len(o.legs)),
                      f"{o.cost_cents:.1f}", f"{o.payout_cents:.0f}",
                      f"{o.profit_cents:.2f}", str(o.max_units))
    console.print(table)
    if any(o.assumes_exhaustive for o in opportunities):
        console.print("[yellow]⚠ all_yes/all_no assume the event's buckets are "
                      "exhaustive — verify the tail buckets exist before trading.[/yellow]")
    console.print(DISCLAIMER)


def cmd_collect(args):
    client = _client(args)
    console.print(f"[cyan]Collecting settled-market snapshots "
                  f"({args.horizon}h before close) for: {', '.join(args.series)}[/cyan]")
    n = collect_snapshots(client, args.series, horizon_hours=args.horizon,
                          max_markets_per_series=args.max_markets,
                          out_path=args.data)
    console.print(f"[green]✓ wrote {n} new snapshots to {args.data}[/green]")


def cmd_calibrate(args):
    snaps = load_snapshots(args.data)
    if len(snaps) < 30:
        console.print(f"[red]Only {len(snaps)} snapshots in {args.data}; "
                      f"collect more first (`collect` command).[/red]")
        sys.exit(1)
    prices = [s.price_cents for s in snaps]
    outcomes = [s.outcome for s in snaps]
    model = CalibrationModel.fit(prices, outcomes)
    model.save(args.out)

    market_brier = brier_score([p / 100 for p in prices], outcomes)
    model_brier = brier_score([model.predict(p) for p in prices], outcomes)
    console.print(Panel.fit(
        f"[bold]Calibration fit[/bold] (n={len(snaps)})\n\n"
        f"q = sigmoid({model.a:+.3f} + {model.b:.3f}·logit(p))\n"
        f"b < 1 ⇒ market overconfident (fade extremes); "
        f"b > 1 ⇒ underconfident (back favorites)\n\n"
        f"Brier — market: {market_brier:.4f}   model (in-sample): {model_brier:.4f}\n"
        f"Saved to [bold]{args.out}[/bold]",
        border_style="green"))

    table = Table(title="Reliability by price decile")
    for col in ("bucket", "n", "mean price¢", "actual yes %"):
        table.add_column(col, justify="right")
    for label, n, mean_p, rate in reliability_table(prices, outcomes):
        table.add_row(label, str(n), f"{mean_p:.1f}", f"{rate:.1f}")
    console.print(table)
    console.print("[dim]In-sample Brier always flatters the model — trust the "
                  "walk-forward backtest, not this table.[/dim]")


def cmd_backtest(args):
    snaps = load_snapshots(args.data)
    if len(snaps) < 30:
        console.print(f"[red]Only {len(snaps)} snapshots in {args.data}; "
                      f"collect more first.[/red]")
        sys.exit(1)
    result = run_backtest(
        snaps, train_frac=args.train_frac,
        bankroll_cents=args.bankroll * 100,
        min_ev_cents=args.min_ev, slippage_cents=args.slippage,
        kelly_multiplier=args.kelly, max_fraction=args.max_fraction)

    verdict = ("[bold green]positive[/bold green]" if result.pnl_cents > 0
               else "[bold red]negative[/bold red]")
    console.print(Panel.fit(
        f"[bold]Walk-forward backtest[/bold] "
        f"(train {result.n_train} / test {result.n_test})\n\n"
        f"Model: q = sigmoid({result.model.a:+.3f} + {result.model.b:.3f}·logit(p))\n"
        f"Trades: {result.n_trades}   wins: {result.n_wins} "
        f"({result.win_rate*100:.1f}%)\n"
        f"Staked: ${result.staked_cents/100:,.2f}   "
        f"P&L: ${result.pnl_cents/100:,.2f}   ROI: {result.roi*100:+.2f}%\n"
        f"Bankroll: ${args.bankroll:,.2f} → ${result.final_bankroll_cents/100:,.2f}   "
        f"max drawdown: {result.max_drawdown*100:.1f}%\n"
        f"Brier — market: {result.market_brier:.4f}   "
        f"model (out-of-sample): {result.model_brier:.4f}\n\n"
        f"Out-of-sample EV is {verdict}.",
        border_style="cyan"))
    if result.pnl_cents > 0:
        console.print("[yellow]Before believing this: live fills face adverse "
                      "selection and fill risk the backtest can't model. "
                      "A thin positive here usually means ~zero live.[/yellow]")
    console.print(DISCLAIMER)


def cmd_weather(args):
    client = _client(args)
    console.print("[cyan]Pricing daily-high markets from NWS forecasts…[/cyan]")
    edges = scan_weather(client, NWSClient(), series_tickers=args.series,
                         min_ev_cents=args.min_ev, bias_degf=args.bias)
    _print_edges(edges, args.bankroll, args.kelly)


def cmd_edges(args):
    if not Path(args.model).exists():
        console.print(f"[red]No model at {args.model} — run `calibrate` first.[/red]")
        sys.exit(1)
    model = CalibrationModel.load(args.model)
    client = _client(args)
    console.print(f"[cyan]Repricing open markets through calibration model "
                  f"(b={model.b:.3f})…[/cyan]")
    edges = scan_calibration_edges(client, model, series_tickers=args.series,
                                   max_events=args.max_events,
                                   min_ev_cents=args.min_ev)
    _print_edges(edges, args.bankroll, args.kelly)


def _print_edges(edges, bankroll_dollars: float, kelly_multiplier: float):
    if not edges:
        console.print("[yellow]No opportunities clear the EV threshold.[/yellow] "
                      "That is the normal state of an efficient market — "
                      "no trade is a valid (and often correct) output.")
        return
    bankroll_cents = bankroll_dollars * 100
    table = Table(title=f"+EV candidates (bankroll ${bankroll_dollars:,.0f}, "
                        f"{kelly_multiplier:.2f}× Kelly)")
    for col in ("ticker", "side", "ask¢", "model p", "EV¢/ct", "size", "depth", "basis"):
        table.add_column(col)
    for e in edges:
        d = e.decision
        size = min(d.stake_contracts(bankroll_cents, kelly_multiplier), e.liquidity)
        table.add_row(e.ticker, d.side.upper(), str(d.price_cents),
                      f"{d.prob:.3f}", f"{d.ev_cents:+.1f}",
                      str(size), str(e.liquidity), e.note)
    console.print(table)
    console.print(DISCLAIMER)


# ── parser ───────────────────────────────────────────────────────────


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="kalshi_ev",
        description="Fee-aware expected-value toolkit for Kalshi markets")
    parser.add_argument("--demo", action="store_true",
                        help="use Kalshi's demo API instead of production")
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("status", help="exchange status")

    p = sub.add_parser("arbs", help="scan for structural arbitrage")
    p.add_argument("--series", nargs="*", default=None)
    p.add_argument("--max-events", type=int, default=50)
    p.add_argument("--min-profit", type=float, default=1.0,
                   help="min guaranteed profit in cents per unit")

    p = sub.add_parser("collect", help="snapshot settled markets for training data")
    p.add_argument("--series", nargs="+", required=True,
                   help="e.g. KXHIGHNY KXHIGHCHI")
    p.add_argument("--horizon", type=int, default=24,
                   help="hours before close to snapshot the price")
    p.add_argument("--max-markets", type=int, default=400)
    p.add_argument("--data", default="data/snapshots.jsonl")

    p = sub.add_parser("calibrate", help="fit calibration model on snapshots")
    p.add_argument("--data", default="data/snapshots.jsonl")
    p.add_argument("--out", default="data/calibration.json")

    p = sub.add_parser("backtest", help="walk-forward backtest on snapshots")
    p.add_argument("--data", default="data/snapshots.jsonl")
    p.add_argument("--train-frac", type=float, default=0.6)
    p.add_argument("--bankroll", type=float, default=1000.0, help="dollars")
    p.add_argument("--min-ev", type=float, default=3.0, help="cents per contract")
    p.add_argument("--slippage", type=int, default=2, help="cents")
    p.add_argument("--kelly", type=float, default=0.25, help="Kelly multiplier")
    p.add_argument("--max-fraction", type=float, default=0.05,
                   help="max fraction of bankroll per trade")

    p = sub.add_parser("weather", help="price daily-high markets from NWS forecasts")
    p.add_argument("--series", nargs="*", default=None,
                   help=f"subset of: {' '.join(STATIONS)}")
    p.add_argument("--min-ev", type=float, default=3.0)
    p.add_argument("--bias", type=float, default=0.0,
                   help="degF added to NWS forecast (station-specific bias)")
    p.add_argument("--bankroll", type=float, default=1000.0)
    p.add_argument("--kelly", type=float, default=0.25)

    p = sub.add_parser("edges", help="scan open markets through the calibration model")
    p.add_argument("--model", default="data/calibration.json")
    p.add_argument("--series", nargs="*", default=None)
    p.add_argument("--max-events", type=int, default=50)
    p.add_argument("--min-ev", type=float, default=3.0)
    p.add_argument("--bankroll", type=float, default=1000.0)
    p.add_argument("--kelly", type=float, default=0.25)

    return parser


def main(argv=None):
    args = build_parser().parse_args(argv)
    dispatch = {
        "status": cmd_status,
        "arbs": cmd_arbs,
        "collect": cmd_collect,
        "calibrate": cmd_calibrate,
        "backtest": cmd_backtest,
        "weather": cmd_weather,
        "edges": cmd_edges,
    }
    dispatch[args.command](args)
