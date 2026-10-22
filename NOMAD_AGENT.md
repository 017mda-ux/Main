# Nomad investment agent

A long-term business analyst built on ideas from the Nomad Investment Partnership letters
(Nick Sleep & Qais Zakaria, 2001-2013), applied to today's business models rather than
copied from the letters.

It looks at every company through four questions:

1. **Which advantages can last?** Above all: does the company share its scale savings with
   customers (lower prices, better product) or keep them?
2. **Why do customers stay?** Because they want to (the product keeps getting better or
   cheaper, trust, habit) or because they have to (contracts, lock-in, cancellation friction)?
3. **Is the product delighting customers?** Evidence from behaviour (repeat use, referrals,
   low marketing spend) rather than company claims.
4. **Do the unit economics persist?** Per-unit profit, acquisition cost, payback and return on
   new investment, judged by their trend across years, not one good quarter.

It then sketches where the business could be in ten years, checks what growth today's price
implies, and runs a pre-mortem.

## Two ways to use it

**In Claude Code (no setup):** the subagent is at `.claude/agents/nomad-investor.md`. Ask
something like *"use the nomad-investor agent to analyse Costco"*.

**As a standalone Python agent** (needs an Anthropic API key):

```bash
pip install -r requirements.txt
cp .env.example .env            # add ANTHROPIC_API_KEY
python nomad_cli.py memo "Duolingo"
python nomad_cli.py ask "Is AWS still sharing its scale economies?"
python nomad_cli.py chat
```

The Python agent uses web search for current numbers plus six calculators
(`nomad/tools.py`):

| Tool | What it answers |
|---|---|
| `scale_economies_shared` | Are falling costs passed to customers (Sharer) or kept (Keeper / Harvester)? |
| `retention_quality` | Does churn fall as customers age? Is loyalty earned or imposed? |
| `unit_economics_persistence` | Which per-unit metrics are improving, stable or getting worse? |
| `destination_analysis` | Where does reinvesting at a given return take the business in N years? |
| `reverse_valuation` | What growth does today's price already assume? |
| `moat_scorecard` | Weighted 0-100 grade, weakest link, and red-flag penalties |

The principles live in one place (the subagent file); the Python agent loads the same text
as its system prompt, so editing that file changes both.

Tests: `python -m pytest tests`

Not financial advice.
