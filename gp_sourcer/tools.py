"""
GP Sourcing Agent Tools

Tool definitions (JSON schema for Claude) and Python implementations.

Tools:
  1.  search_gp_registry          — Find PE/VC/buyout firms in SEC IAPD + EDGAR
  2.  get_gp_regulatory_data      — Form ADV details: AUM, strategy, clients
  3.  track_fund_fundraising      — Form D filings: fund history for a named GP
  4.  search_institutional_lps    — Endowments / foundations on ProPublica (LP capacity)
  5.  get_lp_financials           — 990 investment income and asset trends
  6.  web_search                  — Live web search for news, track record, team, portfolio
  7.  fetch_webpage               — Scrape a specific URL for deep reading
  8.  lp_evaluation_framework     — LP evaluation rubric scaffold for structured scoring
  9.  search_990_lp_investments   — Parse IRS 990 Schedule D/R for actual LP fund commitments
 10.  scan_ivy_hospital_990s      — Batch scan all Ivy + hospital 990s for LP investment data
 11.  form_d_live_feed            — Live Form D feed: new private fund raises by date/type/size
 12.  form_d_filing_detail        — Parse a specific Form D XML: size, persons, exemptions
 13.  form_d_manager_history      — All Form D filings for a GP — fund family + raise trajectory
"""

from __future__ import annotations

import json
from typing import TYPE_CHECKING

from .sec import search_investment_advisers, get_adviser_form_adv, search_form_d_fundraising
from .nonprofits import search_institutional_lps, get_lp_financials
from .web import search_web, scrape_webpage
from .irs_990 import get_lp_investments_from_990, batch_search_ivy_lps, KNOWN_LP_ENTITIES
from .form_d_feed import search_form_d_feed, get_form_d_detail, search_form_d_by_manager

# ──────────────────────────────────────────────────────────────────────
#  Tool JSON schema definitions
# ──────────────────────────────────────────────────────────────────────

