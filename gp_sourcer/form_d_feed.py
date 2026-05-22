"""
SEC EDGAR Form D live feed for GP sourcing.

Form D is filed when a private fund makes its first sale of securities under a
Regulation D exemption (Rule 506(b) or 506(c)).

Use cases:
  - "What new PE/VC/buyout funds launched in the last 90 days?"
  - "Which funds over $500M filed Form D this quarter?"
  - "What growth equity funds raised capital this year?"
  - Track a specific GP's fund family history and raise trajectory

Data source: SEC EDGAR EFTS (free, no API key required)
  Index:   https://efts.sec.gov/LATEST/search-index
  XML:     https://www.sec.gov/Archives/edgar/data/{cik}/{accession}/primary_doc.xml
"""

from __future__ import annotations

import xml.etree.ElementTree as ET
from datetime import datetime, timedelta

import requests

EDGAR_EFTS_URL = "https://efts.sec.gov/LATEST/search-index"
EDGAR_XML_BASE = "https://www.sec.gov/Archives/edgar/data/{cik}/{accession_nodash}/primary_doc.xml"
EDGAR_COMPANY_URL = (
    "https://www.sec.gov/cgi-bin/browse-edgar"
    "?action=getcompany&CIK={cik}&type=D&dateb=&owner=include&count=10"
)

_HEADERS = {
    "User-Agent": "GP-Sourcing-Research research@gp-sourcer.io",
    "Accept": "*/*",
}

# Human-readable labels for Reg D exemption codes as they appear in Form D XML
_RULE_LABELS: dict[str, str] = {
    "06b": "Rule 506(b) — private placement, no general solicitation",
    "06c": "Rule 506(c) — general solicitation OK (can market publicly)",
    "4(a)(5)": "Section 4(a)(5)",
    "4(6)": "Section 4(6)",
    "3(c)": "Section 3(c)",
    "3(c)(1)": "Section 3(c)(1) — max 100 beneficial owners",
    "3(c)(7)": "Section 3(c)(7) — qualified purchasers only",
}

# Strategy keyword patterns for classifying PE/VC/buyout/growth/credit/RE
# from fund entity names (since Form D only has coarse "Other Investment Fund" type)
_STRATEGY_KEYWORDS: dict[str, list[str]] = {
    "buyout": [
        "buyout", "private equity", "capital partners", "equity partners",
        "acquisition fund", "lbo fund", "leveraged",
    ],
    "venture": [
        "venture capital", "venture fund", "venture partners", "ventures fund",
        "early stage", "seed fund", "pre-seed", "startup fund",
    ],
    "growth": [
        "growth equity", "growth capital", "growth fund", "growth partners",
        "expansion capital", "late stage growth",
    ],
    "credit": [
        "credit fund", "credit opportunities", "direct lending",
        "mezzanine fund", "distressed debt", "structured credit",
        "private credit", "private debt", "senior debt",
    ],
    "real_estate": [
        "real estate", "realty fund", "property fund",
        "real assets", "infrastructure fund", "opportunistic real estate",
        "commercial real estate",
    ],
    "hedge_fund": [
        "hedge fund", "master fund", "trading fund", "multi-strategy fund",
        "quant fund", "systematic",
    ],
}

# EFTS query fragments for each strategy type (broader, for text-search)
_STRATEGY_EFTS_TERMS: dict[str, str] = {
    "buyout": '"capital partners" OR "private equity" OR "equity partners"',
    "venture": '"venture capital" OR "venture fund" OR "venture partners"',
    "growth": '"growth equity" OR "growth capital" OR "growth fund"',
    "credit": '"credit fund" OR "direct lending" OR "private credit"',
    "real_estate": '"real estate fund" OR "real assets" OR "infrastructure fund"',
    "hedge_fund": '"hedge fund" OR "master fund"',
}


# ──────────────────────────────────────────────────────────────────────
#  Internal helpers
# ──────────────────────────────────────────────────────────────────────

