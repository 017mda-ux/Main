"""
ProPublica Nonprofit Explorer — endowment and foundation 990 data.

Useful for identifying institutional LPs (endowments, foundations) and their
financial scale, which indicates potential PE/VC allocation capacity.
Free API, no key required.
"""

from __future__ import annotations

import requests

PROPUBLICA_SEARCH = "https://projects.propublica.org/nonprofits/api/v2/search.json"
PROPUBLICA_ORG = "https://projects.propublica.org/nonprofits/api/v2/organizations/{ein}.json"

_HEADERS = {"User-Agent": "GP-Sourcing-Research research@gp-sourcer.io"}


def _get(url: str, params: dict | None = None) -> tuple[dict | None, str | None]:
    try:
        r = requests.get(url, params=params, headers=_HEADERS, timeout=15)
        r.raise_for_status()
        return r.json(), None
    except Exception as e:
        return None, str(e)


def search_institutional_lps(name: str, max_results: int = 10) -> dict:
    """
    Search ProPublica for university endowments, foundations, and family offices
    by name. Returns financial scale metrics to assess LP capacity.

    NTEE codes searched:
      T = Philanthropy / Foundations
      W = Public & Societal Benefit
      B = Education (university endowments)
    """
    results_all = []
    for ntee in ["T", "W", "B"]:
        data, err = _get(PROPUBLICA_SEARCH, params={"q": name, "ntee[]": ntee})
        if data:
            results_all.extend(data.get("organizations", []))

    # Dedupe by EIN, sort by assets descending
    seen: set[str] = set()
    unique = []
    for o in results_all:
        ein = str(o.get("ein", ""))
        if ein and ein not in seen:
            seen.add(ein)
            unique.append(o)

    unique.sort(key=lambda x: x.get("asset_amount", 0) or 0, reverse=True)
    top = unique[:max_results]

    return {
        "total": len(unique),
        "results": [
            {
                "name": o.get("name", ""),
                "ein": o.get("ein", ""),
                "city": o.get("city", ""),
                "state": o.get("state", ""),
                "ntee_code": o.get("ntee_code", ""),
                "total_revenue_usd": o.get("income_amount", 0),
                "total_assets_usd": o.get("asset_amount", 0),
                "propublica_url": (
                    f"https://projects.propublica.org/nonprofits/organizations/{o.get('ein', '')}"
                ),
            }
            for o in top
        ],
    }


def get_lp_financials(ein: str) -> dict:
    """
    Get 990 financial detail for an endowment or foundation by EIN.
    Includes investment income and total asset trends — proxy for allocation capacity.
    """
    ein_clean = ein.replace("-", "")
    data, err = _get(PROPUBLICA_ORG.format(ein=ein_clean))
    if err or not data:
        return {"error": err, "ein": ein}

    org = data.get("organization", {})
    filings = data.get("filings_with_data", [])[:5]

    return {
        "name": org.get("name", ""),
        "ein": ein,
        "city": org.get("city", ""),
        "state": org.get("state", ""),
        "latest_total_assets_usd": org.get("asset_amount", 0),
        "latest_revenue_usd": org.get("income_amount", 0),
        "ntee_code": org.get("ntee_code", ""),
        "recent_filings": [
            {
                "tax_year": f.get("tax_prd_yr", ""),
                "total_revenue_usd": f.get("totrevenue", 0),
                "total_assets_usd": f.get("totassetsend", 0),
                "investment_income_usd": f.get("invstmntinc", 0),
                "total_expenses_usd": f.get("totfuncexpns", 0),
                "net_assets_usd": f.get("netassetsend", 0),
                "form_type": f.get("formtype", ""),
            }
            for f in filings
        ],
        "propublica_url": f"https://projects.propublica.org/nonprofits/organizations/{ein_clean}",
        "note": (
            "990-PF (private foundation) filings include Schedule B investment detail. "
            "To see specific GP fund investments, review the full 990-PF on EDGAR or ProPublica."
        ),
    }