TOOL_DEFINITIONS = [
    {
        "name": "search_gp_registry",
        "description": (
            "Search the SEC Investment Adviser Public Disclosure (IAPD) database "
            "and EDGAR for registered PE/VC/buyout/growth equity fund managers. "
            "Use this to discover candidate GPs by firm name, strategy keyword, "
            "or geography. Returns CRD numbers, registration status, and headcount. "
            "Run this first when researching an unknown GP."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": (
                        "Firm name or keyword. Examples: 'Vista Equity Partners', "
                        "'healthcare buyout New York', 'growth equity software'."
                    ),
                },
                "max_results": {
                    "type": "integer",
                    "description": "Number of results to return (default 20, max 40).",
                    "default": 20,
                },
            },
            "required": ["query"],
        },
    },
    {
        "name": "get_gp_regulatory_data",
        "description": (
            "Retrieve Form ADV regulatory filing data for a specific GP by their "
            "SEC CRD number. Returns: total AUM, discretionary AUM, number of "
            "employees, types of clients (pension funds, endowments, HNW, etc.), "
            "advisory services offered, compensation arrangements, and website. "
            "CRD numbers come from search_gp_registry results."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "crd_number": {
                    "type": "string",
                    "description": "The SEC CRD (Central Registration Depository) number for the firm.",
                },
            },
            "required": ["crd_number"],
        },
    },
    {
        "name": "track_fund_fundraising",
        "description": (
            "Search SEC EDGAR Form D filings to track private fund capital raises "
            "by a GP firm. Form D is filed when a fund first sells securities. "
            "Useful for: identifying recent fund closes, tracking fund size trajectory "
            "across vintages, and finding LP vehicle names. "
            "Each fund (e.g. 'Blackstone Capital Partners X LP') is a separate filer."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "firm_name": {
                    "type": "string",
                    "description": (
                        "GP firm or fund family name to search. Use the broader family name "
                        "(e.g. 'KKR' not 'KKR Americas Fund XIII') to capture all fund vehicles."
                    ),
                },
                "start_date": {
                    "type": "string",
                    "description": "Earliest filing date to include (YYYY-MM-DD). Default: 2020-01-01.",
                    "default": "2020-01-01",
                },
                "max_results": {
                    "type": "integer",
                    "description": "Maximum number of Form D filings to return (default 25).",
                    "default": 25,
                },
            },
            "required": ["firm_name"],
        },
    },
    {
        "name": "search_institutional_lps",
        "description": (
            "Search ProPublica Nonprofit Explorer to find university endowments, "
            "family foundations, and other institutional LPs by name. "
            "Returns total assets and investment income — proxy for PE/VC allocation capacity. "
            "Useful for: finding reference LPs who may have invested with a GP, "
            "or identifying target LPs to mention in GP due diligence conversations."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "name": {
                    "type": "string",
                    "description": "Endowment or foundation name. E.g. 'Harvard', 'Rockefeller Foundation', 'W.K. Kellogg'.",
                },
                "max_results": {
                    "type": "integer",
                    "description": "Number of results to return (default 10).",
                    "default": 10,
                },
            },
            "required": ["name"],
        },
    },
    {
        "name": "get_lp_financials",
        "description": (
            "Get 990 financial history for an endowment or foundation by EIN number. "
            "Returns investment income, total assets, and revenue trends across "
            "recent tax years — useful for assessing LP allocation capacity and "
            "investment policy changes over time. EIN comes from search_institutional_lps."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "ein": {
                    "type": "string",
                    "description": "Tax EIN (Employer Identification Number) of the organization. Format: XX-XXXXXXX or XXXXXXXXX.",
                },
            },
            "required": ["ein"],
        },
    },
    {
        "name": "web_search",
        "description": (
            "Search the web for live information about a GP firm. "
            "Use this for: track record news, portfolio company developments, "
            "team changes and departures, fund performance articles, LP base mentions, "
            "regulatory issues, press releases, and LinkedIn/YouTube presence. "
            "Always search before forming views on team quality or track record."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": (
                        "Search query. Be specific. Examples: "
                        "'Vista Equity Partners fund VI performance IRR', "
                        "'Warburg Pincus 2024 team departures', "
                        "'TPG Rise Climate fund LP investors', "
                        "'General Atlantic portfolio exits 2023 DPI'."
                    ),
                },
                "max_results": {
                    "type": "integer",
                    "description": "Number of search results to return (default 10, max 20).",
                    "default": 10,
                },
            },
            "required": ["query"],
        },
    },
    {
        "name": "fetch_webpage",
        "description": (
            "Fetch and read the text content of a specific URL. "
            "Use this for: GP firm websites (investment thesis, team, portfolio), "
            "news articles about a GP, state pension fund PE portfolio disclosures, "
            "or ProPublica organization pages. "
            "Returns up to 6,000 characters of cleaned text."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "url": {
                    "type": "string",
                    "description": "The full URL to fetch.",
                },
            },
            "required": ["url"],
        },
    },
    {
        "name": "lp_evaluation_framework",
        "description": (
            "Generate a structured LP evaluation framework scaffold for a specific GP. "
            "Returns a JSON template with all scoring dimensions that you should fill in "
            "based on research gathered. Use this after completing research to synthesize "
            "findings into a formal GP tearsheet and LP fit score."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "gp_name": {
                    "type": "string",
                    "description": "Name of the GP firm being evaluated.",
                },
                "fund_strategy": {
                    "type": "string",
                    "enum": ["buyout", "growth_equity", "venture_capital", "credit", "real_assets", "multi_strategy"],
                    "description": "Primary fund strategy.",
                },
                "research_summary": {
                    "type": "string",
                    "description": "Summary of research gathered so far — paste key findings here for Claude to use in scoring.",
                },
                "investment_horizon": {
                    "type": "string",
                    "enum": ["current_vintage", "long_term_relationship"],
                    "description": "Whether evaluating for a single fund commitment or an ongoing GP relationship.",
                    "default": "current_vintage",
                },
            },
            "required": ["gp_name", "fund_strategy", "research_summary"],
        },
    },
    {
        "name": "search_990_lp_investments",
        "description": (
            "Parse IRS Form 990 Schedule D (Investments - Other Securities) and "
            "Schedule R (Unrelated Partnerships) for a specific endowment, university, "
            "or hospital to extract their actual LP fund commitments. "
            "Data comes directly from the IRS public 990 XML dataset. "
            "Best sources: Harvard Management Private Equity Corp, Mass General Brigham, "
            "Yale New Haven Hospital, Dana-Farber, NewYork-Presbyterian — these hospital-affiliated "
            "entities tend to have more granular LP investment disclosure than the universities themselves. "
            "Use entity names from the known list or provide EIN directly."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "entity": {
                    "type": "string",
                    "description": (
                        "Entity name or EIN. Known entities include: "
                        "'Harvard Management Private Equity Corp' (EIN 04-3070522), "
                        "'Harvard Management Company' (EIN 23-7361259), "
                        "'Yale University' (EIN 06-0646973), "
                        "'Princeton University (PRINCO)' (EIN 21-0634501), "
                        "'Mass General Brigham' (EIN 04-3230035), "
                        "'Yale New Haven Hospital' (EIN 06-0646652), "
                        "'Dana-Farber Cancer Institute' (EIN 04-2263923), "
                        "'NewYork-Presbyterian Hospital' (EIN 13-1624096), "
                        "'Columbia University' (EIN 13-5598093), "
                        "'University of Pennsylvania' (EIN 23-1352685)."
                    ),
                },
                "years": {
                    "type": "array",
                    "items": {"type": "integer"},
                    "description": "Filing years to search (default: [2024, 2023, 2022]). Use year the 990 was FILED, not the tax year.",
                    "default": [2024, 2023, 2022],
                },
                "max_filings": {
                    "type": "integer",
                    "description": "Number of filings to parse (default 2, returns most recent first).",
                    "default": 2,
                },
            },
            "required": ["entity"],
        },
    },
    {
        "name": "form_d_live_feed",
        "description": (
            "Pull the live SEC EDGAR Form D feed — new private fund capital raises filtered by "
            "date range, strategy type, and offering size. Form D is filed when a fund makes its "
            "first sale of securities under Regulation D. Use this to answer: "
            "'What new PE/buyout/VC funds launched in the last 90 days?' "
            "'Which funds over $500M filed Form D this quarter?' "
            "Set parse_xml=true to get full offering sizes, investor counts, and key persons "
            "(slower — ~1s per filing). Without parse_xml, returns fast index-only results. "
            "Rule 506(b) = traditional private placement; Rule 506(c) = general solicitation allowed."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "days_back": {
                    "type": "integer",
                    "description": "Look-back window in days. Default 90. Use 30 for recent, 365 for annual sweep.",
                    "default": 90,
                },
                "fund_type": {
                    "type": "string",
                    "enum": ["buyout", "venture", "growth", "credit", "real_estate", "hedge_fund", "all"],
                    "description": (
                        "Strategy filter. 'buyout' matches PE/buyout/capital partners funds; "
                        "'venture' matches VC; 'growth' matches growth equity; "
                        "'credit' matches direct lending/private credit; "
                        "'real_estate' matches RE/infrastructure; 'all' returns everything."
                    ),
                },
                "min_offering_usd": {
                    "type": "integer",
                    "description": "Minimum total offering amount in dollars (e.g. 100000000 = $100M). Only effective with parse_xml=true.",
                },
                "max_offering_usd": {
                    "type": "integer",
                    "description": "Maximum total offering amount in dollars. Only effective with parse_xml=true.",
                },
                "keywords": {
                    "type": "string",
                    "description": (
                        "Free-text search terms added to the EDGAR query. "
                        "Examples: 'healthcare', 'technology', 'Thoma Bravo', 'Francisco Partners'."
                    ),
                },
                "new_filings_only": {
                    "type": "boolean",
                    "description": "If true (default), exclude D/A amendments and return only new fund launches.",
                    "default": True,
                },
                "max_results": {
                    "type": "integer",
                    "description": "Maximum results to return (default 40, max 100).",
                    "default": 40,
                },
                "parse_xml": {
                    "type": "boolean",
                    "description": (
                        "If true, fetch and parse Form D XML for each result — returns offering sizes, "
                        "investor counts, exemptions, and key persons. Slower (~1s per result). "
                        "Use false (default) for fast index browsing, then call form_d_filing_detail "
                        "on specific accession_nos for full detail."
                    ),
                    "default": False,
                },
            },
            "required": [],
        },
    },
    {
        "name": "form_d_filing_detail",
        "description": (
            "Fetch and fully parse a specific Form D XML filing from SEC EDGAR. "
            "Returns complete structured data: total offering amount, amount already sold, "
            "remaining, minimum investment, number of investors, date of first sale, "
            "Rule 506(b)/(c) exemption status, securities type, and key persons (GPs / officers). "
            "Use this after form_d_live_feed to deep-dive on a specific filing. "
            "Requires cik and accession_no from feed results."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "cik": {
                    "type": "string",
                    "description": "EDGAR CIK number (from form_d_live_feed results, e.g. '1234567').",
                },
                "accession_no": {
                    "type": "string",
                    "description": "Accession number from form_d_live_feed results, e.g. '0001234567-25-000001'.",
                },
            },
            "required": ["cik", "accession_no"],
        },
    },
    {
        "name": "form_d_manager_history",
        "description": (
            "Search all Form D filings for a specific GP firm — tracks their complete fund family "
            "and raise trajectory over time. Returns all fund vehicles (each fund series is a "
            "separate Form D filer), offering sizes across vintages, and an offering_trajectory "
            "summary showing fund size growth. Use this to: "
            "(a) identify all fund vehicles in a GP's history; "
            "(b) track fund size from Fund I through current vintage; "
            "(c) spot new fund series before public announcement; "
            "(d) see how frequently a GP returns to market."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "manager_name": {
                    "type": "string",
                    "description": (
                        "GP firm name or partial name. Use the firm family name, not a specific fund. "
                        "Examples: 'Vista Equity', 'Thoma Bravo', 'Francisco Partners', "
                        "'Hellman Friedman', 'General Atlantic', 'Warburg Pincus'."
                    ),
                },
                "days_back": {
                    "type": "integer",
                    "description": "Look-back window in days (default 1825 = ~5 years for full vintage history).",
                    "default": 1825,
                },
                "max_results": {
                    "type": "integer",
                    "description": "Maximum number of filings to return (default 25).",
                    "default": 25,
                },
                "parse_xml": {
                    "type": "boolean",
                    "description": "If true (default), parse each Form D XML to get offering sizes and key persons.",
                    "default": True,
                },
            },
            "required": ["manager_name"],
        },
    },
    {
        "name": "scan_ivy_hospital_990s",
        "description": (
            "Batch scan IRS 990 filings for ALL Ivy League endowments and "
            "affiliated hospital investment pools simultaneously. "
            "Searches Schedule D and Schedule R for LP fund commitments across: "
            "Harvard Management Private Equity Corp, Harvard Management Company, "
            "Yale University, Princeton University, Mass General Brigham, "
            "Yale New Haven Hospital, Columbia University, University of Pennsylvania, "
            "Dana-Farber Cancer Institute, and NewYork-Presbyterian Hospital. "
            "Use this for a broad sweep of which entities have which funds in their 990s. "
            "This may take 30-60 seconds as it downloads multiple XML files."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "years": {
                    "type": "array",
                    "items": {"type": "integer"},
                    "description": "Filing years to search across all entities (default: [2024, 2023, 2022]).",
                    "default": [2024, 2023, 2022],
                },
            },
            "required": [],
        },
    },
]