def _get_json(url: str, params: dict | None = None, timeout: int = 20) -> tuple[dict | None, str | None]:
    try:
        r = requests.get(url, params=params, headers=_HEADERS, timeout=timeout)
        r.raise_for_status()
        return r.json(), None
    except requests.HTTPError as e:
        return None, f"HTTP {e.response.status_code}: {e}"
    except Exception as e:
        return None, str(e)


def _get_text(url: str, timeout: int = 20) -> tuple[str | None, str | None]:
    try:
        r = requests.get(url, headers=_HEADERS, timeout=timeout)
        r.raise_for_status()
        return r.text, None
    except requests.HTTPError as e:
        return None, f"HTTP {e.response.status_code}: {e}"
    except Exception as e:
        return None, str(e)


def _xml_url(cik: str, accession: str) -> str:
    return EDGAR_XML_BASE.format(cik=cik, accession_nodash=accession.replace("-", ""))


def _fmt_usd(raw: str) -> str:
    try:
        v = float(str(raw).replace(",", ""))
        if v == 0:
            return "$0"
        if v >= 1_000_000_000:
            return f"${v / 1_000_000_000:.2f}B"
        if v >= 1_000_000:
            return f"${v / 1_000_000:.1f}M"
        return f"${v:,.0f}"
    except Exception:
        return str(raw)


def _infer_strategy(name: str, xml_type: str = "") -> str:
    n = name.lower()
    if "hedge" in xml_type.lower():
        return "hedge_fund"
    for strategy, patterns in _STRATEGY_KEYWORDS.items():
        if any(p in n for p in patterns):
            return strategy
    if any(s in n for s in [
        "fund i ", "fund ii", "fund iii", "fund iv", "fund v",
        "partners i,", "partners ii", " lp", " l.p.",
    ]):
        return "pooled_fund"
    return "other"


def _matches_strategy_filter(name: str, fund_type: str) -> bool:
    """Name-only strategy filter used when XML is not parsed."""
    patterns = _STRATEGY_KEYWORDS.get(fund_type, [])
    n = name.lower()
    if not patterns:
        return True
    # Buyout gets wider matching since many PE funds don't say "buyout"
    if fund_type == "buyout":
        extra = ["partners", "capital", "equity", "investment fund", "pe fund"]
        return any(p in n for p in patterns) or any(p in n for p in extra)
    return any(p in n for p in patterns)


# ──────────────────────────────────────────────────────────────────────
#  Form D XML parser
# ──────────────────────────────────────────────────────────────────────

