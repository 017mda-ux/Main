#!/usr/bin/env python3
"""Fetch Berkshire letters 2020-2024 (not in the 1977-2019 PDF) and add them to knowledge/berkshire.

Source: the public GitHub repo ReeceHarding/buffett-letters (Markdown conversions of the letters at
berkshirehathaway.com), used because berkshirehathaway.com is blocked in some sandboxes. Some years lost their
spaces in conversion; they are re-segmented using word frequencies from the other letters. Treat quotes from these
files as near-verbatim and check them against the original PDFs before publishing.
Text is git-ignored; INDEX.md rows are added.

    python scripts/fetch_recent_berkshire.py
"""
import glob
import math
import re
from collections import Counter
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parent.parent / "knowledge" / "berkshire"
RAW = "https://raw.githubusercontent.com/ReeceHarding/buffett-letters/main/{y}.md"
YEARS = range(2020, 2025)


def segmenter(corpus_files):
    cnt = Counter()
    for f in corpus_files:
        cnt.update(w.lower() for w in re.findall(r"[A-Za-z]+", Path(f).read_text(encoding="utf-8", errors="ignore")) if len(w) <= 18)
    total = sum(cnt.values())
    cost = {w: math.log(total / c) for w, c in cnt.items()}

    def seg(s):
        low, n = s.lower(), len(s)
        best, back = [0.0] + [1e18] * n, [0] * (n + 1)
        for i in range(1, n + 1):
            for j in range(max(0, i - 18), i):
                c = best[j] + cost.get(low[j:i], 30 + 10 * (i - j))
                if c < best[i]:
                    best[i], back[i] = c, j
        out, i = [], n
        while i > 0:
            out.append(s[back[i]:i])
            i = back[i]
        return " ".join(reversed(out))

    return lambda text: re.sub(r"[A-Za-z]+", lambda m: seg(m.group(0)) if len(m.group(0)) > 12 or m.group(0).lower() not in cost else m.group(0), text)


def main():
    (ROOT / "text").mkdir(parents=True, exist_ok=True)
    fix = segmenter(glob.glob(str(ROOT.parent / "*" / "text" / "*.txt")))
    index = (ROOT / "INDEX.md").read_text(encoding="utf-8").splitlines()
    for y in YEARS:
        r = requests.get(RAW.format(y=y), timeout=30)
        r.raise_for_status()
        text = r.text
        words = re.findall(r"[A-Za-z]+", text)
        if sum(map(len, words)) / max(1, len(words)) > 6:   # spaces were lost in conversion
            text = fix(text)
        (ROOT / "text" / f"{y}.txt").write_text(text, encoding="utf-8")
        row = f"| Berkshire Hathaway shareholder letter {y} (Markdown conversion; verify quotes) | github.com/ReeceHarding/buffett-letters | text/{y}.txt |"
        if not any(f"text/{y}.txt" in line for line in index):
            index.append(row)
        print("added", y)
    index[0] = "# Berkshire Hathaway shareholder letters (1977-2024)"
    (ROOT / "INDEX.md").write_text("\n".join(index) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
