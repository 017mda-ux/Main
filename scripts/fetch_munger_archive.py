#!/usr/bin/env python3
"""
Download the Charlie Munger PDFs listed on the Worldly Partners archive page and
turn them into a searchable text library for the Nomad agent.

    python scripts/fetch_munger_archive.py            # fetch everything new
    python scripts/fetch_munger_archive.py --dry-run  # list what would be fetched

Output:
    knowledge/munger/pdfs/<name>.pdf   (git-ignored)
    knowledge/munger/text/<name>.txt   (plain text, searched by the agent)
    knowledge/munger/INDEX.md          (title, source URL, file for each document)

Downloaded PDFs are untrusted input: they are only read by `pdftotext`, never executed.
"""

from __future__ import annotations

import argparse
import re
import subprocess
import sys
from pathlib import Path
from urllib.parse import unquote, urljoin, urlparse

import requests
from bs4 import BeautifulSoup

ARCHIVE_URL = "https://worldlypartners.com/charlie-munger-archive/"
ROOT = Path(__file__).resolve().parent.parent / "knowledge" / "munger"
HEADERS = {"User-Agent": "Mozilla/5.0 (personal research library builder)"}


def slugify(text: str) -> str:
    text = re.sub(r"[^A-Za-z0-9]+", "-", text).strip("-").lower()
    return text[:90] or "document"


def find_pdf_links(html: str, base: str) -> list[tuple[str, str]]:
    """Return (title, absolute_url) for every link to a PDF, de-duplicated, in page order."""
    soup = BeautifulSoup(html, "html.parser")
    seen, out = set(), []
    for a in soup.find_all("a", href=True):
        url = urljoin(base, a["href"].strip())
        if not urlparse(url).path.lower().endswith(".pdf") or url in seen:
            continue
        seen.add(url)
        title = " ".join(a.get_text(" ", strip=True).split())
        if not title:
            title = unquote(Path(urlparse(url).path).stem).replace("-", " ").replace("_", " ")
        out.append((title, url))
    return out


def pdf_to_text(pdf: Path, txt: Path) -> bool:
    result = subprocess.run(["pdftotext", "-layout", str(pdf), str(txt)],
                            capture_output=True, timeout=300)
    return result.returncode == 0 and txt.exists() and txt.stat().st_size > 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--url", default=ARCHIVE_URL)
    ap.add_argument("--urls-file", help="Text file of PDF URLs (one per line) instead of scraping a page")
    ap.add_argument("--out", help="Output folder (default knowledge/munger)")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    global ROOT
    if args.out:
        ROOT = Path(args.out).resolve()
    if args.urls_file:
        urls = [u.strip() for u in Path(args.urls_file).read_text().splitlines()
                if u.strip() and not u.startswith("#")]
        links = [(unquote(Path(urlparse(u).path).stem).replace("-", " "), u) for u in urls]
        print(f"Read {len(links)} PDF URLs from {args.urls_file}")
    else:
        page = requests.get(args.url, headers=HEADERS, timeout=30)
        page.raise_for_status()
        links = find_pdf_links(page.text, args.url)
        print(f"Found {len(links)} PDF links on {args.url}")
    if args.dry_run:
        for title, url in links:
            print(f"  {title}  ->  {url}")
        return 0

    (ROOT / "pdfs").mkdir(parents=True, exist_ok=True)
    (ROOT / "text").mkdir(parents=True, exist_ok=True)
    index_rows, failures = [], []
    used = set()
    for title, url in links:
        name = slugify(Path(urlparse(url).path).stem)
        while name in used:
            name += "-2"
        used.add(name)
        pdf, txt = ROOT / "pdfs" / f"{name}.pdf", ROOT / "text" / f"{name}.txt"
        try:
            if not pdf.exists():
                r = requests.get(url, headers=HEADERS, timeout=120)
                r.raise_for_status()
                if not r.content.startswith(b"%PDF"):
                    raise ValueError("response is not a PDF")
                pdf.write_bytes(r.content)
            if not txt.exists() and not pdf_to_text(pdf, txt):
                raise ValueError("text extraction failed (scanned PDF?)")
            index_rows.append(f"| {title} | [{url}]({url}) | text/{name}.txt |")
            print(f"  ok   {title}")
        except Exception as exc:  # keep going; report at the end
            failures.append(f"{title} ({url}): {exc}")
            print(f"  FAIL {title}: {exc}")

    (ROOT / "INDEX.md").write_text(
        "# Charlie Munger archive (from Worldly Partners)\n\n"
        f"Source page: {args.url}\n\n"
        "| Title | Source | Text file |\n|---|---|---|\n" + "\n".join(index_rows) + "\n"
        + ("\n## Not fetched\n\n" + "\n".join(f"- {f}" for f in failures) + "\n" if failures else ""),
        encoding="utf-8",
    )
    print(f"\n{len(index_rows)} documents ready, {len(failures)} failed. Index: {ROOT / 'INDEX.md'}")
    return 0 if index_rows else 1


if __name__ == "__main__":
    sys.exit(main())
