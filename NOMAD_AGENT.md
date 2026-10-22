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
| `dilution_risk` | Value per share if equity must be raised at low prices | MBIA (Jun 2008) |
| `moat_scorecard` | Weighted 0-100 grade, weakest link, red-flag penalties | |

The Python agent loads the subagent file as its system prompt, so editing that one file
changes both.

Tests: `python -m pytest tests`

Not financial advice.
