# Buffett Partnership Letters (1957–1970): lessons for the agent

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
