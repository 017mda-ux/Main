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


# Some public endpoints refuse a bare tool User-Agent. Try the descriptive one
# first (SEC asks for it), then fall back to a browser string.
UA_FALLBACK = ("Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
               "(KHTML, like Gecko) Chrome/124.0 Safari/537.36")


def _open(url: str, accept: str, ua: str) -> bytes:
    req = urllib.request.Request(
        url,
        headers={
            "User-Agent": ua,
            "Accept": accept,
            "Accept-Encoding": "gzip",
            "Accept-Language": "en-US,en;q=0.9",
            "Connection": "close",
        },
    )
    with urllib.request.urlopen(req, timeout=TIMEOUT, context=_CTX) as r:
        raw = r.read()
    if raw[:2] == b"\x1f\x8b":
        raw = gzip.decompress(raw)
    return raw


def get(url: str, accept: str = "*/*") -> bytes:
    # Retry every HTTP error with the browser string: federalreserve.gov and
    # EDGAR both rejected the tool User-Agent, with codes that a narrow
    # allow-list missed.
    try:
        return _open(url, accept, UA)
    except urllib.error.HTTPError:
        return _open(url, accept, UA_FALLBACK)


def describe(e: Exception) -> str:
    """Say what actually went wrong, so a failed run is diagnosable from the log."""
    if isinstance(e, urllib.error.HTTPError):
        return f"HTTP {e.code}"
    if isinstance(e, urllib.error.URLError):
        return f"URLError {getattr(e, 'reason', '')}"
    return type(e).__name__


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


# Stooq refuses this runner outright, so the snapshot needs a server-side
# source. Yahoo's chart endpoint is JSON, keyless, and covers almost the whole
# universe. The browser still uses Stooq (Yahoo sends no CORS header), which is
# why the page treats the live fetch as an upgrade rather than a requirement.
YAHOO = {
    '^spx': '^GSPC', '^ndx': '^NDX', '^dji': '^DJI', '^rut': '^RUT',
    '^sx5e': '^STOXX50E', '^dax': '^GDAXI', '^ukx': '^FTSE', '^nkx': '^N225',
    '^hsi': '^HSI', '^kospi': '^KS11', '^bvsp': '^BVSP', '^vix': '^VIX',
    '10usy.b': '^TNX', '5usy.b': '^FVX', '30usy.b': '^TYX', '2usy.b': '2YY=F',
    'dx.f': 'DX-Y.NYB', 'cl.f': 'CL=F', 'hg.f': 'HG=F',
    'xauusd': 'GC=F', 'xagusd': 'SI=F',
    'eurusd': 'EURUSD=X', 'usdjpy': 'USDJPY=X', 'gbpusd': 'GBPUSD=X',
    'usdchf': 'USDCHF=X', 'usdcnh': 'USDCNH=X', 'audusd': 'AUDUSD=X',
    'usdkrw': 'USDKRW=X', 'usdmxn': 'USDMXN=X', 'usdinr': 'USDINR=X',
    'usdbrl': 'USDBRL=X', 'usdcad': 'USDCAD=X', 'eurjpy': 'EURJPY=X',
    # No free server-side source for foreign benchmark yields; the browser
    # picks these up from Stooq when it can reach it.
    '10dey.b': None, '10jpy.b': None, '10uky.b': None,
}


def yahoo_symbol(sym: str) -> str | None:
    if sym in YAHOO:
        return YAHOO[sym]
    if sym.endswith('.us'):
        return sym[:-3].upper()
    return None


