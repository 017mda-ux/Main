# Market Dashboard

A macro brief for a rates/macro seat. It collects from official sources, scores
everything it tracks for how interesting it is *today*, drops what did not clear
the bar, and renders what is left.

The point is that it is **not the same page every day**. A module has to earn its
slot.

## Why it filters

Most dashboards print the same grid regardless of what happened, so the reader
has to do the ranking themselves. Here the ranking is the product. Every
candidate module gets a 0–100 salience score built from independent components:

| Component | What it measures |
|---|---|
| `move` | today's change in trailing daily standard deviations |
| `level` | how extreme the level is against its own trailing window |
| `cross` | a 50/200 moving-average cross fired, or closing and near |
| `surprise` | a data print against consensus, in sigma of past misses |
| `event` | proximity to a scheduled catalyst |
| `divergence` | a ratio parting company with the series it normally tracks |
| `streak` | a persistent directional run |

Components combine as a weighted root-sum-square, so one strong reason outranks
several weak ones. Then three filters apply:

- anything below `SALIENCE.floor` is dropped outright;
- no bucket takes more than `max_per_bucket` slots, so rates cannot crowd out
  everything else;
- modules that led recent runs are decayed against `data/dashboard_state.json`,
  so a quiet week rotates rather than repeating.

Visual weight follows the score — the top module gets a chart and full prose, a
module that scraped in gets one line.

## Sources

Only official statistical agencies, the central bank, the fiscal authority, and
primary market data. No aggregators for anything that has a primary publisher.

| Adapter | Source | Key needed |
|---|---|---|
| `sources/fred.py` | FRED `fredgraph.csv` — Treasury curve, TIPS, breakevens, term premium, OAS, H.10 FX, H.4.1 | no |
| `sources/treasury_rates.py` | Treasury daily par yield curve XML — the primary publication | no |
| `sources/treasury_fiscal.py` | Treasury FiscalData — DTS cash balance, MTS deficit, debt, auction tails, interest expense | no |
| `sources/bls.py` | BLS public API — CPI, payrolls, earnings | optional (`BLS_API_KEY` for v2 limits) |
| `sources/stooq.py` | Stooq EOD — indices, metals, vol (not government-published) | no |
| `sources/feeds.py` | Fed, Treasury, BLS, BEA, CBO, EIA RSS | no |

`feeds.py` tags each item with the official speaking (`FED_PRINCIPALS`,
`CABINET_PRINCIPALS` in `config.py`) and scores it for market-moving potential,
weighting the Chair above a regional president and decaying with age.

## Use

```bash
python -m dashboard probe     # which sources this machine can reach
python -m dashboard build     # collect, rank, render → data/dashboard.html
python -m dashboard rank      # ranking table only, no render
python -m dashboard render dashboard/data/snapshot-2026-09-10.json
```

`build` writes both the HTML and the snapshot JSON that produced it, so any
page can be re-rendered exactly.

## Network requirement

`build` needs egress to the hosts above. Some sandboxes block them — run `probe`
first; it names what is reachable and what is not, and `build` skips blocked
sources rather than failing.

The snapshot in `data/snapshot-2026-09-10.json` was assembled from published
reporting rather than direct collection for exactly this reason. It carries
`"collection_mode": "research"`, and the rendered page says so.

## Configuring

Everything tracked is declarative in `config.py`:

- `SERIES` — what to collect, with per-series notability thresholds
- `RATIOS` — derived ratios and the benchmark each is tested against
- `MA_WATCH` — what gets 50/200 cross detection
- `RELEASES` — the data calendar
- `FEEDS`, `FED_PRINCIPALS`, `CABINET_PRINCIPALS` — the speak feed
- `SALIENCE` — floor, caps, component weights, repeat decay

To make the brief more or less selective, move `SALIENCE.floor`. To change what
it cares about, move the component weights.

## Tests

```bash
python tests/test_analytics.py
```

Runs the maths against synthetic series where the answer is known by hand —
volatility, z-scores, percentile ranks, cross detection, divergence, bucket
caps, repeat decay, and a full render.
