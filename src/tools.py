"""
Agent Tools — definitions (JSON schema) + Python implementations.

Tools available to the investment analyst agent:
  1. search_acquired_transcripts  — RAG search over all Acquired episodes
  2. list_acquired_episodes        — List indexed episodes
  3. analyze_seven_powers          — Hamilton Helmer's 7 Powers framework
  4. analyze_unit_economics        — Unit economics / LTV:CAC analysis
  5. compare_companies             — Side-by-side competitive comparison
  6. build_bear_bull_case          — Structured bear / bull thesis
  7. calculate_rule_of_40          — SaaS Rule of 40 / growth-adjusted metrics
"""

from __future__ import annotations

import json
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .vector_store import VectorStore


# ──────────────────────────────────────────────────────────────────────
#  Tool JSON schema definitions (fed to Claude)
# ──────────────────────────────────────────────────────────────────────

TOOL_DEFINITIONS = [
    {
        "name": "search_acquired_transcripts",
        "description": (
            "Semantic search over all Acquired podcast episode transcripts. "
            "Use this to find what Ben and David have said about a company, "
            "business model, competitive dynamic, or investment principle. "
            "Returns the most relevant transcript excerpts with episode metadata."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": (
                        "The search query. Be specific — e.g. "
                        "'Amazon flywheel unit economics', "
                        "'Costco membership model switching costs', "
                        "'network effects winner-take-all markets'."
                    ),
                },
                "top_k": {
                    "type": "integer",
                    "description": "Number of results to return (default 8, max 20).",
                    "default": 8,
                },
                "episode_filter": {
                    "type": "string",
                    "description": (
                        "Optional: restrict search to a specific episode slug "
                        "e.g. 'nvidia-2023' or 'amazon'."
                    ),
                },
            },
            "required": ["query"],
        },
    },
    {
        "name": "list_acquired_episodes",
        "description": (
            "List all Acquired podcast episodes that have been indexed in the "
            "knowledge base, with their titles and slugs. Use this to discover "
            "which companies / topics have been covered."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "filter": {
                    "type": "string",
                    "description": "Optional case-insensitive substring to filter titles.",
                }
            },
            "required": [],
        },
    },
    {
        "name": "analyze_seven_powers",
        "description": (
            "Score a company across Hamilton Helmer's 7 Powers framework "
            "(Scale Economies, Network Economies, Counter-Positioning, "
            "Switching Costs, Branding, Cornered Resource, Process Power). "
            "Returns a structured JSON analysis. "
            "Supply the evidence you have gathered from transcript searches "
            "and any other knowledge to produce the assessment."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "company": {
                    "type": "string",
                    "description": "Company name to analyse.",
                },
                "evidence": {
                    "type": "string",
                    "description": (
                        "Relevant evidence / context about the company — "
                        "paste in transcript excerpts or other notes here."
                    ),
                },
            },
            "required": ["company", "evidence"],
        },
    },
    {
        "name": "analyze_unit_economics",
        "description": (
            "Evaluate a company's unit economics, including LTV:CAC ratio, "
            "gross margin quality, payback period, and cohort retention dynamics. "
            "Works with whatever numbers you provide; estimates where data is absent."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "company": {"type": "string"},
                "metrics": {
                    "type": "object",
                    "description": (
                        "Known financial metrics as key-value pairs. "
                        "Examples: {'gross_margin_pct': 72, 'cac_usd': 350, "
                        "'ltv_usd': 2800, 'payback_months': 14, "
                        "'net_revenue_retention_pct': 118, 'churn_pct': 5}"
                    ),
                    "additionalProperties": True,
                },
                "context": {
                    "type": "string",
                    "description": "Any qualitative context (business model, segment, etc.).",
                },
            },
            "required": ["company"],
        },
    },
    {
        "name": "compare_companies",
        "description": (
            "Produce a structured competitive comparison table across key dimensions: "
            "moat type, revenue model, growth trajectory, capital intensity, "
            "management quality, and Acquired coverage depth."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "companies": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "List of 2–5 company names to compare.",
                    "minItems": 2,
                    "maxItems": 5,
                },
                "focus": {
                    "type": "string",
                    "description": (
                        "Optional focus area for the comparison, e.g. "
                        "'cloud infrastructure', 'consumer subscription', "
                        "'semiconductor supply chain'."
                    ),
                },
            },
            "required": ["companies"],
        },
    },
    {
        "name": "build_bear_bull_case",
        "description": (
            "Build a structured bear / bull investment thesis for a company. "
            "Organises key debates, risks, upside drivers, and a verdict "
            "grounded in Acquired's analytical principles."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "company": {"type": "string"},
                "context": {
                    "type": "string",
                    "description": "Evidence and context gathered from research.",
                },
                "investment_horizon": {
                    "type": "string",
                    "enum": ["1-year", "3-year", "5-year", "10-year"],
                    "description": "Time horizon for the investment thesis.",
                    "default": "5-year",
                },
            },
            "required": ["company", "context"],
        },
    },
    {
        "name": "calculate_rule_of_40",
        "description": (
            "Calculate the Rule of 40 score and growth-adjusted metrics for a "
            "software / SaaS company. Also computes EV/NTM Revenue multiple at "
            "various Rule of 40 benchmarks for valuation context."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "company": {"type": "string"},
                "revenue_growth_pct": {
                    "type": "number",
                    "description": "YoY revenue growth in percent (e.g. 28 for 28%).",
                },
                "fcf_margin_pct": {
                    "type": "number",
                    "description": "Free cash flow margin in percent (can be negative).",
                },
                "ev_revenue_multiple": {
                    "type": "number",
                    "description": "Optional EV / NTM Revenue multiple for valuation context.",
                },
                "gross_margin_pct": {
                    "type": "number",
                    "description": "Optional gross margin % for quality-adjusted scoring.",
                },
            },
            "required": ["company", "revenue_growth_pct", "fcf_margin_pct"],
        },
    },
]


