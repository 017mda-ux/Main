# Free cash flow valuation: working notes

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
