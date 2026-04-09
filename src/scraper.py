"""
Acquired Podcast Transcript Scraper
Fetches episode list and transcripts from acquired.fm and caches them locally.
"""

import json
import os
import time
from pathlib import Path
from typing import Optional

import requests
from bs4 import BeautifulSoup

ACQUIRED_BASE = "https://www.acquired.fm"
ACQUIRED_EPISODES = "https://www.acquired.fm/episodes"

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (compatible; AcquiredAnalystBot/1.0; "
        "investment research tool)"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
}


class AcquiredScraper:
    """Scrapes and caches Acquired podcast transcripts."""

    def __init__(self, cache_dir: str = "./data/transcripts"):
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.session = requests.Session()
        self.session.headers.update(HEADERS)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def get_episodes(self, max_episodes: Optional[int] = None) -> list[dict]:
        """
        Return a list of episode metadata dicts:
          { slug, title, url, season, description }
        Results are loaded from the local cache if available.
        """
        cache_file = self.cache_dir / "episode_list.json"
        if cache_file.exists():
            with open(cache_file) as f:
                episodes = json.load(f)
            if max_episodes:
                return episodes[:max_episodes]
            return episodes

        episodes = self._scrape_episode_list()
        with open(cache_file, "w") as f:
            json.dump(episodes, f, indent=2)

        if max_episodes:
            return episodes[:max_episodes]
        return episodes

    def get_transcript(self, episode: dict) -> Optional[str]:
        """
        Return the full transcript text for *episode*.
        Loads from cache if available; otherwise scrapes acquired.fm.
        """
        slug = episode["slug"]
        cache_file = self.cache_dir / f"{slug}.txt"
        if cache_file.exists():
            return cache_file.read_text(encoding="utf-8")

        transcript = self._scrape_transcript(episode["url"])
        if transcript:
            cache_file.write_text(transcript, encoding="utf-8")
        return transcript

    def get_all_transcripts(
        self,
        max_episodes: Optional[int] = None,
        delay: float = 1.5,
        verbose: bool = True,
    ) -> list[dict]:
        """
        Scrape / load all episodes and return:
          [{ slug, title, url, season, description, transcript }, ...]
        """
        episodes = self.get_episodes(max_episodes=max_episodes)
        results = []
        for i, ep in enumerate(episodes):
            if verbose:
                print(f"[{i+1}/{len(episodes)}] {ep['title']}")
            transcript = self.get_transcript(ep)
            if transcript:
                results.append({**ep, "transcript": transcript})
            time.sleep(delay)
        return results

    # ------------------------------------------------------------------
    # Internal scrapers
    # ------------------------------------------------------------------

    def _scrape_episode_list(self) -> list[dict]:
        """Crawl the /episodes listing pages and collect episode metadata."""
        episodes: list[dict] = []
        page = 1

        while True:
            url = f"{ACQUIRED_EPISODES}?page={page}" if page > 1 else ACQUIRED_EPISODES
            try:
                resp = self.session.get(url, timeout=15)
                resp.raise_for_status()
            except requests.RequestException as exc:
                print(f"Warning: failed to fetch episode list page {page}: {exc}")
                break

            soup = BeautifulSoup(resp.text, "lxml")
            found = self._parse_episode_cards(soup)
            if not found:
                break
            episodes.extend(found)
            page += 1
            time.sleep(1.0)

        return episodes

    def _parse_episode_cards(self, soup: BeautifulSoup) -> list[dict]:
        """Extract episode metadata from a listing page."""
        cards = []

        # acquired.fm uses <article> or <div> cards — try both selectors
        for article in soup.select("article.episode-card, div.episode-card, article"):
            link_tag = article.find("a", href=True)
            if not link_tag:
                continue
            href: str = link_tag["href"]
            if "/episodes/" not in href:
                continue

            # Normalise URL
            if href.startswith("http"):
                full_url = href
            else:
                full_url = ACQUIRED_BASE + href

            slug = href.rstrip("/").split("/")[-1]
            title_tag = article.find(["h2", "h3", "h4"])
            title = title_tag.get_text(strip=True) if title_tag else slug

            desc_tag = article.find("p")
            description = desc_tag.get_text(strip=True) if desc_tag else ""

            # Try to extract season from title or URL
            season = None
            for part in href.split("/"):
                if part.startswith("s") and part[1:].isdigit():
                    season = int(part[1:])
                    break

            cards.append(
                {
                    "slug": slug,
                    "title": title,
                    "url": full_url,
                    "season": season,
                    "description": description,
                }
            )

        return cards

    def _scrape_transcript(self, episode_url: str) -> Optional[str]:
        """Fetch and extract the transcript text from an episode page."""
        try:
            resp = self.session.get(episode_url, timeout=20)
            resp.raise_for_status()
        except requests.RequestException as exc:
            print(f"  Warning: failed to fetch {episode_url}: {exc}")
            return None

        soup = BeautifulSoup(resp.text, "lxml")

        # Strategy 1: explicit transcript section
        for selector in [
            "div.transcript",
            "section.transcript",
            "#transcript",
            "div[class*='transcript']",
        ]:
            section = soup.select_one(selector)
            if section:
                return self._clean_text(section.get_text())

        # Strategy 2: largest <article> / <main> block (usually episode body)
        for tag in ["article", "main", "div.episode-body", "div.post-content"]:
            block = soup.select_one(tag)
            if block and len(block.get_text()) > 500:
                return self._clean_text(block.get_text())

        # Strategy 3: fall back to all <p> tags combined
        paragraphs = soup.find_all("p")
        if paragraphs:
            text = "\n\n".join(p.get_text() for p in paragraphs)
            if len(text) > 300:
                return self._clean_text(text)

        return None

    @staticmethod
    def _clean_text(text: str) -> str:
        """Collapse whitespace while preserving paragraph breaks."""
        lines = [line.strip() for line in text.splitlines()]
        cleaned: list[str] = []
        blank_run = 0
        for line in lines:
            if line:
                cleaned.append(line)
                blank_run = 0
            else:
                blank_run += 1
                if blank_run == 1:
                    cleaned.append("")
        return "\n".join(cleaned).strip()


