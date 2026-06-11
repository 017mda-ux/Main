"""
LP mandate configuration and fund classification.

Encodes the LP's investment criteria as data, then scores any fund
(from Form D, placement agent teaser, or manual entry) against it:

  - Small buyout:  $200M - $1B
  - Mid buyout:    $2B - $5B
  - Large buyout:  $5B+
  - Growth equity: $200M+
  - Mid/late venture: $200M+
  - Early venture: $200M+ only (deprioritised — covered via fund-of-funds)
  - Emerging managers: Fund I-III preferred for new relationships
"""

from __future__ import annotations

import re

# ---------------------------------------------------------------------------
# Mandate definition
# ---------------------------------------------------------------------------

M = 1_000_000
B = 1_000_000_000

MANDATE_BANDS: list[dict] = [
    {"id": "small_buyout", "label": "Small Buyout", "strategy": "buyout",
     "min_usd": 200 * M, "max_usd": 1 * B, "priority": "core"},
    {"id": "mid_buyout", "label": "Mid Buyout", "strategy": "buyout",
     "min_usd": 2 * B, "max_usd": 5 * B, "priority": "core"},
    {"id": "large_buyout", "label": "Large Buyout", "strategy": "buyout",
     "min_usd": 5 * B, "max_usd": None, "priority": "core"},
    {"id": "growth", "label": "Growth Equity", "strategy": "growth",
     "min_usd": 200 * M, "max_usd": None, "priority": "core"},
    {"id": "mid_late_venture", "label": "Mid/Late-Stage Venture", "strategy": "venture",
     "min_usd": 200 * M, "max_usd": None, "priority": "core",
     "stage": ["mid", "late", "multi", "unknown"]},
    {"id": "early_venture", "label": "Early-Stage Venture", "strategy": "venture",
     "min_usd": 200 * M, "max_usd": None, "priority": "deprioritised",
     "stage": ["early", "seed"],
     "note": "Access already covered via fund-of-funds; only large early-stage funds"},
]

EMERGING_FUND_NUMBERS = (1, 2, 3)

# ---------------------------------------------------------------------------
# Fund number / vintage parsing
# ---------------------------------------------------------------------------

_ROMAN = {
    "i": 1, "ii": 2, "iii": 3, "iv": 4, "v": 5, "vi": 6, "vii": 7,
    "viii": 8, "ix": 9, "x": 10, "xi": 11, "xii": 12, "xiii": 13,
    "xiv": 14, "xv": 15,
}

# "Fund III", "Partners VI", "Ventures II", "Fund 3", trailing "III LP" etc.
_FUND_NUM_RE = re.compile(
    r"\b(?:fund|partners|ventures|capital|equity|opportunities|investors)\s+"
    r"(x{0,2}(?:i[xv]|v?i{0,3})|\d{1,2})\b[\s,.]*(?:l\.?p\.?|llc|scsp|\(a\))?",
    re.IGNORECASE,
)
_TRAILING_NUM_RE = re.compile(
    r"\b(x{0,2}(?:i[xv]|v?i{0,3})|\d{1,2})\s*,?\s*(?:l\.?p\.?|llc|scsp)?\s*$",
    re.IGNORECASE,
)


def parse_fund_number(fund_name: str) -> int | None:
    """Extract the fund sequence number from an entity name, if present."""
    for rx in (_FUND_NUM_RE, _TRAILING_NUM_RE):
        m = rx.search(fund_name)
        if not m:
            continue
        token = m.group(1).lower().strip()
        if not token:
            continue
        if token.isdigit():
            return int(token)
        if token in _ROMAN:
            return _ROMAN[token]
    return None


_EARLY_STAGE_HINTS = ["seed", "pre-seed", "early stage", "early-stage", "angel"]
_LATE_STAGE_HINTS = ["growth", "late stage", "late-stage", "expansion", "opportunity",
                     "crossover", "pre-ipo", "series b", "series c"]


def infer_venture_stage(text: str) -> str:
    """Classify a venture fund as early / late / unknown from its name+description."""
    t = text.lower()
    if any(h in t for h in _EARLY_STAGE_HINTS):
        return "early"
    if any(h in t for h in _LATE_STAGE_HINTS):
        return "late"
    return "unknown"


# ---------------------------------------------------------------------------
# Mandate scoring
# ---------------------------------------------------------------------------

def classify_fund(
    name: str,
    strategy: str,
    size_usd: int | None = None,
    description: str = "",
    fund_number: int | None = None,
) -> dict:
    """
    Score a fund against the mandate. Returns:
      band          - matched mandate band id or None
      fit           - "in_mandate" | "near_mandate" | "outside_mandate" | "size_unknown"
      emerging      - True if Fund I-III
      fund_number   - parsed or supplied sequence number
      flags         - human-readable notes for the feed card
    """
    if fund_number is None:
        fund_number = parse_fund_number(name)
    emerging = fund_number in EMERGING_FUND_NUMBERS if fund_number else None

    stage = infer_venture_stage(f"{name} {description}") if strategy == "venture" else None

    matched = None
    for band in MANDATE_BANDS:
        if band["strategy"] != strategy:
            continue
        if strategy == "venture" and stage == "early" and band["id"] != "early_venture":
            continue
        if strategy == "venture" and stage != "early" and band["id"] == "early_venture":
            continue
        if size_usd is None:
            matched = band  # strategy matches; size pending
            break
        lo, hi = band["min_usd"], band["max_usd"]
        if size_usd >= lo and (hi is None or size_usd <= hi):
            matched = band
            break

    flags: list[str] = []
    if size_usd is None:
        fit = "size_unknown" if matched else "outside_mandate"
        if matched:
            flags.append("Size undisclosed — confirm against mandate band")
    elif matched:
        fit = "in_mandate"
        if matched["priority"] == "deprioritised":
            fit = "near_mandate"
            flags.append(matched.get("note", "Deprioritised strategy"))
    else:
        # buyout $1-2B sits between the small and mid bands — flag, don't hide
        if strategy == "buyout" and 1 * B < size_usd < 2 * B:
            fit = "near_mandate"
            flags.append("Buyout $1-2B — between small and mid bands")
        elif size_usd < 200 * M:
            fit = "outside_mandate"
            flags.append("Below $200M size floor")
        else:
            fit = "outside_mandate"

    if fund_number is not None:
        if emerging:
            flags.append(f"Emerging manager — Fund {fund_number} (new-relationship target)")
        else:
            flags.append(f"Fund {fund_number} — established franchise, not emerging")
    else:
        flags.append("Fund number unknown — check if Fund I-III")

    return {
        "band": matched["id"] if matched else None,
        "band_label": matched["label"] if matched else None,
        "fit": fit,
        "emerging": emerging,
        "fund_number": fund_number,
        "venture_stage": stage,
        "flags": flags,
    }
