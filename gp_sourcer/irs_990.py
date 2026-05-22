"""
IRS Form 990 parser for LP fund commitment extraction.

Pulls Schedule D Part VII (Investments - Other Securities / LP interests) and
Schedule R (Related Organizations / Unrelated Partnerships) directly from the
IRS public 990 XML dataset on AWS S3 and IRS.gov.

Key entities for Ivy + hospital LP research:
  - Harvard Management Private Equity Corporation (EIN 04-3070522)
  - Harvard Management Company (EIN 23-7361259)
  - Yale University (EIN 06-0646973)
  - Princeton University (EIN 21-0634501)
  - Mass General Brigham (EIN 04-3230035)
  - Yale New Haven Hospital (EIN 06-0646652)
  - Dana-Farber Cancer Institute (EIN 04-2263923)
  - NewYork-Presbyterian Hospital (EIN 13-1624096)
  - Columbia University (EIN 13-5598093)
  - University of Pennsylvania (EIN 23-1352685)
"""

from __future__ import annotations

import csv
import io
import xml.etree.ElementTree as ET
from typing import Optional

import requests

# IRS 990 public data (no auth required, but must be accessed from client machines)
IRS_INDEX_URL = "https://apps.irs.gov/pub/epostcard/990/xml/{year}/index_{year}.csv"
IRS_XML_URL = "https://apps.irs.gov/pub/epostcard/990/xml/{year}/{object_id}_public.xml"

# Fallback: AWS S3 public bucket
S3_INDEX_URL = "https://s3.amazonaws.com/irs-form-990/index_{year}.json"
S3_XML_URL = "https://s3.amazonaws.com/irs-form-990/{object_id}_public.xml"

_HEADERS = {
    "User-Agent": "GP-Sourcing-Research research@gp-sourcer.io",
    "Accept": "*/*",
}

# Pre-defined EINs for Ivy endowments and hospital investment offices
KNOWN_LP_ENTITIES = {
    # Harvard ecosystem
    "Harvard Management Company": "237361259",
    "Harvard Management Private Equity Corp": "043070522",
    "Harvard University": "042103580",
    # Yale ecosystem
    "Yale University": "060646973",
    "Yale New Haven Hospital": "060646652",
    "Yale New Haven Health Services": "222529464",
    # Princeton
    "Princeton University (PRINCO)": "210634501",
    # Penn
    "University of Pennsylvania": "231352685",
    "Penn Medicine": "231352685",
    # Cornell
    "Cornell University": "150532082",
    # Columbia
    "Columbia University": "135598093",
    "NewYork-Presbyterian Hospital": "131624096",
    # Dartmouth
    "Dartmouth College": "020222111",
    # Brown
    "Brown University": "050258809",
    # Hospital investment pools
    "Mass General Brigham": "043230035",
    "Massachusetts General Hospital": "042697935",
    "Dana-Farber Cancer Institute": "042263923",
    "Brigham and Womens Hospital": "042693294",
    "Memorial Sloan Kettering": "131924236",
    "Johns Hopkins Hospital": "520591656",
    "Duke University Health System": "560529565",
}


def _get(url: str, timeout: int = 30, stream: bool = False) -> tuple[requests.Response | None, str | None]:
    try:
        r = requests.get(url, headers=_HEADERS, timeout=timeout, stream=stream)
        r.raise_for_status()
        return r, None
    except requests.HTTPError as e:
        return None, f"HTTP {e.response.status_code}: {e}"
    except Exception as e:
        return None, str(e)


def resolve_ein(name_or_ein: str) -> tuple[str, str]:
    """
    Given a name or EIN string, return (canonical_name, EIN digits-only).
    Checks KNOWN_LP_ENTITIES first; falls back to treating input as raw EIN.
    """
    # Strip formatting
    cleaned = name_or_ein.replace("-", "").replace(" ", "").strip()

    # Check by name (case-insensitive partial match)
    lower = name_or_ein.lower()
    for name, ein in KNOWN_LP_ENTITIES.items():
        if lower in name.lower() or name.lower() in lower:
            return name, ein

    # Assume it's an EIN
    if cleaned.isdigit():
        return name_or_ein, cleaned

    return name_or_ein, ""


def find_filings_by_ein(ein: str, years: list[int] | None = None) -> list[dict]:
    """
    Search IRS 990 filing indexes for all filings by a given EIN.
    Returns list of filing metadata dicts with object_id and year.
    """
    if years is None:
        years = [2024, 2023, 2022, 2021]

    ein_clean = ein.replace("-", "")
    found = []

    for year in years:
        url = IRS_INDEX_URL.format(year=year)
        resp, err = _get(url, timeout=45)
        if err or not resp:
            # Try S3 fallback
            s3_url = S3_INDEX_URL.format(year=year)
            resp, err2 = _get(s3_url, timeout=45)
            if err2 or not resp:
                continue

        try:
            text = resp.text
            reader = csv.DictReader(io.StringIO(text))
            for row in reader:
                row_ein = row.get("EIN", row.get("ein", "")).replace("-", "").strip()
                if row_ein == ein_clean:
                    found.append({
                        "year_filed": year,
                        "tax_period": row.get("TaxPeriod", row.get("taxperiod", "")),
                        "form_type": row.get("FormType", row.get("form_type", "990")),
                        "object_id": row.get("ObjectId", row.get("object_id", "")),
                        "org_name": row.get("OrganizationName", row.get("organization_name", "")),
                        "ein": ein_clean,
                    })
        except Exception:
            continue

    return found


