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
