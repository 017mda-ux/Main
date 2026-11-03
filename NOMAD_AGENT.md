# Nomad investment agent

A long-term business analyst built on the Nomad Investment Partnership letters (Nick Sleep &
Qais Zakaria, 2001-2014), applying their ideas to today's business models rather than copying
the letters.

It looks at every company through four questions:

1. **Which advantages can last?** Above all, "scale economics shared": does the company pass
   the savings from growing bigger to customers, so customers buy more and the gap with rivals
   widens? It also looks for many small, hard-to-copy advantages rather than one big one, and
   a simple structure that can keep growing.
2. **Why do customers stay?** Because they want to (prices keep falling, trust, habit, a fair
   fixed deal) or because they have to (contracts, lock-in, cancellation friction)?
3. **Is the product delighting customers?** Evidence from behaviour: customers spending more,
   word of mouth, little need for advertising, management that starts from the customer.
4. **Do the unit economics persist?** Returns on new investment and how long they last,
   self-funded versus rented growth, how young units mature, and earning power hidden by
   expensed growth spending.

It then writes the ten-year "destination", checks what today's price implies, tests dilution
risk, and runs a pre-mortem. The principles, with short attributed quotes, are in
`.claude/agents/nomad-investor.md`.

## Two ways to use it

**In Claude Code (no setup):** ask something like *"use the nomad-investor agent to analyse
Costco"*.

**As a standalone Python agent** (needs an Anthropic API key):

```bash
pip install -r requirements.txt
cp .env.example .env            # add ANTHROPIC_API_KEY
python nomad_cli.py memo "Duolingo"
python nomad_cli.py ask "Is AWS still sharing its scale economics?"
python nomad_cli.py chat
```

The Python agent uses web search for current numbers plus ten calculators
(`nomad/tools.py`), several taken straight from worked examples in the letters:

| Tool | What it answers | From the letters |
|---|---|---|
| `scale_economics_shared` | Are falling costs passed to customers (Sharer) or kept (Keeper / Harvester)? | |
| `robustness_ratio` | Customer + employee gains per dollar kept by shareholders, and the trend | Costco ~5:1, Geico ~1:1 (May 2005) |
| `retention_quality` | Does churn fall as customers age? Is loyalty earned or imposed? | |
| `unit_economics_persistence` | Which per-unit metrics are improving, stable or getting worse? | |
| `maturity_uplift` | Profit growth already built into young stores or cohorts | Costco store ages (Dec 2004) |
| `hidden_investment` | Earning power before discretionary growth spending vs market value | Amazon (Dec 2006) |
| `destination_analysis` | Where does reinvesting at a given return take the business? | |
| `reverse_valuation` | What growth does the price imply? Expected return from a discount to value | "Typical purchase" (Dec 2003) |
| `free_cash_flow` | FCFF/FCFE from NI, CFO, EBIT, EBITDA (cross-checked); incremental capex and working capital as % of sales increase | CFA L2 *Free Cash Flow Valuation* |
| `multistage_dcf` | Two/three-stage FCFF or FCFE DCF; ROIC-consistent terminal; non-operating assets; implied return; r × g grid | CFA L2 *Free Cash Flow Valuation* |
| `multiples_valuation` | Justified P/E, P/B, P/S, EV/EBITDA; perpetual growth implied by P/E; PEG; underlying/normalized EPS; peer mean/median/harmonic mean; EV build | CFA L2 *Market-Based Valuation* |
| `workout_return` | Merger/tender/liquidation: return if it closes, expected and annualised return, break-even probability | Buffett Partnership letters (work-outs) |
| `position_sizing` | Concentration check: bad-case drag on the portfolio vs index, 40% cap | Buffett Partnership letters (Jan 1966) |
| `owner_earnings` | Net income + D&A − maintenance capex; yield vs market cap; growth vs maintenance capex | Berkshire letters (1986) |
| `retained_earnings_test` | $1 of market value per $1 retained over five years | Berkshire letters (1983) |
| `buyback_check` | Buybacks only with ample funds and a material discount to conservative value | Berkshire letters (2011) |
| `dilution_risk` | Value per share if equity must be raised at low prices | MBIA (Jun 2008) |
| `moat_scorecard` | Weighted 0-100 grade, weakest link, red-flag penalties | |

The Python agent loads the subagent file as its system prompt, so editing that one file
changes both.

## Charlie Munger library

Both agents can draw on Munger's talks and writings from the
[Worldly Partners archive](https://worldlypartners.com/charlie-munger-archive/):

```bash
python scripts/fetch_munger_archive.py --dry-run   # list the PDFs found
python scripts/fetch_munger_archive.py             # download + extract text
```

This writes `knowledge/munger/text/*.txt` and `knowledge/munger/INDEX.md` (the PDFs themselves
are git-ignored). The Claude Code subagent searches the text with Grep; the Python agent uses the
`search_library` tool. Both quote exact passages and name the source document.

Tests: `python -m pytest tests`

Not financial advice.


## Letter libraries (full text, searchable)

Build once per machine from PDFs you own (text is git-ignored; INDEX.md files are committed):

```
python scripts/build_letter_libraries.py nomad     Full_Collection_Nomad_Letters_.pdf
python scripts/build_letter_libraries.py bpl       buffett-partnership-letters.pdf
python scripts/build_letter_libraries.py berkshire All-Berkshire-Hathaway-Letters.pdf
```

Then add Berkshire 2020–2024 with `python scripts/fetch_recent_berkshire.py` (GitHub mirror). `search_library` searches all of them (102 documents) and cites the letter and date.