def fetch_990_xml(object_id: str, year: int) -> tuple[str | None, str | None]:
    """Fetch the XML content of a specific 990 filing by object_id."""
    url = IRS_XML_URL.format(year=year, object_id=object_id)
    resp, err = _get(url, timeout=45)
    if err or not resp:
        # Try S3
        s3_url = S3_XML_URL.format(object_id=object_id)
        resp, err2 = _get(s3_url, timeout=45)
        if err2 or not resp:
            return None, err or err2
    return resp.text, None


def parse_schedule_d_investments(xml_content: str) -> list[dict]:
    """
    Parse IRS 990 Schedule D Part VII: Investments - Other Securities.
    Returns list of LP/fund investments with name, book value, and valuation method.
    """
    try:
        root = ET.fromstring(xml_content)
    except ET.ParseError as e:
        return [{"error": f"XML parse error: {e}"}]

    # Handle namespaced elements — IRS 990 XML uses URN namespaces
    ns = ""
    for elem in root.iter():
        if "}" in elem.tag:
            ns = elem.tag.split("}")[0] + "}"
            break

    def find(parent, *tags):
        for tag in tags:
            child = parent.find(f"{ns}{tag}")
            if child is not None:
                return child
        return None

    def findall(parent, *tags):
        for tag in tags:
            children = parent.findall(f"{ns}{tag}")
            if children:
                return children
        return []

    def text(elem) -> str:
        return (elem.text or "").strip() if elem is not None else ""

    investments = []

    # Search through the entire XML tree for Schedule D investment groups
    # The path varies by filing version and form type
    sched_d_paths = [
        "IRS990ScheduleD",
        "ReturnData/IRS990ScheduleD",
    ]

    sched_d = None
    for path in sched_d_paths:
        sched_d = root.find(f".//{ns}IRS990ScheduleD")
        if sched_d is not None:
            break

    if sched_d is None:
        # Look for it differently in group returns
        for elem in root.iter(f"{ns}IRS990ScheduleD"):
            sched_d = elem
            break

    if sched_d is None:
        return [{"note": "Schedule D not found in this filing (may be filed separately or entity uses pooled reporting)"}]

    # Part VII: Investments - Other Securities (LP interests live here)
    inv_groups = findall(
        sched_d,
        "InvestmentsOtherSecuritiesGrp",
        "OtherInvestmentsGrp",
    )

    for grp in inv_groups:
        items = findall(
            grp,
            "InvestmentsOtherSecurities",
            "OtherInvestments",
            "InvestmentsOtherSecuritiesGrp",
        )
        # Sometimes items are direct children
        if not items:
            items = [grp]

        for item in items:
            desc_elem = find(item, "Desc", "Description", "SecurityDesc")
            bv_elem = find(item, "BookValueAmt", "BookValue", "EndOfYearFMVAmt")
            method_elem = find(item, "ValuationMethodCd", "ValuationMethod")

            desc = text(desc_elem)
            bv = text(bv_elem)
            method = text(method_elem)

            # Map valuation codes
            method_map = {
                "C": "Cost",
                "E": "End-of-year FMV",
                "F": "Fair Market Value",
                "M": "Method description in Schedule O",
                "FMV": "Fair Market Value",
            }
            method_human = method_map.get(method, method)

            if desc or bv:
                investments.append({
                    "description": desc,
                    "book_value_usd": int(bv) if bv.isdigit() else bv,
                    "valuation_method": method_human,
                })

    # Also check for any unstructured investment listing in Schedule D Part VII total line
    if not investments:
        # Some orgs report only totals in Part VII with a single line
        total_elem = sched_d.find(f".//{ns}InvestmentsOtherSecuritiesAmt")
        if total_elem is not None:
            investments.append({
                "description": "TOTAL - Investments in Other Securities (LP interests aggregated)",
                "book_value_usd": text(total_elem),
                "note": "This entity reports LP investments as a single aggregate line. Schedule O or audited financials contain the fund-level detail.",
            })

    return investments


