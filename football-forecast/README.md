# footy — football forecasting and value betting

A time-weighted Dixon-Coles model for the **Premier League**, **La Liga** and the
**Champions League**, with every betting market derived from a single scoreline
distribution, honest overround removal, thresholded value detection with
fractional Kelly staking, and a walk-forward backtest scored **against the
closing line**.

The design assumption throughout: the hard part isn't building a model that
looks profitable in a backtest. The hard part is telling whether you have an
edge or variance. Everything here is arranged to answer that question rather
than to flatter the model.

```bash
pip install -r requirements.txt
python -m footy demo          # end-to-end on simulated data, no network needed
```

---

## The model

For a match between home `i` and away `j` in competition `c`:

```
log λ = level[c] + hfa[c]·(venue not neutral) + attack[i] − defence[j]
log μ = level[c]                              + attack[j] − defence[i]
```

Goals are Poisson around those rates, with the Dixon-Coles `τ` correction on the
four low-scoring cells. The fitted `ρ` is negative in real data, meaning more
0-0 and 1-1 results and fewer 1-0 and 0-1 results than independent Poissons
predict — the dependence that plain Poisson models get wrong.

Every match is weighted by `φ = exp(−ξ · age_in_days)` with `ξ = ln2 / half_life`,
so the half-life is the one knob controlling how fast form is forgotten. It is
tunable, not a constant (see [Tuning](#tuning)).

**Fitting on expected goals.** `xg_weight` blends the two signals:

```
target = xg_weight · xg + (1 − xg_weight) · goals
```

`1.0` fits purely on xG, `0.0` reduces *exactly* to textbook Dixon-Coles on raw
goals (there is a test asserting that), and anything in between tests the mix.
The blended target is continuous, so the Poisson kernel is evaluated in its
continuous form. The `τ` correction is a property of real scorelines, so it is
always evaluated against the observed integer score whatever the blend. Matches
with no xG coverage fall back to goals individually, which matters because
Champions League xG coverage is patchy.

**Three competitions, one parameter space.** Each competition gets its own
scoring level and home advantage, but teams share one attack/defence scale.
Champions League fixtures are what link the English and Spanish scales together,
so a La Liga side can be priced against a Premier League side coherently.
Neutral venues drop the home-advantage term.

Attack and defence are each pinned to mean zero for identifiability and
ridge-shrunk toward zero, which stops teams with a handful of European matches
acquiring absurd strengths.

Fitting uses L-BFGS-B with a hand-derived analytic gradient (including the `τ`
terms), verified against finite differences to better than 1e-5 relative error
in the test suite. A wrong gradient converges to the wrong answer quietly, so
that check earns its place.

```python
from footy import fit_dixon_coles, DixonColesConfig

model = fit_dixon_coles(matches, config=DixonColesConfig(half_life_days=180, xg_weight=0.6))
model.team_strength()          # attack / defence / net ratings
model.home_advantage("UCL")
```

## One distribution, every market

`model.predict(...)` returns a **scoreline matrix**, and every market is a
different way of summing it:

| Market | Derived from |
|---|---|
| Match odds (1X2) | win / draw / lose regions |
| Asian handicap, any line incl. quarters | goal-difference distribution |
| Over/under, any line incl. quarters | goals-total distribution |
| Double chance, draw-no-bet, BTTS, correct score | the same matrix |

This is what keeps the board internally consistent: the over-2.5 price and the
−1.5 handicap price can never disagree about the same match. `consistency_check()`
asserts the identities that should hold (level handicap ≡ draw-no-bet, −0.5
handicap ≡ home win, double chance ≡ sums of 1X2) and the test suite runs it.

Each selection carries win/push **weight matrices** rather than a bare
probability, so quarter-ball lines fall out naturally as half-weights and push
protection is priced correctly: break-even odds are `1 + lose/win`, not `1/win`.

```python
board = build_markets(forecast)
board["ah_-0.25"]["Home"].fair_odds
board["ou_2.5"]["Over"].fair_probability   # conditional on no push
```

## Reading the bookmaker

Raw inverse odds sum to more than one; the excess has to come out before any
comparison means anything. *How* it comes out matters more than people expect —
naive proportional scaling systematically overstates longshots.

Four methods: `shin` (default, Shin's insider-trading model), `power`,
`multiplicative`, `odds_ratio`. They agree closely on a balanced two-way market
and diverge most where it matters — a 1X2 book with a big favourite:

```python
remove_overround({"H": 1.25, "D": 6.00, "A": 12.00}, method="shin")
# multiplicative prices the longshot higher than shin does; there is a test for it
```

Partial books are skipped rather than guessed at, because de-vigging half a
market invents edges that don't exist.

## Finding and sizing bets

**A positive edge is not a bet.** A selection has to clear an explicit threshold
on *both* expected value and probability edge. The defaults are deliberately not
zero.

**Fractional Kelly.** Full Kelly is optimal only if your probabilities are
exactly right, which they are not. A quarter to a half gives up little growth
for a large cut in variance. Pushes are handled properly:

```
f* = (p_win·(o−1) − p_lose) / ((o−1)·(p_win + p_lose))
```

which reduces to the textbook formula when nothing can push. A slate-level cap
scales a busy Saturday down, since Kelly sized each bet as if it were alone.

```python
bets = find_value_bets(board, book, ValueConfig(min_ev=0.03, min_prob_edge=0.02,
                                                kelly_fraction=0.25))
```

## Parlays, and refusing to fake independence

Multiplying same-match legs is the most common way to turn a modest edge into a
guaranteed loss. This library will not do it. Legs are grouped by match, and a
group of more than one is either priced **exactly** off that match's shared
scoreline matrix, or the parlay is refused (`on_correlation="reject"`).

```
3 leg(s), combined odds 9.55
  naive independent probability : 0.13979
  correctly priced probability  : 0.16186
  correlation factor            : 1.158
  ! EPL 01 v EPL 02: 2 legs from the same match priced jointly
                     (exact 0.3332 vs naive independent 0.2878)
```

A home win and over 2.5 reinforce each other, so the naive product *understates*
that parlay. It cuts the other way too — home win **and** away win comes back as
probability 0.0000, where naive multiplication would happily quote it as a live
bet. Legs from genuinely different matches are multiplied, and the correlation
factor comes back at exactly 1.000.

## Backtesting

Two decisions carry the weight:

**Nothing leaks.** For every match day the model is refitted on matches that
finished strictly before it. There is a test asserting the training set never
crosses the cutoff.

**The benchmark is the closing line.** Closing prices absorb every steam move
and team-news leak in the market, and are the hardest thing in sports betting to
beat. Backtesting against openers mostly measures how slow the book was on a
Tuesday. So the headline output is not profit — it's whether the model's
forecasts score better than the **de-vigged closing market** on the same matches,
by log loss, Brier and RPS, with a side-by-side calibration table.

```
metric           model    market     delta
------------------------------------------
log_loss        0.9748    0.9543   +0.0204
brier           0.5796    0.5653   +0.0143
rps             0.2094    0.2028   +0.0066
ece             0.0242    0.0120   +0.0119

model does NOT beat the closing line
  its forecasts score +0.0204 on log loss against the
  de-vigged close, so it is the less accurate of the two.

bets           : 2556
flat profit    : +85.36 u  (ROI +3.34%)
kelly bankroll : 4892.03 (from 1000.00, growth +389.20%)
```

That output is the whole point. A +3.3% ROI and a bankroll that nearly 5×'d,
printed directly underneath the verdict that the model is *less accurate than
the market*. Without the second panel you would ship this.

Bets can be struck at closing prices (the strict test) or opening prices (the
realistic one). When you bet at the open, **closing line value** is reported —
the fastest-converging read on edge there is. CLV is suppressed when betting at
the close, where it is identically zero by construction rather than informative.

Note that beating the close on *forecast accuracy* and getting positive *CLV* are
different claims, and a strategy can pass one while failing the other — typically
when it beats sloppy openers without ever being better than the market's final
word. The verdict distinguishes them.

## Tuning

Half-life and xG blend are real free parameters, usually set by folklore. Grid
search them against out-of-sample log loss instead — not profit, which over a few
hundred bets is far too noisy to rank configurations and is an efficient way to
fit noise.

```
 half_life   xg_w   log_loss    brier      rps      n
-----------------------------------------------------
        90   0.50    0.97237  0.57809  0.20866   2307 *
       180   0.50    0.97431  0.57926  0.20924   2307
        90   1.00    0.97639  0.58070  0.20986   2307
        90   0.00    0.97890  0.58284  0.21100   2307
       365   0.00    0.98176  0.58443  0.21170   2307
```

`sensitivity()` reports how much the criterion actually moves across the grid.
If the spread is negligible the parameter isn't doing real work and a mid-range
default is fine.

## Data

```python
# football-data.co.uk season CSVs — results plus prices, closing columns preferred
matches, books = load_football_data_csv("E0.csv")     # SP1.csv for La Liga

# any CSV, via a column mapping — for xG feeds or private data
xg = load_matches_csv("understat.csv", column_map={"home": "home_team"})

merged, unmatched = attach_xg(matches, xg)
coverage_report(merged)      # per-competition match counts and xG coverage
```

Team names are normalised on every load. Name mismatches are the single most
common source of silent data loss when stitching an xG source onto an odds
source, and `attach_xg` deliberately *returns* what it couldn't match rather than
swallowing it — a long tail there means a missing alias, and quietly fitting on
half your xG is worse than not using xG at all.

`generate_synthetic_dataset()` simulates both leagues, a Champions League and a
bookmaker from a known ground truth, with team strengths following a random walk
so form genuinely decays. It makes the whole pipeline runnable offline and gives
the tests something real to assert against — the fit recovers attack/defence at
r ≈ 0.92, `ρ` to within 0.02, and the tuner recovers both the finite half-life
and the fact that a blend beats either pure signal.

**Its bookmaker is far sharper than any real one** — it knows the true model and
only jitters it, so its closing line sits essentially on the irreducible scoring
floor. Treat a backtest there as a test of the machinery, not as evidence a
strategy works.

## CLI

```bash
python -m footy demo
python -m footy fit       --football-data E0.csv SP1.csv --top 20
python -m footy predict   --football-data E0.csv --home Arsenal --away Chelsea --competition EPL
python -m footy value     --football-data E0.csv --odds-json slate.json --min-ev 0.03
python -m footy parlay    --football-data E0.csv --legs legs.json --on-correlation reject
python -m footy backtest  --football-data E0.csv --bet-on opening --bets-csv bets.csv
python -m footy tune      --football-data E0.csv
```

Every command takes `--synthetic` instead of a data source. `--help` on any
subcommand lists the model and betting knobs.

## Tests

```bash
python -m pytest tests/ -q     # 135 tests
```

They cover the gradient against finite differences, parameter recovery from
simulated data, the `xg_weight=0` reduction, market consistency identities,
quarter-line settlement, push-aware fair odds and Kelly, every de-vigging method,
threshold gating, parlay correlation (including mutually exclusive legs at
probability zero), scoring rules against known constants, calibration detection,
and that the backtester never trains on the future.

## Limitations

Worth knowing before pointing real money at this:

- **No lineup, injury, rest or motivation information.** The market has all of
  it, which is a large part of why the closing line is hard to beat.
- **Team strength is a snapshot, not a state-space model.** Exponential decay
  approximates drift; it does not model it. A proper time-varying Kalman/Bayesian
  formulation would use the data better.
- **No promotion/relegation handling.** Newly promoted sides start from the
  ridge-shrunk mean with no prior from the division below.
- **No in-play, no goal-time information**, and the scoreline matrix assumes the
  two scoring rates are fixed for ninety minutes.
- **Backtests ignore limits and price movement.** Real stakes at real prices move
  the line, and the account that consistently beats the close gets restricted.

## Layout

```
footy/
  types.py        Match, BookOdds, OddsQuote
  data.py         loaders, name normalisation, xG joining, synthetic world
  dixoncoles.py   the model: likelihood, analytic gradient, fitting, prediction
  markets.py      scoreline matrix -> every market, as weight matrices
  odds.py         overround removal (shin / power / multiplicative / odds-ratio)
  value.py        thresholds, fractional Kelly, correlated parlays
  metrics.py      Brier, log loss, RPS, calibration, skill vs reference
  backtest.py     walk-forward, settlement, P&L, CLV
  tuning.py       half-life and xG-blend grid search
  cli.py          command line interface
tests/            135 tests
```
