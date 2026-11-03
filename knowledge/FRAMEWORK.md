# How to think about an investment: the framework

This is the operating system the agent uses on **your** ideas and **your** portfolio. It is distilled from the
Nomad letters (Sleep & Zakaria), the Buffett Partnership and Berkshire letters, Munger, and the CFA valuation
readings. Those sources are used for **how to think**, not for what to buy: never favour a stock because Nomad or
Berkshire owned it; use their holdings only as worked examples of a principle. Full texts live in
`knowledge/*/text/` (searchable with `search_library`); lessons files: `knowledge/berkshire/LESSONS.md`,
`knowledge/buffett/partnership_letters.md`, `knowledge/cfa/*.md`.

Run the steps in order. Each step ends with a short written answer. If a step can't be answered, the idea goes in
the **too-hard pile** — that is a valid outcome.

---

## Step 0. Rules before any idea
- **Yardstick and hurdle first.** Your hurdle (15% a year) and the benchmark (an index fund). Judge over 3–5 years.
- **No macro or market forecasts** drive decisions. Focus on what should happen to the business, not when the stock
  moves. Price swings are opportunities to use, never instructions.
- **Circle of competence.** Can you explain how this business makes money and what could break it, in plain words?
  Knowing the boundary matters more than its size.
- **Write it down.** A thesis, the numbers that would prove it wrong, and a pre-mortem. Memory rewrites history.

## Step 1. Understand the business (one paragraph)
- Who pays, for what, why they choose it over the alternative, and how the company makes money on each unit.
- What does the business look like if it succeeds for 10–20 years (the **destination**)? What has to be true?
- Red flags: you can't describe the unit economics; success depends on a technology or credit judgment you can't make.

## Step 2. Durability: why it lasts (the moat)
Ask which engine the company runs, and whether it gets **stronger with size**:
- **Scale economics shared**: savings from scale go back to customers as lower prices → more volume → more scale.
  Size becomes an asset. Test: do prices/fees fall or value rise as volume grows? (`scale_economics_shared`)
- **Low-cost producer, brand, network, switching costs, regulation, owned distribution, culture of a thousand
  small decisions.** Many small advantages beat one big one.
- **Robustness ratio**: value given to customers and employees versus profit kept. High and rising = a moat being
  widened; falling = harvesting. (`robustness_ratio`)
- **Capital cycle**: high returns attract capital and competitors. Who is adding capacity, and what does that do to
  returns in five years?
- Classify: **great** (high returns, little capital to grow), **good** (good returns, capital-hungry), **gruesome**
  (grows, eats capital, earns little).
- Red flags: returns depend on a temporary shortage, a single product, or pricing customers resent.

## Step 3. Customers: why they stay
- **Want-to vs have-to** loyalty. Want-to (delight, value, habit, product improves) lasts; have-to (contracts,
  lock-in, switching pain) invites disruption and regulation. (`retention_quality`)
- Evidence: retention/renewal curves that flatten, net revenue retention, reviews, referral, price restraint.
- **Is the company entitled to its margins?** Would a well-informed customer agree the price is fair? Margins earned
  by giving more value last; margins rented from inertia or ignorance do not.
- **Cheap-intelligence test (today)**: if AI agents remove search costs and inertia, do customers still choose this?
  Advantages that survive: data, real-world assets, proximity, trust, scale, love of the product.

## Step 4. Unit economics and reinvestment
- **Owner earnings** = net income + depreciation and other non-cash charges − maintenance capex (− extra working
  capital). Separate maintenance from growth capex. (`owner_earnings`)
- **Hidden investment**: is the company spending through the P&L to grow (marketing, new stores, R&D)? What would
  it earn as a mature cash cow? (`hidden_investment`)
- **Incremental returns**: return on the capital it will invest next, not on the capital it has. Growth is only
  valuable when incremental ROIC exceeds the cost of capital.
- **Self-funding**: do customers or suppliers fund working capital? Does growth need outside money? (`dilution_risk`)
- **Maturity uplift**: young units (stores, cohorts, regions) earning below mature ones = profit still to come.
  (`maturity_uplift`)
- Persistence: are CAC, churn, contribution margin, revenue per unit stable or improving? (`unit_economics_persistence`)

## Step 5. Management and capital allocation
- **Owner orientation**: insider ownership, pay tied to per-share value over years, candor about mistakes.
- **$1 test**: has each dollar retained created at least a dollar of market value over five years?
  (`retained_earnings_test`)
- **Buybacks** only with ample cash and a material discount to conservatively calculated value; issue shares only
  when receiving equal value. (`buyback_check`)
- Watch for the **institutional imperative** (copying peers), empire building, acquisitions paid in cheap stock,
  and "thumb-sucking" (slow to fix mistakes).
