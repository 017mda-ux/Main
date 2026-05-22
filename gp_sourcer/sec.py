"""
SEC EDGAR and IAPD data retrieval for GP sourcing.

Free APIs:
  - IAPD (Investment Adviser Public Disclosure): registered advisers + Form ADV
  - EDGAR EFTS full-text search: Form D (fund raises) and Form ADV filings
"""

from __future__ import annotations

import requests

IAPD_SEARCH_URL = "https://api.adviserinfo.sec.gov/search/firm"
IAPD_FIRM_URL = "https://api.adviserinfo.sec.gov/firm/{crd}"
EDGAR_EFTS_URL = "https://efts.sec.gov/LATEST/search-index"

_HEADERS = {
    "User-Agent": "GP-Sourcing-Research research@gp-sourcer.io",
    "Accept": "application/json",
}


def _get(url: str, params: dict | None = None, timeout: int = 15) -> tuple[dict | None, str | None]:
    try:
        r = requests.get(url, params=params, headers=_HEADERS, timeout=timeout)
        r.raise_for_status()
        return r.json(), None
    except requests.HTTPError as e:
        return None, f"HTTP {e.response.status_code}: {e}"
    except Exception as e:
        return None, str(e)


def search_investment_advisers(query: str, max_results: int = 20) -> dict:
    """
    Search SEC IAPD for registered investment advisers (PE/VC/buyout firms).
    Falls back to EDGAR EFTS Form ADV search if IAPD is unavailable.
    """
    data, err = _get(IAPD_SEARCH_URL, params={
        "query": query,
        "hl": "true",
        "type": "firm",
        "hitsPerPage": str(max_results),
    })

    if not err and data:
        hits = data.get("hits", {}).get("hits", [])
        return {
            "source": "IAPD",
            "total": len(hits),
            "results": [
                {
                    "firm_name": h.get("_source", {}).get("firm_name", ""),
                    "crd": str(h.get("_source", {}).get("firm_id", "")),
                    "sec_number": h.get("_source", {}).get("sec_number", ""),
                    "registration_status": h.get("_source", {}).get("registration_status", ""),
                    "hq_state": h.get("_source", {}).get("state_cd", ""),
                }
                for h in hits
            ],
        }

    # Fallback: EDGAR EFTS full-text search on Form ADV filers
    data2, err2 = _get(EDGAR_EFTS_URL, params={
        "q": f'"{query}"',
        "forms": "ADV",
    })
    if err2 or not data2:
        return {"results": [], "error": err or err2, "source": "none"}

    hits = data2.get("hits", {}).get("hits", [])[:max_results]
    return {
        "source": "EDGAR_EFTS_ADV",
        "total": data2.get("hits", {}).get("total", {}).get("value", 0),
        "results": [
            {
                "firm_name": h.get("_source", {}).get("entity_name", ""),
                "cik": h.get("_source", {}).get("entity_id", ""),
                "filing_date": h.get("_source", {}).get("file_date", ""),
                "accession": h.get("_source", {}).get("accession_no", ""),
            }
            for h in hits
        ],
    }


def get_adviser_form_adv(crd: str) -> dict:
    """
    Get Form ADV regulatory details for an investment adviser by CRD number.
    Returns AUM, client types, advisory services, headcount, and location.
    """
    data, err = _get(IAPD_FIRM_URL.format(crd=crd))
    if err or not data:
        return {"error": err or "No data returned", "crd": crd}

    # Defensive parse — IAPD nesting varies by registration type
    root = data[0] if isinstance(data, list) and data else data
    ia = root.get("iaInfo", root)
    basic = ia.get("basicInfo", ia)
    reg = ia.get("iaRegistrationInfo", {})

    return {
        "firm_name": basic.get("primaryBusinessName", basic.get("firmName", "")),
        "crd": crd,
        "registration_date": reg.get("registrationDate", basic.get("registrationDate", "")),
        "website": basic.get("officialWebsite", basic.get("firmWebsite", "")),
        "hq_city": basic.get("mainOfficeCity", ""),
        "hq_state": basic.get("mainOfficeStateCode", basic.get("mainOfficeState", "")),
        "total_employees": basic.get("totalEmployees", basic.get("numberOfEmployees", 0)),
        "regulatory_aum_usd": basic.get("totalAum", basic.get("totalRegulatoryAum", 0)),
        "discretionary_aum_usd": basic.get("discretionaryAum", 0),
        "num_accounts": basic.get("totalAccounts", 0),
        "client_types": basic.get("clientTypes", ia.get("typesOfClients", [])),
        "advisory_services": basic.get("advisoryServices", ia.get("typesOfAdvisoryServices", [])),
        "compensation_arrangements": basic.get("compensationArrangements", []),
        "iapd_url": f"https://adviserinfo.sec.gov/firm/summary/{crd}",
    }


def search_form_d_fundraising(firm_name: str, start_date: str = "2020-01-01", max_results: int = 25) -> dict:
    """
    Search EDGAR for Form D private placement filings by a GP firm.
    Form D is filed when a private fund first sells securities — tracks fund launches/closes.
    Newer fund entities (e.g. 'Blackstone Capital Partners X LP') appear as separate filers.
    """
    data, err = _get(EDGAR_EFTS_URL, params={
        "q": f'"{firm_name}"',
        "forms": "D",
        "dateRange": "custom",
        "startdt": start_date,
    })
    if err or not data:
        return {"results": [], "error": err}

    hits = data.get("hits", {}).get("hits", [])[:max_results]
    total = data.get("hits", {}).get("total", {}).get("value", 0)

    return {
        "total": total,
        "results": [
            {
                "entity_name": h.get("_source", {}).get("entity_name", ""),
                "file_date": h.get("_source", {}).get("file_date", ""),
                "period_of_report": h.get("_source", {}).get("period_of_report", ""),
                "accession": h.get("_source", {}).get("accession_no", ""),
                "cik": h.get("_source", {}).get("entity_id", ""),
                "edgar_url": (
                    "https://www.sec.gov/cgi-bin/browse-edgar"
                    f"?action=getcompany&CIK={h.get('_source', {}).get('entity_id', '')}"
                    "&type=D&dateb=&owner=include&count=40"
                ),
            }
            for h in hits
        ],
        "note": (
            "Each LP fund vehicle is a separate Form D filer. "
            "Search for fund family names (e.g. 'Vista Equity') rather than specific fund names "
            "to capture the full fundraising history."
        ),
    }