# ──────────────────────────────────────────────────────────────────────
#  Paul Graham Essay Scraper
# ──────────────────────────────────────────────────────────────────────

PG_BASE = "http://paulgraham.com"
PG_ARTICLES_INDEX = "http://paulgraham.com/articles.html"

# High-priority essays most relevant to business strategy & investing
PG_PRIORITY_SLUGS = {
    "growth", "foundermode", "aord", "schlep", "ambitious", "ds",
    "startupideas", "determined", "wealth", "good", "submarine",
    "relres", "before", "avg", "hwh", "hiring", "makersschedule",
    "fr", "ramen", "identity", "badeconomy", "notnot", "13sentences",
    "ideas", "investors", "die", "equity", "foundervsceo",
    "jessica", "addiction", "sun", "worked",
}


class PaulGrahamScraper:
    """
    Scrapes Paul Graham's essays from paulgraham.com and caches them locally.

    Returns essay dicts compatible with VectorStore.ingest_pg_essays():
      { slug, title, url, transcript }
    """

    def __init__(self, cache_dir: str = "./data/pg_essays"):
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": (
                "Mozilla/5.0 (compatible; PGEssayBot/1.0; "
                "investment research tool)"
            ),
            "Accept": "text/html,application/xhtml+xml,*/*;q=0.8",
        })

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def get_essay_list(self) -> list[dict]:
        """
        Return list of essay metadata dicts: { slug, title, url }
        Loads from cache if available; otherwise scrapes paulgraham.com.
        """
        cache_file = self.cache_dir / "essay_list.json"
        if cache_file.exists():
            with open(cache_file) as f:
                return json.load(f)

        essays = self._scrape_essay_list()
        with open(cache_file, "w") as f:
            json.dump(essays, f, indent=2)
        return essays

    def get_essay_text(self, essay: dict) -> Optional[str]:
        """
        Return full text of *essay*. Loads from cache or scrapes.
        """
        slug = essay["slug"]
        cache_file = self.cache_dir / f"{slug}.txt"
        if cache_file.exists():
            return cache_file.read_text(encoding="utf-8")

        text = self._scrape_essay(essay["url"])
        if text:
            cache_file.write_text(text, encoding="utf-8")
        return text

    def get_all_essays(
        self,
        priority_only: bool = False,
        max_essays: Optional[int] = None,
        delay: float = 1.0,
        verbose: bool = True,
    ) -> list[dict]:
        """
        Scrape / load all essays and return:
          [{ slug, title, url, transcript }, ...]

        Args:
            priority_only: If True, only fetch the curated high-signal list.
            max_essays:    Cap the total number fetched (useful for testing).
        """
        all_meta = self.get_essay_list()

        if priority_only:
            all_meta = [e for e in all_meta if e["slug"] in PG_PRIORITY_SLUGS]

        if max_essays:
            all_meta = all_meta[:max_essays]

        results = []
        for i, essay in enumerate(all_meta):
            if verbose:
                print(f"[{i+1}/{len(all_meta)}] {essay['title']}")
            text = self.get_essay_text(essay)
            if text and len(text) > 200:
                results.append({**essay, "transcript": text})
            time.sleep(delay)

        return results

    # ------------------------------------------------------------------
    # Internal scrapers
    # ------------------------------------------------------------------

    def _scrape_essay_list(self) -> list[dict]:
        """Fetch paulgraham.com/articles.html and extract essay links."""
        try:
            resp = self.session.get(PG_ARTICLES_INDEX, timeout=15)
            resp.raise_for_status()
        except requests.RequestException as exc:
            print(f"Warning: failed to fetch PG articles index: {exc}")
            return []

        soup = BeautifulSoup(resp.text, "lxml")
        essays: list[dict] = []

        for link in soup.find_all("a", href=True):
            href: str = link["href"]
            # PG essay links are like "growth.html" (relative)
            if not href.endswith(".html") or "/" in href:
                continue
            slug = href.replace(".html", "")
            title = link.get_text(strip=True)
            if not title or len(title) < 3:
                continue
            full_url = f"{PG_BASE}/{href}"
            essays.append({"slug": slug, "title": title, "url": full_url})

        # Deduplicate by slug
        seen: set[str] = set()
        unique: list[dict] = []
        for e in essays:
            if e["slug"] not in seen:
                seen.add(e["slug"])
                unique.append(e)

        return unique

    def _scrape_essay(self, url: str) -> Optional[str]:
        """Fetch and extract the main text body from a PG essay page."""
        try:
            resp = self.session.get(url, timeout=15)
            resp.raise_for_status()
        except requests.RequestException as exc:
            print(f"  Warning: failed to fetch {url}: {exc}")
            return None

        soup = BeautifulSoup(resp.text, "lxml")

        # PG's site uses a simple <font> / <table> layout — grab all <p> and <font> text
        # Try table cell with the most text first
        best_cell = None
        best_len = 0
        for td in soup.find_all("td"):
            text = td.get_text()
            if len(text) > best_len:
                best_len = len(text)
                best_cell = td

        if best_cell and best_len > 300:
            return self._clean_pg_text(best_cell.get_text())

        # Fallback: concatenate all <p> tags
        paragraphs = soup.find_all("p")
        if paragraphs:
            text = "\n\n".join(p.get_text() for p in paragraphs)
            if len(text) > 200:
                return self._clean_pg_text(text)

        return None

    @staticmethod
    def _clean_pg_text(text: str) -> str:
        """Normalise whitespace for PG essay text."""
        lines = [line.strip() for line in text.splitlines()]
        cleaned: list[str] = []
        blank_run = 0
        for line in lines:
            if line:
                cleaned.append(line)
                blank_run = 0
            else:
                blank_run += 1
                if blank_run == 1:
                    cleaned.append("")
        return "\n".join(cleaned).strip()


