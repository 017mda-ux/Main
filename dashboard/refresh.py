#!/usr/bin/env python3
"""
refresh.py — builds dashboard/data.json

Two jobs:
  1. A compact market snapshot so the page paints useful numbers even when the
     browser cannot reach a market host.
  2. The day's items from primary sources only — the issuing institution, never
     an aggregator and never secondary commentary.

Standard library only. Every source is fetched independently: one dead feed
never takes down the file, and a failed run never overwrites good data with
empty data.

Usage:  python3 dashboard/refresh.py
Env:    CONTACT_EMAIL  — appended to the User-Agent. The SEC asks for a contact
                         address in automated requests; without it EDGAR may
                         refuse. Optional; nothing else needs it.
"""

from __future__ import annotations

import gzip
import json
import os
import re
import ssl
import sys
import urllib.error
import urllib.parse
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
from pathlib import Path
from xml.etree import ElementTree as ET

HERE = Path(__file__).resolve().parent
OUT = HERE / "data.json"
CONFIG = HERE / "config.js"

TRIM_ROWS = 260          # ~1 trading year: enough for sparklines, z-scores, 1y percentiles
HISTORY_YEARS = 2        # fetched window; trimmed to TRIM_ROWS before writing
TIMEOUT = 25
MAX_PER_FEED = 7

CONTACT = os.environ.get("CONTACT_EMAIL", "").strip()
UA = "Vantage-Dashboard/1.0 (+https://github.com/; static dashboard refresh)"
if CONTACT:
    UA = f"Vantage-Dashboard/1.0 ({CONTACT})"

_CTX = ssl.create_default_context()


def get(url: str, accept: str = "*/*") -> bytes:
    req = urllib.request.Request(
        url,
        headers={
            "User-Agent": UA,
            "Accept": accept,
            "Accept-Encoding": "gzip",
            "Accept-Language": "en-US,en;q=0.9",
        },
    )
    with urllib.request.urlopen(req, timeout=TIMEOUT, context=_CTX) as r:
        raw = r.read()
    if raw[:2] == b"\x1f\x8b":
        raw = gzip.decompress(raw)
    return raw


def warn(msg: str) -> None:
    print(f"  · {msg}", file=sys.stderr)


# ----------------------------------------------------------------------------
# Market snapshot
# ----------------------------------------------------------------------------

def symbols_from_config() -> list[str]:
    """Single source of truth is config.js — do not duplicate the universe here."""
    try:
        src = CONFIG.read_text(encoding="utf-8")
    except OSError as e:
        warn(f"cannot read config.js: {e}")
        return []

    found: list[str] = []
    found += re.findall(r"\bs:\s*'([^']+)'", src)
    # theme tuples look like  ['wmt.us', 'Walmart', 'grocery share']
    for tok in re.findall(r"\[\s*'([^']+)'\s*,", src):
        # ticker-shaped only: must carry a letter or a caret, so the FOMC
        # date list and the link titles in RAIL are both excluded.
        if re.fullmatch(r"[\^a-z0-9][a-z0-9^.]{1,14}", tok) and re.search(r"[a-z^]", tok):
            found.append(tok)

    seen, out = set(), []
    for s in found:
        if s not in seen:
            seen.add(s)
            out.append(s)
    return out


def fetch_history(sym: str) -> tuple[str, dict | None]:
    d1 = (datetime.now(timezone.utc) - timedelta(days=365 * HISTORY_YEARS + 30)).strftime("%Y%m%d")
    url = f"https://stooq.com/q/d/l/?s={urllib.parse.quote(sym)}&d1={d1}&i=d"
    try:
        text = get(url, "text/csv").decode("utf-8", "replace")
    except Exception as e:                                    # noqa: BLE001
        warn(f"{sym}: {type(e).__name__}")
        return sym, None

    lines = text.strip().splitlines()
    if len(lines) < 40 or not lines[0].lower().startswith("date"):
        warn(f"{sym}: no usable series")
        return sym, None

    dates, closes = [], []
    for line in lines[1:]:
        p = line.split(",")
        if len(p) < 5:
            continue
        try:
            c = float(p[4])
        except ValueError:
            continue
        if c == 0:
            continue
        dates.append(p[0])
        closes.append(round(c, 4))

    if len(closes) < 40:
        return sym, None
    return sym, {"d": dates[-TRIM_ROWS:], "c": closes[-TRIM_ROWS:]}


def build_market() -> dict:
    syms = symbols_from_config()
    print(f"market: {len(syms)} symbols")
    out: dict[str, dict] = {}
    with ThreadPoolExecutor(max_workers=6) as ex:
        for sym, series in ex.map(fetch_history, syms):
            if series:
                out[sym] = series
    print(f"market: {len(out)}/{len(syms)} resolved")
    return out