def parse_schedule_r_partnerships(xml_content: str) -> list[dict]:
    """
    Parse IRS 990 Schedule R: Related Organizations and Unrelated Partnerships.
    Returns unrelated partnership interests — PE funds often appear here when
    the filer is a non-controlling LP.
    """
    try:
        root = ET.fromstring(xml_content)
    except ET.ParseError as e:
        return [{"error": f"XML parse error: {e}"}]

    ns = ""
    for elem in root.iter():
        if "}" in elem.tag:
            ns = elem.tag.split("}")[0] + "}"
            break

    def text(elem) -> str:
        return (elem.text or "").strip() if elem is not None else ""

    partnerships = []

    for grp in root.iter(f"{ns}UnrelatedPartnershipGrp"):
        name_elem = grp.find(f"{ns}PartnershipName") or grp.find(f"{ns}BusinessName")
        ein_elem = grp.find(f"{ns}EIN")
        pct_elem = grp.find(f"{ns}EndingCapitalAcctPct") or grp.find(f"{ns}OwnershipPct")
        income_elem = grp.find(f"{ns}GrossReceiptsAmt") or grp.find(f"{ns}PartnershipIncomeLossAmt")
        asset_elem = grp.find(f"{ns}PartnershipTotalAssetsAmt")

        name_text = ""
        if name_elem is not None:
            biz_nm = name_elem.find(f"{ns}BusinessNameLine1Txt") or name_elem.find(f"{ns}Name")
            name_text = text(biz_nm) if biz_nm is not None else text(name_elem)

        partnerships.append({
            "partnership_name": name_text,
            "ein": text(ein_elem),
            "ownership_pct": text(pct_elem),
            "income_or_receipts_usd": text(income_elem),
            "total_assets_usd": text(asset_elem),
        })

    return partnerships


def get_lp_investments_from_990(
    name_or_ein: str,
    years: list[int] | None = None,
    max_filings: int = 2,
) -> dict:
    """
    Main entry point: given an entity name or EIN, find their 990 filings
    and extract LP fund investment data from Schedule D and Schedule R.
    """
    canonical_name, ein = resolve_ein(name_or_ein)
    if not ein:
        return {
            "error": f"Could not resolve EIN for '{name_or_ein}'. Provide EIN directly (e.g. '04-3070522').",
            "known_entities": list(KNOWN_LP_ENTITIES.keys()),
        }

    filings = find_filings_by_ein(ein, years=years or [2024, 2023, 2022, 2021])
    if not filings:
        return {
            "entity": canonical_name,
            "ein": ein,
            "error": (
                "No 990 filings found in the IRS index for the requested years. "
                "Possible reasons: entity files on paper (not electronically), "
                "fiscal year mismatch, or index not yet updated for recent filings. "
                "Try https://apps.irs.gov/app/eos/ with this EIN to find filings manually."
            ),
        }

    results = []
    for filing in filings[:max_filings]:
        obj_id = filing["object_id"]
        year = filing["year_filed"]

        if not obj_id:
            results.append({**filing, "error": "No object_id in index — filing may be unavailable"})
            continue

        xml_content, err = fetch_990_xml(obj_id, year)
        if err or not xml_content:
            results.append({**filing, "error": f"Could not download XML: {err}"})
            continue

        schedule_d = parse_schedule_d_investments(xml_content)
        schedule_r = parse_schedule_r_partnerships(xml_content)

        results.append({
            **filing,
            "schedule_d_lp_investments": schedule_d,
            "schedule_r_partnerships": schedule_r,
            "xml_url": IRS_XML_URL.format(year=year, object_id=obj_id),
        })

    return {
        "entity": canonical_name,
        "ein": ein,
        "filings_found": len(filings),
        "filings_parsed": len(results),
        "data": results,
        "note": (
            "Schedule D Part VII lists investments in other securities including LP interests. "
            "Universities often report aggregate LP values — fund-level names appear in "
            "Schedule O (supplemental statements) or audited financial statements. "
            "Hospital-affiliated entities (e.g. Mass General Brigham EIN 04-3230035) "
            "tend to have more granular LP disclosure."
        ),
    }


def batch_search_ivy_lps(years: list[int] | None = None) -> dict:
    """
    Search 990s for all known Ivy + hospital LP entities at once.
    Returns a summary of filings found and their investment data.
    """
    years = years or [2024, 2023, 2022]
    summary = {}

    priority_entities = {
        "Harvard Management Private Equity Corp": "043070522",
        "Harvard Management Company": "237361259",
        "Yale University": "060646973",
        "Princeton University (PRINCO)": "210634501",
        "Mass General Brigham": "043230035",
        "Yale New Haven Hospital": "060646652",
        "Columbia University": "135598093",
        "University of Pennsylvania": "231352685",
        "Dana-Farber Cancer Institute": "042263923",
        "NewYork-Presbyterian Hospital": "131624096",
    }

    for name, ein in priority_entities.items():
        result = get_lp_investments_from_990(ein, years=years, max_filings=1)
        filings_found = result.get("filings_found", 0)
        has_investments = any(
            f.get("schedule_d_lp_investments") or f.get("schedule_r_partnerships")
            for f in result.get("data", [])
        )
        summary[name] = {
            "ein": ein,
            "filings_found": filings_found,
            "has_investment_data": has_investments,
            "detail": result,
        }

    return summary