# ──────────────────────────────────────────────────────────────────────
#  Jeff Bezos Annual Shareholder Letter Scraper
# ──────────────────────────────────────────────────────────────────────

BEZOS_ABOUT_BASE = "https://www.aboutamazon.com"

# Primary URL for each letter year (letter for year X published in X+1 proxy)
# These are the letters Bezos wrote as CEO (1997–2020)
BEZOS_LETTER_URLS: dict[int, list[str]] = {
    2020: [
        "https://www.aboutamazon.com/news/company-news/2020-letter-to-shareholders",
        "https://www.aboutamazon.com/news/leadership/2020-letter-to-shareholders",
    ],
    2019: [
        "https://www.aboutamazon.com/news/company-news/2019-letter-to-shareholders",
        "https://www.aboutamazon.com/news/leadership/2019-letter-to-shareholders",
    ],
    2018: [
        "https://www.aboutamazon.com/news/company-news/2018-letter-to-shareholders",
        "https://www.aboutamazon.com/news/leadership/2018-letter-to-shareholders",
    ],
    2017: [
        "https://www.aboutamazon.com/news/company-news/2017-letter-to-shareholders",
        "https://www.aboutamazon.com/news/leadership/2017-letter-to-shareholders",
    ],
    2016: [
        "https://www.aboutamazon.com/news/company-news/2016-letter-to-shareholders",
        "https://www.aboutamazon.com/news/leadership/2016-letter-to-shareholders",
    ],
    2015: [
        "https://www.aboutamazon.com/news/company-news/2015-letter-to-shareholders",
        "https://www.aboutamazon.com/news/leadership/2015-letter-to-shareholders",
    ],
    2014: [
        "https://www.aboutamazon.com/news/company-news/2014-letter-to-shareholders",
    ],
    2013: [
        "https://www.aboutamazon.com/news/company-news/2013-letter-to-shareholders",
    ],
    # Pre-2013 letters — try SEC EDGAR annual report filings
    2012: [
        "https://s2.q4cdn.com/299287126/files/doc_financials/annual/2012-Annual-Report.pdf",
    ],
    2011: [
        "https://s2.q4cdn.com/299287126/files/doc_financials/annual/2011-Annual-Report.pdf",
    ],
    2010: [
        "https://s2.q4cdn.com/299287126/files/doc_financials/annual/2010-Annual-Report.pdf",
    ],
    2009: [
        "https://s2.q4cdn.com/299287126/files/doc_financials/annual/2009-Annual-Report.pdf",
    ],
    2008: [
        "https://s2.q4cdn.com/299287126/files/doc_financials/annual/2008-Annual-Report.pdf",
    ],
    2007: [
        "https://s2.q4cdn.com/299287126/files/doc_financials/annual/2007-Annual-Report.pdf",
    ],
    2006: [
        "https://s2.q4cdn.com/299287126/files/doc_financials/annual/2006-Annual-Report.pdf",
    ],
    2005: [
        "https://s2.q4cdn.com/299287126/files/doc_financials/annual/2005-Annual-Report.pdf",
    ],
    2004: [
        "https://s2.q4cdn.com/299287126/files/doc_financials/annual/2004-Annual-Report.pdf",
    ],
    2003: [
        "https://s2.q4cdn.com/299287126/files/doc_financials/annual/2003-Annual-Report.pdf",
    ],
    2002: [
        "https://s2.q4cdn.com/299287126/files/doc_financials/annual/2002-Annual-Report.pdf",
    ],
    2001: [
        "https://s2.q4cdn.com/299287126/files/doc_financials/annual/2001-Annual-Report.pdf",
    ],
    2000: [
        "https://s2.q4cdn.com/299287126/files/doc_financials/annual/2000-Annual-Report.pdf",
    ],
    1999: [
        "https://s2.q4cdn.com/299287126/files/doc_financials/annual/1999-Annual-Report.pdf",
    ],
    1998: [
        "https://s2.q4cdn.com/299287126/files/doc_financials/annual/1998-Annual-Report.pdf",
    ],
    1997: [
        "https://s2.q4cdn.com/299287126/files/doc_financials/annual/1997-Annual-Report.pdf",
    ],
}