# ──────────────────────────────────────────────────────────────────────
#  Tool implementations (called by the agent executor)
# ──────────────────────────────────────────────────────────────────────

def execute_tool(name: str, tool_input: dict, vector_store: "VectorStore") -> str:
    """Dispatch a tool call and return the result as a string."""
    dispatch = {
        "search_acquired_transcripts": _search_transcripts,
        "list_acquired_episodes": _list_episodes,
        "analyze_seven_powers": _analyze_seven_powers,
        "analyze_unit_economics": _analyze_unit_economics,
        "compare_companies": _compare_companies,
        "build_bear_bull_case": _build_bear_bull_case,
        "calculate_rule_of_40": _calculate_rule_of_40,
    }
    fn = dispatch.get(name)
    if fn is None:
        return f"Error: unknown tool '{name}'"
    try:
        return fn(tool_input, vector_store)
    except Exception as exc:  # noqa: BLE001
        return f"Tool error in '{name}': {exc}"


# ──────────────────────────────────────────────────────────────────────
#  Individual tool functions
# ──────────────────────────────────────────────────────────────────────

def _search_transcripts(inp: dict, vs: "VectorStore") -> str:
    query = inp["query"]
    top_k = min(int(inp.get("top_k", 8)), 20)
    episode_filter = inp.get("episode_filter")

    where = {"slug": episode_filter} if episode_filter else None
    results = vs.search(query, top_k=top_k, where=where)

    if not results:
        return "No results found. The knowledge base may be empty — run `python main.py build-kb` first."

    lines = [f"## Search results for: '{query}'\n"]
    for i, r in enumerate(results, 1):
        lines.append(
            f"### [{i}] {r['title']} (relevance: {r['score']:.3f})\n"
            f"**Episode:** {r['slug']}  |  chunk {r['chunk_index']}\n\n"
            f"{r['text']}\n"
        )
    return "\n---\n".join(lines)


def _list_episodes(inp: dict, vs: "VectorStore") -> str:
    slugs = vs.get_episode_slugs()
    if not slugs:
        return "Knowledge base is empty. Run `python main.py build-kb` to index transcripts."

    filt = (inp.get("filter") or "").lower()
    filtered = [s for s in slugs if filt in s.lower()] if filt else slugs

    lines = [f"## Indexed Acquired episodes ({len(filtered)} shown)\n"]
    for s in filtered:
        lines.append(f"- `{s}`")
    return "\n".join(lines)


