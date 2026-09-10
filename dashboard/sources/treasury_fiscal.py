"""Treasury FiscalData API — issuance, deficit, cash balance, debt.

Open, keyless, and the authoritative record for anything fiscal.
Docs: https://fiscaldata.treasury.gov/api-documentation/
"""

from __future__ import annotations

from datetime import date, datetime

from .http import HttpError, get_json

BASE = "https://api.fiscaldata.treasury.gov/services/api/fiscal_service"


def _query(path: str, *, fields: str = "", sort: str = "-record_date",
           filters: str = "", size: int = 100, **kw) -> list[dict]:
    parts = [f"sort={sort}", f"page%5Bsize%5D={size}"]
    if fields:
        parts.append(f"fields={fields}")
    if filters:
        parts.append(f"filter={filters}")
    url = f"{BASE}/{path}?" + "&".join(parts)
    payload = get_json(url, **kw)
    if "data" not in payload:
        raise HttpError(f"FiscalData {path}: no data key")
    return payload["data"]


def _d(s: str) -> date | None:
    try:
        return datetime.strptime(s[:10], "%Y-%m-%d").date()
    except (ValueError, TypeError):
        return None


def _f(s) -> float | None:
    try:
        return float(str(s).replace(",", ""))
    except (ValueError, TypeError):
        return None


def operating_cash_balance(size: int = 60, **kw) -> list[dict]:
    """Treasury General Account, from the Daily Treasury Statement."""
    rows = _query(
        "v1/accounting/dts/operating_cash_balance",
        fields="record_date,account_type,open_today_bal,close_today_bal",
        size=size, **kw,
    )
    out = []
    for r in rows:
        if "Treasury General Account" not in (r.get("account_type") or ""):
            continue
        out.append({
            "date": _d(r.get("record_date", "")),
            "close": _f(r.get("close_today_bal")),
        })
    return [r for r in out if r["date"]]


def monthly_deficit(size: int = 36, **kw) -> list[dict]:
    """Monthly Treasury Statement receipts, outlays and the resulting balance."""
    rows = _query(
        "v1/accounting/mts/mts_table_1",
        fields=("record_date,classification_desc,current_month_gross_rcpt_amt,"
                "current_month_gross_outly_amt,current_month_dfct_sur_amt,"
                "current_fytd_dfct_sur_amt"),
        size=size, **kw,
    )
    out = []
    for r in rows:
        if "Total" not in (r.get("classification_desc") or ""):
            continue
        out.append({
            "date": _d(r.get("record_date", "")),
            "receipts": _f(r.get("current_month_gross_rcpt_amt")),
            "outlays": _f(r.get("current_month_gross_outly_amt")),
            "balance": _f(r.get("current_month_dfct_sur_amt")),
            "fytd_balance": _f(r.get("current_fytd_dfct_sur_amt")),
        })
    return [r for r in out if r["date"]]


def debt_outstanding(size: int = 90, **kw) -> list[dict]:
    """Total public debt outstanding, daily."""
    rows = _query(
        "v2/accounting/od/debt_to_penny",
        fields="record_date,tot_pub_debt_out_amt",
        size=size, **kw,
    )
    return [
        {"date": _d(r.get("record_date", "")), "total": _f(r.get("tot_pub_debt_out_amt"))}
        for r in rows if _d(r.get("record_date", ""))
    ]


def auction_results(size: int = 60, **kw) -> list[dict]:
    """Recent auctions with the tail and bid-to-cover — the demand read."""
    rows = _query(
        "v1/accounting/od/auctions_query",
        fields=("record_date,security_type,security_term,auction_date,"
                "issue_date,high_yield,bid_to_cover_ratio,"
                "indirect_bidder_accepted,primary_dealer_accepted,"
                "offering_amt"),
        sort="-auction_date", size=size, **kw,
    )
    out = []
    for r in rows:
        out.append({
            "auction_date": _d(r.get("auction_date", "")),
            "type": r.get("security_type"),
            "term": r.get("security_term"),
            "high_yield": _f(r.get("high_yield")),
            "bid_to_cover": _f(r.get("bid_to_cover_ratio")),
            "indirect": _f(r.get("indirect_bidder_accepted")),
            "dealer": _f(r.get("primary_dealer_accepted")),
            "offering": _f(r.get("offering_amt")),
        })
    return [r for r in out if r["auction_date"]]


def interest_expense(size: int = 24, **kw) -> list[dict]:
    """Interest expense on the public debt — the fiscal cost of the curve."""
    rows = _query(
        "v2/accounting/od/interest_expense",
        fields="record_date,expense_type_desc,month_expense_amt,fytd_expense_amt",
        size=size, **kw,
    )
    return [
        {
            "date": _d(r.get("record_date", "")),
            "type": r.get("expense_type_desc"),
            "month": _f(r.get("month_expense_amt")),
            "fytd": _f(r.get("fytd_expense_amt")),
        }
        for r in rows if _d(r.get("record_date", ""))
    ]
