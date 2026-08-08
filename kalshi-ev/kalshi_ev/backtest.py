"""Walk-forward backtest of the calibration strategy.

Protocol (the order matters — it is what keeps the result honest):

1. Sort snapshots by close time.
2. Fit the calibration model on the earliest ``train_frac`` of them.
3. Trade the remainder chronologically: for each snapshot, compute the
   calibrated probability, apply slippage to the snapshot price to
   approximate the ask you'd actually pay, and take the trade only if
   net EV clears ``min_ev_cents``. Size with fractional Kelly.

What this still cannot capture (and why live results will be worse):
- Adverse selection: the fills you get most easily are the ones someone
  smarter was happy to give you.
- Fill probability: we assume every wanted trade fills at price+slippage.
- Regime drift: a bias measured on last quarter's markets may be gone.
Treat a backtest that only barely clears zero as a losing strategy.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional

from .calibration import CalibrationModel, brier_score
from .data import Snapshot
from .ev import TradeDecision, evaluate_market
from .fees import STANDARD_RATE, fee_cents_exact


@dataclass
class SimTrade:
    ticker: str
    side: str
    price_cents: int
    contracts: int
    prob: float
    ev_cents: float
    pnl_cents: float


@dataclass
class BacktestResult:
    n_snapshots: int
    n_train: int
    n_test: int
    n_trades: int
    n_wins: int
    staked_cents: float
    pnl_cents: float
    final_bankroll_cents: float
    max_drawdown: float
    model: CalibrationModel
    market_brier: float
    model_brier: float
    trades: List[SimTrade] = field(default_factory=list)

    @property
    def roi(self) -> float:
        return self.pnl_cents / self.staked_cents if self.staked_cents else 0.0

    @property
    def win_rate(self) -> float:
        return self.n_wins / self.n_trades if self.n_trades else 0.0


def run_backtest(snapshots: List[Snapshot],
                 train_frac: float = 0.6,
                 bankroll_cents: float = 100_000.0,  # $1,000
                 min_ev_cents: float = 3.0,
                 slippage_cents: int = 2,
                 kelly_multiplier: float = 0.25,
                 max_fraction: float = 0.05,
                 rate: float = STANDARD_RATE,
                 model: Optional[CalibrationModel] = None) -> BacktestResult:
    if len(snapshots) < 30:
        raise ValueError("need at least 30 snapshots for a meaningful split")

    snaps = sorted(snapshots, key=lambda s: s.close_ts)
    n_train = int(len(snaps) * train_frac)
    train, test = snaps[:n_train], snaps[n_train:]

    if model is None:
        model = CalibrationModel.fit(
            [s.price_cents for s in train], [s.outcome for s in train])

    bankroll = bankroll_cents
    peak = bankroll
    max_dd = 0.0
    staked = 0.0
    pnl_total = 0.0
    trades: List[SimTrade] = []
    n_wins = 0

    for snap in test:
        q = model.predict(snap.price_cents)
        # approximate the two asks from the snapshot price plus slippage
        yes_ask = int(round(snap.price_cents)) + slippage_cents
        no_ask = 100 - int(round(snap.price_cents)) + slippage_cents
        yes_ask = yes_ask if 0 < yes_ask < 100 else None
        no_ask = no_ask if 0 < no_ask < 100 else None

        decision = evaluate_market(q, yes_ask, no_ask, rate=rate,
                                   min_ev_cents=min_ev_cents)
        if decision is None:
            continue
        contracts = decision.stake_contracts(bankroll, kelly_multiplier, max_fraction)
        if contracts < 1:
            continue

        fee = fee_cents_exact(decision.price_cents, contracts, rate)
        won = (snap.outcome == 1) == (decision.side == "yes")
        if won:
            pnl = contracts * (100 - decision.price_cents) - fee
            n_wins += 1
        else:
            pnl = -contracts * decision.price_cents - fee

        bankroll += pnl
        pnl_total += pnl
        staked += contracts * decision.price_cents
        peak = max(peak, bankroll)
        if peak > 0:
            max_dd = max(max_dd, (peak - bankroll) / peak)

        trades.append(SimTrade(
            ticker=snap.ticker, side=decision.side,
            price_cents=decision.price_cents, contracts=contracts,
            prob=decision.prob, ev_cents=decision.ev_cents, pnl_cents=pnl,
        ))
        if bankroll <= 0:
            break

    test_prices = [s.price_cents for s in test]
    test_outcomes = [s.outcome for s in test]
    return BacktestResult(
        n_snapshots=len(snaps), n_train=len(train), n_test=len(test),
        n_trades=len(trades), n_wins=n_wins,
        staked_cents=staked, pnl_cents=pnl_total,
        final_bankroll_cents=bankroll, max_drawdown=max_dd,
        model=model,
        market_brier=brier_score([p / 100.0 for p in test_prices], test_outcomes),
        model_brier=brier_score([model.predict(p) for p in test_prices], test_outcomes),
        trades=trades,
    )
