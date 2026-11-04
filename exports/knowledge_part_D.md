# PART D — REFERENCE LESSONS (upload as project knowledge, or keep in the chat)

## Berkshire Hathaway letters


Our distillation of Warren Buffett's shareholder letters (plus Charlie Munger's 2014 essay). Quotations are exact and
dated; everything else is paraphrase. The full text is searchable with `search_library` once
`scripts/build_berkshire_library.py` has been run (text is generated locally, not committed).

## 1. What a business is worth
- "We define intrinsic value as the discounted value of the cash that can be taken out of a business during its
  remaining life." (1994) It is a range, revised as cash-flow estimates and interest rates change.
- **Owner earnings** (1986): reported earnings + depreciation, depletion, amortization and other non-cash charges −
  "the average annual amount of capitalized expenditures for plant and equipment, etc. that the business requires to
  fully maintain its long-term competitive position and its unit volume" (± working capital needed). → `owner_earnings`.
- Growth and value are "joined at the hip: Growth is always a component in the calculation of value" — and growth can
  destroy value when it needs capital that earns too little. "Value investing" is redundant. (1992)
- **Look-through earnings** (1989): count your share of investees' retained earnings, not just dividends.

## 2. What makes a great business
- Criteria (2007): "a) a business we understand; b) favorable long-term economics; c) able and trustworthy management;
  and d) a sensible price tag."
- "A truly great business must have an enduring 'moat' that protects excellent returns on invested capital." Moats
  include being "the lowcost producer (GEICO, Costco)" or a powerful brand. (2007) "I look for economic castles
  protected by unbreachable 'moats.'" (1995)
- **Great / Good / Gruesome** (2007): great = high returns needing little capital to grow (See's); good = good returns
  but capital-hungry growth (utilities); gruesome = "grows rapidly, requires significant capital to engender the
  growth, and then earns little or no money. Think airlines."
- Inflation favors businesses with "intangibles of lasting value with relatively minor requirements for tangible
  assets." (1983)
- "Buy commodities, sell brands" (2011). Pricing power and low capital needs compound.

## 3. Price, quality and patience
- "It's far better to buy a wonderful company at a fair price than a fair company at a wonderful price. Charlie
  understood this early; I was a slow learner." (1989)
- "When a management with a reputation for brilliance tackles a business with a reputation for poor fundamental
  economics, it is the reputation of the business that remains intact." (quoted in 1985)
- "Your goal as an investor should simply be to purchase, at a rational price, a part interest in an
  easily-understandable business whose earnings are virtually certain to be materially higher five, ten and twenty
  years from now." (1996)
- "When we own portions of outstanding businesses with outstanding managements, our favorite holding period is
  forever." Selling winners and holding losers is "cutting the flowers and watering the weeds" (Lynch). (1988)
- "Inactivity strikes us as intelligent behavior." (1996)

## 4. Market prices, risk, concentration
- Mr. Market (1987): a partner quoting a price every day; use him, never be guided by him.
- "We simply attempt to be fearful when others are greedy and to be greedy only when others are fearful." (1986)
- "Price is what you pay; value is what you get." (Graham, quoted 2008)
- "Volatility is far from synonymous with risk." Risk = the chance of permanent loss of purchasing power over the
  holding period. (2014)
- Concentration "may well decrease risk if it raises ... both the intensity with which an investor thinks about a
  business and the comfort-level he must feel with its economic characteristics." (1993)
- "You only have to be able to evaluate companies within your circle of competence. The size of that circle is not
  very important; knowing its boundaries, however, is vital." (1996) On tech: "we have no insights into which
  participants in the tech field possess a truly durable competitive advantage." (1999)
- For most people a low-cost index fund beats paid "helpers" (2016; the hedge-fund bet).
- "It's only when the tide goes out that you learn who's been swimming naked." (1992) — leverage and under-reserving.

## 5. Capital allocation (the CEO's real job)
- **The $1 test** (1983 owner principles): retention must deliver "at least $1 of market value for each $1
  retained," judged on a five-year rolling basis. → `retained_earnings_test`.
- **Buybacks** only when two conditions are met: ample funds for the business's needs, and the stock "selling at a
  material discount to the company's intrinsic business value, conservatively calculated." (2011) → `buyback_check`.
- Issue stock only when receiving as much business value as you give. (1983)
- **Institutional imperative** (1989–90): "the tendency of executives to mindlessly imitate the behavior of their
  peers, no matter how foolish it may be to do so."
- Judge performance over at least five years against what American business earns on equity. (1983)

## 6. Insurance and float (how Berkshire compounded)
- Float is money held for others; if underwriting breaks even or better, float is free (or negative-cost) capital.
  The cost of float = underwriting loss ÷ average float. Underwriting discipline beats volume.

## 7. Munger's 2014 essay
- Berkshire's system: decentralised operations, owner-like managers, centralised capital allocation, rare use of
  leverage, preference for whole businesses with durable advantages, and a culture of trust.

## How the agent applies this
1. Value = cash that can be taken out; use **owner earnings**, not EPS.
2. Classify the business: great / good / gruesome by return on incremental capital and capital needs.
3. Name the moat (low cost, brand, network, switching, regulation) and evidence it is widening or narrowing.
4. Price: pay fair prices for great businesses; avoid cheap gruesome ones.
5. Capital allocation: run the $1 test; check buybacks against intrinsic value; watch for the institutional imperative.
6. Risk is permanent loss, not volatility; stay in the circle of competence; leverage kills.

## 8. Topics added after the first pass

### Owner-related business principles (1983)
- "Although our form is corporate, our attitude is partnership." Managers think of shareholders as owner-partners.
- Retain earnings only if each $1 retained creates at least $1 of market value (five-year rolling test); issue stock
  only when receiving as much business value as is given; use little debt; report candidly, good and bad.

### Acquisition criteria (1982 onward)
- Prefer large purchases, "demonstrated consistent earning power (future projections are of little interest to us,
  nor are 'turn-around' situations)," good returns on equity with little or no debt, management in place, simple
  businesses, and a stated price.