def from_yahoo(sym: str) -> dict | None:
    y = yahoo_symbol(sym)
    if not y:
        return None
    url = (f"https://query1.finance.yahoo.com/v8/finance/chart/"
           f"{urllib.parse.quote(y)}?range={HISTORY_YEARS}y&interval=1d")
    doc = json.loads(get(url, "application/json").decode("utf-8", "replace"))
    res = (doc.get("chart") or {}).get("result") or []
    if not res:
        raise ValueError("empty result")
    r = res[0]
    ts = r.get("timestamp") or []
    quote = ((r.get("indicators") or {}).get("quote") or [{}])[0]
    closes = quote.get("close") or []

    dates, vals = [], []
    for t, c in zip(ts, closes):
        if c is None or c == 0:
            continue
        dates.append(datetime.fromtimestamp(t, timezone.utc).strftime("%Y-%m-%d"))
        vals.append(round(float(c), 4))
    if len(vals) < 40:
        raise ValueError(f"only {len(vals)} rows")
    return {"d": dates, "c": vals}


def from_stooq(sym: str) -> dict | None:
    d1 = (datetime.now(timezone.utc) - timedelta(days=365 * HISTORY_YEARS + 30)).strftime("%Y%m%d")
    url = f"https://stooq.com/q/d/l/?s={urllib.parse.quote(sym)}&d1={d1}&i=d"
    text = get(url, "text/csv").decode("utf-8", "replace")
    lines = text.strip().splitlines()
    if not lines or not lines[0].lower().startswith("date"):
        raise ValueError(f"not CSV: {text.strip()[:60]!r}")
    dates, vals = [], []
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
        vals.append(round(c, 4))
    if len(vals) < 40:
        raise ValueError(f"only {len(vals)} rows")
    return {"d": dates, "c": vals}


PROVIDERS = (("yahoo", from_yahoo), ("stooq", from_stooq))


def fetch_history(sym: str) -> tuple[str, dict | None, str]:
    problems = []
    for name, fn in PROVIDERS:
        try:
            series = fn(sym)
        except Exception as e:                                # noqa: BLE001
            problems.append(f"{name} {describe(e)}")
            continue
        if series:
            return sym, {"d": series["d"][-TRIM_ROWS:], "c": series["c"][-TRIM_ROWS:]}, name
    warn(f"{sym}: {'; '.join(problems) or 'no provider'}")
    return sym, None, ""


def build_market() -> dict:
    syms = symbols_from_config()
    print(f"market: {len(syms)} symbols")
    out: dict[str, dict] = {}
    used: dict[str, int] = {}
    with ThreadPoolExecutor(max_workers=6) as ex:
        for sym, series, via in ex.map(fetch_history, syms):
            if not series:
                continue
            out[sym] = series
            used[via] = used.get(via, 0) + 1
            # Log the last value so a wrong ticker or a scale error (a yield
            # quoted x10, say) is visible in the run log rather than on the page.
            print(f"  {sym:9} via {via:5} {len(series['c']):4} rows  last={series['c'][-1]}")
    via_txt = ", ".join(f"{k} {v}" for k, v in sorted(used.items())) or "none"
    print(f"market: {len(out)}/{len(syms)} resolved ({via_txt})")
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
        ("SEC 13D/G", "https://www.sec.gov/cgi-bin/browse-edgar?action=getcurrent&type=SC+13D&dateb=&owner=include&count=40&output=atom"),
        ("SEC Form D/A", "https://www.sec.gov/cgi-bin/browse-edgar?action=getcurrent&type=D%2FA&dateb=&owner=include&count=40&output=atom"),
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

# federalreserve.gov and sec.gov refuse cloud runner IPs outright, so Fed and
# fiscal policy come from the Federal Register instead — the same documents, at
# the government's own publication-of-record, over an API meant for automation.
FR = "https://www.federalregister.gov/api/v1/documents.json"
FR_FIELDS = "&fields[]=title&fields[]=html_url&fields[]=publication_date&fields[]=agencies"

