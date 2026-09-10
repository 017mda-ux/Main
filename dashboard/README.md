# Vantage

A single screen for a global cross-asset allocator. Open it, read it, close it.

It answers one question first — *what moved, and does it mean anything* — and
only then offers the detail. Nothing is estimated, interpolated or modelled. A
number that could not be sourced reads `—` rather than a plausible guess.

## Running it

```bash
python3 dashboard/refresh.py     # builds dashboard/data.json
cd dashboard && python3 -m http.server 8000
```

Then open <http://localhost:8000>. `refresh.py` needs no packages — standard
library only.

## How data reaches the page

Two independent paths. Either one alone is enough to render the page.

| Path | Source | When |
|---|---|---|
| Snapshot | `data.json`, committed by the workflow | Every page load, instantly |
| Live | Stooq daily CSV, fetched by your browser | Every page load, in the background |

The snapshot paints first so the page is never blank; the live fetch then
upgrades the numbers and deepens the history (about a year in the snapshot,
about five years live). Percentile labels state the window actually used, so
they never claim more history than they have.

Live series are cached in `localStorage` for twelve hours. **Refresh** clears
that cache and refetches.

If your browser cannot reach Stooq — a blocked network, or no CORS header on
their response — the page silently keeps the snapshot. Nothing breaks.

## What it deliberately does not do

- **No forward multiples.** No free, keyless, browser-reachable source
  publishes forward P/E. The valuation section shows price percentiles against
  each index's own history and links to the primary sources (S&P, MSCI,
  Damodaran, Shiller) for real forward multiples.
- **No aggregated news.** Every headline comes from the issuing institution —
  the Fed, the ECB, the BIS, NBER, the SEC, USTR, EIA. No secondary commentary.
- **No CDX or ACM term premium.** Neither is free. `HYG/IEF` and `HYG/LQD` are
  labelled as proxies, and the real series are linked.

## Editing it

`config.js` is the whole editable surface — instruments, the bellwether
baskets and what each one is a read on, and the source rail. `refresh.py`
reads the ticker list straight out of it, so adding an instrument in one place
is enough.

`refresh.py`'s `FEEDS` map holds the feed URLs, grouped into the blocks the
page renders. A feed that dies is dropped from that run and the previous
items are kept — a failed refresh never blanks good data.

## Deploying

`.github/workflows/dashboard.yml` refreshes the snapshot every six hours and
publishes `dashboard/` to GitHub Pages. One-time setup:

1. **Settings → Pages → Source: GitHub Actions.**
2. If the workflow runs from a non-default branch, allow that branch under
   **Settings → Environments → github-pages → Deployment branches**.
3. Optional: set a repository variable `CONTACT_EMAIL`. The SEC asks for a
   contact address in automated requests and may throttle EDGAR without one.

## Reading the numbers

- **σ** — the day's move divided by that instrument's own trailing 60-day
  volatility. It is why a 22bp day in the 10-year outranks a 3% day in the
  Nasdaq. The mover list shows only what clears 1.5σ.
- **Percentile** — where today sits in that series' own recent distribution.
- **bp** — basis points, used for anything quoted as a yield.
- **Copper/gold vs the 10-year** — both indexed to 100 on one axis, never two
  scales. They normally travel together; when they separate, one of them is
  early.

Not investment advice. Verify every figure at its source before acting on it.
