"""
What the dashboard tracks, and the thresholds that decide what earns a slot.

Everything here is declarative so the watchlist can be edited without touching
collection or render logic.  Sources are restricted to official statistical
agencies, the central bank, the fiscal authority, and primary exchange data.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal

# ──────────────────────────────────────────────────────────────────────
#  Series registry
# ──────────────────────────────────────────────────────────────────────

Bucket = Literal[
    "policy",      # front-end / Fed reaction function
    "curve",       # Treasury curve shape and term premium
    "fiscal",      # issuance, deficit, cash balance
    "fx",
    "commodity",
    "equity",
    "credit",
    "activity",    # real-economy prints
]


@dataclass(frozen=True)
class Series:
    """One tracked time series and how to judge whether it is interesting."""

    key: str
    label: str
    bucket: Bucket
    source: str                 # adapter name in dashboard.sources
    source_id: str              # series id within that source
    unit: str = "pct"           # pct | bp | usd | index | ratio | count
    decimals: int = 2
    # A move this many trailing standard deviations counts as notable.
    z_notable: float = 1.5
    # Levels in the top/bottom N% of their trailing window are notable on their own.
    extreme_pctile: float = 5.0
    # Trailing window (business days) for vol and percentile context.
    window: int = 504
    invert: bool = False        # True where "up" is risk-off (e.g. spreads)


SERIES: tuple[Series, ...] = (
    # ---- Policy / front end -------------------------------------------------
    Series("EFFR", "Effective fed funds", "policy", "fred", "EFFR", "pct", 2),
    Series("SOFR", "SOFR", "policy", "fred", "SOFR", "pct", 2),
    Series("DGS3MO", "3-month bill", "policy", "fred", "DGS3MO", "pct", 2),
    Series("DGS2", "2-year", "policy", "fred", "DGS2", "pct", 2, z_notable=1.25),
    # Front-end expectations proxy: 2y less effective funds tells you how much
    # policy change the market has embedded over the next ~2 years.
    Series("SOFR_IORB", "SOFR less IORB", "policy", "fred", "IORB", "bp", 0),

    # ---- Curve --------------------------------------------------------------
    Series("DGS5", "5-year", "curve", "fred", "DGS5", "pct", 2),
    Series("DGS10", "10-year", "curve", "fred", "DGS10", "pct", 2, z_notable=1.25),
    Series("DGS30", "30-year", "curve", "fred", "DGS30", "pct", 2, z_notable=1.25),
    Series("T10Y2Y", "2s10s", "curve", "fred", "T10Y2Y", "bp", 0),
    Series("T10Y3M", "3m10s", "curve", "fred", "T10Y3M", "bp", 0),
    Series("DFII10", "10y real (TIPS)", "curve", "fred", "DFII10", "pct", 2),
    Series("T10YIE", "10y breakeven", "curve", "fred", "T10YIE", "pct", 2),
    Series("T5YIFR", "5y5y forward inflation", "curve", "fred", "T5YIFR", "pct", 2),
    Series("THREEFYTP10", "10y term premium (ACM)", "curve", "fred", "THREEFYTP10", "pct", 2),

    # ---- Fiscal -------------------------------------------------------------
    Series("WTREGEN", "Treasury General Account", "fiscal", "fred", "WTREGEN", "usd", 0),
    Series("RRPONTSYD", "Overnight reverse repo", "fiscal", "fred", "RRPONTSYD", "usd", 0),
    Series("WALCL", "Fed balance sheet", "fiscal", "fred", "WALCL", "usd", 0),

    # ---- FX -----------------------------------------------------------------
    Series("DTWEXBGS", "Broad dollar index", "fx", "fred", "DTWEXBGS", "index", 2),
    Series("DEXUSEU", "EUR/USD", "fx", "fred", "DEXUSEU", "index", 4),
    Series("DEXJPUS", "USD/JPY", "fx", "fred", "DEXJPUS", "index", 2),
    Series("DEXCHUS", "USD/CNY", "fx", "fred", "DEXCHUS", "index", 4),
    Series("DEXUSUK", "GBP/USD", "fx", "fred", "DEXUSUK", "index", 4),
    Series("DEXCAUS", "USD/CAD", "fx", "fred", "DEXCAUS", "index", 4),
    Series("DEXKOUS", "USD/KRW", "fx", "fred", "DEXKOUS", "index", 2),
    Series("DEXMXUS", "USD/MXN", "fx", "fred", "DEXMXUS", "index", 4),

    # ---- Commodities --------------------------------------------------------
    Series("GOLD", "Gold", "commodity", "stooq", "xauusd", "usd", 2),
    Series("COPPER", "Copper", "commodity", "stooq", "hg.f", "usd", 4),
    Series("BRENT", "Brent crude", "commodity", "fred", "DCOILBRENTEU", "usd", 2),
    Series("WTI", "WTI crude", "commodity", "fred", "DCOILWTICO", "usd", 2),

    # ---- Equity / vol -------------------------------------------------------
    Series("SPX", "S&P 500", "equity", "stooq", "^spx", "index", 2),
    Series("NDX", "Nasdaq 100", "equity", "stooq", "^ndx", "index", 2),
    Series("VIX", "VIX", "equity", "fred", "VIXCLS", "index", 2, invert=True),
    Series("MOVE", "MOVE (rate vol)", "equity", "stooq", "^move", "index", 2, invert=True),

    # ---- Credit -------------------------------------------------------------
    Series("HY_OAS", "US high yield OAS", "credit", "fred",
           "BAMLH0A0HYM2", "bp", 0, invert=True),
    Series("IG_OAS", "US IG OAS", "credit", "fred",
           "BAMLC0A0CM", "bp", 0, invert=True),
    Series("CCC_OAS", "CCC & lower OAS", "credit", "fred",
           "BAMLH0A3HYC", "bp", 0, invert=True),
)

SERIES_BY_KEY = {s.key: s for s in SERIES}


# ──────────────────────────────────────────────────────────────────────
#  Cross-asset ratios
# ──────────────────────────────────────────────────────────────────────

@dataclass(frozen=True)
class Ratio:
    """A derived ratio, optionally compared against a benchmark series.

    `scale` puts the ratio on a comparable axis to `versus` so the two can be
    read on one scale — never a dual y-axis (see dataviz rules).
    """

    key: str
    label: str
    numerator: str
    denominator: str
    scale: float = 1.0
    versus: str | None = None
    note: str = ""


RATIOS: tuple[Ratio, ...] = (
    Ratio(
        "COPPER_GOLD", "Copper / gold", "COPPER", "GOLD", scale=1000.0,
        versus="DGS10",
        note="Classic growth-vs-debasement read. The ratio and the 10y normally "
             "track; a wide gap means one of them is pricing something the "
             "other is not.",
    ),
    Ratio(
        "GOLD_OIL", "Gold / oil", "GOLD", "BRENT", scale=1.0,
        note="Barrels of Brent per ounce. Spikes on either a supply shock or a "
             "flight into gold — check which leg moved.",
    ),
    Ratio(
        "SPX_GOLD", "S&P 500 / gold", "SPX", "GOLD", scale=1.0,
        note="Equities priced in hard money; strips out currency debasement.",
    ),
    Ratio(
        "STOCK_BOND", "Stocks / long bonds", "SPX", "DGS30", scale=1.0,
        note="Relative performance of duration versus equity risk.",
    ),
    Ratio(
        "REAL_10Y_GOLD", "10y real yield vs gold", "DFII10", "GOLD", scale=1.0,
        note="Gold's usual inverse. A positive correlation regime means the "
             "bid is fiscal, not monetary.",
    ),
)


# ──────────────────────────────────────────────────────────────────────
#  Moving-average configuration
# ──────────────────────────────────────────────────────────────────────

MA_FAST = 50
MA_SLOW = 200
# Flag a cross as "approaching" when the two averages are within this
# percentage of each other and closing.
MA_PROXIMITY_PCT = 1.5

# Series and ratios watched for 50/200 crosses.
MA_WATCH: tuple[str, ...] = (
    "SPX", "NDX", "GOLD", "COPPER", "BRENT", "DGS10", "DGS2",
    "DTWEXBGS", "DEXJPUS", "HY_OAS",
    "COPPER_GOLD", "GOLD_OIL", "SPX_GOLD",
)


# ──────────────────────────────────────────────────────────────────────
#  Release calendar / consensus
# ──────────────────────────────────────────────────────────────────────

@dataclass(frozen=True)
class Release:
    """A scheduled data release worth tracking against consensus."""

    key: str
    label: str
    agency: str
    # Salience multiplier — how much this print typically moves rates.
    weight: float = 1.0
    source: str = "bls"
    source_id: str = ""


RELEASES: tuple[Release, ...] = (
    Release("CPI", "Consumer Price Index", "BLS", 1.0, "bls", "CUSR0000SA0"),
    Release("CORECPI", "Core CPI", "BLS", 1.0, "bls", "CUSR0000SA0L1E"),
    Release("NFP", "Nonfarm payrolls", "BLS", 1.0, "bls", "CES0000000001"),
    Release("UNRATE", "Unemployment rate", "BLS", 0.8, "bls", "LNS14000000"),
    Release("AHE", "Average hourly earnings", "BLS", 0.6, "bls", "CES0500000003"),
    Release("PPI", "Producer Price Index", "BLS", 0.5, "bls", "WPUFD4"),
    Release("PCE", "PCE price index", "BEA", 1.0, "fred", "PCEPILFE"),
    Release("RETAIL", "Retail sales", "Census", 0.7, "fred", "RSAFS"),
    Release("ISM", "ISM manufacturing", "ISM", 0.6, "fred", "NAPM"),
)


# ──────────────────────────────────────────────────────────────────────
#  Primary-source feeds
# ──────────────────────────────────────────────────────────────────────

FEEDS: dict[str, str] = {
    "fed_press": "https://www.federalreserve.gov/feeds/press_all.xml",
    "fed_speeches": "https://www.federalreserve.gov/feeds/speeches.xml",
    "fed_testimony": "https://www.federalreserve.gov/feeds/testimony.xml",
    "fed_fomc": "https://www.federalreserve.gov/feeds/press_monetary.xml",
    "treasury_press": "https://home.treasury.gov/rss/press.xml",
    "treasury_remarks": "https://home.treasury.gov/rss/statements-remarks.xml",
    "bls_news": "https://www.bls.gov/feed/bls_latest.rss",
    "bea_news": "https://apps.bea.gov/rss/rss.xml",
    "cbo": "https://www.cbo.gov/publications/all/rss.xml",
    "eia": "https://www.eia.gov/rss/todayinenergy.xml",
}

# Officials whose remarks are tracked out of the feeds above.  Matching is on
# surname within the item title/description.
FED_PRINCIPALS: tuple[str, ...] = (
    "Warsh", "Jefferson", "Williams", "Bowman", "Waller", "Barr",
    "Cook", "Kugler", "Goolsbee", "Logan", "Schmid", "Musalem",
    "Hammack", "Collins", "Kashkari", "Daly", "Bostic", "Harker",
)

CABINET_PRINCIPALS: tuple[str, ...] = (
    "Bessent",     # Treasury
    "Lutnick",     # Commerce
    "Greer",       # USTR
    "Rubio",       # State
    "Hassett",     # NEC
    "Wright",      # Energy
)


# ──────────────────────────────────────────────────────────────────────
#  Salience thresholds
# ──────────────────────────────────────────────────────────────────────

@dataclass
class SalienceConfig:
    """Controls how aggressively the brief filters.

    The whole point of the dashboard is that it is *not* the same every day:
    a module has to earn its place by scoring above `floor`.
    """

    floor: float = 25.0          # below this a module is dropped entirely
    lead_floor: float = 60.0     # above this a module can lead the page
    max_modules: int = 14        # hard cap so the page stays readable
    max_per_bucket: int = 3      # stops one asset class crowding out the rest

    # Component weights.
    w_move: float = 1.0          # size of today's move in trailing sigma
    w_level: float = 0.8         # how extreme the level is vs its own history
    w_cross: float = 1.1         # moving-average cross fired or imminent
    w_surprise: float = 1.2      # data print vs consensus
    w_event: float = 1.0         # proximity to a scheduled catalyst
    w_divergence: float = 1.0    # ratio decoupled from its benchmark
    w_streak: float = 0.5        # persistent directional run

    # Decay applied to a module that scored highly on the previous run, so the
    # brief rotates rather than repeating itself.
    repeat_decay: float = 0.75
    repeat_lookback: int = 3     # runs over which decay applies


SALIENCE = SalienceConfig()
