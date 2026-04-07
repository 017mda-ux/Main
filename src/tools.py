"""
Agent Tools — definitions (JSON schema) + Python implementations.

Tools available to the strategy & investment analyst agent:
  1.  search_acquired_transcripts  — RAG search over all Acquired episodes
  2.  list_acquired_episodes        — List indexed episodes
  3.  analyze_seven_powers          — Hamilton Helmer's 7 Powers framework
  4.  analyze_unit_economics        — Unit economics / LTV:CAC analysis
  5.  compare_companies             — Side-by-side competitive comparison
  6.  build_bear_bull_case          — Structured bear / bull thesis
  7.  calculate_rule_of_40          — SaaS Rule of 40 / growth-adjusted metrics
  8.  analyze_moat_taxonomy         — Reaction Wheel taxonomy of moats
  9.  analyze_aggregation_theory    — Ben Thompson's Aggregation Theory assessment
  10. analyze_marketing_laws        — 22 Immutable Laws of Marketing audit
  11. assess_leadership_health      — 15 Commitments of Conscious Leadership scorecard
  12. analyze_tps_excellence        — Toyota Production System / Process Power audit
  13. apply_munger_models           — Munger mental models cross-check
  14. assess_pmf_quantitative       — Tribe Capital quantitative PMF framework
  15. search_paul_graham_essays     — RAG search over Paul Graham's essays
  16. list_paul_graham_essays       — List all indexed PG essays
  17. apply_paul_graham_thinking    — Apply PG frameworks (growth, founder mode, schlep, etc.)
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
    # ── New framework tools ────────────────────────────────────────────
    {
        "name": "analyze_moat_taxonomy",
        "description": (
            "Assess a company's competitive moats using the Reaction Wheel "
            "Taxonomy of Moats — a richer classification than 7 Powers alone. "
            "Covers Process/Knowledge, Cultural, Network Effect (direct/indirect/data/protocol), "
            "Switching Cost (financial/procedural/relational/risk), Cost (scale/supply/geographic), "
            "and Risk/Uncertainty moats. Returns a structured breadth-and-depth assessment."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "company": {"type": "string", "description": "Company name to analyse."},
                "evidence": {
                    "type": "string",
                    "description": "Relevant evidence / context — paste in transcript excerpts or research notes.",
                },
                "industry": {
                    "type": "string",
                    "description": "Optional: industry context to calibrate benchmarks (e.g. 'cloud software', 'consumer marketplace').",
                },
            },
            "required": ["company", "evidence"],
        },
    },
    {
        "name": "analyze_aggregation_theory",
        "description": (
            "Apply Ben Thompson's Aggregation Theory to assess whether a company "
            "is an Aggregator (owns the demand relationship, commoditises suppliers) "
            "or a Supplier (at risk of commoditisation). Classifies the tier "
            "(Tier 1: own supply; Tier 2: some supply ownership; Tier 3: pure aggregator), "
            "identifies the demand relationship, and assesses long-term value capture dynamics."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "company": {"type": "string"},
                "business_model_description": {
                    "type": "string",
                    "description": "Brief description of how the business works — who are the suppliers, who are the end users, and how does the company sit between them?",
                },
                "evidence": {
                    "type": "string",
                    "description": "Evidence from transcripts or research about platform dynamics, supplier relationships, and demand-side network effects.",
                },
            },
            "required": ["company", "business_model_description"],
        },
    },
    {
        "name": "analyze_marketing_laws",
        "description": (
            "Audit a company's marketing strategy against Al Ries & Jack Trout's "
            "22 Immutable Laws of Marketing. Identifies which laws the company is "
            "mastering (building lasting position) and which it is violating "
            "(eroding its positioning). Returns a laws-by-category analysis with "
            "strategic implications and recommendations."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "company": {"type": "string"},
                "brand_and_products": {
                    "type": "string",
                    "description": "Description of the company's main brands, product lines, and current market positioning.",
                },
                "evidence": {
                    "type": "string",
                    "description": "Evidence about the company's marketing strategy, brand history, and competitive positioning.",
                },
                "focus_laws": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Optional: specific law names to focus on, e.g. ['Law of Line Extension', 'Law of Focus'].",
                },
            },
            "required": ["company", "brand_and_products"],
        },
    },
    {
        "name": "assess_leadership_health",
        "description": (
            "Assess the organisational leadership health of a company using "
            "the 15 Commitments of Conscious Leadership framework. "
            "Identifies signals of Above-the-Line leadership (radical responsibility, "
            "curiosity, candor, integrity) vs. Below-the-Line patterns (blame culture, "
            "defensiveness, gossip, scarcity mindset). Scores the C-suite and "
            "surfaces the investment implications."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "company": {"type": "string"},
                "leadership_evidence": {
                    "type": "string",
                    "description": "Evidence about leadership culture — earnings call tone, CEO interviews, Glassdoor signals, employee reviews, management turnover, public statements.",
                },
                "key_leaders": {
                    "type": "string",
                    "description": "Optional: names and roles of key leaders to assess (CEO, CFO, founders, etc.).",
                },
            },
            "required": ["company", "leadership_evidence"],
        },
    },
    {
        "name": "analyze_tps_excellence",
        "description": (
            "Evaluate a company's operational excellence through the lens of the "
            "Toyota Production System (TPS) — the canonical model of Process Power. "
            "Assesses evidence of Just-In-Time, Jidoka (built-in quality), Kaizen "
            "culture, waste elimination (7 Muda), Heijunka (levelling), and visual "
            "management. Surfaces whether the company has durable Process Power "
            "or accumulated operational waste."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "company": {"type": "string"},
                "operational_evidence": {
                    "type": "string",
                    "description": "Evidence about operations — supply chain design, manufacturing/engineering culture, incident response, deployment practices, inventory management, defect rates, continuous improvement programs.",
                },
                "industry": {
                    "type": "string",
                    "description": "Industry context to calibrate TPS analogues (e.g. 'automotive', 'cloud software', 'e-commerce fulfilment', 'semiconductor fab').",
                },
            },
            "required": ["company", "operational_evidence"],
        },
    },
    {
        "name": "apply_munger_models",
        "description": (
            "Apply Charlie Munger's Worldly Wisdom mental model latticework to a "
            "company or investment question. Runs through key models: incentive analysis, "
            "inversion, opportunity cost, compounding dynamics, psychological biases at play, "
            "circle of competence check, and margin of safety assessment. "
            "Forces multi-disciplinary thinking before forming a final view."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "subject": {
                    "type": "string",
                    "description": "Company, investment thesis, or strategic question to analyse.",
                },
                "context": {
                    "type": "string",
                    "description": "Relevant facts, evidence, and preliminary views about the subject.",
                },
                "primary_question": {
                    "type": "string",
                    "description": "The core question you are trying to answer (e.g. 'Is this a durable business?', 'Should we invest at this valuation?', 'What destroys this business?').",
                },
                "models_to_emphasise": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Optional: specific Munger models to apply with extra rigour, e.g. ['inversion', 'incentive analysis', 'compounding'].",
                },
            },
            "required": ["subject", "context", "primary_question"],
        },
    },
    {
        "name": "assess_pmf_quantitative",
        "description": (
            "Evaluate product-market fit using Tribe Capital's quantitative PMF "
            "framework. Analyses retention curves, engagement metrics (DAU/MAU), "
            "Quick Ratio, NRR, payback period, and organic growth share. "
            "Classifies the company on the PMF spectrum: "
            "Pre-PMF → Early PMF → Strong PMF → Escape Velocity. "
            "Works with whatever metrics are available — estimates benchmarks where data is missing."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "company": {"type": "string"},
                "product_type": {
                    "type": "string",
                    "enum": ["consumer_social", "saas_b2b", "marketplace", "fintech", "ecommerce", "other"],
                    "description": "Product type to calibrate PMF benchmarks correctly.",
                },
                "retention_metrics": {
                    "type": "object",
                    "description": "Known retention data as key-value pairs, e.g. {'d1': 60, 'd7': 40, 'd30': 25, 'd90': 18, 'd365': 12, 'logo_retention_12m': 85}.",
                    "additionalProperties": True,
                },
                "engagement_metrics": {
                    "type": "object",
                    "description": "Engagement data, e.g. {'dau_mau_ratio': 0.45, 'sessions_per_day': 3.2, 'nps': 52}.",
                    "additionalProperties": True,
                },
                "growth_metrics": {
                    "type": "object",
                    "description": "Growth quality data, e.g. {'quick_ratio': 3.8, 'nrr_pct': 118, 'payback_months': 16, 'organic_pct': 40, 'viral_coefficient': 0.3}.",
                    "additionalProperties": True,
                },
                "context": {
                    "type": "string",
                    "description": "Qualitative context about the product and its market.",
                },
            },
            "required": ["company", "product_type"],
        },
    },
    # ── Paul Graham Essay Tools ─────────────────────────────────────
    {
        "name": "search_paul_graham_essays",
        "description": (
            "Semantic search over Paul Graham's essays (paulgraham.com). "
            "Use this to retrieve PG's thinking on: startups, growth, founder quality, "
            "default alive/dead, schlep blindness, doing things that don't scale, "
            "frightening ambition, determination, wealth creation, and more. "
            "Returns the most relevant essay excerpts with title and URL."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": (
                        "What to search for. Be specific — e.g. "
                        "'default alive startup survival', "
                        "'schlep blindness unsexy work moat', "
                        "'growth rate startup definition', "
                        "'founder mode vs manager mode', "
                        "'do things that don\\'t scale early customers'."
                    ),
                },
                "top_k": {
                    "type": "integer",
                    "description": "Number of results to return (default 6, max 15).",
                    "default": 6,
                },
            },
            "required": ["query"],
        },
    },
    {
        "name": "list_paul_graham_essays",
        "description": (
            "List all Paul Graham essays that have been indexed in the knowledge base. "
            "Use this to discover which essays are available before searching."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "filter": {
                    "type": "string",
                    "description": "Optional case-insensitive substring to filter essay titles.",
                },
            },
            "required": [],
        },
    },
    {
        "name": "apply_paul_graham_thinking",
        "description": (
            "Apply Paul Graham's key frameworks to analyse a company or startup. "
            "Covers: Growth Rate Test, Default Alive/Dead, Founder Mode, Schlep Blindness, "
            "Frighteningly Ambitious ideas, Do Things That Don't Scale, "
            "Relentlessly Resourceful test, Power Law / Black Swan Farming, "
            "Wealth Creation vs. Extraction, and the Be Good filter. "
            "Produces an integrated PG-lens verdict on the company."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "company": {
                    "type": "string",
                    "description": "Company or startup name to analyse.",
                },
                "context": {
                    "type": "string",
                    "description": "Evidence, financials, and background about the company.",
                },
                "stage": {
                    "type": "string",
                    "enum": ["early_startup", "growth_stage", "public_company", "any"],
                    "description": "Company stage — calibrates which PG frameworks apply most.",
                    "default": "any",
                },
                "focus_frameworks": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": (
                        "Optional: limit to specific PG frameworks. "
                        "Options: 'growth_rate', 'default_alive', 'founder_mode', "
                        "'schlep_blindness', 'frighteningly_ambitious', "
                        "'do_things_that_dont_scale', 'relentlessly_resourceful', "
                        "'power_law', 'wealth_creation', 'be_good'."
                    ),
                },
            },
            "required": ["company", "context"],
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
        # Framework tools
        "analyze_moat_taxonomy": _analyze_moat_taxonomy,
        "analyze_aggregation_theory": _analyze_aggregation_theory,
        "analyze_marketing_laws": _analyze_marketing_laws,
        "assess_leadership_health": _assess_leadership_health,
        "analyze_tps_excellence": _analyze_tps_excellence,
        "apply_munger_models": _apply_munger_models,
        "assess_pmf_quantitative": _assess_pmf_quantitative,
        # Paul Graham tools
        "search_paul_graham_essays": _search_pg_essays,
        "list_paul_graham_essays": _list_pg_essays,
        "apply_paul_graham_thinking": _apply_paul_graham_thinking,
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


def _calculate_rule_of_40(inp: dict, _vs: "VectorStore") -> str:  # noqa: C901
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


# ──────────────────────────────────────────────────────────────────────
#  New framework tool implementations
# ──────────────────────────────────────────────────────────────────────

def _analyze_moat_taxonomy(inp: dict, _vs: "VectorStore") -> str:
    company = inp["company"]
    evidence = inp.get("evidence", "")
    industry = inp.get("industry", "general")

    scaffold = {
        "company": company,
        "industry": industry,
        "framework": "Reaction Wheel Taxonomy of Moats",
        "moat_categories": {
            "process_knowledge": {
                "description": "Superior operational systems and tacit organisational know-how that compounds over time",
                "sub_types": ["Documented process advantage", "Tacit knowledge / organisational memory", "R&D compounding"],
                "score": None,
            },
            "cultural": {
                "description": "Mission-driven talent density and values alignment attracting best people",
                "sub_types": ["Mission clarity", "Values-driven hiring", "Retention and engagement"],
                "score": None,
            },
            "network_effects": {
                "description": "Value increases as more participants join",
                "sub_types": ["Direct (same-side)", "Indirect (cross-side platform)", "Data (ML flywheel)", "Protocol (interoperability standard)"],
                "score": None,
            },
            "switching_costs": {
                "description": "Pain a customer endures to leave",
                "sub_types": ["Financial (hard cost to switch)", "Procedural (relearning / retraining)", "Relational (relationship loss)", "Risk-based (fear of failure)"],
                "score": None,
            },
            "cost_advantages": {
                "description": "Structural cost advantages vs. competitors",
                "sub_types": ["Scale economies", "Proprietary supply access", "Geographic density / last-mile advantage"],
                "score": None,
            },
            "risk_uncertainty": {
                "description": "Barriers rooted in regulatory, compliance, or certification complexity",
                "sub_types": ["Regulatory licenses", "Compliance moats", "Certification requirements", "Safety / liability barriers"],
                "score": None,
            },
        },
        "scoring_guide": "Score each category 0 (absent) → 3 (strong). Assess both BREADTH (how many categories) and DEPTH (how hard each is to replicate).",
        "instruction": (
            f"Using the evidence below, complete the moat taxonomy for {company}. "
            f"For each category: score it 0-3, cite specific evidence, name the primary sub-type, "
            f"and assess durability (years to replicate by a well-funded competitor). "
            f"Conclude with: (1) the single strongest moat, (2) the most vulnerable moat, "
            f"and (3) an overall moat breadth rating (Wide / Narrow / No Moat).\n\nEvidence:\n{evidence}"
        ),
    }
    return json.dumps(scaffold, indent=2)


def _analyze_aggregation_theory(inp: dict, _vs: "VectorStore") -> str:
    company = inp["company"]
    description = inp["business_model_description"]
    evidence = inp.get("evidence", "")

    scaffold = {
        "company": company,
        "framework": "Ben Thompson's Aggregation Theory",
        "theory_summary": (
            "Aggregators win by owning the demand relationship and commoditising suppliers. "
            "Value flows to whoever controls the end-user relationship at zero marginal cost of distribution."
        ),
        "tiers": {
            "tier_1": "Owns supply AND demand (e.g. Netflix — owns content)",
            "tier_2": "Owns some supply, aggregates rest (e.g. Amazon 1P + 3P marketplace)",
            "tier_3": "Pure demand aggregator — zero supply ownership (e.g. Google, Uber, Airbnb)",
        },
        "analysis_dimensions": {
            "demand_relationship": "Does the company own the end-user relationship? How sticky is it?",
            "supplier_leverage": "Can suppliers reach users without this aggregator? What is their outside option?",
            "marginal_cost": "What is the marginal cost of serving one more user? Approaching zero?",
            "commoditisation_dynamic": "Is the aggregator commoditising suppliers, or vice versa?",
            "network_effect_direction": "Does more demand attract more/better supply, which attracts more demand?",
            "regulatory_exposure": "Does aggregator power attract antitrust or regulatory scrutiny?",
            "counter_positioning": "Can incumbents copy this model without destroying their own supply relationships?",
        },
        "business_model": description,
        "instruction": (
            f"Apply Aggregation Theory to {company} using the evidence below. "
            f"Determine: (1) Is {company} an Aggregator or a Supplier? (2) Which tier? "
            f"(3) Who currently holds the demand relationship — and is it growing stronger or weaker? "
            f"(4) What is the long-run value capture trajectory? "
            f"(5) What is the key strategic risk (regulatory, new aggregator, supplier revolt)?\n\nEvidence:\n{evidence}"
        ),
    }
    return json.dumps(scaffold, indent=2)


def _analyze_marketing_laws(inp: dict, _vs: "VectorStore") -> str:
    company = inp["company"]
    brand_info = inp["brand_and_products"]
    evidence = inp.get("evidence", "")
    focus_laws = inp.get("focus_laws", [])

    laws = {
        "leadership": "Better to be first than better. Leading brand gets 2× share of #2.",
        "category": "If you can't be first in a category, create a new one you can lead.",
        "the_mind": "Being first in the mind beats being first in the marketplace.",
        "perception": "Marketing is a battle of perceptions, not products.",
        "focus": "The most powerful concept is owning one word in the prospect's mind.",
        "exclusivity": "Two companies cannot own the same word in the prospect's mind.",
        "the_ladder": "Strategy depends on which rung of the ladder you occupy.",
        "duality": "Every market becomes a two-horse race long-term.",
        "the_opposite": "If you're shooting for #2, your strategy is defined by the leader.",
        "division": "Categories divide over time — new sub-categories emerge.",
        "perspective": "Marketing effects play out over years, not quarters.",
        "line_extension": "Extending a brand name almost always backfires.",
        "sacrifice": "You must give something up to gain a strong position.",
        "attributes": "For every attribute, there's an opposite effective attribute to own.",
        "candor": "Admitting a negative earns you a positive in the prospect's mind.",
        "singularity": "Only one move produces substantial results in any situation.",
        "unpredictability": "You can't predict the future — build flexible plans.",
        "success": "Success leads to arrogance; arrogance leads to failure.",
        "failure": "Expect and accept failure — fail fast, learn fast.",
        "hype": "The situation is often the opposite of how the press portrays it.",
        "acceleration": "Build on trends, not fads.",
        "resources": "Without adequate funding, a great idea won't get off the ground.",
    }

    active_laws = (
        {k: v for k, v in laws.items() if any(fl.lower() in k for fl in focus_laws)}
        if focus_laws else laws
    )

    scaffold = {
        "company": company,
        "brand_and_products": brand_info,
        "framework": "22 Immutable Laws of Marketing — Ries & Trout",
        "laws_reference": active_laws,
        "instruction": (
            f"Audit {company}'s marketing strategy against the 22 Immutable Laws above. "
            f"For each relevant law: (1) Is {company} mastering or violating it? "
            f"(2) Provide specific evidence. (3) State the strategic implication. "
            f"Prioritise the 5 most important law verdicts. "
            f"Conclude with the single highest-leverage marketing recommendation.\n\n"
            f"Evidence:\n{evidence}"
        ),
    }
    return json.dumps(scaffold, indent=2)


def _assess_leadership_health(inp: dict, _vs: "VectorStore") -> str:
    company = inp["company"]
    evidence = inp["leadership_evidence"]
    key_leaders = inp.get("key_leaders", "")

    scaffold = {
        "company": company,
        "key_leaders": key_leaders,
        "framework": "15 Commitments of Conscious Leadership — Dethmer, Chapman, Warner",
        "axis": "Above the Line (learning / curiosity / ownership) vs. Below the Line (defending / protecting / controlling)",
        "above_line_signals": [
            "Takes 100% responsibility — no blame, no victim narrative in public statements",
            "Curious and learning-oriented — admits mistakes openly",
            "Processes emotions without drama or projection",
            "Candid communication — says uncomfortable truths with care",
            "Eliminates gossip — only talks to people who can solve problems",
            "Keeps agreements — cleans them up quickly when broken",
            "Generates genuine enthusiasm and energy",
            "Abundant mindset — celebrates competitors' wins without threat",
            "Operates from zone of genius, not just competence",
            "Wholehearted collaboration — no hidden agendas",
        ],
        "below_line_signals": [
            "Blame culture — 'not my fault' narratives in earnings calls or press",
            "Chronic secrecy — hiding bad news until forced",
            "Leadership team turnover and public dysfunction",
            "CEO defensiveness rather than curiosity in analyst calls",
            "Culture of fear rather than culture of learning",
            "Short-termism over long-term value creation",
            "Misaligned incentives (compensation vs. shareholder interests)",
        ],
        "investment_implications": (
            "Below-the-line leadership is a leading indicator of organisational decay. "
            "Conscious leadership organisations (Netflix culture, Bridgewater principles, Amazon LP culture) "
            "tend to compound; blame cultures tend to erode."
        ),
        "instruction": (
            f"Assess the leadership health of {company} using the above framework. "
            f"For each signal category: cite specific evidence, classify above/below the line, "
            f"and rate the severity. "
            f"Produce an overall leadership health score (A/B/C/D/F) with key evidence. "
            f"Identify the single biggest leadership risk and the single biggest leadership asset. "
            f"State the investment implication clearly.\n\nEvidence:\n{evidence}"
        ),
    }
    return json.dumps(scaffold, indent=2)


def _analyze_tps_excellence(inp: dict, _vs: "VectorStore") -> str:
    company = inp["company"]
    evidence = inp["operational_evidence"]
    industry = inp.get("industry", "general")

    scaffold = {
        "company": company,
        "industry": industry,
        "framework": "Toyota Production System (TPS) — Process Power Assessment",
        "pillars": {
            "just_in_time": {
                "description": "Produce/deliver only what is needed, when needed, in the quantity needed",
                "tech_analogy": "CI/CD pipelines, JIT feature delivery, lean inventory / zero-waste supply chains",
                "score": None,
            },
            "jidoka_built_in_quality": {
                "description": "Stop and fix problems immediately; never pass defects downstream",
                "tech_analogy": "Automated testing gates, incident response culture, Andon cord authority",
                "score": None,
            },
            "kaizen_continuous_improvement": {
                "description": "Every employee identifies and eliminates waste — cultural, not just managerial",
                "tech_analogy": "Engineering retros, blameless post-mortems, OKR iteration cycles",
                "score": None,
            },
            "seven_wastes_muda": {
                "description": "Overproduction, Waiting, Transportation, Over-processing, Inventory, Motion, Defects",
                "tech_analogy": "Feature bloat, deployment lag, handoff delays, tech debt, WIP backlog",
                "score": None,
            },
            "heijunka_levelling": {
                "description": "Smooth demand and production variation to enable consistent flow",
                "tech_analogy": "Load balancing, sprint cadence, demand forecasting accuracy",
                "score": None,
            },
            "standardised_work": {
                "description": "Document the one best current method as the baseline for improvement",
                "tech_analogy": "Runbooks, playbooks, coding standards, deployment checklists",
                "score": None,
            },
            "visual_management": {
                "description": "Make problems and work-in-progress immediately visible",
                "tech_analogy": "Dashboards, observability, Kanban boards, on-call alerting",
                "score": None,
            },
        },
        "scoring_guide": "Score each pillar 0 (absent/dysfunctional) → 3 (world-class). Total ≥ 16 = Process Power moat.",
        "instruction": (
            f"Assess {company}'s operational excellence against each TPS pillar above. "
            f"Score each 0-3, cite specific evidence, and identify waste patterns. "
            f"Conclude with: (1) Does {company} have genuine Process Power? "
            f"(2) What is the single biggest operational waste / improvement opportunity? "
            f"(3) How does this operational profile compare to the best in class "
            f"(Toyota, Amazon Operations, SpaceX manufacturing)?\n\nEvidence:\n{evidence}"
        ),
    }
    return json.dumps(scaffold, indent=2)


def _apply_munger_models(inp: dict, _vs: "VectorStore") -> str:
    subject = inp["subject"]
    context = inp["context"]
    primary_question = inp["primary_question"]
    emphasise = inp.get("models_to_emphasise", [])

    models = {
        "incentive_analysis": (
            "Map every key incentive structure. Show me the incentive, I'll show you the outcome. "
            "Check: management comp vs. shareholder alignment, supplier incentives, employee incentives."
        ),
        "inversion": (
            "Invert the question: What would DESTROY this business / thesis? "
            "List the top 5 ways this could go to zero. If you can't find them, look harder."
        ),
        "opportunity_cost": (
            "What is the opportunity cost? Every dollar here is a dollar not in the best alternative. "
            "What would you have to believe about alternatives to justify this?"
        ),
        "compounding": (
            "Model the compounding dynamics over 10 years. What compounds favourably? "
            "What compounds against (debt, dilution, competitive erosion)?"
        ),
        "circle_of_competence": (
            "Am I inside my circle of competence here? What do I genuinely know vs. what am I guessing? "
            "Where is the analysis most speculative?"
        ),
        "availability_bias": (
            "What recent events are dominating the narrative? "
            "What does the base rate say vs. the recent experience?"
        ),
        "confirmation_bias_check": (
            "What evidence would DISPROVE my thesis? Have I sought it? "
            "Play devil's advocate for 2 minutes before concluding."
        ),
        "lollapalooza_effects": (
            "Are multiple biases/forces reinforcing each other in the same direction? "
            "A confluence of 3+ forces creates non-linear outcomes — for better or worse."
        ),
        "margin_of_safety": (
            "What is the margin of safety in this thesis? "
            "How wrong can I be on the key assumptions before the thesis breaks?"
        ),
        "simplicity_test": (
            "Buffett: 'If you can't explain it simply, you don't understand it.' "
            "State the core thesis in one sentence. If you can't, keep digging."
        ),
    }

    active_models = (
        {k: v for k, v in models.items() if any(e.lower() in k for e in emphasise)}
        if emphasise else models
    )

    scaffold = {
        "subject": subject,
        "primary_question": primary_question,
        "framework": "Charlie Munger's Worldly Wisdom — Mental Model Latticework",
        "models": active_models,
        "instruction": (
            f"Apply the Munger mental model latticework to: '{primary_question}' for {subject}. "
            f"Work through each model in turn. Be brutally honest — Munger's value is in "
            f"catching mistakes and blind spots, not confirming existing views. "
            f"Conclude with: (1) The 2-3 most important insights from this cross-check, "
            f"(2) The single biggest risk the models reveal, "
            f"(3) Your updated conviction level (Higher / Same / Lower) and why.\n\nContext:\n{context}"
        ),
    }
    return json.dumps(scaffold, indent=2)


def _search_pg_essays(inp: dict, vs: "VectorStore") -> str:
    query = inp["query"]
    top_k = min(int(inp.get("top_k", 6)), 15)

    results = vs.search_pg(query, top_k=top_k)

    if not results:
        return json.dumps({
            "query": query,
            "results": [],
            "note": (
                "No PG essays indexed yet. Run 'python main.py build-pg' "
                "to scrape and index paulgraham.com essays."
            ),
        })

    formatted = []
    for r in results:
        formatted.append({
            "essay_title": r["title"],
            "url": r["url"],
            "relevance_score": r["score"],
            "excerpt": r["text"][:800],
        })

    return json.dumps(
        {
            "query": query,
            "total_results": len(formatted),
            "results": formatted,
            "instruction": (
                "Integrate these PG essay excerpts into your analysis. "
                "Reference specific essays by name. "
                "Apply the frameworks directly to the subject at hand — "
                "don't just quote PG, derive the investment/strategic implication."
            ),
        },
        indent=2,
    )


def _list_pg_essays(inp: dict, vs: "VectorStore") -> str:
    titles = vs.get_pg_essay_titles()
    filter_str = inp.get("filter", "").lower()

    if filter_str:
        titles = [t for t in titles if filter_str in t.lower()]

    if not titles:
        return json.dumps({
            "count": 0,
            "essays": [],
            "note": "No PG essays indexed. Run 'python main.py build-pg' first.",
        })

    return json.dumps(
        {
            "count": len(titles),
            "essays": titles,
            "instruction": (
                "These are the Paul Graham essays available for search. "
                "Use search_paul_graham_essays to retrieve specific content."
            ),
        },
        indent=2,
    )


def _assess_pmf_quantitative(inp: dict, _vs: "VectorStore") -> str:
    company = inp["company"]
    product_type = inp["product_type"]
    retention = inp.get("retention_metrics", {})
    engagement = inp.get("engagement_metrics", {})
    growth = inp.get("growth_metrics", {})
    context = inp.get("context", "")

    # Benchmarks by product type
    benchmarks = {
        "consumer_social": {
            "d30_retention_strong": 25, "d30_retention_pmf": 15,
            "dau_mau_strong": 0.5, "dau_mau_pmf": 0.25,
            "nps_strong": 50,
        },
        "saas_b2b": {
            "logo_retention_12m_strong": 90, "logo_retention_12m_pmf": 80,
            "nrr_strong": 120, "nrr_pmf": 100,
            "payback_months_strong": 12, "payback_months_pmf": 24,
        },
        "marketplace": {
            "d30_gtv_retention_strong": 30, "d30_gtv_retention_pmf": 20,
            "quick_ratio_strong": 4, "quick_ratio_pmf": 2,
        },
        "fintech": {
            "d90_retention_strong": 40, "d90_retention_pmf": 25,
            "nrr_strong": 110, "nrr_pmf": 95,
        },
        "ecommerce": {
            "repeat_purchase_12m_strong": 50, "repeat_purchase_12m_pmf": 30,
            "d90_retention_strong": 25, "d90_retention_pmf": 15,
        },
        "other": {
            "d30_retention_strong": 20, "d30_retention_pmf": 10,
            "nrr_strong": 110, "nrr_pmf": 100,
        },
    }

    pmf_stages = {
        "pre_pmf": "Retention curves declining; churn > acquisition; no stable core user base",
        "early_pmf": "Retention flattening in a small segment; some users love it but not scalable yet",
        "strong_pmf": "Flat retention curve + NRR > 100% + organic growth loop forming",
        "escape_velocity": "Network effects or viral coefficient > 1 compounding PMF into defensible moat",
    }

    scaffold = {
        "company": company,
        "product_type": product_type,
        "framework": "Tribe Capital Quantitative PMF Framework",
        "provided_metrics": {
            "retention": retention,
            "engagement": engagement,
            "growth": growth,
        },
        "benchmarks_for_product_type": benchmarks.get(product_type, benchmarks["other"]),
        "pmf_stages": pmf_stages,
        "key_diagnostic_questions": [
            "Do retention curves flatten or continue declining past D30/D90?",
            "Is NRR > 100% (users expand usage over time)?",
            "What % of new users come organically (true PMF signal)?",
            "Is the Quick Ratio > 2 (growing faster than leaking)?",
            "What does the DAU/MAU ratio indicate about habitual usage?",
            "Is payback period shortening over time (improving CAC efficiency)?",
        ],
        "instruction": (
            f"Assess {company}'s product-market fit quantitatively. "
            f"For each provided metric: compare to the benchmark, interpret the signal, "
            f"and classify as: Strong PMF / Approaching PMF / Below PMF Threshold / Unknown. "
            f"Identify which metrics are missing and what they would tell us. "
            f"Classify the company's current PMF stage (Pre-PMF / Early PMF / Strong PMF / Escape Velocity). "
            f"State what metrics to watch most closely as leading indicators. "
            f"Conclude with the PMF conviction level: High / Medium / Low / Too Early to Tell.\n\nContext:\n{context}"
        ),
    }
    return json.dumps(scaffold, indent=2)


def _apply_paul_graham_thinking(inp: dict, _vs: "VectorStore") -> str:
    company = inp["company"]
    context = inp.get("context", "")
    stage = inp.get("stage", "any")
    focus = inp.get("focus_frameworks", [])

    all_frameworks = {
        "growth_rate": {
            "essay": "Startup = Growth (2012)",
            "core_principle": (
                "A startup is a company designed to grow fast. "
                "The only essential thing is growth. "
                "5-7% weekly growth = exceptional trajectory. "
                "10% monthly = high growth. 1-2% monthly = lifestyle business."
            ),
            "diagnostic_questions": [
                "What is the week-over-week or month-over-month growth rate?",
                "Is the growth rate accelerating, flat, or decelerating?",
                "What is the company growing — revenue, users, GMV, ARR?",
                "Is growth organic (PMF signal) or paid (cash-dependent)?",
            ],
            "investment_implication": (
                "Growth rate is the single most important metric for a growth company. "
                "A decelerating growth rate is the earliest warning sign. "
                "An accelerating growth rate is the strongest buy signal."
            ),
        },
        "default_alive": {
            "essay": "Default Alive or Default Dead? (2015)",
            "core_principle": (
                "If a startup's expenses are growing faster than its revenue, "
                "it will run out of money and die — unless it raises more capital. "
                "The question to ask: assuming no future fundraising, "
                "does the company survive? "
                "Default Alive = revenue growth outpaces burn. "
                "Default Dead = dependent on perpetual capital raises."
            ),
            "diagnostic_questions": [
                "What is the monthly burn rate vs. monthly revenue?",
                "How many months of runway remain at current burn?",
                "Is revenue growth rate faster than expense growth rate?",
                "What is the path to cash flow positive — months or years?",
                "If capital markets closed tomorrow, would this company survive?",
            ],
            "investment_implication": (
                "Default Dead companies are options, not businesses — underwrite them as such. "
                "Default Alive companies have power in negotiations and can be patient. "
                "The shift from Default Dead to Default Alive is a major re-rating event."
            ),
        },
        "founder_mode": {
            "essay": "Founder Mode (2024)",
            "core_principle": (
                "Founders who continue operating like founders — "
                "deep involvement in details, skip-level meetings, "
                "direct customer relationships, authentic culture — "
                "outperform those who switch to 'hired CEO mode' (trust the layers, delegate everything). "
                "The conventional manager wisdom ('hire good people and get out of their way') "
                "often fails in the hands of founders because it cedes the culture to layers."
            ),
            "diagnostic_questions": [
                "Is the founder/CEO still deeply involved in product and strategy?",
                "Does management feel 'bureaucratic' or 'startup-like' despite scale?",
                "Are there signs of skip-level engagement (CEO talking to engineers, customers)?",
                "Has the culture remained authentic to the founder's original vision?",
                "Is the CEO running the company or has the company started running the CEO?",
            ],
            "investment_implication": (
                "Founder-mode CEOs (Jensen Huang at NVIDIA, Bezos at Amazon, Jobs at Apple) "
                "tend to compound for decades. "
                "Manager-mode transitions at founder-led companies often precede mean-reversion. "
                "Watch for: increasing bureaucracy, slower product cycles, declining culture survey scores."
            ),
        },
        "schlep_blindness": {
            "essay": "Schlep Blindness (2012)",
            "core_principle": (
                "Founders and investors systematically avoid hard, unglamorous work ('schleps'). "
                "This creates enormous opportunity: the best startup ideas are often the ones "
                "that seem boring, dirty, or difficult. "
                "Stripe's insight: payments processing is a schlep everyone avoids — "
                "therefore it's a massive opportunity with no competition from glory-seekers."
            ),
            "diagnostic_questions": [
                "What is the hardest, most unsexy part of what this company does?",
                "Is the company doing work competitors refuse because it's too difficult?",
                "Does the founder actively embrace the schlep or try to engineer around it?",
                "Would a VC-seeking founder with options skip this problem entirely?",
            ],
            "investment_implication": (
                "Companies that embrace schlep build the deepest moats. "
                "The harder and more unsexy the work, the fewer competitors will persist. "
                "Schlep = process power in the making."
            ),
        },
        "frighteningly_ambitious": {
            "essay": "Frighteningly Ambitious Startup Ideas (2012)",
            "core_principle": (
                "The best startup ideas look bad at first to most people. "
                "If they looked obviously good, they'd already be done. "
                "The most important ideas seem 'too ambitious' to skeptics "
                "but 'inevitable' to those who deeply understand the domain. "
                "The tell: smart people have dismissed it for plausible but ultimately wrong reasons."
            ),
            "diagnostic_questions": [
                "Did the idea seem absurd when first pitched? What was the specific objection?",
                "Why did smart people think this was impossible / not worth doing?",
                "What specific insight unlocks the idea that most people lack?",
                "Is the company doing something that will look obvious in 10 years?",
            ],
            "investment_implication": (
                "Non-consensus, frighteningly ambitious bets are where 100x returns live. "
                "The consensus is always right about what seems crazy today. "
                "The contrarian is right when the underlying insight is correct. "
                "NVIDIA building CUDA before AI existed is the canonical example."
            ),
        },
        "do_things_that_dont_scale": {
            "essay": "Do Things That Don't Scale (2013)",
            "core_principle": (
                "Startups that succeed often begin with intensive manual work "
                "that is impossible to sustain at scale — and that's fine. "
                "Airbnb photographed apartments; Stripe manually configured payments; "
                "DoorDash founders delivered food themselves. "
                "This forces customer intimacy that builds the intuition to build the right product. "
                "The manual phase is a learning phase, not a failure."
            ),
            "diagnostic_questions": [
                "Did the founders personally do the work their product now automates?",
                "Is there evidence of intense early customer intimacy?",
                "Has the 'unscalable' phase built proprietary insights competitors can't replicate?",
                "What do they know about customers that only comes from doing things manually?",
            ],
            "investment_implication": (
                "Evidence that founders did things that don't scale is a founder quality signal. "
                "Companies with this foundation tend to have better product instincts "
                "and deeper customer empathy than those who tried to scale immediately."
            ),
        },
        "relentlessly_resourceful": {
            "essay": "Relentlessly Resourceful (2009)",
            "core_principle": (
                "The most important quality in a founder is being 'relentlessly resourceful' — "
                "a combination of determination and creative problem-solving. "
                "Not smart (necessary but not sufficient). "
                "Not determined (can become stubbornness). "
                "Relentlessly resourceful = finds a way forward when every door is closed."
            ),
            "diagnostic_questions": [
                "What near-death experiences has this company navigated?",
                "How did the founder respond when the obvious path was blocked?",
                "Are there examples of creative pivots that preserved the core insight?",
                "Does the founder attract other resourceful people, or bureaucratic ones?",
            ],
            "investment_implication": (
                "Relentlessly resourceful founders build companies that survive adversity. "
                "Test: find the hardest moment in company history and ask 'what did they do?' "
                "The answer tells you everything about the founder's quality."
            ),
        },
        "power_law": {
            "essay": "Black Swan Farming / How to Be an Angel Investor (2009)",
            "core_principle": (
                "Investment returns follow a power law, not a normal distribution. "
                "The best investment in a portfolio should return more than all others combined. "
                "This means: optimize for maximum upside scenarios, not average scenarios. "
                "The question is not 'what is the expected return?' "
                "but 'what is the maximum possible return if everything goes right?'"
            ),
            "diagnostic_questions": [
                "What is the maximum value this company could reach (TAM × market share)?",
                "Is the upside scenario plausible, or does it require magic?",
                "How much of the portfolio return would this represent if it works?",
                "Is this a compounder bet (expected value) or a power law bet (maximum value)?",
            ],
            "investment_implication": (
                "For venture-style bets: size for the power law. "
                "For compounders: size for expected value. "
                "Distinguish which type of bet you're making before sizing."
            ),
        },
        "wealth_creation": {
            "essay": "How to Make Wealth (2004)",
            "core_principle": (
                "Wealth is created by building things people want. "
                "The best companies create value from nothing — "
                "they don't redistribute existing wealth, they expand the pie. "
                "The test: if this company disappeared, would the world be meaningfully worse? "
                "Value extractors (rent-seekers, monopolists extracting surplus) "
                "tend to face regulatory and competitive backlash over time."
            ),
            "diagnostic_questions": [
                "Does this company create net new value, or redistribute existing value?",
                "If it disappeared tomorrow, who would suffer and how much?",
                "Is pricing power from genuine value creation or from rent extraction?",
                "Is this company expanding the market it operates in, or fighting for share?",
            ],
            "investment_implication": (
                "Genuine wealth creators tend to earn loyalty, pricing power, and regulatory goodwill. "
                "Value extractors (toll roads, financial intermediaries without efficiency gains) "
                "invite disruption and regulation. "
                "Long-term compounders are almost always in the first category."
            ),
        },
        "be_good": {
            "essay": "Be Good (2008)",
            "core_principle": (
                "The simplest filter for whether a company will succeed long-term: "
                "is it genuinely good? Do good people work there? "
                "Does it make customers' lives meaningfully better? "
                "PG's insight: being good is not just morally right — it's strategically powerful. "
                "Good companies attract better people, earn more trust, and build more durable relationships."
            ),
            "diagnostic_questions": [
                "Would you describe this company as genuinely good for the people it serves?",
                "Does the culture attract idealistic people or purely mercenary ones?",
                "Are there signs of ethical shortcuts that will eventually catch up?",
                "Does the CEO seem like a good person, or a person optimizing only for outcomes?",
            ],
            "investment_implication": (
                "Companies that are genuinely good tend to compound more durably "
                "because they attract better talent, earn greater customer loyalty, "
                "and avoid the reputational crises that destroy short-term optimizers. "
                "'Be good' is a useful final-stage filter after all other analysis."
            ),
        },
    }

    # Filter to requested frameworks if specified
    active = (
        {k: v for k, v in all_frameworks.items() if k in focus}
        if focus else all_frameworks
    )

    # Calibrate to stage
    stage_note = {
        "early_startup": "Focus most on: growth_rate, default_alive, do_things_that_dont_scale, relentlessly_resourceful",
        "growth_stage": "Focus most on: growth_rate, default_alive, founder_mode, schlep_blindness",
        "public_company": "Focus most on: founder_mode, wealth_creation, be_good, power_law",
        "any": "Apply all frameworks proportionally based on evidence available",
    }.get(stage, "Apply all frameworks proportionally")

    scaffold = {
        "company": company,
        "stage": stage,
        "stage_calibration": stage_note,
        "framework": "Paul Graham Essay Canon — Startup & Founder Thinking",
        "frameworks": active,
        "instruction": (
            f"Apply Paul Graham's frameworks to {company} using the evidence below. "
            f"For each relevant framework: "
            f"(1) State the PG principle in one sentence, "
            f"(2) Apply it specifically to {company} with evidence, "
            f"(3) Give the investment/strategic implication. "
            f"Be direct and specific — PG's value is in cutting through noise to the essential truth. "
            f"Conclude with: "
            f"(a) The single most important PG insight for this company, "
            f"(b) The biggest PG-identified risk, "
            f"(c) An overall PG-lens verdict (Strong / Mixed / Weak) with one-sentence rationale."
            f"\n\nContext:\n{context}"
        ),
    }
    return json.dumps(scaffold, indent=2)