def parse_form_d_xml(xml_text: str, entity_name: str = "", file_date: str = "") -> dict:
    """
    Parse a Form D primary_doc.xml into a structured dict.

    Form D XML schema (EDGAR): each fund files a separate Form D document.
    Key sections: primaryIssuer, relatedPersonsList, offeringData.
    """
    try:
        root = ET.fromstring(xml_text)
    except ET.ParseError as e:
        return {"parse_error": str(e), "entity_name": entity_name, "file_date": file_date}

    def ft(*tags: str) -> str:
        for tag in tags:
            el = root.find(f".//{tag}")
            if el is not None and el.text and el.text.strip():
                return el.text.strip()
        return ""

    # Issuer
    name = ft("entityName") or entity_name
    ein = ft("ein")
    city = ft("city")
    state = ft("stateOrCountry")

    # Industry / fund type
    industry_type = ft("industryGroupType")
    fund_type_xml = ft("investmentFundType")
    is_pooled = ft("isPooledInvestmentFundType").lower() == "true"

    # Filing classification
    filing_type = ft("newOrAmendment")  # "New" or "Amendment"

    # Federal exemptions (Rule 506(b), 506(c), etc.)
    exemptions = [
        _RULE_LABELS.get(el.text.strip(), el.text.strip())
        for el in root.findall(".//federalExemptionsExclusions/item")
        if el.text and el.text.strip()
    ]

    # Offering amounts
    total_offering_raw = ft("totalOfferingAmount")
    total_sold_raw = ft("totalAmountSold")
    total_remaining_raw = ft("totalRemaining")
    min_invest_raw = ft("minimumInvestmentAccepted")

    # Investor counts
    num_inv_str = ft("totalNumberAlreadyInvested")
    num_investors = int(num_inv_str) if num_inv_str.isdigit() else 0

    # Dates
    date_first_sale = ft("value") or ft("dateOfFirstSale")

    # Securities type
    is_equity = ft("isEquityType").lower() == "true"
    is_debt = ft("isDebtType").lower() == "true"
    securities = "Equity" if is_equity else ("Debt" if is_debt else "Mixed/Other")

    # Duration
    multi_year = ft("moreThanOneYear").lower() == "true"

    # Related persons — GPs / executive officers
    key_persons = []
    for rp in root.findall(".//relatedPersonInfo")[:6]:
        first = (rp.findtext(".//firstName") or "").strip()
        last = (rp.findtext(".//lastName") or "").strip()
        person_name = f"{first} {last}".strip()

        # Roles may be nested differently across schema versions
        roles = [
            el.text.strip()
            for el in rp.findall(".//relatedPersonRelationship")
            if el.text and el.text.strip()
        ]
        if not roles:
            roles = [
                el.text.strip()
                for el in rp.findall(".//relationship")
                if el.text and el.text.strip()
            ]

        if person_name or roles:
            key_persons.append({"name": person_name, "roles": roles})

    total_offering_usd = 0.0
    try:
        total_offering_usd = float(total_offering_raw.replace(",", "")) if total_offering_raw else 0.0
    except (ValueError, AttributeError):
        pass

    return {
        "entity_name": name,
        "ein": ein,
        "city": city,
        "state": state,
        "file_date": file_date,
        "filing_type": filing_type or "Unknown",
        "is_pooled_fund": is_pooled,
        "industry_group": industry_type,
        "fund_type_declared": fund_type_xml,
        "strategy_inferred": _infer_strategy(name, fund_type_xml),
        "exemptions": exemptions,
        "securities_type": securities,
        "multi_year_offering": multi_year,
        "total_offering": _fmt_usd(total_offering_raw) if total_offering_raw else "Not disclosed",
        "total_offering_raw_usd": total_offering_usd,
        "total_sold": _fmt_usd(total_sold_raw) if total_sold_raw else "Not disclosed",
        "remaining": _fmt_usd(total_remaining_raw) if total_remaining_raw else "",
        "min_investment": _fmt_usd(min_invest_raw) if min_invest_raw else "Not specified",
        "num_investors_so_far": num_investors,
        "date_of_first_sale": date_first_sale,
        "key_persons": key_persons,
    }


# ──────────────────────────────────────────────────────────────────────
#  Public API
# ──────────────────────────────────────────────────────────────────────

