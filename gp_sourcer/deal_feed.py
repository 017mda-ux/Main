"""
Deal Flow Feed — the primary view.

Merges fund opportunities from all sources, scores each against the LP
mandate (mandate.py), and ranks: in-mandate emerging managers first.

Live source: form_d_feed.search_form_d_feed (SEC EDGAR EFTS).
Fallback/seed: SEED_FILINGS — current filings compiled from Dakota's weekly
Form D coverage (March-June 2026) for environments where EDGAR is blocked.
"""

from __future__ import annotations

from .mandate import classify_fund

# Compiled from Dakota "Top 10 New Form D Filings" weekly coverage and
# monthly fund launch reports, March-June 2026. sizes are None where the
# Form D amount was undisclosed/indefinite.
SEED_FILINGS: list[dict] = [
    # --- Buyout / PE ---
    {"fund_name": "Centre Lane Partners VI, L.P.", "gp_name": "Centre Lane Partners",
     "strategy": "buyout", "size_usd": None, "file_date": "2026-05-06",
     "description": "Middle-market PE — carve-outs, distressed, complex situations, North America",
     "source": "Form D via Dakota (May 4-8)"},
    {"fund_name": "Northmont Capital Evergreen Fund, L.P.", "gp_name": "Northmont Capital",
     "strategy": "buyout", "size_usd": None, "file_date": "2026-05-05", "fund_number": 1,
     "description": "Evergreen lower middle-market buyout — healthcare, industrial, business services",
     "source": "Form D via Dakota (May 4-8)"},
    {"fund_name": "TerraNova Partners Fund I", "gp_name": "TerraNova Partners",
     "strategy": "buyout", "size_usd": None, "file_date": "2026-05-27",
     "description": "Middle-market buyout — established Canadian businesses with strong cash flows",
     "source": "Form D via Dakota (May 25-29)"},
    {"fund_name": "Benford Capital Partners III UGM CIV-A, L.P.", "gp_name": "Benford Capital Partners",
     "strategy": "buyout", "size_usd": None, "file_date": "2026-04-15", "fund_number": 3,
     "description": "Lower middle-market control — industrials and business services",
     "source": "Form D via Dakota (Apr 13-17)"},
    {"fund_name": "Harbor Anchor I LP", "gp_name": "Harbor Anchor",
     "strategy": "buyout", "size_usd": None, "file_date": "2026-04-22",
     "description": "Lower middle-market manufacturing, Virginia / Southeast US, active ownership",
     "source": "Form D via Dakota (Apr 20-24)"},
    {"fund_name": "Breakwall Harbor Fund, L.P.", "gp_name": "Breakwall",
     "strategy": "buyout", "size_usd": None, "file_date": "2026-04-21", "fund_number": 1,
     "description": "2026-vintage closed-end PE — opportunistic and co-investment transactions",
     "source": "Form D via Dakota (Apr 20-24)"},
    {"fund_name": "Snowhawk Capital Digital Opportunities SMA I LP", "gp_name": "Snowhawk Partners",
     "strategy": "buyout", "size_usd": None, "file_date": "2026-05-04",
     "description": "Majority investments in digital infrastructure — data centers, cloud, connectivity",
     "source": "Form D via Dakota (May 4-8)"},
    {"fund_name": "Blackstone I Fund Absolute Return L.P.", "gp_name": "Blackstone",
     "strategy": "buyout", "size_usd": None, "file_date": "2026-05-13",
     "description": "Absolute return via undervalued assets, multi-sector global",
     "source": "Form D via Dakota (May 11-15)"},
    # --- Growth equity ---
    {"fund_name": "West Street Growth Equity Partners II", "gp_name": "Goldman Sachs Asset Management",
     "strategy": "growth", "size_usd": None, "file_date": "2026-05-07",
     "description": "Minority growth stakes — enterprise tech, fintech, healthcare, consumer, global",
     "source": "Form D via Dakota (May 4-8)"},
    {"fund_name": "Hughes Growth Equity Fund II", "gp_name": "Hughes & Company",
     "strategy": "growth", "size_usd": None, "file_date": "2026-05-28",
     "description": "Lower middle-market growth — healthcare and software, Chicago",
     "source": "Form D via Dakota (May 25-29)"},
    {"fund_name": "Crescent Growth I", "gp_name": "Crescent Capital Partners",
     "strategy": "growth", "size_usd": None, "file_date": "2026-05-20",
     "description": "Mid-market growth, Australia/NZ; firm has raised $3B+ across six funds since 2000",
     "source": "Form D via Dakota (May 18-22)"},
    {"fund_name": "General Atlantic (TRA) Coinvest, L.P.", "gp_name": "General Atlantic",
     "strategy": "growth", "size_usd": None, "file_date": "2026-04-23",
     "description": "Co-invest alongside GA primary funds — growth equity across sectors",
     "source": "Form D via Dakota (Apr 20-24)"},
    # --- Venture ---
    {"fund_name": "Crosscourt Ventures II, LP", "gp_name": "Crosscourt",
     "strategy": "venture", "size_usd": None, "file_date": "2026-05-05",
     "description": "Early-stage — AI, defense, space, robotics, healthcare, software; San Francisco",
     "source": "Form D via Dakota (May 4-8)"},
    {"fund_name": "Cambium Capital Partners III LP", "gp_name": "Cambium Capital",
     "strategy": "venture", "size_usd": None, "file_date": "2026-05-06",
     "description": "Venture — advanced computing technology companies",
     "source": "Form D via Dakota (May 4-8)"},
    {"fund_name": "Banyan Ventures Fund II", "gp_name": "Banyan Ventures",
     "strategy": "venture", "size_usd": None, "file_date": "2026-05-27",
     "description": "Series A/B software and SaaS — Intermountain West",
     "source": "Form D via Dakota (May 25-29)"},
    {"fund_name": "Moonfire Ventures Fund III LP", "gp_name": "Moonfire",
     "strategy": "venture", "size_usd": None, "file_date": "2026-05-26",
     "description": "Early-stage European technology, London",
     "source": "Form D via Dakota (May 25-29)"},
    {"fund_name": "IEQ Capital Access Fund - IEQ VC 2026, L.P.", "gp_name": "iCapital / IEQ Capital",
     "strategy": "venture", "size_usd": None, "file_date": "2026-04-08",
     "description": "Later-stage venture access fund — North American technology",
     "source": "Form D via Dakota (Apr 6-10)"},
    {"fund_name": "Private Access Cybersecurity 2026 Fund LP", "gp_name": "iCapital",
     "strategy": "venture", "size_usd": None, "file_date": "2026-04-09",
     "description": "Growth-stage cybersecurity access vehicle",
     "source": "Form D via Dakota (Apr 6-10)"},
    # --- Credit (outside mandate, shown for completeness in unfiltered view) ---
    {"fund_name": "Centerbridge Special Credit Partners V", "gp_name": "Centerbridge Partners",
     "strategy": "credit", "size_usd": None, "file_date": "2026-05-12",
     "description": "Opportunistic / distressed credit, North America",
     "source": "Form D via Dakota (May 11-15)"},
    {"fund_name": "Kohlberg Private Credit TE Investors, L.P.", "gp_name": "Kohlberg & Company",
     "strategy": "credit", "size_usd": None, "file_date": "2026-05-13",
     "description": "Middle-market private credit, tax-exempt sleeve",
     "source": "Form D via Dakota (May 11-15)"},
]

