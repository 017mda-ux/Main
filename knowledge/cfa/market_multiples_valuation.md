# Market-based valuation: price and EV multiples — working notes

Distilled in our own words from the CFA Institute Level II refresher reading *Market-Based Valuation: Price
and Enterprise Value Multiples* (2026 curriculum, RR_2026_L2V5R4). Standard formulas; the reading itself is
copyrighted and not stored here.

## 1. Two ways to use a multiple
- **Method of comparables** (law of one price): compare a stock's multiple with a benchmark — a close peer,
  the peer median/harmonic mean, the industry, the index, or the company's own history. It tells you
  *relative* value only: if the whole group is expensive, "cheap vs peers" can still be overpriced.
- **Forecasted fundamentals**: a *justified* multiple from a DCF/dividend model. It tells you what the
  multiple *should* be given growth, ROE/profitability and the required return. Use it to explain why a stock
  deserves a premium or discount to peers.
- Best practice: run comparables, then explain every gap with fundamentals (growth, risk, ROE, margins,
  leverage, accounting). An unexplained gap is a candidate mispricing.

## 2. Justified multiples (single-stage, sustainable growth g = retention × ROE)
- Payout = 1 − g/ROE
- Forward P/E = payout ÷ (r − g); trailing P/E = payout × (1 + g) ÷ (r − g)
- P/B = (ROE − g) ÷ (r − g)  → above 1 only when ROE > r
- P/S = net margin × payout × (1 + g) ÷ (r − g)
- EV/EBITDA rises with FCFF growth and FCFF/EBITDA conversion, falls with WACC
- Drivers in one line: multiples rise with growth and profitability, fall with the required return.
- **Single-stage formulas explode as g approaches r.** For compounders (Costco, Alphabet) use a multistage DCF
  and divide value by next-year EPS. Better still, invert the P/E into the **perpetual growth it implies** —
  a clean, comparable read on what the market is pricing.

## 3. Choosing and cleaning the denominator
- **P/E**: the main earnings-power yardstick. Use **underlying (persistent) EPS**: strip one-offs such as
  investment gains/losses, legal fines, tax refunds, restructuring. (Alphabet's 2026 EPS includes large
  SpaceX/Anthropic mark-to-market gains; Apple FY26 includes a $0.11 tariff refund.)
- **Normalized EPS** for cyclicals: average EPS over a full cycle, or average ROE × current book value per share.
- **Earnings yield (E/P)** works when EPS is negative or near zero (rank by E/P, not P/E).
- **PEG** = P/E ÷ growth (%). A rough growth adjustment; assumes a linear P/E–growth link and ignores risk
  and the duration of growth.
- **P/B**: suits financials and asset-heavy firms; adjust book value for intangibles, off-balance-sheet items
  and inflation. Weak for asset-light franchises.
- **P/S / EV/S**: stable, never negative, hard to manipulate — but blind to cost structure. EV/S beats P/S
  across capital structures.
- **Price to cash flow**: earnings + non-cash charges is traditional; FCFE has the best theoretical link.
- **EV/EBITDA**: flow to all capital, neutral to leverage, popular for capital-intensive firms — but EBITDA
  ignores capex, taxes and working capital. It flatters heavy spenders (Alphabet during the AI build-out).
- **Dividend yield**: a component of return; weak for buyback-driven payouts (Apple, Alphabet).

## 4. Enterprise value
EV = market cap + debt + preferred + minority interest − cash and investments. Count equity stakes once:
either subtract them in EV or value them separately, never both.

## 5. Comparables mechanics
- Benchmarks: median resists outliers; **harmonic mean** damps the effect of very high multiples (it averages
  earnings yields); arithmetic mean is pulled up by outliers.
- Use forward multiples when earnings are changing fast; lag trailing data to avoid look-ahead bias in
  back-tests.
- Cross-border: adjust for accounting standards (IFRS vs US GAAP), growth and country risk.
- Predicted P/E by cross-sectional regression on payout, growth and risk is possible, but coefficients are
  unstable and the variables correlate with each other.

## 6. Multiples in DCF terminal values
- Terminal value = benchmark trailing P/E × Eₙ, or forward P/E × Eₙ₊₁ (similarly for EV/EBITDA).
- It is a market cross-check, not a substitute: if today's multiple is high, it imports today's optimism
  into year n. Always reconcile the exit multiple with the justified multiple from fundamentals at year n.

## 7. Momentum and screening
- Earnings surprise, standardized unexpected earnings (SUE = surprise ÷ std. dev. of past surprises),
  relative strength. Useful timing signals, not value.
- Screens narrow a universe quickly but rely on vendor data definitions and miss qualitative factors.

## 8. Our checklist
1. Which multiple fits the business (P/E for steady earners, EV/S or EV/EBITDA for early or levered, P/B
   for banks)? Is the denominator underlying, normalized, forward?
2. Comparables: median and harmonic mean of a real peer set; explain gaps with growth, ROE and risk.
3. Fundamentals: justified multiple (multistage for compounders) and the perpetual growth implied by the
   current P/E.
4. Exit multiples in DCFs must be consistent with the justified multiple at exit.

## 9. Our applications (Nov 2026; ROE inputs approximate)
| | Forward P/E | PEG | Perpetual growth implied by P/E | Notes |
|---|---|---|---|---|
| Costco (k 7.5%, ROE ~30%) | 45x | 4.8 | ~5.7% | DCF-justified FY31 P/E ~29x vs our 38x exit |
| Apple (k 8.3%, ROE very high from buybacks) | 36x | 3.8 | ~5.6% | underlying EPS excludes $0.11 tariff refund |
| Alphabet (k 8.2%, ROE ~30%) | 18x | 1.0 | ~3.2% | lowest bar of the three |
