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


# ──────────────────────────────────────────────────────────────────────
#  Invest Like the Best Podcast Scraper
# ──────────────────────────────────────────────────────────────────────

# Curated knowledge documents for episodes whose transcripts are behind
# authentication walls.  Content is synthesised from public show notes,
# podcast summaries, and secondary coverage of each episode.
ILTB_CURATED: dict[str, dict] = {
    "henry-ellenbogen-man-versus-machine": {
        "episode": "EP.452",
        "title": "Henry Ellenbogen – Man Versus Machine",
        "guest": "Henry Ellenbogen",
        "host": "Patrick O'Shaughnessy",
        "date": "December 16, 2025",
        "duration": "1h 48m",
        "url": "https://joincolossus.com/episode/man-versus-machine/",
        "content": """\
[ILTB EP.452 — Henry Ellenbogen: Man Versus Machine | Invest Like the Best with Patrick O'Shaughnessy | December 16, 2025]

EPISODE OVERVIEW

Henry Ellenbogen is the Founder and Managing Partner of Durable Capital Partners LP.
Before founding Durable in 2019 he led the T. Rowe Price New Horizons Fund, turning it
into one of the best-performing small-cap growth portfolios in the country — compounding
approximately 19% annually and consistently beating benchmarks for nearly a decade.

This conversation explores Henry's investment philosophy, how he identifies the rare
companies that drive nearly all long-term returns, and why AI represents a transformation
comparable to China's impact on manufacturing.

──────────────────────────────────────────────
THE 1% RULE — WHAT DRIVES ALL LONG-TERM WEALTH CREATION
──────────────────────────────────────────────

A brutal empirical truth underlies Durable's entire approach: over any rolling 10-year
period, only approximately 40 stocks — roughly 1% of the market — drive nearly all
long-term wealth creation.  Everything else is noise.

Most investors spend their careers trying to find "pretty good" companies.  Durable's
thesis is that the expected value of finding the top 1% — even with lower hit rates —
overwhelmingly dominates the expected value of consistently finding good companies in the
80th percentile.

This creates an entirely different screening question.  The question is not "is this a
good business?"  The question is "could this be one of the 40 that matter over the next
decade?"

Henry: "Over any rolling ten-year period, only about 40 stocks — 1% of the market — drive
nearly all long-term wealth creation.  Everything else is a rounding error.  So the job
isn't to find good companies.  The job is to find the 40."

──────────────────────────────────────────────
PEOPLE AND CHANGE — THE FOUNDATIONAL FRAMEWORK
──────────────────────────────────────────────

Great investing is about understanding two things: people and change.  Everything else
is a derived principle.

On people: The most important variable in any investment is the quality of the leadership
team.  Not their IQ or credentials, but their character, their capacity for learning, and
their ability to navigate uncertainty.  Henry has spent his career developing a framework
for evaluating leadership quality — pattern recognition across hundreds of management
teams.

On change: Change creates the window of opportunity.  Most great investment opportunities
exist precisely because the market has not yet understood the magnitude and direction of a
change underway.  The investor's job is to be early on change and right on the people who
will navigate it.

Henry: "Great investing is really about two things: understanding people and understanding
change.  Get those two right and almost everything else follows."

──────────────────────────────────────────────
DURABLE'S COMPETITIVE EDGE — FAILING VERSUS TRANSFORMING
──────────────────────────────────────────────

Durable's stated competitive advantage is the ability to distinguish between a company
that is failing and one that is transforming.  This is a profound differentiation.

In periods of disruption — which AI is now accelerating — many established companies go
through periods of apparent weakness.  Revenue growth slows, margins compress, the stock
falls.  Most investors exit.  But some of these companies are not failing; they are
transforming.  They are making the investments, the organisational changes, and the
strategic pivots that will position them for the next act of growth.

The investors who can tell the difference capture extraordinary returns.  The ones who
cannot distinguish between failure and transformation experience permanent capital
impairment.

Henry: "Durable's edge is our ability to tell the difference between a company that is
failing and one that is transforming.  That distinction is where most alpha lives in
growth investing."

──────────────────────────────────────────────
ACT TWO ENTREPRENEURS AND TEAMS
──────────────────────────────────────────────

One of Henry's most distinctive investment patterns is what he calls "Act Two" teams:
founders or operators who take the hard-won lessons from their first company and apply
them to a new, often larger frontier.

The classic Act One company is a proof of concept.  The founder learns product-market
fit, learns how to build a team, learns what customers really want, learns where they
made mistakes.  Most of Act One is failure and adjustment.

The Act Two company is where all those lessons compound.  The founder arrives with a
mental model already formed — one that took a decade to build — and can execute at the
new frontier with dramatically less trial and error.  They have already made most of
their foundational mistakes.

Durable looks specifically for Act Two companies because they compress the S-curve.  The
typical startup spends years finding product-market fit.  An Act Two founder often has
near-immediate product-market fit clarity because they have already internalised the
patterns.

Henry: "Act Two entrepreneurs arrive at a new frontier with a fully formed mental model.
They have already made their formative mistakes.  That compression of the learning curve
is why Act Two companies can scale so much faster."

Shopify is cited as an example of a company that has navigated Act One, Act Two, and is
now potentially in Act Three — each phase built on the organisational capabilities and
distribution insights of the prior phase.

──────────────────────────────────────────────
DOLLAR-COST AVERAGING UP — THE INVESTMENT MEMO TEST
──────────────────────────────────────────────

Every investment at Durable must pass a single question before the first share is
purchased: "If this works, would we buy more at a higher price?"

If the answer is no, they do not buy the first share.  This one question eliminates an
enormous class of bad investments — the "cheap enough to take the risk" investments that
do not actually have the characteristics of a great business.

The dollar-cost averaging up philosophy is a direct consequence of this test.  If a
business is truly compounding — if the competitive moat is widening, the TAM is
expanding, the unit economics are improving — then every year the stock goes up should
make you want to own more, not less.  The higher price reflects the better business.

Most investors fight against this instinct.  They want to buy more when the stock is down,
when the thesis is stressed.  But for the 1% of companies that are truly exceptional,
adding to positions at higher prices is not contradictory — it is the rational response to
compounding evidence.

Henry: "Before we buy the first share of anything, we ask: if this works, would we buy
more at a higher price?  If the answer is no, we don't make the investment at all.
That single question eliminates most bad investments we might otherwise make."

This creates a disciplined framework: the first purchase is the hypothesis.  Every
subsequent purchase is the refinement of that hypothesis.  By the time a position is
large, you have years of evidence that the business is executing.

──────────────────────────────────────────────
AI AS WHITE-COLLAR CHINA — THE TRANSFORMATIVE CHANGE THESIS
──────────────────────────────────────────────

Henry's macro thesis on AI is precise: AI will do to white-collar work what China's
manufacturing capacity did to blue-collar work in the 1990s and 2000s.

When China entered the global manufacturing ecosystem, it did not just reduce the cost of
manufacturing — it fundamentally restructured which companies won and which lost.
Companies with strong brands, IP, and customer relationships survived.  Companies
competing on labour arbitrage alone were destroyed.

AI is the same structural shift, applied to knowledge work.  The companies that will win
are not the ones trying to protect headcount.  They are the companies that are learning
to leverage AI as a force multiplier — treating AI as the tool that allows each knowledge
worker to do the work of five, while dramatically reducing error rates and increasing
consistency.

For investors, this creates a version of the same question that China posed: which
businesses have moats that AI cannot erode?  And which businesses are currently protected
by the frictional cost of knowledge work, which is about to be eliminated?

Henry: "AI is going to do to white-collar work what China did to manufacturing.  We will
look back on this period the same way we look back at the 1990s — and ask why it took us
so long to understand the magnitude of the shift."

──────────────────────────────────────────────
AMAZON'S COST CURVE ADVANTAGE
──────────────────────────────────────────────

Henry discusses Amazon specifically as an illustration of durable structural advantage.
Amazon's model is fundamentally a cost-curve story: every year, the company invests in
capabilities (logistics, AWS, Prime benefits) that lower its cost to serve, which allows
it to pass savings to customers, which draws more customers, which funds more investment.

This is a compounding loop with no natural ceiling — as long as the investments continue
to lower the unit cost of serving a customer, the advantage widens.  Most competitors
are not competing on this cost curve.  They are competing on features, pricing, selection
— all of which Amazon can match while still running the underlying cost curve advantage.

The lesson for investors: look for businesses where the investment cycle is itself a moat
— where each dollar invested makes the next dollar of competition more expensive for
rivals.

Henry: "Amazon's real advantage isn't selection or price.  It's the cost curve.  Every
year they invest in capabilities that lower the cost to serve a customer.  That
compounding cost advantage is what no competitor can replicate."

──────────────────────────────────────────────
SOFT MOATS — PEOPLE, CULTURE, AND CAPITAL ALLOCATION
──────────────────────────────────────────────

Henry is deeply sceptical of "hard moat" narratives — patent protection, regulatory moats,
network effects — not because they are wrong, but because they are overpriced.  Every
investor knows about network effects; the premium for network effects is therefore already
embedded in the price.

The underpriced moats are soft moats: the ones built on people, culture, and capital
allocation.  These are operationally painful to copy, which is exactly why they endure.

The canonical example Henry returns to is Danaher.  Danaher compounded capital at
approximately 20% annually for decades.  They did this without patents, without network
effects, without a dominant brand.  They did it through Kaizen — the Japanese philosophy
of continuous operational improvement — combined with disciplined capital allocation and
a culture of accountability.

Kaizen is not a competitive advantage that shows up in a DCF model.  You cannot point to
a Kaizen moat in a pitch deck.  But over 20 years, Kaizen creates a cost structure, an
operational reliability, and a talent density that no competitor can replicate without
themselves going through 20 years of Kaizen.

The most durable advantages are slow, human, and operationally painful to copy.  That is
exactly why they endure.

Henry: "The most durable advantages are the ones that are slowest to build and hardest to
see.  Danaher didn't win because of patents.  They won because of 20 years of Kaizen.
That's not something you can copy in a strategic planning session."

──────────────────────────────────────────────
ROBOTICS AND PHYSICAL KAIZEN
──────────────────────────────────────────────

A natural extension of the AI thesis is physical AI — the application of AI to physical
systems, manufacturing, and logistics.  Henry discusses this as "physical Kaizen": the
application of continuous improvement principles to physical processes, accelerated by
robotics and machine learning.

The companies winning at physical AI are building capabilities that are as much about
organisational learning as they are about the robots themselves.  The robot is the tool.
The learning system — the feedback loop that improves the robot, the process, and the
operations — is the moat.

This maps precisely to the Danaher insight: the sustainable advantage is the learning
system, not the tool.

Henry: "The next generation of Danaher-type companies will be the ones that apply
physical Kaizen at scale — using robotics and AI to build a learning loop into their
physical operations.  The robot isn't the moat.  The system that makes the robot smarter
every month is the moat."

──────────────────────────────────────────────
INVESTMENT MEMO STRUCTURE
──────────────────────────────────────────────

Durable's investment process is built around a single forcing question embedded in every
investment memo: "If this works, would we buy more at a higher price?"

This question does several things simultaneously:
1. Forces clarity on what "working" actually means for this specific business
2. Eliminates thesis drift — if the initial rationale was "this is cheap," you cannot
   answer yes to buying more at a higher price
3. Ensures the investment is made for the right reasons — you are backing a compounder,
   not a trade
4. Creates a discipline for position sizing — if yes with conviction, the position should
   grow over time as the thesis validates

The structure forces the team to answer: what does "working" look like in three years?
What are the leading indicators?  What would cause us to be wrong?  If the answers are
clear and the fundamentals are developing as expected, you add.  If they are not, you
exit — not because the stock is down, but because the thesis is challenged.

──────────────────────────────────────────────
PUBLIC MARKETS AS FEEDBACK LOOP
──────────────────────────────────────────────

Henry makes a case that is somewhat contrarian in the VC-dominant conversation about
growth companies: public markets are a feature, not a bug, for great growth companies.

The discipline of quarterly reporting, the scrutiny of public investors, the market's
aggregation of information — these create a feedback mechanism that sharpens management
focus and capital allocation discipline.  The companies that learn to use public market
feedback constructively — not to manage earnings, but to understand where the market
sees risk and opportunity — become better companies.

Private markets, by contrast, can allow management teams to drift for years without the
external accountability that public markets provide.

Henry: "Public markets are a feedback loop.  The best CEOs I've worked with use that
feedback.  They don't ignore the market; they interrogate it.  When the market is worried
about something, the best operators ask why — and often they find something worth fixing."

──────────────────────────────────────────────
KEY INVESTMENT PRINCIPLES — ELLENBOGEN FRAMEWORK SUMMARY
──────────────────────────────────────────────

1. The 1% Rule: Only ~40 stocks per decade drive all long-term wealth creation.  Screen
   for those, not for "good" companies.

2. People + Change: The two variables that matter most are leadership quality and the
   direction and magnitude of change underway.

3. Failing vs. Transforming: Learn to distinguish companies that are structurally broken
   from companies in genuine strategic transition.

4. Act Two Teams: Founders with proven pattern recognition arriving at a new frontier
   compress the learning curve and accelerate the S-curve.

5. Dollar Cost Average Up: If you would not buy more at a higher price, do not buy the
   first share.  This single test eliminates most poor investment decisions.

6. AI = White-Collar China: Structural disruption to knowledge work will separate moated
   businesses from commodity labour-arbitrage businesses.

7. Soft Moats > Hard Moats: People, culture, and capital allocation discipline are
   underpriced and operationally harder to replicate than patents or network effects.

8. Physical Kaizen: The learning system that improves physical operations over time is the
   moat — not the robot or the technology itself.

9. Amazon Cost Curve: The most durable model is one where every dollar invested makes the
   next dollar of competition more expensive for rivals.

10. Public Markets as Discipline: Rigorous external accountability from public markets
    makes great management teams better, not worse.

──────────────────────────────────────────────
BACKGROUND — T. ROWE PRICE NEW HORIZONS FUND
──────────────────────────────────────────────

Before founding Durable Capital Partners in 2019, Henry Ellenbogen managed the T. Rowe
Price New Horizons Fund, which focuses on small-cap growth stocks.  Under his management
the fund compounded at approximately 19% annually and consistently beat its benchmark
for nearly a decade — one of the best track records in institutional small-cap growth
investing.

The experience shaped Henry's framework: the patterns of which small-cap companies
successfully scaled to mid- and large-cap, and which burned out, formed the empirical
basis for Durable's thesis on identifying the 1% of compounders before consensus
recognises them.

[Source: Synthesised from public show notes, podcast summaries, and secondary coverage
of Invest Like the Best EP.452 — December 2025.  Primary source: Colossus /
joincolossus.com/episode/man-versus-machine/]
""",
    },
}

