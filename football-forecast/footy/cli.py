"""Command line interface.

    python -m footy demo
    python -m footy fit --matches data/matches.csv --top 15
    python -m footy predict --matches data/matches.csv --home Arsenal --away Chelsea --competition EPL
    python -m footy value --matches data/matches.csv --odds-json slate.json
    python -m footy backtest --matches data/matches.csv --odds-csv odds.csv
    python -m footy tune --matches data/matches.csv
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Optional, Sequence

from .backtest import BacktestConfig, run_backtest
from .data import (
    coverage_report,
    generate_synthetic_dataset,
    load_football_data_csv,
    load_matches_csv,
    normalise_team,
)
from .dixoncoles import DixonColesConfig, fit_dixon_coles
from .markets import build_markets, consistency_check
from .tuning import DEFAULT_HALF_LIVES, DEFAULT_XG_WEIGHTS, sensitivity, tune
from .types import BookOdds, Match
from .value import ParlayLeg, ValueConfig, evaluate_parlay, find_value_bets


# --------------------------------------------------------------------------
# helpers
# --------------------------------------------------------------------------


def _model_config(args) -> DixonColesConfig:
    return DixonColesConfig(
        half_life_days=None if args.half_life <= 0 else args.half_life,
        xg_weight=args.xg_weight,
        ridge=args.ridge,
        max_goals=args.max_goals,
        allow_unknown_teams=getattr(args, "allow_unknown_teams", False),
    )


def _value_config(args) -> ValueConfig:
    return ValueConfig(
        min_ev=args.min_ev,
        min_prob_edge=args.min_edge,
        kelly_fraction=args.kelly,
        max_stake_fraction=args.max_stake,
        bankroll=args.bankroll,
        devig_method=args.devig,
    )


def _load_matches(args) -> tuple[list[Match], dict[str, BookOdds]]:
    """Resolve whichever data source the user pointed at."""
    matches: list[Match] = []
    odds: dict[str, BookOdds] = {}

    if getattr(args, "synthetic", False) or (
        not getattr(args, "matches", None) and not getattr(args, "football_data", None)
    ):
        data = generate_synthetic_dataset(seasons=args.seasons, seed=args.seed)
        return data.matches, data.odds

    for path in getattr(args, "football_data", None) or []:
        ms, books = load_football_data_csv(path)
        matches.extend(ms)
        for b in books:
            odds[b.match_id] = b

    if getattr(args, "matches", None):
        matches.extend(load_matches_csv(args.matches))

    if not matches:
        raise SystemExit("no matches loaded; pass --matches, --football-data or --synthetic")
    return matches, odds


def _print_coverage(matches: Sequence[Match]) -> None:
    print("data coverage")
    print(f"  {'competition':<14}{'matches':>9}{'played':>9}{'xG cover':>10}")
    for comp, row in sorted(coverage_report(matches).items()):
        print(
            f"  {comp:<14}{row['matches']:>9.0f}{row['played']:>9.0f}"
            f"{row['xg_coverage']:>9.0%}"
        )
    print()


# --------------------------------------------------------------------------
# commands
# --------------------------------------------------------------------------


def cmd_fit(args) -> int:
    matches, _ = _load_matches(args)
    _print_coverage(matches)
    model = fit_dixon_coles(matches, config=_model_config(args))

    print(
        f"fitted on {model.n_matches} matches "
        f"({model.effective_matches:.0f} effective after time decay) "
        f"as of {model.as_of}"
    )
    print(f"  log-likelihood {model.log_likelihood:.2f}   converged={model.converged}")
    print(
        f"  rho {model.rho:+.4f}   "
        "(negative => more 0-0 and 1-1, fewer 1-0 and 0-1, than independent Poissons)"
    )
    for comp, lvl in sorted(model.level.items()):
        print(f"  {comp:<10} scoring level {lvl:+.3f}   home advantage {model.home_advantage(comp):+.3f}")
    print()

    strength = model.team_strength()
    print(f"{'team':<28}{'attack':>9}{'defence':>9}{'net':>9}{'matches':>9}")
    print("-" * 64)
    for team, row in list(strength.items())[: args.top]:
        print(
            f"{team:<28}{row['attack']:>+9.3f}{row['defence']:>+9.3f}"
            f"{row['net']:>+9.3f}{row['matches']:>9.0f}"
        )
    return 0


def cmd_predict(args) -> int:
    matches, _ = _load_matches(args)
    model = fit_dixon_coles(matches, config=_model_config(args))
    home, away = normalise_team(args.home), normalise_team(args.away)
    forecast = model.predict(home, away, args.competition, neutral=args.neutral)

    lam, mu = forecast.expected_goals()
    print(f"{home} v {away}  [{args.competition}{', neutral' if args.neutral else ''}]")
    print(f"  expected goals: {lam:.2f} - {mu:.2f}")
    probs = forecast.outcome_probabilities()
    print(
        "  1X2: "
        + "  ".join(f"{k} {v:.1%} ({1 / v:.2f})" for k, v in probs.items())
    )
    print()

    board = build_markets(forecast)
    problems = consistency_check(board)
    if problems:
        print("!! market consistency violations:", *problems, sep="\n   ")
        print()

    print(f"{'market':<12}{'selection':<10}{'prob':>9}{'fair odds':>11}")
    print("-" * 42)
    for market in args.markets:
        for name, sel in board.get(market, {}).items():
            push = "  (push %.1f%%)" % (sel.push_prob * 100) if sel.has_push else ""
            print(
                f"{market:<12}{name:<10}{sel.fair_probability:>9.4f}"
                f"{sel.fair_odds:>11.3f}{push}"
            )

    top = sorted(
        ((float(forecast.matrix[i, j]), i, j)
         for i in range(forecast.matrix.shape[0])
         for j in range(forecast.matrix.shape[1])),
        reverse=True,
    )[:6]
    print("\nmost likely scorelines: " + "  ".join(f"{i}-{j} {p:.1%}" for p, i, j in top))
    return 0


def cmd_value(args) -> int:
    matches, odds = _load_matches(args)
    model = fit_dixon_coles(matches, config=_model_config(args))
    vcfg = _value_config(args)

    if args.odds_json:
        slate = json.loads(Path(args.odds_json).read_text())
        fixtures = []
        for row in slate:
            match_id = row.get("match_id") or f"{row['home']} v {row['away']}"
            book = BookOdds.from_mapping(match_id, row["odds"])
            forecast = model.predict(
                normalise_team(row["home"]), normalise_team(row["away"]),
                row.get("competition", args.competition), neutral=row.get("neutral", False),
            )
            fixtures.append((forecast, book))
    else:
        # Scan the most recent matches in the loaded data that carry odds.
        fixtures = []
        for match in sorted(matches, key=lambda m: m.date)[-args.limit:]:
            book = odds.get(match.match_id)
            if book is None:
                continue
            fixtures.append((model.predict_match(match), book))

    if not fixtures:
        print("no fixtures with odds to scan")
        return 1

    all_bets = []
    for forecast, book in fixtures:
        board = build_markets(forecast)
        scoped = {k: v for k, v in board.items() if not args.markets or k in args.markets}
        all_bets.extend(find_value_bets(scoped, book, vcfg, forecast=forecast))

    if not all_bets:
        print(
            f"no bet cleared the thresholds "
            f"(min EV {vcfg.min_ev:.1%}, min edge {vcfg.min_prob_edge:.1%}) "
            f"across {len(fixtures)} fixture(s)."
        )
        print("That is the normal result against a sharp book. Lower the thresholds only")
        print("if you have a reason to believe your model is better than they assume.")
        return 0

    all_bets.sort(key=lambda b: -b.ev)
    print(f"{len(all_bets)} selection(s) cleared the thresholds, best first:\n")
    header = (
        f"{'match':<26}{'market':<10}{'sel':<7}{'odds':>7}{'fair':>7}"
        f"{'edge':>8}{'EV':>8}{'stake':>9}"
    )
    print(header)
    print("-" * len(header))
    for b in all_bets[: args.top]:
        label = f"{b.home} v {b.away}" if b.home else b.match_id
        print(
            f"{label[:25]:<26}{b.market:<10}{b.selection:<7}{b.odds:>7.2f}"
            f"{b.fair_odds:>7.2f}{b.edge:>+8.3f}{b.ev:>+8.3f}{b.stake:>9.2f}"
        )
    print(f"\ntotal staked: {sum(b.stake for b in all_bets[: args.top]):.2f} "
          f"of a {vcfg.bankroll:.2f} bankroll ({vcfg.kelly_fraction:.0%} Kelly)")
    return 0


def cmd_parlay(args) -> int:
    matches, _ = _load_matches(args)
    model = fit_dixon_coles(matches, config=_model_config(args))
    spec = json.loads(Path(args.legs).read_text())

    boards, forecasts, legs = {}, {}, []
    for row in spec:
        match_id = row.get("match_id") or f"{row['home']} v {row['away']}"
        if match_id not in boards:
            fc = model.predict(
                normalise_team(row["home"]), normalise_team(row["away"]),
                row.get("competition", args.competition), neutral=row.get("neutral", False),
            )
            forecasts[match_id] = fc
            boards[match_id] = build_markets(fc)
        legs.append(ParlayLeg(match_id, row["market"], row["selection"], float(row["odds"])))

    ev = evaluate_parlay(legs, boards, forecasts, _value_config(args), on_correlation=args.on_correlation)
    print(f"{len(legs)} leg(s), combined odds {ev.combined_odds:.2f}")
    print(f"  naive independent probability : {ev.naive_independent_prob:.5f}")
    if ev.priced:
        print(f"  correctly priced probability  : {ev.joint_prob:.5f}")
        print(f"  correlation factor            : {ev.correlation_factor:.3f}")
        print(f"  expected value                : {ev.ev:+.4f} per unit staked")
        print(f"  {args.kelly:.0%} Kelly stake              : {ev.stake:.2f}")
    else:
        print("  NOT PRICED")
    for w in ev.warnings:
        print(f"  ! {w}")
    return 0 if ev.priced else 1


def cmd_backtest(args) -> int:
    matches, odds = _load_matches(args)
    if not odds:
        raise SystemExit(
            "backtesting needs odds; use --football-data (which carries prices) or --synthetic"
        )
    _print_coverage(matches)
    cfg = BacktestConfig(
        model=_model_config(args),
        value=_value_config(args),
        train_window_days=None if args.train_window <= 0 else args.train_window,
        min_train_matches=args.min_train,
        refit_every_days=args.refit_every,
        bet_on=args.bet_on,
        bet_markets=tuple(args.markets) if args.markets else ("1X2",),
        starting_bankroll=args.bankroll,
    )
    result = run_backtest(matches, odds, cfg)
    print(result.summary())

    print("\ncalibration -- model (left) vs closing market (right)")
    print(f"{'bucket':<14}{'n':>7}{'pred':>8}{'obs':>8}{'gap':>8}   |{'n':>7}{'pred':>8}{'obs':>8}{'gap':>8}")
    market_by_bucket = {(b.lower, b.upper): b for b in result.market_calibration}
    for b in result.calibration:
        m = market_by_bucket.get((b.lower, b.upper))
        right = (
            f"{m.count:>7}{m.mean_predicted:>8.3f}{m.observed_rate:>8.3f}{m.gap:>+8.3f}"
            if m else " " * 31
        )
        print(
            f"[{b.lower:.1f},{b.upper:.1f})".ljust(14)
            + f"{b.count:>7}{b.mean_predicted:>8.3f}{b.observed_rate:>8.3f}{b.gap:>+8.3f}   |"
            + right
        )

    if args.bets_csv and result.bets:
        import csv as _csv

        out = Path(args.bets_csv)
        out.parent.mkdir(parents=True, exist_ok=True)
        with out.open("w", newline="", encoding="utf-8") as fh:
            w = _csv.writer(fh)
            w.writerow([
                "date", "match", "competition", "market", "selection", "odds_taken",
                "closing_odds", "model_prob", "market_prob", "edge", "ev",
                "stake_kelly", "profit_per_unit", "bankroll_after", "clv",
            ])
            for b in result.bets:
                w.writerow([
                    b.date, f"{b.home} v {b.away}", b.competition, b.market, b.selection,
                    b.odds_taken, b.closing_odds, round(b.model_prob, 5),
                    round(b.market_prob, 5), round(b.edge, 5), round(b.ev, 5),
                    round(b.stake_kelly, 2), round(b.profit_per_unit, 4),
                    round(b.bankroll_after, 2), round(b.clv, 5) if b.clv is not None else "",
                ])
        print(f"\nbet log written to {out}")
    return 0


def cmd_tune(args) -> int:
    matches, _ = _load_matches(args)
    half_lives = args.half_lives or list(DEFAULT_HALF_LIVES)
    weights = args.xg_weights or list(DEFAULT_XG_WEIGHTS)
    print(f"grid: {len(half_lives)} half-lives x {len(weights)} blends "
          f"= {len(half_lives) * len(weights)} walk-forward evaluations\n")
    result = tune(
        matches, half_lives=half_lives, xg_weights=weights,
        base_config=_model_config(args), criterion=args.criterion,
        train_window_days=None if args.train_window <= 0 else args.train_window,
        min_train_matches=args.min_train, refit_every_days=args.refit_every,
    )
    print(result.table())
    print(f"\nbest: {result.best_config_kwargs}")
    s = sensitivity(result)
    print(
        f"{args.criterion} spread across the grid: {s['spread']:.5f} "
        f"({s['relative_spread']:.2%} of the best value)"
    )
    if s["relative_spread"] < 0.005:
        print("that is small -- these parameters are not doing much on this data")
    return 0


def cmd_demo(args) -> int:
    """End-to-end run on simulated data."""
    print("=" * 70)
    print("Simulating three seasons of EPL, La Liga and Champions League")
    print("=" * 70)
    data = generate_synthetic_dataset(seasons=args.seasons, seed=args.seed)
    _print_coverage(data.matches)

    cfg = DixonColesConfig(half_life_days=args.half_life, xg_weight=args.xg_weight)
    model = fit_dixon_coles(data.matches, config=cfg)
    print(f"fitted: {model.n_matches} matches, rho {model.rho:+.4f}, "
          f"converged={model.converged}")
    for comp in sorted(model.level):
        print(f"  {comp:<8} home advantage {model.home_advantage(comp):+.3f} "
              f"(true {data.true_hfa:+.3f})")

    strongest = list(model.team_strength())[0]
    weakest = list(model.team_strength())[-1]
    forecast = model.predict(strongest, weakest, "EPL")
    lam, mu = forecast.expected_goals()
    print(f"\nstrongest v weakest: {strongest} v {weakest}")
    print(f"  expected goals {lam:.2f} - {mu:.2f}")
    print("  " + "  ".join(f"{k} {v:.1%}" for k, v in forecast.outcome_probabilities().items()))

    board = build_markets(forecast)
    problems = consistency_check(board)
    print(f"\nmarket consistency check across {len(board)} markets: "
          f"{'PASS' if not problems else problems}")
    for market in ("1X2", "ah_-1.5", "ah_-1.25", "ou_2.5", "ou_3", "btts"):
        if market in board:
            print(f"  {market:<10} " + "  ".join(
                f"{n} {s.fair_odds:.2f}" for n, s in board[market].items()))

    print("\n" + "=" * 70)
    print("Walk-forward backtest against the simulated CLOSING line")
    print("=" * 70)
    bt = BacktestConfig(
        model=cfg,
        value=ValueConfig(min_ev=args.min_ev, min_prob_edge=args.min_edge,
                          kelly_fraction=args.kelly, bankroll=args.bankroll),
        refit_every_days=14, min_train_matches=300, bet_on="opening",
        starting_bankroll=args.bankroll,
    )
    result = run_backtest(data.matches, data.odds, bt)
    print(result.summary())
    print(
        "\nNote: this simulated bookmaker prices the true model with only a little\n"
        "noise, so its closing line sits almost exactly on the irreducible scoring\n"
        "floor -- sharper than any real book. Failing to beat it is the correct\n"
        "answer here, and printing that verdict next to a healthy-looking profit\n"
        "curve is the entire point of the exercise. Point it at real data to ask\n"
        "the question for real."
    )
    return 0


# --------------------------------------------------------------------------
# parser
# --------------------------------------------------------------------------


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="footy",
        description="Dixon-Coles football forecasting and value betting.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    sub = p.add_subparsers(dest="command", required=True)

    def common(sp):
        src = sp.add_argument_group("data source")
        src.add_argument("--matches", help="generic match CSV")
        src.add_argument("--football-data", nargs="*", help="football-data.co.uk season CSVs")
        src.add_argument("--synthetic", action="store_true", help="use simulated data")
        src.add_argument("--seasons", type=int, default=3, help="synthetic seasons")
        src.add_argument("--seed", type=int, default=7, help="synthetic seed")

        m = sp.add_argument_group("model")
        m.add_argument("--half-life", type=float, default=180.0,
                       help="time-decay half-life in days; <=0 disables decay")
        m.add_argument("--xg-weight", type=float, default=0.7,
                       help="0 = raw goals only, 1 = expected goals only")
        m.add_argument("--ridge", type=float, default=0.02, help="shrinkage on attack/defence")
        m.add_argument("--max-goals", type=int, default=12, help="scoreline matrix truncation")
        m.add_argument("--allow-unknown-teams", action="store_true",
                       help="treat unseen teams as competition-average instead of failing")

    def betting(sp):
        b = sp.add_argument_group("betting")
        b.add_argument("--min-ev", type=float, default=0.03,
                       help="minimum expected value per unit staked")
        b.add_argument("--min-edge", type=float, default=0.02,
                       help="minimum probability edge over the de-vigged market")
        b.add_argument("--kelly", type=float, default=0.25,
                       help="Kelly fraction; 0.25-0.5 is the sane range")
        b.add_argument("--max-stake", type=float, default=0.05,
                       help="cap on any single stake as a fraction of bankroll")
        b.add_argument("--bankroll", type=float, default=1000.0)
        b.add_argument("--devig", default="shin",
                       choices=["shin", "power", "multiplicative", "odds_ratio"])

    sp = sub.add_parser("fit", help="fit the model and print team ratings")
    common(sp)
    sp.add_argument("--top", type=int, default=20)
    sp.set_defaults(func=cmd_fit)

    sp = sub.add_parser("predict", help="price a single fixture across every market")
    common(sp)
    sp.add_argument("--home", required=True)
    sp.add_argument("--away", required=True)
    sp.add_argument("--competition", default="EPL")
    sp.add_argument("--neutral", action="store_true")
    sp.add_argument("--markets", nargs="*", default=["1X2", "ah_-0.5", "ou_2.5", "btts"])
    sp.set_defaults(func=cmd_predict)

    sp = sub.add_parser("value", help="scan bookmaker odds for bets that clear the thresholds")
    common(sp)
    betting(sp)
    sp.add_argument("--odds-json", help="JSON slate: [{home, away, competition, odds:{market:{sel:price}}}]")
    sp.add_argument("--competition", default="EPL")
    sp.add_argument("--markets", nargs="*", default=[])
    sp.add_argument("--limit", type=int, default=40, help="fixtures to scan from loaded data")
    sp.add_argument("--top", type=int, default=25)
    sp.set_defaults(func=cmd_value)

    sp = sub.add_parser("parlay", help="price a parlay, handling same-match correlation")
    common(sp)
    betting(sp)
    sp.add_argument("--legs", required=True, help="JSON: [{home, away, market, selection, odds}]")
    sp.add_argument("--competition", default="EPL")
    sp.add_argument("--on-correlation", default="exact", choices=["exact", "reject"])
    sp.set_defaults(func=cmd_parlay)

    sp = sub.add_parser("backtest", help="walk-forward backtest against the closing line")
    common(sp)
    betting(sp)
    sp.add_argument("--train-window", type=int, default=900, help="rolling window in days; <=0 for expanding")
    sp.add_argument("--min-train", type=int, default=250)
    sp.add_argument("--refit-every", type=int, default=7)
    sp.add_argument("--bet-on", default="closing", choices=["closing", "opening"])
    sp.add_argument("--markets", nargs="*", default=["1X2"])
    sp.add_argument("--bets-csv", help="write the bet log here")
    sp.set_defaults(func=cmd_backtest)

    sp = sub.add_parser("tune", help="grid-search half-life and xG blend")
    common(sp)
    sp.add_argument("--half-lives", nargs="*", type=float)
    sp.add_argument("--xg-weights", nargs="*", type=float)
    sp.add_argument("--criterion", default="log_loss", choices=["log_loss", "brier", "rps"])
    sp.add_argument("--train-window", type=int, default=900)
    sp.add_argument("--min-train", type=int, default=250)
    sp.add_argument("--refit-every", type=int, default=14)
    sp.set_defaults(func=cmd_tune)

    sp = sub.add_parser("demo", help="end-to-end run on simulated data")
    common(sp)
    betting(sp)
    sp.set_defaults(func=cmd_demo)
    return p


def main(argv: Optional[Sequence[str]] = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        return args.func(args)
    except (ValueError, KeyError, FileNotFoundError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