- Culture: is cost-consciousness or customer obsession plan A, built in from the start, or a crisis response?

## Step 6. Value the business (mechanics)
- Value = cash that can be taken out over the business's life, discounted at your required return.
- Match cash flow to rate: **FCFF at WACC** (subtract debt) or **FCFE at cost of equity**. Reconcile FCF from net
  income, CFO and EBIT for the last year before forecasting. (`free_cash_flow`)
- **Forecast from sales**: margins, then growth capex and working capital as a % of each sales increase.
  Maintenance capex ≈ depreciation. When growth slows, reinvestment must fall.
- **Stages by life cycle**: mature → single stage; one step-down → two stages; long-runway compounder → three
  stages with a fade. Don't fade growth in year 3–5 just because models usually do (Sleep's warning).
  (`multistage_dcf`)
- **Terminal value**: reinvestment = g ÷ ROIC; report its share of value and a k × g grid.
- **Non-operating assets** (cash, stakes, investments) valued separately and counted once; subtract debt-like items.
- **Multiples are a cross-check**, on underlying/normalized EPS. Convert today's P/E into the perpetual growth it
  implies. Exit multiples must match the multiple your fundamentals justify at exit. (`multiples_valuation`)
- Normalized earnings are the most dangerous estimate — Buffett's Precision Castparts lesson.

## Step 7. Price versus value: what is the market assuming?
- **Read the price as a language**: what growth and duration does today's price imply? (`reverse_valuation`,
  `multiples_valuation`) Compare with your destination.
- Build **bear / base / bull** (and a severe tail) with probabilities; look at the distribution, not one number.
- **Expected return** over 5 years and hold-forever (the discount rate that equates value and price), versus your
  hurdle. Show where the return comes from: earnings growth, dividends/buybacks, multiple change.
- **Margin of safety** against permanent loss, not volatility.
- Price discipline both ways: a wonderful company at a fair price beats a fair company at a wonderful price; but
  "nothing at all conservative" about paying any multiple for quality.
- Typical opportunity pattern (Sleep): a great business priced as if it will fade soon or stop growing — the market
  pays for a cash cow and gives the runway away.

## Step 8. Size it (portfolio construction)
- Start from "what weight out of 100%?", not from 1%. Concentrate in your best ideas; over-diversifying lowers
  expected return more than it lowers risk.
- Size by **expected return and the chance of a large permanent loss**. Up to ~40% only when facts are near-certain
  and value can't be drastically impaired. Keep one position's bad case from dragging the whole portfolio more than
  ~10 points below the index. Treat correlated holdings as one. (`position_sizing`, `portfolio_review`)
- A new idea must beat your current best (risk-adjusted) to get capital. Cash is a fine placeholder.
- Little or no leverage: "even five minutes is a long time if one's head is being held under water."
- Event-driven ideas (mergers, spin-offs): compute the workout return and what breaks it. (`workout_return`)

## Step 9. Own it: monitoring, selling, mistakes
- Track the few **thesis drivers** (KPIs) that would prove you wrong; check them each quarter, ignore the rest.
- **Sell** when the thesis breaks, when price far exceeds value with a better use for the money, or when you find
  a clearly better idea. Don't sell a great compounder just because it looks "expensive" — errors of omission
  (selling Walmart, Amazon early; not buying) cost more than errors of commission.
- Fix mistakes fast; don't anchor on your purchase price or original analysis.

## Step 10. Check your own thinking (Munger's misjudgments)
Incentives (who benefits if I believe this?), social proof, authority, anchoring, commitment/consistency, vivid
recent news, overconfidence, envy, loss aversion, "man with a hammer". Invert: how would this lose money? Weigh
facts by how long they stay true — customers wanting lower prices is near-certain; next quarter's EPS is not.

---

## Templates

### One-page idea memo
1. Business in one paragraph, and the destination in 10–20 years.
2. Engine and moat (Step 2); great/good/gruesome; robustness.
3. Why customers stay; entitled to margins? cheap-intelligence test.
4. Owner earnings, incremental returns, self-funding, hidden investment.
5. Management and capital allocation.
6. Valuation: method, key assumptions, value range.
7. What the price implies; bear/base/bull with odds; expected 5-year and hold-forever return vs hurdle.
8. Suggested weight and why; what would make you add, trim or sell.
9. Pre-mortem: the most likely way this loses money.

### Portfolio review
For each holding: category (General / Workout / Control-like), thesis in one line, what the price implies, expected
5-year return, bad case and its odds, current weight. Then for the whole book: expected return vs hurdle,
concentration and correlated clusters, the weakest thesis, the best idea under-weighted, and the actions
(add / hold / trim / exit) with reasons. (`portfolio_review`)
