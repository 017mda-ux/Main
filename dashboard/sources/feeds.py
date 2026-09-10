"""Primary-source news: Fed, Treasury, BLS, BEA, CBO and EIA RSS.

Items are tagged with the official who is speaking and scored for
market-moving potential, so the page can lead with the two or three that
matter instead of listing every press release.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import date, datetime, timezone
from email.utils import parsedate_to_datetime
from xml.etree import ElementTree as ET

from ..config import CABINET_PRINCIPALS, FED_PRINCIPALS, FEEDS
from .http import HttpError, get

# Words that historically precede a repricing, weighted by how much.
POLICY_TERMS = {
    "rate hike": 5.0, "raise rates": 5.0, "tighten": 4.0, "restrictive": 4.0,
    "rate cut": 5.0, "lower rates": 4.5, "accommodative": 3.5, "easing": 3.5,
    "inflation": 3.0, "price stability": 2.5, "labor market": 2.5,
    "balance sheet": 3.0, "quantitative": 3.0, "reserve": 2.0,
    "dissent": 4.0, "unanimous": 2.0, "projections": 3.0, "dot plot": 4.0,
    "target range": 4.0, "federal funds": 3.5, "policy stance": 3.5,
}

FISCAL_TERMS = {
    "refunding": 5.0, "buyback": 4.5, "auction": 3.0, "issuance": 4.0,
    "debt limit": 5.0, "debt ceiling": 5.0, "extraordinary measures": 4.5,
    "deficit": 3.5, "borrowing": 3.5, "bill share": 4.0, "coupon": 3.5,
    "tariff": 4.0, "sanction": 3.5,
}

DOC_TYPES = {
    "fomc": 5.0, "minutes": 4.0, "statement": 3.5, "testimony": 3.5,
    "speech": 3.0, "press conference": 4.0, "quarterly refunding": 5.0,
}


@dataclass
class Item:
    """One feed entry with everything the page needs to rank and cite it."""

    title: str
    link: str
    published: datetime | None
    source: str
    summary: str = ""
    speakers: list[str] = field(default_factory=list)
    tags: list[str] = field(default_factory=list)
    score: float = 0.0

    @property
    def day(self) -> date | None:
        return self.published.date() if self.published else None

    @property
    def is_speech(self) -> bool:
        return bool(self.speakers)


def _text(node: ET.Element | None) -> str:
    if node is None or node.text is None:
        return ""
    return re.sub(r"<[^>]+>", " ", node.text).strip()


def _parse_date(raw: str) -> datetime | None:
    raw = raw.strip()
    if not raw:
        return None
    try:
        dt = parsedate_to_datetime(raw)
        return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)
    except (TypeError, ValueError):
        pass
    for fmt in ("%Y-%m-%dT%H:%M:%S%z", "%Y-%m-%dT%H:%M:%SZ", "%Y-%m-%d"):
        try:
            dt = datetime.strptime(raw[:25] if "%z" in fmt else raw[:19], fmt)
            return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)
        except ValueError:
            continue
    return None


def parse(xml: str, source: str) -> list[Item]:
    """Parse RSS 2.0 or Atom into Items."""
    try:
        root = ET.fromstring(xml)
    except ET.ParseError as exc:
        raise HttpError(f"{source}: {exc}") from exc

    items: list[Item] = []

    for node in root.findall(".//item"):
        items.append(Item(
            title=_text(node.find("title")),
            link=_text(node.find("link")),
            published=_parse_date(_text(node.find("pubDate"))),
            summary=_text(node.find("description"))[:600],
            source=source,
        ))

    if not items:                      # Atom
        ns = {"a": "http://www.w3.org/2005/Atom"}
        for node in root.findall(".//a:entry", ns):
            link_el = node.find("a:link", ns)
            items.append(Item(
                title=_text(node.find("a:title", ns)),
                link=(link_el.get("href") if link_el is not None else ""),
                published=_parse_date(
                    _text(node.find("a:updated", ns))
                    or _text(node.find("a:published", ns))
                ),
                summary=_text(node.find("a:summary", ns))[:600],
                source=source,
            ))

    for item in items:
        _annotate(item)
    return items


def _annotate(item: Item) -> None:
    """Tag speakers and score market-moving potential."""
    blob = f"{item.title} {item.summary}".lower()

    for name in FED_PRINCIPALS:
        if re.search(rf"\b{name.lower()}\b", blob):
            item.speakers.append(f"{name} (Fed)")
    for name in CABINET_PRINCIPALS:
        if re.search(rf"\b{name.lower()}\b", blob):
            item.speakers.append(f"{name} (Cabinet)")

    score = 0.0
    for term, weight in POLICY_TERMS.items():
        if term in blob:
            score += weight
            item.tags.append("policy")
    for term, weight in FISCAL_TERMS.items():
        if term in blob:
            score += weight
            item.tags.append("fiscal")
    for term, weight in DOC_TYPES.items():
        if term in blob:
            score += weight

    # The Chair moves more than a regional president.
    if any("Warsh" in s for s in item.speakers):
        score *= 1.6
    elif item.speakers:
        score *= 1.15

    # Freshness: a week-old speech is context, not news.
    if item.published:
        age = (datetime.now(timezone.utc) - item.published).days
        score *= max(0.25, 1.0 - age * 0.12)

    item.tags = sorted(set(item.tags))
    item.score = round(score, 2)


def collect(names: list[str] | None = None, **kw) -> list[Item]:
    """Read the configured feeds, skipping any that fail."""
    out: list[Item] = []
    for name, url in FEEDS.items():
        if names and name not in names:
            continue
        try:
            out.extend(parse(get(url, **kw), name))
        except HttpError:
            continue
    out.sort(key=lambda i: (i.score, i.published or datetime.min.replace(
        tzinfo=timezone.utc)), reverse=True)
    return out


def speak(items: list[Item], limit: int = 8) -> list[Item]:
    """Just the items where an official is on the record."""
    return [i for i in items if i.is_speech][:limit]