# ──────────────────────────────────────────────────────────────────────
#  Tool dispatcher
# ──────────────────────────────────────────────────────────────────────

def execute_tool(name: str, tool_input: dict) -> str:
    """Dispatch a tool call and return the result as a JSON string."""
    dispatch = {
        "search_gp_registry": _tool_search_gp_registry,
        "get_gp_regulatory_data": _tool_get_gp_regulatory_data,
        "track_fund_fundraising": _tool_track_fund_fundraising,
        "search_institutional_lps": _tool_search_institutional_lps,
        "get_lp_financials": _tool_get_lp_financials,
        "web_search": _tool_web_search,
        "fetch_webpage": _tool_fetch_webpage,
        "lp_evaluation_framework": _tool_lp_evaluation_framework,
        "search_990_lp_investments": _tool_search_990_lp_investments,
        "scan_ivy_hospital_990s": _tool_scan_ivy_hospital_990s,
        "form_d_live_feed": _tool_form_d_live_feed,
        "form_d_filing_detail": _tool_form_d_filing_detail,
        "form_d_manager_history": _tool_form_d_manager_history,
    }
    fn = dispatch.get(name)
    if fn is None:
        return json.dumps({"error": f"Unknown tool: '{name}'"})
    try:
        result = fn(tool_input)
        return json.dumps(result, indent=2, default=str)
    except Exception as exc:
        return json.dumps({"error": f"Tool '{name}' failed: {exc}"})