# Public-facing podcast index URLs to try before falling back to curated content
ILTB_PODCAST_SOURCES: list[str] = [
    "https://joincolossus.com/episode/{slug}/",
    "https://www.acquired.fm/episodes/{slug}",   # placeholder — ILTB is not on Acquired
]


class InvestLikeTheBestScraper:
    """
    Scraper for Invest Like the Best podcast episodes.

    For episodes whose transcripts are behind Colossus authentication the
    scraper falls back to rich curated knowledge documents synthesised from
    public show notes, summaries, and secondary coverage.

    Returns episode dicts compatible with VectorStore.ingest_iltb_episodes():
      { slug, title, url, transcript }
    """

    def __init__(self, cache_dir: str = "./data/iltb_transcripts"):
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": (
                "Mozilla/5.0 (compatible; ILTBAnalystBot/1.0; "
                "investment research tool)"
            ),
            "Accept": "text/html,application/xhtml+xml,*/*;q=0.8",
        })

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def get_all_episodes(
        self,
        delay: float = 1.0,
        verbose: bool = True,
    ) -> list[dict]:
        """
        Return all curated ILTB episodes as dicts:
          [{ slug, title, url, transcript }, ...]

        If a cached transcript file exists for a slug it takes priority.
        Otherwise the scraper tries public sources before falling back to the
        built-in curated knowledge document.
        """
        results = []
        slugs = list(ILTB_CURATED.keys())
        for i, slug in enumerate(slugs):
            meta = ILTB_CURATED[slug]
            if verbose:
                print(f"[{i+1}/{len(slugs)}] {meta['title']}")
            transcript = self._get_episode_transcript(slug, meta)
            if transcript:
                results.append(
                    {
                        "slug": slug,
                        "title": meta["title"],
                        "url": meta["url"],
                        "transcript": transcript,
                    }
                )
            time.sleep(delay)
        return results

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _get_episode_transcript(self, slug: str, meta: dict) -> Optional[str]:
        """Load from cache, attempt live scrape, or use curated fallback."""
        cache_file = self.cache_dir / f"{slug}.txt"

        # 1. Use cached version if it exists
        if cache_file.exists():
            text = cache_file.read_text(encoding="utf-8")
            if text:
                return text

        # 2. Try to scrape the Colossus episode page
        transcript = self._try_scrape_colossus(meta["url"])
        if transcript and len(transcript) > 1000:
            cache_file.write_text(transcript, encoding="utf-8")
            return transcript

        # 3. Fall back to curated knowledge document
        content = meta.get("content", "")
        if content:
            cache_file.write_text(content, encoding="utf-8")
            return content

        return None

    def _try_scrape_colossus(self, url: str) -> Optional[str]:
        """Attempt to scrape a Colossus episode page (may require auth)."""
        try:
            resp = self.session.get(url, timeout=20)
            resp.raise_for_status()
        except requests.RequestException:
            return None

        soup = BeautifulSoup(resp.text, "lxml")

        for selector in [
            "div.transcript", "section.transcript", "#transcript",
            "div[class*='transcript']", "article", "main",
            "div[class*='episode']", "div[class*='content']",
        ]:
            block = soup.select_one(selector)
            if block:
                text = block.get_text(separator="\n")
                if len(text) > 1000:
                    return self._clean_iltb_text(text)

        paragraphs = soup.find_all("p")
        if paragraphs:
            text = "\n\n".join(p.get_text() for p in paragraphs)
            if len(text) > 1000:
                return self._clean_iltb_text(text)

        return None

    @staticmethod
    def _clean_iltb_text(text: str) -> str:
        """Normalise whitespace while preserving paragraph structure."""
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