def _analyze_seven_powers(inp: dict, _vs: "VectorStore") -> str:
    company = inp["company"]
    evidence = inp.get("evidence", "")

    # This is a structured prompt scaffold; Claude will fill in the substance
    template = {
        "company": company,
        "framework": "Hamilton Helmer's 7 Powers",
        "powers": {
            "scale_economies": {
                "description": "Fixed costs spread over larger volume → declining unit costs",
                "signals": ["High fixed-cost base", "Market share advantages", "Infrastructure moats"],
            },
            "network_economies": {
                "description": "Product value increases as more participants join",
                "signals": ["Multi-sided platforms", "Data network effects", "Viral adoption"],
            },
            "counter_positioning": {
                "description": "New business model incumbents can't copy without self-disruption",
                "signals": ["Asymmetric cost structure", "Incumbent channel conflict", "Disruptive pricing"],
            },
            "switching_costs": {
                "description": "Customers incur pain/cost/risk when leaving",
                "signals": ["Deep workflow integration", "Data lock-in", "Ecosystem entanglement"],
            },
            "branding": {
                "description": "Durable premium pricing power via trusted identity",
                "signals": ["Price premium vs. peers", "Emotional resonance", "Aspirational positioning"],
            },
            "cornered_resource": {
                "description": "Preferential access to a key asset others can't replicate",
                "signals": ["IP / patents", "Exclusive talent", "Proprietary data", "Regulatory licenses"],
            },
            "process_power": {
                "description": "Embedded organisational capability delivering superior output",
                "signals": ["Toyota Production System-style culture", "Operational excellence compounding over decades"],
            },
        },
        "instruction": (
            f"Using the evidence below, score {company} on each of the 7 Powers "
            f"(0 = absent, 1 = weak, 2 = moderate, 3 = strong). "
            f"For each power: quote specific evidence, assign a score, and explain "
            f"the competitive barrier it creates (or why it's absent).\n\n"
            f"Evidence:\n{evidence}"
        ),
    }
    return json.dumps(template, indent=2)


def _analyze_unit_economics(inp: dict, _vs: "VectorStore") -> str:
    company = inp["company"]
    metrics = inp.get("metrics", {})
    context = inp.get("context", "")

    ltv = metrics.get("ltv_usd")
    cac = metrics.get("cac_usd")
    gm = metrics.get("gross_margin_pct")
    nrr = metrics.get("net_revenue_retention_pct")
    churn = metrics.get("churn_pct")
    payback = metrics.get("payback_months")

    computed: dict = {}
    if ltv and cac and cac > 0:
        computed["ltv_cac_ratio"] = round(ltv / cac, 2)
        computed["ltv_cac_quality"] = (
            "Excellent (>3x)" if ltv / cac >= 3 else
            "Good (2-3x)" if ltv / cac >= 2 else
            "Below benchmark (<2x)"
        )
    if gm and churn:
        implied_ltv = (gm / 100) / (churn / 100)
        computed["implied_ltv_multiple_of_acv"] = round(implied_ltv, 2)
    if nrr:
        computed["nrr_quality"] = (
            "World-class (>120%)" if nrr >= 120 else
            "Strong (110-120%)" if nrr >= 110 else
            "Good (100-110%)" if nrr >= 100 else
            "Concerning (<100%)"
        )

    return json.dumps(
        {
            "company": company,
            "provided_metrics": metrics,
            "computed": computed,
            "context": context,
            "instruction": (
                f"Provide a full unit economics assessment for {company}. "
                "For each metric above: interpret the number, benchmark it against "
                "best-in-class peers (Snowflake NRR >160%, ServiceNow payback <18m, etc.), "
                "explain what drives it, and identify the risks / leverage points. "
                "Conclude with a unit economics quality rating: "
                "Exceptional / Strong / Average / Weak, with key swing factors."
            ),
        },
        indent=2,
    )


