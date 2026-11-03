# Berkshire Hathaway letters (1977–2024): lessons for the agent

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
