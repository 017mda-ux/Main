#!/usr/bin/env python3
"""Split the 'All Berkshire Hathaway Letters' PDF (1977-2019) into one text file per letter for search_library.

    python scripts/build_berkshire_library.py /path/to/All-Berkshire-Hathaway-Letters.pdf

Writes knowledge/berkshire/text/<year>.txt (git-ignored: the letters are Berkshire's copyright; the PDF is
public at berkshirehathaway.com) and knowledge/berkshire/INDEX.md (committed).
"""
import re
import subprocess
import sys
from pathlib import Path

OUT = Path(__file__).resolve().parent.parent / "knowledge" / "berkshire"


def main(pdf: str) -> int:
    text = subprocess.run(["pdftotext", pdf, "-"], capture_output=True, text=True, check=True).stdout
    starts = [m.start() for m in re.finditer(r"To the (Stock|Share)holders of Berkshire Hathaway", text, re.I)]
    labels = []
    year = 1977
    for i, s in enumerate(starts):
        head = text[s:s + 400]
        if "Vice Chairman" in text[max(0, s - 200):s] or head.startswith("To the shareholders of Berkshire Hathaway Inc.:\nI closely"):
            labels.append(("2014-munger", "Charlie Munger, Vice Chairman's Thoughts - Past and Future (2014 report)"))
            continue
        labels.append((str(year), f"Berkshire Hathaway shareholder letter {year}"))
        year += 1
    (OUT / "text").mkdir(parents=True, exist_ok=True)
    rows = ["# Berkshire Hathaway shareholder letters (1977-2019)", "",
            "Source: All-Berkshire-Hathaway-Letters.pdf (letters as published at berkshirehathaway.com).",
            "Text files are generated locally by scripts/build_berkshire_library.py and are not committed.", "",
            "| Document | Source | File |", "|---|---|---|"]
    for i, (s, (slug, title)) in enumerate(zip(starts, labels)):
        e = starts[i + 1] if i + 1 < len(starts) else len(text)
        (OUT / "text" / f"{slug}.txt").write_text(text[s:e], encoding="utf-8")
        rows.append(f"| {title} | [berkshirehathaway.com](https://www.berkshirehathaway.com/letters/letters.html) | text/{slug}.txt |")
    (OUT / "INDEX.md").write_text("\n".join(rows) + "\n", encoding="utf-8")
    print(f"wrote {len(starts)} documents to {OUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1]))