def search_form_d_feed(
    days_back: int = 90,
    fund_type: str | None = None,
    min_offering_usd: int | None = None,
    max_offering_usd: int | None = None,
    keywords: str | None = None,
    new_filings_only: bool = True,
    max_results: int = 40,
    parse_xml: bool = False,
) -> dict:
    """
    Pull the live SEC Form D feed — new private fund capital raises.

    Answers questions like:
      "What new buyout funds launched in the last 90 days?"
      "Which VC funds over $100M filed Form D this quarter?"
      "What growth equity funds raised capital in the last year?"

    Args:
        days_back:        Look-back window in days. Default 90.
        fund_type:        Strategy filter — "buyout", "venture", "growth",
                          "credit", "real_estate", "hedge_fund", or None (all).
        min_offering_usd: Minimum total offering in dollars (e.g. 50_000_000).
        max_offering_usd: Maximum total offering in dollars.
        keywords:         Extra free-text search terms (GP name, sector, etc.).
        new_filings_only: Exclude D/A amendments — only new fund launches.
        max_results:      Results to return (default 40).
        parse_xml:        If True, fetch Form D XML per filing for offering size,
                          investor counts, and key persons (slower, ~1s/filing).
    """
    end_dt = datetime.today()
    start_dt = end_dt - timedelta(days=days_back)

    # Build EFTS query
    # "pooled investment fund" is a phrase present in the XML of every fund Form D,
    # reliably separating investment funds from operating company Reg D filings.
    q_parts = ['"pooled investment fund"']

    if fund_type and fund_type in _STRATEGY_EFTS_TERMS:
        q_parts.append(f"({_STRATEGY_EFTS_TERMS[fund_type]})")

    if keywords:
        q_parts.append(keywords)

    params: dict = {
        "q": " ".join(q_parts),
        "forms": "D" if new_filings_only else "D,D/A",
        "dateRange": "custom",
        "startdt": start_dt.strftime("%Y-%m-%d"),
        "enddt": end_dt.strftime("%Y-%m-%d"),
    }

    data, err = _get_json(EDGAR_EFTS_URL, params=params)
    if err or not data:
        return {"error": err or "No response from EDGAR EFTS", "query": params, "results": []}

    all_hits = data.get("hits", {}).get("hits", [])
    total_edgar = data.get("hits", {}).get("total", {}).get("value", 0)

    results = []
    for h in all_hits:
        src = h.get("_source", {})
        entity_name = src.get("entity_name", "")
        cik = str(src.get("entity_id", ""))
        accession = src.get("accession_no", "")
        file_date = src.get("file_date", "")
        form_type = src.get("form_type", "D")

        entry: dict = {
            "entity_name": entity_name,
            "cik": cik,
            "accession_no": accession,
            "file_date": file_date,
            "form_type": form_type,
            "strategy_inferred": _infer_strategy(entity_name),
            "edgar_url": EDGAR_COMPANY_URL.format(cik=cik),
            "xml_url": _xml_url(cik, accession) if cik and accession else "",
        }

        if parse_xml and cik and accession:
            xml_text, xml_err = _get_text(_xml_url(cik, accession))
            if xml_text:
                parsed = parse_form_d_xml(xml_text, entity_name, file_date)
                entry.update(parsed)
            else:
                entry["xml_error"] = xml_err

        # Post-parse strategy filter (when XML not fetched, use name match)
        if fund_type and fund_type != "all" and not parse_xml:
            if not _matches_strategy_filter(entity_name, fund_type):
                continue

        # Post-parse amount filter (only effective when XML parsed)
        if parse_xml and (min_offering_usd or max_offering_usd):
            raw = entry.get("total_offering_raw_usd", 0)
            if min_offering_usd and raw > 0 and raw < min_offering_usd:
                continue
            if max_offering_usd and raw > 0 and raw > max_offering_usd:
                continue

        results.append(entry)
        if len(results) >= max_results:
            break

    return {
        "date_range": f"{start_dt.strftime('%Y-%m-%d')} to {end_dt.strftime('%Y-%m-%d')}",
        "filters_applied": {
            "fund_type": fund_type or "all",
            "min_offering_usd": min_offering_usd,
            "max_offering_usd": max_offering_usd,
            "keywords": keywords,
            "new_filings_only": new_filings_only,
            "parse_xml": parse_xml,
        },
        "total_matching_edgar": total_edgar,
        "results_returned": len(results),
        "results": results,
        "how_to_get_details": (
            "Pass parse_xml=true to get offering size, investor counts, and key persons. "
            "Or use form_d_filing_detail tool with a specific cik + accession_no."
        ),
        "notes": {
            "506b": "Rule 506(b) = traditional private placement, no advertising to public",
            "506c": "Rule 506(c) = general solicitation allowed — manager is marketing broadly",
            "new_vs_amendment": "Form D = new fund launch; Form D/A = amendment to prior filing",
        },
    }