# ──────────────────────────────────────────────────────────────────────
#  Individual tool implementations
# ──────────────────────────────────────────────────────────────────────

def _tool_search_gp_registry(inp: dict) -> dict:
    query = inp["query"]
    max_results = min(int(inp.get("max_results", 20)), 40)
    return search_investment_advisers(query, max_results=max_results)


def _tool_get_gp_regulatory_data(inp: dict) -> dict:
    crd = str(inp["crd_number"]).strip()
    return get_adviser_form_adv(crd)


def _tool_track_fund_fundraising(inp: dict) -> dict:
    firm = inp["firm_name"]
    start = inp.get("start_date", "2020-01-01")
    max_r = min(int(inp.get("max_results", 25)), 50)
    return search_form_d_fundraising(firm, start_date=start, max_results=max_r)


def _tool_search_institutional_lps(inp: dict) -> dict:
    return search_institutional_lps(inp["name"], max_results=int(inp.get("max_results", 10)))


def _tool_get_lp_financials(inp: dict) -> dict:
    return get_lp_financials(inp["ein"])


def _tool_web_search(inp: dict) -> dict:
    query = inp["query"]
    max_r = min(int(inp.get("max_results", 10)), 20)
    return search_web(query, max_results=max_r)


def _tool_fetch_webpage(inp: dict) -> dict:
    return scrape_webpage(inp["url"])


