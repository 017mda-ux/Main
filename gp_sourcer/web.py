"""
Web search and page scraping for GP sourcing research.

Search priority:
  1. Tavily (if TAVILY_API_KEY env var is set) — higher quality, AI-optimised results
  2. DuckDuckGo via duckduckgo-search (free, no key required)
"""

from __future__ import annotations

import os

import requests
from bs4 import BeautifulSoup

_SCRAPE_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
}

_TAVILY_KEY = os.getenv("TAVILY_API_KEY")


def search_web(query: str, max_results: int = 10) -> dict:
    """Search the web for GP research. Uses Tavily if API key is set, else DuckDuckGo."""
    if _TAVILY_KEY:
        result = _tavily_search(query, max_results)
        if "error" not in result:
            return result

    return _ddg_search(query, max_results)


def _tavily_search(query: str, max_results: int) -> dict:
    try:
        resp = requests.post(
            "https://api.tavily.com/search",
            json={
                "api_key": _TAVILY_KEY,
                "query": query,
                "max_results": max_results,
                "search_depth": "advanced",
                "include_answer": True,
            },
            timeout=20,
        )
        resp.raise_for_status()
        data = resp.json()
        return {
            "source": "tavily",
            "answer": data.get("answer", ""),
            "results": [
                {
                    "title": r.get("title", ""),
                    "url": r.get("url", ""),
                    "content": r.get("content", ""),
                    "score": r.get("score", 0),
                }
                for r in data.get("results", [])
            ],
        }
    except Exception as e:
        return {"error": str(e)}


def _ddg_search(query: str, max_results: int) -> dict:
    # Try both package names (ddgs is the renamed successor to duckduckgo-search)
    ddgs_module = None
    for mod_name, cls_name in [("ddgs", "DDGS"), ("duckduckgo_search", "DDGS")]:
        try:
            import importlib
            mod = importlib.import_module(mod_name)
            ddgs_module = getattr(mod, cls_name)
            break
        except ImportError:
            continue

    if ddgs_module is None:
        return {
            "error": (
                "Web search requires 'ddgs' package: pip install ddgs. "
                "Alternatively, set TAVILY_API_KEY for Tavily search."
            ),
            "results": [],
        }

    try:
        with ddgs_module() as ddgs:
            hits = list(ddgs.text(query, max_results=max_results))

        return {
            "source": "duckduckgo",
            "results": [
                {
                    "title": r.get("title", ""),
                    "url": r.get("href", r.get("url", "")),
                    "content": r.get("body", r.get("content", "")),
                }
                for r in hits
            ],
        }
    except Exception as e:
        return {"error": f"DuckDuckGo search failed: {e}", "results": []}


def scrape_webpage(url: str, max_chars: int = 6000) -> dict:
    """Fetch and extract readable text content from a URL."""
    try:
        resp = requests.get(url, headers=_SCRAPE_HEADERS, timeout=20, allow_redirects=True)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "lxml")

        # Strip non-content elements
        for tag in soup.find_all(["script", "style", "nav", "footer", "header", "aside", "iframe"]):
            tag.decompose()

        main = soup.find("main") or soup.find("article") or soup.body
        raw = main.get_text(separator="\n", strip=True) if main else soup.get_text(separator="\n", strip=True)

        lines = [ln.strip() for ln in raw.splitlines() if ln.strip()]
        text = "\n".join(lines)[:max_chars]

        return {
            "url": url,
            "title": soup.title.string.strip() if soup.title and soup.title.string else "",
            "content": text,
            "truncated": len(text) >= max_chars,
        }
    except Exception as e:
        return {"url": url, "error": str(e), "content": ""}