# ----------------------------------------------------------------------------
# Primary-source feeds
# ----------------------------------------------------------------------------

ATOM = "{http://www.w3.org/2005/Atom}"

FEEDS: dict[str, list[tuple[str, str]]] = {
    "policy": [
        ("Federal Reserve", "https://www.federalreserve.gov/feeds/press_monetary.xml"),
        ("Fed speeches", "https://www.federalreserve.gov/feeds/speeches.xml"),
        ("Fed testimony", "https://www.federalreserve.gov/feeds/testimony.xml"),
        ("ECB", "https://www.ecb.europa.eu/rss/press.html"),
        ("Bank of Japan", "https://www.boj.or.jp/en/rss/whatsnew.xml"),
        ("Bank of England", "https://www.bankofengland.co.uk/rss/news"),
    ],
    "research": [
        ("NBER", "https://back.nber.org/rss/new.xml"),
        ("BIS working papers", "https://www.bis.org/list/wppubl/rss.xml"),
        ("Fed FEDS papers", "https://www.federalreserve.gov/feeds/feds.xml"),
        ("IMF working papers", "https://www.imf.org/en/Publications/RSS?language=eng&series=IMF%20Working%20Papers"),
        ("ECB working papers", "https://www.ecb.europa.eu/rss/wps.html"),
    ],
    "private": [
        ("SEC Form D", "https://www.sec.gov/cgi-bin/browse-edgar?action=getcurrent&type=D&dateb=&owner=include&count=40&output=atom"),
        ("SEC press", "https://www.sec.gov/news/pressreleases.rss"),
    ],
    "allocators": [
        ("SEC 13F", "https://www.sec.gov/cgi-bin/browse-edgar?action=getcurrent&type=13F-HR&dateb=&owner=include&count=40&output=atom"),
        ("Norges Bank IM", "https://www.nbim.no/en/rss/"),
    ],
    "geo": [
        ("USTR", "https://ustr.gov/rss.xml"),
        ("Treasury press", "https://home.treasury.gov/news/press-releases/feed"),
        ("State Department", "https://www.state.gov/rss-feed/press-releases/feed/"),
    ],
    "assets": [
        ("EIA", "https://www.eia.gov/rss/todayinenergy.xml"),
        ("CFTC", "https://www.cftc.gov/RSS/RSSGP/rssgp.xml"),
    ],
}

DATE_PATTERNS = (
    "%a, %d %b %Y %H:%M:%S %z",
    "%a, %d %b %Y %H:%M:%S %Z",
    "%a, %d %b %Y %H:%M:%S",
    "%Y-%m-%dT%H:%M:%S%z",
    "%Y-%m-%dT%H:%M:%SZ",
    "%Y-%m-%d",
)


def parse_date(raw: str | None) -> str | None:
    if not raw:
        return None
    raw = raw.strip()
    for pat in DATE_PATTERNS:
        try:
            return datetime.strptime(raw, pat).strftime("%Y-%m-%d")
        except ValueError:
            continue
    m = re.search(r"(\d{4})-(\d{2})-(\d{2})", raw)
    return f"{m.group(1)}-{m.group(2)}-{m.group(3)}" if m else None


def text_of(node) -> str:
    return re.sub(r"\s+", " ", "".join(node.itertext())).strip() if node is not None else ""


def parse_feed(source: str, url: str) -> list[dict]:
    try:
        raw = get(url, "application/rss+xml, application/atom+xml, application/xml;q=0.9")
        root = ET.fromstring(raw)
    except Exception as e:                                    # noqa: BLE001
        warn(f"{source}: {type(e).__name__}")
        return []

    items: list[dict] = []

    for it in root.iter():
        tag = it.tag.split("}")[-1]
        if tag not in ("item", "entry"):
            continue

        title = text_of(it.find("title")) or text_of(it.find(ATOM + "title"))

        link = ""
        ln = it.find("link")
        if ln is not None and (ln.text or "").strip():
            link = ln.text.strip()
        if not link:
            for a in it.findall(ATOM + "link") + it.findall("link"):
                href = a.get("href")
                if href and a.get("rel", "alternate") == "alternate":
                    link = href
                    break
        if not link:
            link = text_of(it.find("guid"))

        date = None
        for tname in ("pubDate", "published", "updated", "date",
                      ATOM + "published", ATOM + "updated",
                      "{http://purl.org/dc/elements/1.1/}date"):
            node = it.find(tname)
            if node is not None:
                date = parse_date(node.text)
                if date:
                    break

        if not title or not link.startswith("http"):
            continue
        if len(title) > 190:
            title = title[:187].rstrip() + "…"

        items.append({"t": title, "u": link, "s": source, "d": date})
        if len(items) >= MAX_PER_FEED * 3:
            break

    return items