# Discovery URL — Amazon IR page that lists all annual reports
BEZOS_IR_INDEX = (
    "https://ir.aboutamazon.com/annual-reports-proxies-and-shareholder-letters"
    "/annual-reports/default.aspx"
)

# High-priority years containing the most strategically important frameworks
BEZOS_PRIORITY_YEARS = {
    1997,  # Day 1, long-term orientation, customer obsession — the founding manifesto
    2002,  # Free cash flow supremacy over net income
    2004,  # Free cash flow as the north star metric
    2008,  # Frugality + invention; survive adversity
    2011,  # Missionaries vs. mercenaries
    2014,  # Wandering; invention; long-term willingness to be misunderstood
    2015,  # Type 1 vs. Type 2 decisions; regret minimisation framework
    2016,  # High standards; Disagree and Commit; misalignment types
    2017,  # Day 2 defined; customer obsession vs. competitor obsession
    2018,  # High standards: recognition + scope + coaching
    2019,  # "What's not going to change"; Earth's Best Employer
    2020,  # Final Bezos letter; civilizational responsibility
}


class BezosLetterScraper:
    """
    Scrapes Jeff Bezos's annual shareholder letters (1997–2020) and caches
    them locally for ingestion into the vector knowledge base.

    Returns letter dicts compatible with VectorStore.ingest_bezos_letters():
      { year, title, url, transcript }
    """

    def __init__(self, cache_dir: str = "./data/bezos_letters"):
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": (
                "Mozilla/5.0 (compatible; BezosLetterBot/1.0; "
                "investment research tool)"
            ),
            "Accept": "text/html,application/xhtml+xml,*/*;q=0.8",
        })

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def get_all_letters(
        self,
        priority_only: bool = False,
        max_letters: int | None = None,
        delay: float = 1.5,
        verbose: bool = True,
    ) -> list[dict]:
        """
        Fetch / load all Bezos letters and return:
          [{ year, title, url, transcript }, ...]

        Args:
            priority_only: Only fetch the curated high-signal years.
            max_letters:   Cap the number of letters fetched (useful for testing).
            delay:         Seconds between HTTP requests.
            verbose:       Print progress.
        """
        years = sorted(BEZOS_LETTER_URLS.keys(), reverse=True)
        if priority_only:
            years = [y for y in years if y in BEZOS_PRIORITY_YEARS]
        if max_letters is not None:
            years = years[:max_letters]

        results = []
        for year in years:
            if verbose:
                print(f"[{year}] Fetching Bezos letter…")
            letter = self._get_letter(year)
            if letter:
                results.append(letter)
            time.sleep(delay)

        return results

    def get_letter(self, year: int) -> Optional[dict]:
        """Return a single letter dict for *year*, loading from cache first."""
        return self._get_letter(year)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _get_letter(self, year: int) -> Optional[dict]:
        """Load from cache or scrape a single year's letter."""
        cache_file = self.cache_dir / f"{year}.txt"
        if cache_file.exists():
            text = cache_file.read_text(encoding="utf-8")
            if text:
                return {
                    "year": year,
                    "title": f"Bezos Shareholder Letter {year}",
                    "url": BEZOS_LETTER_URLS.get(year, [""])[0],
                    "transcript": text,
                }

        # Try each URL for this year
        for url in BEZOS_LETTER_URLS.get(year, []):
            text = self._scrape_url(url, year)
            if text and len(text) > 500:
                cache_file.write_text(text, encoding="utf-8")
                return {
                    "year": year,
                    "title": f"Bezos Shareholder Letter {year}",
                    "url": url,
                    "transcript": text,
                }

        return None

    def _scrape_url(self, url: str, year: int) -> Optional[str]:
        """Fetch URL and extract letter text; skip PDFs (binary)."""
        if url.lower().endswith(".pdf"):
            # PDF extraction requires pdfplumber — attempt basic fallback
            return self._try_pdf(url, year)

        try:
            resp = self.session.get(url, timeout=20)
            resp.raise_for_status()
        except requests.RequestException as exc:
            print(f"  Warning: {url} — {exc}")
            return None

        soup = BeautifulSoup(resp.text, "lxml")

        # Remove nav, header, footer, scripts
        for tag in soup(["nav", "header", "footer", "script", "style", "aside"]):
            tag.decompose()

        # Strategy 1: article / main content blocks
        for selector in [
            "article", "main", "div.article-body", "div.content-body",
            "div[class*='article']", "div[class*='content']",
            "div[class*='letter']", "div[class*='post']",
        ]:
            block = soup.select_one(selector)
            if block:
                text = block.get_text(separator="\n")
                if len(text) > 500:
                    return self._clean_letter_text(text, year)

        # Strategy 2: largest block of <p> tags
        paragraphs = soup.find_all("p")
        if len(paragraphs) > 5:
            text = "\n\n".join(p.get_text() for p in paragraphs)
            if len(text) > 500:
                return self._clean_letter_text(text, year)

        return None

    def _try_pdf(self, url: str, year: int) -> Optional[str]:
        """Attempt to extract text from a PDF annual report."""
        try:
            import pdfplumber  # optional dependency
        except ImportError:
            print(f"  pdfplumber not installed; skipping PDF for {year}.")
            return None

        try:
            resp = self.session.get(url, timeout=30)
            resp.raise_for_status()
        except requests.RequestException as exc:
            print(f"  Warning: PDF fetch failed for {year}: {exc}")
            return None

        import io
        try:
            with pdfplumber.open(io.BytesIO(resp.content)) as pdf:
                pages_text = []
                # Shareholder letter is typically in the first 10-20 pages
                for page in pdf.pages[:30]:
                    t = page.extract_text()
                    if t:
                        pages_text.append(t)
                full_text = "\n\n".join(pages_text)
                if len(full_text) > 500:
                    return self._clean_letter_text(full_text, year)
        except Exception as exc:
            print(f"  Warning: PDF parse failed for {year}: {exc}")
        return None

    def _clean_letter_text(self, text: str, year: int) -> str:
        """Normalise and prepend year metadata to letter text."""
        lines = [line.strip() for line in text.splitlines()]
        cleaned: list[str] = []
        blank_run = 0
        for line in lines:
            if line:
                cleaned.append(line)
                blank_run = 0
            else:
                blank_run += 1
                if blank_run == 1:
                    cleaned.append("")
        body = "\n".join(cleaned).strip()
        # Prepend year context for better RAG retrieval
        return f"[Bezos Shareholder Letter — Year: {year}]\n\n{body}"