def _tool_lp_evaluation_framework(inp: dict) -> dict:
    gp = inp["gp_name"]
    strategy = inp["fund_strategy"]
    summary = inp.get("research_summary", "")
    horizon = inp.get("investment_horizon", "current_vintage")

    # Strategy-specific benchmarks
    benchmarks = {
        "buyout": {
            "target_gross_irr": "20-25%+",
            "target_net_irr": "15-20%+",
            "target_moic": "2.5-3.5x gross",
            "typical_hold_period_years": "4-6",
            "key_metric": "DPI — realised cash returns to LPs",
            "standard_mgmt_fee": "1.5-2.0% during investment period",
            "standard_carry": "20% above 8% preferred return",
            "pme_benchmark": "S&P 500 or LPX50",
        },
        "growth_equity": {
            "target_gross_irr": "25-35%+",
            "target_net_irr": "20-25%+",
            "target_moic": "3-5x gross",
            "typical_hold_period_years": "3-5",
            "key_metric": "Revenue growth trajectory and pathway to profitability",
            "standard_mgmt_fee": "2.0% flat",
            "standard_carry": "20% above 8% preferred return",
            "pme_benchmark": "Russell 2000 Growth",
        },
        "venture_capital": {
            "target_gross_irr": "30%+",
            "target_net_irr": "20%+",
            "target_moic": "3-5x net (power law — top 10% drive returns)",
            "typical_hold_period_years": "7-10",
            "key_metric": "Portfolio construction and ownership at exit",
            "standard_mgmt_fee": "2.0-2.5%",
            "standard_carry": "20-30%",
            "pme_benchmark": "NASDAQ Composite or Cambridge Associates VC Index",
        },
        "credit": {
            "target_gross_irr": "12-18%",
            "target_net_irr": "10-14%",
            "target_moic": "1.5-2.0x",
            "typical_hold_period_years": "3-5",
            "key_metric": "Default rate and loss-adjusted yield vs. public credit",
            "standard_mgmt_fee": "1.5% on committed",
            "standard_carry": "15-20% above 8% hurdle",
            "pme_benchmark": "BAML High Yield Index / Leveraged Loan Index",
        },
        "real_assets": {
            "target_gross_irr": "15-20%",
            "target_net_irr": "12-16%",
            "target_moic": "2.0-2.5x",
            "typical_hold_period_years": "5-8",
            "key_metric": "Cash yield during hold + terminal value realization",
            "standard_mgmt_fee": "1.5% on committed",
            "standard_carry": "20% above 8% preferred return",
            "pme_benchmark": "NCREIF / Infrastructure benchmarks",
        },
        "multi_strategy": {
            "target_gross_irr": "Strategy-dependent",
            "target_net_irr": "Strategy-dependent",
            "target_moic": "Strategy-dependent",
            "typical_hold_period_years": "Varies",
            "key_metric": "Portfolio diversification and manager selection alpha",
            "standard_mgmt_fee": "1.0-1.5% on NAV",
            "standard_carry": "10-15%",
            "pme_benchmark": "Cambridge Associates All PE Index",
        },
    }

    bm = benchmarks.get(strategy, benchmarks["buyout"])

    return {
        "gp_name": gp,
        "fund_strategy": strategy,
        "investment_horizon": horizon,
        "benchmarks": bm,
        "research_summary_provided": summary,
        "evaluation_dimensions": {
            "1_track_record": {
                "weight_pct": 35,
                "metrics_to_assess": [
                    "DPI across all vintages (prioritize funds 5+ years old)",
                    "TVPI and gap vs. DPI (how much is paper vs. realized)",
                    "Net IRR vs. benchmark and vs. PME",
                    "Loss ratio (% of portfolio companies at or near zero)",
                    "Batting average (% investments above 1x)",
                    "Attribution: is performance driven by 1-2 outliers or consistent?",
                ],
                "red_flags": [
                    "Large TVPI-DPI gap in mature funds (>5 years)",
                    "IRR boosted by subscription credit lines",
                    "Strategy drift between vintages",
                    "Track record tied to a departed partner",
                ],
                "score_1_to_10": "TODO",
                "evidence": "TODO",
            },
            "2_team": {
                "weight_pct": 25,
                "metrics_to_assess": [
                    "Key investment partners: tenure, background, individual deal attribution",
                    "Key person risk: what triggers suspension / wind-down",
                    "Team stability: departures in the last 3 years",
                    "Carry allocation: is it concentrated at the top or distributed?",
                    "Next-generation talent pipeline",
                    "GP commitment to the fund (skin in the game)",
                ],
                "red_flags": [
                    "Founding partner(s) stepping back with no clear succession",
                    "Multiple senior departures in recent vintages",
                    "Concentrated carry with no team ownership",
                    "Excessive time on outside activities / fundraising",
                ],
                "score_1_to_10": "TODO",
                "evidence": "TODO",
            },
            "3_strategy": {
                "weight_pct": 20,
                "metrics_to_assess": [
                    "Thesis clarity: is the investment mandate specific and differentiated?",
                    "Sourcing edge: proprietary vs. process-driven deal flow",
                    "Consistency: same strategy across vintages or scope creep?",
                    "Fund size vs. addressable market (is fund too large for strategy?)",
                    "Win rate in competitive processes",
                    "Value-add thesis: operational, strategic, or financial engineering?",
                ],
                "red_flags": [
                    "Rapid AUM growth outpacing deal flow capacity",
                    "Generalist pivot from prior sector focus",
                    "Increasing reliance on auction processes",
                    "Co-investment program as primary source of deal flow",
                ],
                "score_1_to_10": "TODO",
                "evidence": "TODO",
            },
            "4_terms": {
                "weight_pct": 10,
                "market_benchmark": bm,
                "metrics_to_assess": [
                    f"Management fee vs. market ({bm['standard_mgmt_fee']})",
                    f"Carried interest vs. market ({bm['standard_carry']})",
                    "Preferred return / hurdle rate (market: 8%)",
                    "Catch-up structure (100% GP catch-up is LP-unfriendly)",
                    "Clawback provisions and escrow",
                    "GP commitment percentage (prefer ≥2%)",
                    "Key man clause strength",
                    "LPAC composition and independence",
                    "MFN / most-favored-nation rights for large LPs",
                    "Co-investment economics (fee/carry-free or reduced?)",
                    "Management fee offset for deal/monitoring fees",
                ],
                "red_flags": [
                    "No clawback or weak clawback without interest",
                    "GP commitment <1%",
                    "No LPAC or LPAC stacked with GP-friendly LPs",
                    "Full fees on co-investments",
                ],
                "score_1_to_10": "TODO",
                "evidence": "TODO",
            },
            "5_lp_base": {
                "weight_pct": 10,
                "metrics_to_assess": [
                    "Anchor LPs: institutional quality signal (endowments, sovereign funds, ERISA plans)",
                    "LP re-up rate from prior fund (% existing LPs reinvesting)",
                    "LP concentration: over-reliance on 1-2 large LPs?",
                    "Secondary market liquidity / overhang",
                    "Geographic LP diversification (domestic vs. international)",
                    "Public LP disclosures: state pensions with disclosed PE holdings",
                ],
                "score_1_to_10": "TODO",
                "evidence": "TODO",
            },
        },
        "final_output_template": {
            "lp_fit_score_weighted": "TODO — calculate: (track_record × 0.35) + (team × 0.25) + (strategy × 0.20) + (terms × 0.10) + (lp_base × 0.10)",
            "recommendation": "TODO — one of: PASS / WATCH LIST / SOFT CIRCLE / FULL DILIGENCE",
            "conviction_level": "TODO — High / Medium / Low",
            "key_upside_driver": "TODO",
            "key_risk_factor": "TODO",
            "data_gaps_requiring_follow_up": [],
            "suggested_next_steps": [],
        },
        "instruction": (
            f"Using all research gathered on {gp}, complete the evaluation above. "
            f"Score each dimension 1-10, populate the evidence fields with specific "
            f"data points (cite sources: SEC filings, Form D dates, news articles, "
            f"website content). "
            f"Calculate the weighted LP fit score and give a clear recommendation. "
            f"Be direct — a 'Watch List' is not a 'Pass'. Flag all data gaps honestly."
        ),
    }