def build_feeds() -> dict[str, list[dict]]:
    cutoff = (datetime.now(timezone.utc) - timedelta(days=21)).strftime("%Y-%m-%d")
    out: dict[str, list[dict]] = {}

    jobs = [(block, src, url) for block, lst in FEEDS.items() for src, url in lst]
    results: dict[tuple[str, str], list[dict]] = {}
    with ThreadPoolExecutor(max_workers=8) as ex:
        futs = {ex.submit(parse_feed, src, url): (block, src) for block, src, url in jobs}
        for fut, key in futs.items():
            try:
                results[key] = fut.result()
            except Exception:                                 # noqa: BLE001
                results[key] = []

    for block in FEEDS:
        merged: list[dict] = []
        for (b, _src), items in results.items():
            if b == block:
                merged += items

        # Recent first; undated items sink rather than disappear.
        merged = [m for m in merged if (m["d"] or "9999") >= cutoff or m["d"] is None]
        merged.sort(key=lambda m: m["d"] or "0000-00-00", reverse=True)

        seen, dedup = set(), []
        for m in merged:
            key = m["u"]
            if key in seen:
                continue
            seen.add(key)
            dedup.append(m)

        out[block] = dedup[:MAX_PER_FEED]
        print(f"feeds/{block}: {len(out[block])}")

    return out


# ----------------------------------------------------------------------------
# FOMC calendar — scraped from the Fed's own page, best effort
# ----------------------------------------------------------------------------

MONTHS = {m: i + 1 for i, m in enumerate(
    ["January", "February", "March", "April", "May", "June",
     "July", "August", "September", "October", "November", "December"])}


def build_fomc() -> list[str]:
    url = "https://www.federalreserve.gov/monetarypolicy/fomccalendars.htm"
    try:
        html = get(url, "text/html").decode("utf-8", "replace")
    except Exception as e:                                    # noqa: BLE001
        warn(f"fomc: {type(e).__name__} — page keeps its fallback dates")
        return []

    dates: list[str] = []
    # Each year is a panel headed "<year> FOMC Meetings"; months carry day ranges.
    for ym in re.finditer(r"(\d{4})\s+FOMC\s+Meetings(.*?)(?=\d{4}\s+FOMC\s+Meetings|\Z)", html, re.S | re.I):
        year = int(ym.group(1))
        block = ym.group(2)
        for mm in re.finditer(
            r">\s*(January|February|March|April|May|June|July|August|September|October|November|December)\s*<"
            r"(.{0,400}?)(?=>\s*(?:January|February|March|April|May|June|July|August|September|October|November|December)\s*<|\Z)",
            block, re.S | re.I,
        ):
            month = MONTHS[mm.group(1).capitalize()]
            days = re.search(r"(\d{1,2})\s*[-–]\s*(\d{1,2})", mm.group(2))
            day = int(days.group(2)) if days else None
            if day is None:
                one = re.search(r">\s*(\d{1,2})\s*\*?\s*<", mm.group(2))
                day = int(one.group(1)) if one else None
            if day and 1 <= day <= 31:
                try:
                    dates.append(datetime(year, month, day).strftime("%Y-%m-%d"))
                except ValueError:
                    pass

    dates = sorted(set(dates))
    print(f"fomc: {len(dates)} dates scraped")
    return dates


# ----------------------------------------------------------------------------

def main() -> int:
    print(f"refresh @ {datetime.now(timezone.utc).isoformat(timespec='seconds')}")

    previous: dict = {}
    if OUT.exists():
        try:
            previous = json.loads(OUT.read_text(encoding="utf-8"))
        except Exception:                                     # noqa: BLE001
            previous = {}

    market = build_market()
    feeds = build_feeds()
    fomc = build_fomc()

    # Never let a bad run replace good data with nothing.
    if not market and previous.get("market"):
        warn("market empty — keeping previous snapshot")
        market = previous["market"]
    for block, items in list(feeds.items()):
        if not items and previous.get("feeds", {}).get(block):
            feeds[block] = previous["feeds"][block]
    if not fomc:
        fomc = previous.get("fomc", [])

    payload = {
        "generated": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "window": TRIM_ROWS,
        "market": market,
        "feeds": feeds,
        "fomc": fomc,
    }

    OUT.write_text(json.dumps(payload, separators=(",", ":"), sort_keys=True), encoding="utf-8")
    kb = OUT.stat().st_size / 1024
    print(f"wrote {OUT.relative_to(HERE.parent)} — {kb:.0f} KB, "
          f"{len(market)} series, {sum(len(v) for v in feeds.values())} items")

    if not market and not any(feeds.values()):
        warn("nothing resolved at all — check network egress")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
