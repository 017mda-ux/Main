#!/usr/bin/env python3
"""Build searchable text libraries (one file per letter) from PDFs you own.

    python scripts/build_letter_libraries.py nomad    /path/Full_Collection_Nomad_Letters_.pdf
    python scripts/build_letter_libraries.py bpl      /path/buffett-partnership-letters.pdf
    python scripts/build_letter_libraries.py berkshire /path/All-Berkshire-Hathaway-Letters.pdf

    python scripts/build_letter_libraries.py cfa       /path/RR_2026_L2V5R3_v1.Free_Cash_Flow_Valuation.pdf
    python scripts/build_letter_libraries.py cfa       /path/RR_2026_L2V5R4_v1.Market-Based_Valuation...pdf

Writes knowledge/<name>/text/*.txt and knowledge/<name>/INDEX.md, which search_library reads. Personal research
library built from the user's own files. Requires pdftotext.
"""
import re
import subprocess
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent / "knowledge"
MONTHS = "January|February|March|April|May|June|July|August|September|October|November|December"


def pdf_lines(pdf):
    return subprocess.run(["pdftotext", "-layout", pdf, "-"], capture_output=True, text=True, check=True).stdout.splitlines()


def write(name, title, source, docs):
    out = ROOT / name
    (out / "text").mkdir(parents=True, exist_ok=True)
    rows = [f"# {title}", "", f"Source: {source}. Text files are generated locally by "
            "scripts/build_letter_libraries.py from the user's own files.", "", "| Document | Source | File |", "|---|---|---|"]
    used = Counter()
    for slug, label, body in docs:
        used[slug] += 1
        if used[slug] > 1:
            slug = f"{slug}-{used[slug]}"
        (out / "text" / f"{slug}.txt").write_text(body, encoding="utf-8")
        rows.append(f"| {label} | {source} | text/{slug}.txt |")
    (out / "INDEX.md").write_text("\n".join(rows) + "\n", encoding="utf-8")
    print(f"{name}: wrote {len(docs)} documents")


def nomad(pdf):
    lines = pdf_lines(pdf)
    head = re.compile(r"^\s*(Interim Report|Interim Letter|Annual Letter|Annual Report)\.?\s*$")
    period = re.compile(rf"^\s+For the period ended ({MONTHS}) (\d+)(st|th|nd|rd)?,? ((19|20)\d\d)")
    marks = []
    for i, ln in enumerate(lines):
        if head.match(ln) or period.match(ln):
            if not marks or i - marks[-1] > 5:
                marks.append(i)
    docs, last = [], None
    for k, s in enumerate(marks):
        e = marks[k + 1] if k + 1 < len(marks) else len(lines)
        label = None
        for ln in lines[s:s + 6]:
            m = period.match(ln)
            if m:
                label = (int(m.group(4)), 6 if m.group(1) == "June" else 12)
        if label is None and last:
            label = (last[0], 12) if last[1] == 6 else (last[0] + 1, 6)
        last = label
        kind = "interim" if label and label[1] == 6 else "annual"
        slug = f"{label[0]}-{'h1' if label[1] == 6 else 'fy'}" if label else f"doc{k}"
        docs.append((slug, f"Nomad Investment Partnership {kind} letter, period ended {'June' if label[1]==6 else 'December'} {label[0]}", "\n".join(lines[s:e])))
    if marks and marks[0] > 0:
        docs.insert(0, ("2001-fy", "Nomad Investment Partnership: cover, contents and 2001 annual letter", "\n".join(lines[:marks[0]])))
    write("nomad", "Nomad Investment Partnership letters (Nick Sleep and Qais Zakaria), 2001-2014",
          "Full_Collection_Nomad_Letters_.pdf (uploaded by the user)", docs)


# Late letters whose date line is missing from the PDF (dated by content and order).
BPL_UNDATED = {
    "About eighteen months ago I wrote to you regarding changed": ("1969-may", "May 1969 (decision to wind up the partnership)"),
    "Here is my present estimate of the BPL calendar": ("1969-oct", "October 1969 (calendar for winding up; Bill Ruane)"),
    "This letter is to supply you with some published information relating to our two controlled":
        ("1969-dec-controls", "December 1969 (information on the controlled companies)"),
    "This letter will attempt to provide a very elementary education regarding tax-exempt bonds":
        ("1970-feb-bonds", "February 1970 (tax-exempt bonds primer)"),
}


