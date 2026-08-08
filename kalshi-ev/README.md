# kalshi-ev — a fee-aware expected-value toolkit for Kalshi

A research toolkit for finding, sizing, and validating positive-EV trades on
[Kalshi](https://kalshi.com) event markets. It does not place orders — it
finds candidate trades, prices them net of fees, sizes them with fractional
Kelly, and lets you verify the whole strategy on historical data before a
single cent is at risk.

## Where +EV can actually come from

Kalshi is a real exchange with professional participants. Buying things that
"feel likely" is -EV after the ~7% × P×(1−P) taker fee and the spread. This
toolkit attacks the three places a small, disciplined trader plausibly has an
edge:

1. **Structural arbitrage** (`arbs`) — model-free. In a mutually exclusive
   event, if the YES asks across all buckets sum to less than $1 minus fees
   (or the NO asks to less than $(n−1) minus fees), buying every leg locks a
   profit regardless of outcome. Rare and small on liquid events, real on
   thin multi-bucket ones. The scanner does the fee math and reports the
   executable size (minimum depth across legs).

2. **Calibration / favorite-longshot bias** (`collect` → `calibrate` →
   `backtest` → `edges`) — the classic prediction-market inefficiency:
   longshots trade rich, near-certainties trade cheap. The pipeline snapshots
   settled markets at a fixed horizon before close (via candlesticks — never
   the settled `last_price`, which is 0/100 by construction), fits
   `q = sigmoid(a + b·logit(price))` by maximum likelihood, and **walk-forward
   backtests** the strategy with fees, slippage, and Kelly sizing. If `b ≈ 1`
   in your data, the market is calibrated and there is no edge — the toolkit
   will tell you that, and *no trade* is the correct output.

3. **Weather models** (`weather`) — daily high-temperature markets settle on
   the official NWS climate report. The free NWS point forecast plus its
   published error distribution (`high ~ Normal(forecast, σ(lead))`) is a
   genuinely informed prior, and much of the flow on these markets is not.
   The scanner prices every bucket with a continuity-corrected Normal CDF and
   flags asks trading below model probability net of fees.

## Quick start

```bash
cd kalshi-ev
pip install -r requirements.txt

# is there free money lying around? (usually no — that's the honest answer)
python -m kalshi_ev arbs --min-profit 2

# weather: price today's high-temp buckets from NWS forecasts
python -m kalshi_ev weather --series KXHIGHNY KXHIGHCHI --bankroll 500

# calibration pipeline: collect history, fit, and validate out-of-sample
python -m kalshi_ev collect --series KXHIGHNY KXHIGHCHI KXHIGHMIA --horizon 24
python -m kalshi_ev calibrate
python -m kalshi_ev backtest --min-ev 3 --kelly 0.25
# only if the walk-forward backtest is convincingly positive:
python -m kalshi_ev edges --min-ev 3
```

`--demo` on any command targets Kalshi's demo environment instead of
production.

## The discipline built into the numbers

- **Fees first.** Every EV figure is net of the taker fee
  `0.07·P·(1−P)`, which peaks exactly where markets are most tempting
  (50c). An "edge" that ignores fees is how most people donate.
- **EV floor.** Trades must clear `--min-ev` (default 3c/contract). That
  buffer is the defense against model error and adverse selection, which no
  EV formula can see.
- **Fractional Kelly.** Default 0.25× Kelly, capped at 5% of bankroll per
  trade. Full Kelly on an overestimated edge is ruin; probabilities from a
  fitted model are always partly overestimated.
- **Walk-forward only.** The backtest fits on the earliest 60% of snapshots
  and trades the rest chronologically. In-sample results are shown but
  explicitly labeled as flattery.

## What this cannot promise

A backtest that clears fees and slippage is *evidence of* positive expected
value, not a guarantee: fills face adverse selection (you get filled fastest
when you're wrong), measured biases decay as markets mature, and weather
sigmas vary by station and season. Paper-trade the signals, re-collect and
re-fit regularly, and treat a thin backtested edge as zero. This is a
research tool, not investment advice; never trade money you can't afford to
lose. If gambling stops being fun: 1-800-GAMBLER.

## Layout

```
kalshi_ev/
  client.py      Kalshi public API client + orderbook math (asks derived from
                 opposite-side bids: yes_ask = 100 − best_no_bid)
  fees.py        taker-fee model (ceil per order; exact form used in EV)
  ev.py          EV per contract, Kelly sizing, trade decisions
  calibration.py 2-param Platt fit (Newton-Raphson, no dependencies)
  weather.py     NWS client + Normal-CDF bucket probabilities
  arbitrage.py   all-YES / all-NO / box structural arb detection
  data.py        settled-market snapshot collection (candlesticks at horizon)
  backtest.py    walk-forward simulation with fees, slippage, Kelly
  scanner.py     live scanners tying the above together
  cli.py         `python -m kalshi_ev` commands
tests/           37 offline tests covering all quantitative logic
```