_FIT_RANK = {"in_mandate": 0, "size_unknown": 1, "near_mandate": 2, "outside_mandate": 3}


def build_deal_feed(
    filings: list[dict] | None = None,
    strategy: str | None = None,
    fit: str | None = None,              # "in_mandate" | "near_mandate" | "outside_mandate" | "size_unknown"
    emerging_only: bool = False,
    include_outside_mandate: bool = True,
    limit: int = 50,
) -> dict:
    """
    Score filings against the mandate and return ranked feed cards.
    If `filings` is None, uses SEED_FILINGS (live EDGAR results should be
    passed in from form_d_feed when network access allows).
    """
    rows = filings if filings is not None else SEED_FILINGS
    cards = []
    for f in rows:
        cls = classify_fund(
            name=f["fund_name"],
            strategy=f.get("strategy", ""),
            size_usd=f.get("size_usd"),
            description=f.get("description", ""),
            fund_number=f.get("fund_number"),
        )
        card = {**f, **cls}
        if strategy and card.get("strategy") != strategy:
            continue
        if fit and card["fit"] != fit:
            continue
        if emerging_only and not card["emerging"]:
            continue
        if not include_outside_mandate and card["fit"] == "outside_mandate":
            continue
        cards.append(card)

    cards.sort(key=lambda c: (
        _FIT_RANK.get(c["fit"], 9),
        0 if c["emerging"] else 1,
        c.get("file_date", ""),
    ))
    counts = {
        "total": len(cards),
        "emerging": sum(1 for c in cards if c["emerging"]),
        "in_mandate_or_pending": sum(1 for c in cards if c["fit"] in ("in_mandate", "size_unknown")),
    }
    return {"cards": cards[:limit], "summary": counts,
            "data_source": "live_edgar" if filings is not None else "seed_dakota_2026"}