def bpl(pdf):
    lines = pdf_lines(pdf)
    pats = [re.compile(r"^\s*(19[56]\d) Letter\s*$"), re.compile(rf"^\s*({MONTHS}) \d{{1,2}}, (19[567]\d)\s*$"),
            re.compile(r"^\s*To My Partners:\s*$")]
    marks = []
    for i, ln in enumerate(lines):
        if any(p.match(ln) for p in pats) and (not marks or i - marks[-1] > 3):
            marks.append(i)
    docs = []
    for k, s in enumerate(marks):
        e = marks[k + 1] if k + 1 < len(marks) else len(lines)
        body = "\n".join(lines[s:e])
        m = re.search(rf"({MONTHS}) \d{{1,2}}, (19[567]\d)", "\n".join(lines[max(0, s - 3):s + 4]))
        y = re.match(r"^\s*(19[56]\d) Letter", lines[s])
        if y:
            when = f"{y.group(1)} annual letter"
            slug = f"{y.group(1)}"
        elif m:
            when = m.group(0)
            slug = f"{m.group(2)}-{m.group(1).lower()[:3]}"
        else:
            yrs = Counter(re.findall(r"\b(19[567]\d)\b", body[:4000])).most_common(1)
            when = f"letter c. {yrs[0][0]}" if yrs else "undated letter"
            slug = f"{yrs[0][0] if yrs else 'undated'}-letter"
        for opening, (oslug, owhen) in BPL_UNDATED.items():
            if opening in body[:600]:
                slug, when = oslug, owhen
        docs.append((slug, f"Buffett Partnership letter, {when}", body))
    write("bpl", "Buffett Partnership Ltd. letters to partners, 1957-1970",
          "buffett-partnership-letters.pdf (uploaded by the user)", docs)


def berkshire(pdf):
    text = "\n".join(pdf_lines(pdf))
    starts = [m.start() for m in re.finditer(r"To the (Stock|Share)holders of Berkshire Hathaway", text, re.I)]
    docs, year = [], 1977
    for i, s in enumerate(starts):
        e = starts[i + 1] if i + 1 < len(starts) else len(text)
        if "Vice Chairman" in text[max(0, s - 300):s]:
            docs.append(("2014-munger", "Charlie Munger, Vice Chairman's Thoughts - Past and Future (2014 report)", text[s:e]))
            continue
        docs.append((str(year), f"Berkshire Hathaway shareholder letter {year}", text[s:e]))
        year += 1
    write("berkshire", "Berkshire Hathaway shareholder letters (1977-2019)",
          "All-Berkshire-Hathaway-Letters.pdf (letters as published at berkshirehathaway.com)", docs)


def cfa(pdf):
    """CFA refresher readings: one text file per reading, appended to knowledge/cfa/INDEX.md."""
    text = "\n".join(pdf_lines(pdf))
    name = Path(pdf).name
    slug = "free_cash_flow_valuation" if "Free_Cash_Flow" in name else "market_multiples_valuation" if "Multiples" in name else Path(pdf).stem
    title = {"free_cash_flow_valuation": "CFA Level II reading: Free Cash Flow Valuation (2026)",
             "market_multiples_valuation": "CFA Level II reading: Market-Based Valuation - Price and Enterprise Value Multiples (2026)"}.get(slug, name)
    out = ROOT / "cfa"
    (out / "text").mkdir(parents=True, exist_ok=True)
    (out / "text" / f"{slug}.txt").write_text(text, encoding="utf-8")
    idx = out / "INDEX.md"
    rows = idx.read_text(encoding="utf-8").splitlines() if idx.exists() else [
        "# CFA Institute refresher readings (user's copies)", "", "| Document | Source | File |", "|---|---|---|"]
    if not any(f"text/{slug}.txt" in r for r in rows):
        rows.append(f"| {title} | {name} (uploaded by the user) | text/{slug}.txt |")
    idx.write_text("\n".join(rows) + "\n", encoding="utf-8")
    print(f"cfa: wrote {slug}")


if __name__ == "__main__":
    {"nomad": nomad, "bpl": bpl, "berkshire": berkshire, "cfa": cfa}[sys.argv[1]](sys.argv[2])
