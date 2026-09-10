"""Shared HTTP with retry, caching and a descriptive user agent.

Agency endpoints rate-limit anonymous traffic, so responses are cached on disk
and re-used within `ttl`.  Nothing here needs an API key.
"""

from __future__ import annotations

import hashlib
import json
import os
import time
import urllib.error
import urllib.request
from pathlib import Path

USER_AGENT = (
    "market-dashboard/0.1 (research tool; contact: repo owner)"
)

CACHE_DIR = Path(os.getenv("DASHBOARD_CACHE", "./data/cache"))
DEFAULT_TTL = int(os.getenv("DASHBOARD_CACHE_TTL", "1800"))  # 30 minutes


class HttpError(RuntimeError):
    """Raised when a source cannot be read; callers degrade rather than crash."""


def _cache_path(url: str, body: bytes | None) -> Path:
    h = hashlib.sha256(url.encode() + (body or b"")).hexdigest()[:20]
    return CACHE_DIR / f"{h}.cache"


def get(
    url: str,
    *,
    ttl: int = DEFAULT_TTL,
    retries: int = 3,
    timeout: int = 30,
    headers: dict[str, str] | None = None,
    body: bytes | None = None,
) -> str:
    """Fetch a URL as text, serving from cache when fresh."""
    path = _cache_path(url, body)
    if ttl > 0 and path.exists() and time.time() - path.stat().st_mtime < ttl:
        return path.read_text(encoding="utf-8", errors="replace")

    req_headers = {"User-Agent": USER_AGENT, "Accept": "*/*"}
    if headers:
        req_headers.update(headers)

    last: Exception | None = None
    for attempt in range(retries):
        try:
            req = urllib.request.Request(url, data=body, headers=req_headers)
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                text = resp.read().decode("utf-8", errors="replace")
            CACHE_DIR.mkdir(parents=True, exist_ok=True)
            path.write_text(text, encoding="utf-8")
            return text
        except (urllib.error.URLError, urllib.error.HTTPError, OSError) as exc:
            last = exc
            if attempt < retries - 1:
                time.sleep(2 ** attempt)

    # Stale cache beats no data at all — the renderer flags the age.
    if path.exists():
        return path.read_text(encoding="utf-8", errors="replace")
    raise HttpError(f"{url}: {last}")


def get_json(url: str, **kw) -> dict:
    raw = get(url, **kw)
    try:
        return json.loads(raw)
    except json.JSONDecodeError as exc:
        raise HttpError(f"{url}: invalid JSON ({exc})") from exc