JSON_FEEDS: dict[str, list[tuple[str, str]]] = {
    "policy": [
        ("Federal Register — Fed & Treasury",
         f"{FR}?per_page=12&order=newest{FR_FIELDS}"
         "&conditions[agencies][]=federal-reserve-system"
         "&conditions[agencies][]=treasury-department"),
    ],
    "geo": [
        ("Federal Register — presidential documents",
         f"{FR}?per_page=8&order=newest{FR_FIELDS}&conditions[type][]=PRESDOCU"),
        ("Federal Register — trade & sanctions",
         f"{FR}?per_page=8&order=newest{FR_FIELDS}"
         "&conditions[agencies][]=trade-representative-office-of-united-states"
         "&conditions[agencies][]=foreign-assets-control-office"),
    ],
}


def parse_json_feed(source: str, url: str) -> list[dict]:
    try:
        doc = json.loads(get(url, "application/json").decode("utf-8", "replace"))
    except Exception as e:                                    # noqa: BLE001
        warn(f"{source}: {describe(e)}")
        return []

    items = []
    for r in (doc.get("results") or [])[:MAX_PER_FEED * 2]:
        title = (r.get("title") or "").strip()
        link = r.get("html_url") or ""
        if not title or not link.startswith("http"):
            continue
        if len(title) > 190:
            title = title[:187].rstrip() + "…"
        agencies = r.get("agencies") or []
        name = next((a.get("name") for a in agencies if a.get("name")), None)
        items.append({
            "t": title,
            "u": link,
            "s": f"{source.split(' — ')[0]} · {name}" if name else source,
            "d": r.get("publication_date"),
        })
    return items


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
        warn(f"{source}: {describe(e)}")
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
                      "{http://purl.org/dc/elements/1.1/}date",
                      "{http://purl.org/dc/terms/}date",
                      "{http://purl.org/rss/1.0/modules/dc/}date"):
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


# The Federal Register is a firehose of procedural filings. These are the
# document shapes that are never market-moving, dropped by title so the block
# stays worth reading rather than merely being primary.
NOISE = re.compile(
    r"performance review board|senior executive service|privacy act|sunshine act"
    r"|advisory committee|notice of meeting|meeting notice|request for nominations"
    r"|agency information collection|paperwork reduction|information collection activit"
    r"|renewal of the charter|combined notice of filings|membership of the"
    r"|proposed collection|comment request|correction to|petition for",
    re.I,
)

# One source must not crowd out the others in a block: the Federal Register
# publishes dozens a day, the ECB a handful, and both matter.
MAX_PER_SOURCE = 3


def relevant(item: dict) -> bool:
    return not NOISE.search(item["t"])


def dedupe_key(title: str) -> str:
    """Near-identical filings (the same sanctions notice, reissued) collapse."""
    t = re.sub(r"[^a-z0-9 ]", "", title.lower())
    t = re.sub(r"\s+", " ", t).strip()
    return t[:45]


def build_feeds() -> dict[str, list[dict]]:
    cutoff = (datetime.now(timezone.utc) - timedelta(days=21)).strftime("%Y-%m-%d")
    out: dict[str, list[dict]] = {}

    jobs = [(block, src, url, parse_feed) for block, lst in FEEDS.items() for src, url in lst]
    jobs += [(block, src, url, parse_json_feed) for block, lst in JSON_FEEDS.items() for src, url in lst]
    results: dict[tuple[str, str], list[dict]] = {}
    with ThreadPoolExecutor(max_workers=8) as ex:
        futs = {ex.submit(fn, src, url): (block, src) for block, src, url, fn in jobs}
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
        merged = [m for m in merged if relevant(m)]
        merged.sort(key=lambda m: m["d"] or "0000-00-00", reverse=True)

        seen_url, seen_title, per_source, dedup = set(), set(), {}, []
        for m in merged:
            title_key = dedupe_key(m["t"])
            src = m["s"].split(" · ")[0]
            if m["u"] in seen_url or title_key in seen_title:
                continue
            if per_source.get(src, 0) >= MAX_PER_SOURCE:
                continue
            seen_url.add(m["u"])
            seen_title.add(title_key)
            per_source[src] = per_source.get(src, 0) + 1
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
        warn(f"fomc: {describe(e)} — page keeps its fallback dates")
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