def _tool_search_990_lp_investments(inp: dict) -> dict:
    entity = inp["entity"]
    years = inp.get("years", [2024, 2023, 2022])
    max_filings = int(inp.get("max_filings", 2))
    return get_lp_investments_from_990(entity, years=years, max_filings=max_filings)


def _tool_scan_ivy_hospital_990s(inp: dict) -> dict:
    years = inp.get("years", [2024, 2023, 2022])
    return batch_search_ivy_lps(years=years)


def _tool_form_d_live_feed(inp: dict) -> dict:
    return search_form_d_feed(
        days_back=int(inp.get("days_back", 90)),
        fund_type=inp.get("fund_type") or None,
        min_offering_usd=inp.get("min_offering_usd"),
        max_offering_usd=inp.get("max_offering_usd"),
        keywords=inp.get("keywords"),
        new_filings_only=bool(inp.get("new_filings_only", True)),
        max_results=min(int(inp.get("max_results", 40)), 100),
        parse_xml=bool(inp.get("parse_xml", False)),
    )


def _tool_form_d_filing_detail(inp: dict) -> dict:
    cik = str(inp["cik"]).strip()
    accession = str(inp["accession_no"]).strip()
    return get_form_d_detail(cik, accession)


def _tool_form_d_manager_history(inp: dict) -> dict:
    return search_form_d_by_manager(
        manager_name=inp["manager_name"],
        days_back=int(inp.get("days_back", 1825)),
        max_results=min(int(inp.get("max_results", 25)), 50),
        parse_xml=bool(inp.get("parse_xml", True)),
    )