def _compare_companies(inp: dict, _vs: "VectorStore") -> str:
    companies = inp["companies"]
    focus = inp.get("focus", "general")

    dimensions = [
        "Primary moat type (7 Powers)",
        "Revenue model & pricing power",
        "Gross margin profile",
        "Growth trajectory (past 3 years + outlook)",
        "Capital intensity & FCF conversion",
        "Management quality & capital allocation track record",
        "TAM & penetration",
        "Key risk / bear case",
        "Acquired episode coverage",
        "Overall competitive positioning verdict",
    ]

    return json.dumps(
        {
            "companies": companies,
            "focus": focus,
            "dimensions": dimensions,
            "instruction": (
                f"Build a detailed comparison table for {companies} "
                f"across all dimensions above. "
                f"Where Acquired has covered a company, reference specific "
                f"insights from the podcast. "
                f"Conclude with a ranked order of investment attractiveness "
                f"with reasoning."
            ),
        },
        indent=2,
    )


def _build_bear_bull_case(inp: dict, _vs: "VectorStore") -> str:
    company = inp["company"]
    context = inp.get("context", "")
    horizon = inp.get("investment_horizon", "5-year")

    return json.dumps(
        {
            "company": company,
            "horizon": horizon,
            "context": context,
            "structure": {
                "bull_case": {
                    "thesis_statement": "...",
                    "drivers": ["driver 1", "driver 2", "driver 3"],
                    "key_assumptions": ["assumption 1", "assumption 2"],
                    "upside_scenario": "...",
                },
                "bear_case": {
                    "thesis_statement": "...",
                    "risks": ["risk 1", "risk 2", "risk 3"],
                    "key_assumptions": ["assumption 1", "assumption 2"],
                    "downside_scenario": "...",
                },
                "key_debates": ["debate 1", "debate 2", "debate 3"],
                "verdict": "...",
            },
            "instruction": (
                f"Complete the bear/bull case structure above for {company} "
                f"over a {horizon} horizon. "
                f"Ground every point in evidence — use Acquired insights where "
                f"available, plus first-principles business analysis. "
                f"The verdict should give a clear recommendation with conviction level "
                f"(High / Medium / Low) and the single most important factor to monitor."
            ),
        },
        indent=2,
    )


def _calculate_rule_of_40(inp: dict, _vs: "VectorStore") -> str:
    company = inp["company"]
    growth = float(inp["revenue_growth_pct"])
    fcf_margin = float(inp["fcf_margin_pct"])
    ev_rev = inp.get("ev_revenue_multiple")
    gm = inp.get("gross_margin_pct")

    rule_of_40 = round(growth + fcf_margin, 1)

    quality = (
        "Elite (>60)" if rule_of_40 >= 60 else
        "Strong (40-60)" if rule_of_40 >= 40 else
        "Below benchmark (20-40)" if rule_of_40 >= 20 else
        "Needs improvement (<20)"
    )

    # Rough EV/Revenue fair-value anchor based on Rule of 40
    # Empirical SaaS comps: ~0.5x per Rule-of-40 point at 20% discount rate
    implied_multiple = round(rule_of_40 * 0.5, 1)
    premium_discount = None
    if ev_rev:
        premium_discount = round(((ev_rev - implied_multiple) / implied_multiple) * 100, 1)

    # Gross-margin-adjusted score (Bessemer Venture Partners variant)
    gm_adjusted = None
    if gm:
        gm_adjusted = round((growth * (gm / 100)) + fcf_margin, 1)

    result = {
        "company": company,
        "inputs": {
            "revenue_growth_pct": growth,
            "fcf_margin_pct": fcf_margin,
            "gross_margin_pct": gm,
            "ev_revenue_multiple": ev_rev,
        },
        "rule_of_40_score": rule_of_40,
        "quality_rating": quality,
        "implied_ev_revenue_multiple": implied_multiple,
        "current_multiple_premium_discount_pct": premium_discount,
        "gm_adjusted_rule_of_40": gm_adjusted,
        "instruction": (
            f"Interpret these Rule of 40 metrics for {company}. "
            f"Compare to best-in-class benchmarks (Veeva ~70, "
            f"Palantir ~35, Snowflake historically >100 but FCF-negative). "
            f"Discuss quality of growth (organic vs. M&A, "
            f"NRR contribution, land-and-expand). "
            f"Comment on valuation if a multiple was provided. "
            f"Note any caveats (e.g. stock-based compensation distorting FCF)."
        ),
    }
    return json.dumps(result, indent=2)