### Economic vs accounting goodwill (1983 appendix "Goodwill and its Amortization: The Rules and The Realities")
- Businesses that earn high returns on modest tangible assets have **economic goodwill** far larger than any
  accounting goodwill; intrinsic value includes it, book value does not. Amortization of purchased goodwill is not a
  real economic cost; inflation punishes asset-heavy businesses and rewards those with lasting intangibles.

### Inflation (1979–1981)
- The "investor's misery index" (1979): when inflation plus taxes on the business's returns exceed its return on
  equity, real capital shrinks even if the investor consumes nothing. Reported earnings in asset-heavy businesses
  overstate what owners can take out (1980): "We have owned 100% of businesses whose reported earnings were not worth
  close to 100 cents on the dollar to us."

### Two-column valuation of Berkshire (2007–2008 "Yardsticks")
- Value = investments per share + a multiple of pre-tax operating earnings per share from non-insurance businesses.
  A practical template for any conglomerate or holding company (Alphabet's stakes vs operations is the same idea).

### Derivatives and leverage (2002)
- "Derivatives are financial weapons of mass destruction, carrying dangers that, while now latent, are potentially
  lethal." Counterparty chains and mark-to-model accounting hide risk until a crisis.

### Mistakes, in his own accounting
- Dexter Shoe (2007 review): "What I had assessed as durable competitive advantage vanished within a few years," and
  paying in Berkshire stock turned a ~$400 million error into ~$3.5 billion. Lesson: never pay with undervalued stock;
  moats in commoditised, import-exposed industries are fragile.
- Stock-for-stock deals: "the worst deal of all" for the acquirer on tax grounds (1999).
- US Airways (1997): "a record that is unblemished by success"; airlines are the archetypal gruesome business.
- Textiles: a "chronically-leaking boat" — "energy devoted to changing vessels is likely to be more productive than
  energy devoted to patching leaks" (1985).

### Munger, "Vice Chairman's Thoughts – Past and Future" (2014)
- "The Berkshire system": a diffuse conglomerate "averse only to activities about which it could not make useful
  predictions," extreme autonomy for subsidiary CEOs, almost nothing at headquarters, centralised capital allocation,
  little debt, and a reputation as the preferred buyer for family businesses.
- On mistakes: "almost all huge errors were in not making a purchase, including not purchasing Walmart stock when
  that was sure to work out enormously well. The errors of omission were of much importance." — echoed by Nomad.
- Buffett "often displayed almost inhuman patience and seldom bought."

## 9. The 2020–2024 letters (from Markdown conversions; quotes near-verbatim — check the PDFs before publishing)
- **Own your mistakes, with numbers** (2020): the $11 billion write-down "is almost entirely the quantification of a
  mistake I made in 2016" — Precision Castparts: "I paid too much for the company ... I was simply too optimistic about
  PCC's normalized profit potential." Lesson: normalized earnings are the most dangerous estimate in a valuation.
- **Concentration in a few compounders** (2021 "Our Four Giants": insurance, Apple, BNSF, BHE). Most of the value sits
  in a handful of businesses.
- **"The Secret Sauce"** (2022): Coca-Cola bought for $1.3 billion by 1994 now pays $704 million a year in dividends.
  "The weeds wither away in significance as the flowers bloom. Over time, it takes just a few winners to work wonders."
  — the case for holding great businesses and letting position sizes drift up.
- **Munger as "architect"** (2023): Charlie "was the 'architect' of the present Berkshire, and I acted as the 'general
  contractor'" — the shift from cigar butts to wonderful businesses. Realistic goal: "slightly better" than the average
  American company "with materially less risk of permanent loss of capital. Anything beyond 'slightly better,' though,
  is wishful thinking." Size caps returns.
- **Mistakes and "thumb-sucking"** (2024): "The cardinal sin is delaying the correction of mistakes or what Charlie
  Munger called 'thumb-sucking.' Problems ... cannot be wished away." He counted 16 uses of "mistake" or "error" in
  2019–23 letters — candor as a test of management.
- **Businesses over cash** (2024): "Berkshire will never prefer ownership of cash-equivalent assets over the ownership
  of good businesses ... Paper money can see its value evaporate if fiscal folly prevails." Japan's five trading houses:
  a rare non-US bet on companies that "operate in a manner somewhat similar to Berkshire itself."

## Still missing (blocked by the session's network settings)
- Buffett's November 2025 letter and Greg Abel's first letter as CEO (berkshirehathaway.com), pre-1977 letters,
  annual-meeting transcripts, and the Worldly Partners Munger archive and case studies (worldlypartners.com).


## Buffett Partnership letters


Distilled from the Buffett Partnership Ltd. letters to limited partners. Short quotations are exact and dated;
everything else is our paraphrase. Use alongside the Nomad letters (which drew heavily on this lineage) and
the CFA valuation notes.

## 1. The ground rules (Jan 1963 and later "Ground Rules" mailings)
- Judge results **relative to a yardstick** (the Dow then; an index fund now), not plus/minus for the year.
  "If our record is better than that of these yardsticks, we consider it a good year whether we are plus or minus."
- **Three years minimum, five preferred** to judge. Expect to lag in strong bull markets and shine in down years.
- **No market forecasting.** "I am not in the business of predicting general stock market or business fluctuations."
  "We tend to concentrate on what should happen, not when it should happen." (July 1966)
- Promise process, not results: buy on **value, not popularity**; minimise **permanent** capital loss (not quotational
  loss) through a **wide margin of safety**; the manager eats his own cooking.
- State the goal and the measuring stick in advance (his: beat the Dow by ~10 points a year; lowered in Oct 1967).

## 2. Three categories of investment (Jan 1962 "Our Method of Operation"; Jan 1967 refinements)
| Category | What it is | Behaviour | Agent use |
|---|---|---|---|
| **Generals** | Undervalued stocks with no timetable. Later split into *Private Owner* (cheap vs what a buyer of the whole business would pay) and *Relatively Undervalued* (cheap vs comparable securities) | Moves with the market short term; the main source of long-run gains | Our DCF / multiples work. Sell somewhere between cost and value to a private owner |
| **Workouts** | Profit depends on a **corporate event** — merger, liquidation, tender, spin-off — "when we will get how much and what might upset the applecart" | Steady 10–20% returns largely independent of the market; the only place he used modest borrowing (≤25% of net worth) | `workout_return` tool: spread × probability ÷ time, with the downside if the deal breaks |
| **Controls** | Buy enough to influence policy (Dempster Mill, Berkshire) | Value set by the business, not the quote; judged over several years | Value as the cash a sale would bring "under current conditions in a reasonably short period," not a hoped-for price |

## 3. Conservatism is knowledge, not consensus (Jan 1962, repeated)
- "There is nothing at all conservative, in my opinion, about speculating as to just how high a multiplier a greedy
  and capricious public will put on earnings."
- "You will not be right simply because a large number of people momentarily agree with you."
- "True conservatism is only possible through knowledge and reason." Test it by results in **down markets**.

## 4. Compounding and realistic goals (Jan 1963 "The Joys of Compounding"; Jan 1965 "Our Goal")
- Small differences in rate become huge over decades — a few points over the index is "a very worthwhile achievement."
- Expect the market itself to return far less than a lucky recent period; plan for −20% to −40% years. "If a 20% or
  30% drop in the market value of your equity holdings ... is going to produce emotional or financial distress, you
  should simply avoid common stock type investments."
- Every manager should "state unequivocally what he is going to attempt to accomplish and how he proposes to measure"
  it. → Our habit: a stated hurdle (user: 15%) and implied-return math on every idea.

## 5. Concentration with arithmetic (Jan 1966 "Diversification")
- New Ground Rule: up to **40% in one security** when there is "an extremely high probability that our facts and
  reasoning are correct with a very low probability that anything could drastically change the underlying value."
- Size by **expectation and downside**, not comfort: two ideas with equal expected return differ if one has a 5% vs 1%
  chance of a very bad outcome.
- His sizing limit: keep tiny the chance that one position (or a correlated group) makes the **whole portfolio
  more than ten points worse** than the benchmark → `position_sizing` tool.
- Over-diversification ("the Noah School of Investing — two of everything") lowers expected return more than it
  lowers risk. New ideas must beat the current best idea to be added.
- Willing to accept bumpier relative results for a better long-run margin; never willing to risk **substantial
  permanent loss**. Borrowing kept small: "even five minutes is a long time if one's head is being held under water."

## 6. Patience in accumulation (1957; Jan 1967 "Private Owner")
- When buying, he wanted the stock to **do nothing or fall**; a rising price before a full position is a cost, not a win.
- Good ideas are rare ("a trickle has considerably more chance of drying up completely than a flow"), so use them
  intensively.

## 7. Quantitative vs qualitative (Oct 9, 1967) — the bridge to Munger/Nomad
- "The really big money tends to be made by investors who are right on qualitative decisions but ... the more sure
  money tends to be made on the obvious quantitative decisions."
- His biggest wins came from a "high-probability insight" on quality (the letters do not name the holding), even
  though he called himself a quantitative investor. This is the Nomad/Munger direction: great businesses, held long.

## 8. Circle of competence and temperament (Jan 1967; Oct 1967; 1969)
- "We will not go into businesses where technology which is away over my head is crucial to the investment decision."
- "If I can't understand something, I tend to forget it. Passing an opportunity which I don't understand ... doesn't
  bother me." (1969, on bonds)
- "I will not abandon a previous approach whose logic I understand ... even though it may mean foregoing large and
  apparently easy, profits." (Oct 1967)
- Rejects "fashion" investing where guessing market action overrides business value; when he had no first-class
  ideas he **closed the partnership** rather than "grope around, hoping to 'get lucky' with other people's money."
- Do not mix what *should* happen (socially, politically) with what *will* happen in decisions (1969).

## 9. Using Mr. Market (July 1966)
- A quote is an option to be used "if it gets silly enough in either direction," never a liability that forms your
  judgment. Graham's *Intelligent Investor* chapter on market fluctuations: "more investment importance than anything
  else that has been written."

## 10. Size
- Bigger capital hurts passive small-cap ideas, helps control situations; be honest with partners when size becomes
  a drag (Jan 1967, Oct 1967).

## How the agent applies this
1. Classify every idea: General (Private-Owner or Relative), Workout, or Control-like (activist/special situation).
2. State the yardstick and hurdle up front; judge over 3–5 years.
3. Margin of safety = gap between price and conservative value; size positions by expectation **and** the chance of
   a large permanent loss (`position_sizing`).
4. For event-driven ideas, compute the workout return and what breaks it (`workout_return`).
5. Stay inside the circle of competence; say "too hard" without embarrassment.
6. No market or macro forecasts as the basis of a decision; use price swings, don't follow them.


## CFA: Free cash flow valuation


Distilled in our own words from the CFA Institute Level II refresher reading *Free Cash Flow Valuation*
(2026 curriculum, reading RR_2026_L2V5R3). Formulas are standard finance; the reading itself is
copyrighted and not stored here. Add lessons from our own models at the bottom.

## 1. Pick the cash flow and match the rate

| | FCFF (to all capital providers) | FCFE (to common shareholders) |
|---|---|---|
| Discount at | WACC (market-value weights, after-tax cost of debt) | Required return on equity |
| Gives | Firm value → subtract debt (and preferred) → equity | Equity directly |
| Prefer when | Leverage is high or changing; FCFE is negative; control view | Capital structure is stable; minority view |

- FCFF/FCFE beat dividends when the company pays no dividend, pays far less than it could, or the
  investor takes a control view. They also beat dividends when cash flow tracks profit within a
  forecast horizon you trust.
- Dividends, buybacks and share issuance do **not** change FCFF or FCFE. They are uses of it.
  Borrowing changes FCFE (one-off) and, through the WACC, firm value only modestly.

## 2. Four ways to compute it (they must reconcile)

- FCFF = NI + non-cash charges + Interest × (1 − t) − FCInv − WCInv
- FCFF = CFO + Interest × (1 − t) − FCInv
- FCFF = EBIT × (1 − t) + Depreciation − FCInv − WCInv
- FCFF = EBITDA × (1 − t) + Depreciation × t − FCInv − WCInv
- FCFE = FCFF − Interest × (1 − t) + Net borrowing = NI + NCC − FCInv − WCInv + Net borrowing

Rules of thumb:
- Add back only *non-cash* charges. Subtract non-cash gains (e.g., unrealised gains on investments,
  which matters for Alphabet's SpaceX/Anthropic marks).
- Working capital excludes cash and short-term debt.
- Under IFRS, interest and dividends can sit in operating, investing or financing. Check where they
  are before starting from CFO.
- Stock compensation is a real cost. Keep it in operating costs, or count the dilution in the share count.
- **Never discount net income, EBIT, EBITDA or CFO as if they were free cash flow.** They double-count or
  ignore capex, working capital or taxes. Net income is a fair proxy only when capex ≈ depreciation
  and working capital is stable.

## 3. Forecasting from sales (the reading's preferred practical method)

1. Forecast sales growth and an after-tax operating margin (FCFF) or net margin (FCFE).
2. Split capex into **maintenance ≈ depreciation** (scales with the sales level) and **growth capex**.
3. Forecast growth capex and working capital as a **% of each sales increase**, using history:
   - Incremental FCInv rate = (Capex − Depreciation) ÷ Increase in sales
   - WCInv rate = Increase in working capital ÷ Increase in sales
4. FCFF = EBIT(1 − t) − (incremental FCInv rate + WCInv rate) × ΔSales
5. For FCFE with a target debt ratio DR: FCFE = NI − (1 − DR) × [(FCInv − Dep) + WCInv].

Why it matters: it ties reinvestment to growth automatically. When growth slows, reinvestment falls
and free cash flow rises. A fixed "capex = x% of revenue" does not do that and understates mature
cash flow.

## 4. Choosing the model

- **Single stage (Gordon):** value = CF₁ ÷ (r − g). Only for mature, stable companies, with g ≤ long-run nominal GDP.
- **Two stage:** high growth for n years, then stable. Either a constant growth in stage 1, or growth
  that declines through stage 1 to the sustainable rate.
- **Three stage:** high growth, a transition where growth fades (often linearly), then mature. Best for
  real companies whose cash flows are lumpy or still building toward a long runway.
- Pick the model from the company's characteristics: where it is in its life, how long its competitive
  advantage lasts, and how stable its reinvestment is.

## 5. Terminal value

- Usually 60–90%+ of the value, so it gets the most scrutiny.
- Gordon on next year's cash flow: TVₙ = CFₙ₊₁ ÷ (r − g). **The final year's reinvestment must already be
  steady-state.** If capex is still at growth-phase levels, set terminal reinvestment = g ÷ ROIC
  (terminal FCF = NOPAT × (1 + g) × (1 − g/ROIC)).
- Alternative: an exit multiple × the terminal metric. This is a market-based cross-check, not a substitute
  for cash flow.
- Report the terminal share of value and an r × g sensitivity grid every time.

## 6. Non-operating assets

- Value operating assets from operating cash flow, then **add non-operating assets separately**: excess cash,
  marketable and non-current investments, idle assets.
- Do not let their income leak into the operating cash flow (no double count). Alphabet: the $90B of
  marketable equity securities sit inside "cash and securities". Count them once, either inside net cash
  or as stakes.

## 7. Sensitivity and judgement

- Flex growth (stage-1 and terminal), the discount rate, margins and reinvestment rates. Show which input
  moves value most; that is where research time belongs.
- Compare value with price: overvalued, fairly valued or undervalued. Then solve the **implied return**
  (the discount rate that equates value to price) for an apples-to-apples hurdle comparison.
- ESG and other qualitative risks enter as explicit cash-flow, timing or probability adjustments, not as
  a vague discount-rate premium.

## 8. Checklist we run on every model

1. Is it FCFF at WACC or FCFE at cost of equity? Never mix.
2. Do the routes (NI, CFO, EBIT) reconcile for the last actual year?
3. Is maintenance vs growth capex separated, and reinvestment tied to the sales increase?
4. Is terminal reinvestment consistent with g and ROIC?
5. Are non-operating assets added once, and debt-like items (leases, pensions) subtracted?
6. Share count: dilution from stock compensation vs buybacks. Buybacks don't add value at fair prices.
7. Terminal share of value, r × g grid, implied return at today's price.

## 9. Lessons from our own models

- **Alphabet:** segment margins are after depreciation, so FCFF = NOPAT + D&A − capex − WCInv. We had
  left out WCInv; TPU systems inventory (built before revenue) is a real working-capital drain in
  2026–27. A Gordon terminal on a year with capex at 38% of revenue implies about a 7% ROIC on new
  capital. Keep it only as a stress view, and show the ROIC-consistent version alongside.
- **Costco:** incremental FCInv ≈ 13.7% of the sales increase, but working capital *releases* ≈ 14% of it
  (members and suppliers fund inventory). Growth is close to self-funding, so FCFE ≈ 95% of net income.
  A flat "capex = 2.5% of revenue" understated cash flow by about $3B a year. Use a three-stage model
  (long runway): the implied return at $1,009 is about 6.8%.


## CFA: Market multiples


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