def get_form_d_detail(cik: str, accession_no: str) -> dict:
    """
    Fetch and fully parse a specific Form D filing XML.

    Returns complete structured data: offering amounts, key persons,
    exemptions, date of first sale, investor count, and min investment.

    Args:
        cik:          EDGAR CIK number (from search_form_d_feed results).
        accession_no: Accession number like "0001234567-25-000001".
    """
    url = _xml_url(cik, accession_no)
    xml_text, err = _get_text(url)
    if err or not xml_text:
        return {
            "error": err or "Could not fetch Form D XML",
            "cik": cik,
            "accession_no": accession_no,
            "xml_url": url,
            "edgar_url": EDGAR_COMPANY_URL.format(cik=cik),
        }

    result = parse_form_d_xml(xml_text)
    result["cik"] = cik
    result["accession_no"] = accession_no
    result["xml_url"] = url
    result["edgar_url"] = EDGAR_COMPANY_URL.format(cik=cik)
    return result


def search_form_d_by_manager(
    manager_name: str,
    days_back: int = 365 * 5,
    max_results: int = 25,
    parse_xml: bool = True,
) -> dict:
    """
    Search all Form D filings associated with a GP firm — tracks full fund family history.

    Useful for:
      - Identifying all fund vehicles under a GP umbrella
      - Tracking fund size growth across vintages
      - Spotting new fund series before public announcement

    Args:
        manager_name: GP firm name or partial name (e.g. "Vista Equity", "Thoma Bravo").
        days_back:    Look-back window (default 5 years to capture full vintage history).
        max_results:  Max filings to return.
        parse_xml:    Fetch XML for each hit to get offering sizes and key persons.
    """
    end_dt = datetime.today()
    start_dt = end_dt - timedelta(days=days_back)

    data, err = _get_json(EDGAR_EFTS_URL, params={
        "q": f'"{manager_name}"',
        "forms": "D,D/A",
        "dateRange": "custom",
        "startdt": start_dt.strftime("%Y-%m-%d"),
        "enddt": end_dt.strftime("%Y-%m-%d"),
    })
    if err or not data:
        return {"error": err, "manager": manager_name, "results": []}

    hits = data.get("hits", {}).get("hits", [])
    total = data.get("hits", {}).get("total", {}).get("value", 0)

    results = []
    for h in hits[:max_results]:
        src = h.get("_source", {})
        cik = str(src.get("entity_id", ""))
        accession = src.get("accession_no", "")
        entity_name = src.get("entity_name", "")
        file_date = src.get("file_date", "")

        entry: dict = {
            "entity_name": entity_name,
            "cik": cik,
            "accession_no": accession,
            "file_date": file_date,
            "form_type": src.get("form_type", "D"),
            "strategy_inferred": _infer_strategy(entity_name),
            "edgar_url": EDGAR_COMPANY_URL.format(cik=cik),
        }

        if parse_xml and cik and accession:
            xml_text, xml_err = _get_text(_xml_url(cik, accession))
            if xml_text:
                parsed = parse_form_d_xml(xml_text, entity_name, file_date)
                entry.update(parsed)
            else:
                entry["xml_error"] = xml_err

        results.append(entry)

    # Sort newest first
    results.sort(key=lambda x: x.get("file_date", ""), reverse=True)

    # Compute offering trajectory
    trajectory = []
    for r in results:
        if r.get("form_type") == "D" and r.get("total_offering_raw_usd", 0) > 0:
            trajectory.append({
                "fund": r["entity_name"],
                "filed": r["file_date"],
                "offering": r.get("total_offering", ""),
            })

    return {
        "manager": manager_name,
        "date_range": f"{start_dt.strftime('%Y-%m-%d')} to {end_dt.strftime('%Y-%m-%d')}",
        "total_filings_found": total,
        "results_returned": len(results),
        "new_funds_count": sum(1 for r in results if r.get("form_type") == "D"),
        "amendments_count": sum(1 for r in results if r.get("form_type") == "D/A"),
        "offering_trajectory": trajectory,
        "results": results,
    }
