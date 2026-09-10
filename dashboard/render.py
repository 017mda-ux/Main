"""Snapshot → HTML.

The page is a scanning surface, not a document: visual weight tracks salience,
so the module that earned the top score gets a chart and full prose while a
module that barely cleared the floor gets one line. That is what keeps the
brief from reading the same way every day.
"""

from __future__ import annotations

import html
import json
from datetime import date, datetime
from pathlib import Path

# ──────────────────────────────────────────────────────────────────────
#  Design tokens
# ──────────────────────────────────────────────────────────────────────

CSS = """
:root {
  color-scheme: light;

  /* Neutrals carry a slight cool bias — chosen for a rates surface, not
     inherited mid-grey. */
  --ground:        #f6f7f8;
  --surface:       #ffffff;
  --surface-sunk:  #eef0f2;
  --rule:          #dfe2e6;
  --rule-strong:   #c4c9d0;

  --ink:           #14171c;
  --ink-2:         #545c68;
  --ink-3:         #838c99;

  --accent:        #2a78d6;
  --accent-soft:   #e8f0fc;

  /* Semantic polarity. In rates the meaningful axis is hawkish/inflationary
     against dovish/disinflationary, so the diverging pair does real work. */
  --hot:           #c93a39;
  --hot-soft:      #fbeceb;
  --cool:          #2a78d6;
  --cool-soft:     #e8f0fc;
  --watch:         #b07800;
  --watch-soft:    #fdf3dc;
  --flat:          #838c99;

  --spark:         #2a78d6;

  --shadow: 0 1px 2px rgba(20, 23, 28, .06), 0 6px 18px rgba(20, 23, 28, .05);

  --sans: "IBM Plex Sans", ui-sans-serif, system-ui, -apple-system, "Segoe UI", sans-serif;
  --serif: "Newsreader", ui-serif, Georgia, "Times New Roman", serif;
  --mono: "IBM Plex Mono", ui-monospace, SFMono-Regular, Menlo, Consolas, monospace;
}

@media (prefers-color-scheme: dark) {
  :root:not([data-theme="light"]) {
    color-scheme: dark;
    --ground:        #101318;
    --surface:       #171b21;
    --surface-sunk:  #1e232b;
    --rule:          #272d36;
    --rule-strong:   #3a424e;

    --ink:           #eef1f4;
    --ink-2:         #a6afbc;
    --ink-3:         #6e7887;

    --accent:        #4d92e8;
    --accent-soft:   #16273d;

    --hot:           #e46a68;
    --hot-soft:      #2e1a1a;
    --cool:          #4d92e8;
    --cool-soft:     #16273d;
    --watch:         #d99f26;
    --watch-soft:    #2b2313;
    --flat:          #6e7887;

    --spark:         #4d92e8;

    --shadow: 0 1px 2px rgba(0, 0, 0, .4), 0 6px 20px rgba(0, 0, 0, .3);
  }
}

:root[data-theme="dark"] {
  color-scheme: dark;
  --ground:        #101318;
  --surface:       #171b21;
  --surface-sunk:  #1e232b;
  --rule:          #272d36;
  --rule-strong:   #3a424e;

  --ink:           #eef1f4;
  --ink-2:         #a6afbc;
  --ink-3:         #6e7887;

  --accent:        #4d92e8;
  --accent-soft:   #16273d;

  --hot:           #e46a68;
  --hot-soft:      #2e1a1a;
  --cool:          #4d92e8;
  --cool-soft:     #16273d;
  --watch:         #d99f26;
  --watch-soft:    #2b2313;
  --flat:          #6e7887;

  --spark:         #4d92e8;

  --shadow: 0 1px 2px rgba(0, 0, 0, .4), 0 6px 20px rgba(0, 0, 0, .3);
}

* { box-sizing: border-box; }

body {
  margin: 0;
  background: var(--ground);
  color: var(--ink);
  font-family: var(--sans);
  font-size: 15px;
  line-height: 1.55;
  -webkit-font-smoothing: antialiased;
}

.wrap {
  max-width: 1080px;
  margin: 0 auto;
  padding-inline: 20px;
  padding-block: 0 72px;
}

/* ---- masthead ------------------------------------------------------ */

.masthead {
  display: flex;
  flex-wrap: wrap;
  align-items: baseline;
  justify-content: space-between;
  gap: 12px 24px;
  padding-block: 28px 18px;
  border-bottom: 2px solid var(--ink);
}

.masthead h1 {
  font-family: var(--serif);
  font-size: clamp(26px, 4.4vw, 38px);
  font-weight: 500;
  letter-spacing: -.015em;
  margin: 0;
  text-wrap: balance;
}

.stamp {
  font-family: var(--mono);
  font-size: 11.5px;
  letter-spacing: .04em;
  text-transform: uppercase;
  color: var(--ink-3);
  text-align: right;
  line-height: 1.7;
}
.stamp b { color: var(--ink-2); font-weight: 500; }

/* ---- thesis -------------------------------------------------------- */

.thesis { padding-block: 26px 6px; }

.thesis .lede {
  font-family: var(--serif);
  font-size: clamp(19px, 2.6vw, 25px);
  line-height: 1.35;
  font-weight: 400;
  letter-spacing: -.01em;
  margin: 0 0 16px;
  text-wrap: balance;
  max-width: 46ch;
  min-width: 0;
}

.thesis .body {
  font-family: var(--serif);
  font-size: 16.5px;
  line-height: 1.62;
  color: var(--ink-2);
  margin: 0;
  max-width: 68ch;
}

.thesis .kicker {
  margin-top: 16px;
  padding: 12px 14px;
  border-left: 3px solid var(--hot);
  background: var(--hot-soft);
  font-size: 14.5px;
  color: var(--ink);
  border-radius: 0 4px 4px 0;
}

/* ---- tape ---------------------------------------------------------- */

.tape-head {
  display: flex;
  align-items: center;
  gap: 12px;
  margin: 34px 0 10px;
}

.section-label {
  font-family: var(--mono);
  font-size: 11px;
  letter-spacing: .12em;
  text-transform: uppercase;
  color: var(--ink-3);
  white-space: nowrap;
}
.section-label + .hr { flex: 1; height: 1px; background: var(--rule); }

.tape {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(148px, 1fr));
  background: var(--surface);
  border: 1px solid var(--rule);
  border-radius: 5px;
  overflow: hidden;
}

.tick {
  background: var(--surface);
  padding: 11px 13px 12px;
  display: flex;
  flex-direction: column;
  gap: 2px;
  border-top: 2px solid transparent;
  border-right: 1px solid var(--rule);
  border-bottom: 1px solid var(--rule);
}
.tick.hot  { border-top-color: var(--hot); }
.tick.cool { border-top-color: var(--cool); }
.tick.neutral { border-top-color: var(--rule-strong); }

.tick .k {
  font-family: var(--sans);
  font-size: 11.5px;
  color: var(--ink-3);
  letter-spacing: .02em;
}
.tick .v {
  font-family: var(--mono);
  font-size: 19px;
  font-weight: 500;
  font-variant-numeric: tabular-nums;
  letter-spacing: -.02em;
}
.tick .s {
  font-size: 11.5px;
  color: var(--ink-2);
  line-height: 1.35;
}

/* ---- modules ------------------------------------------------------- */

.modules { display: flex; flex-direction: column; gap: 2px; margin-top: 8px; }

.mod {
  background: var(--surface);
  border: 1px solid var(--rule);
  border-left: 3px solid var(--rule-strong);
  border-radius: 0 5px 5px 0;
  padding: 18px 20px;
}
.mod.lead {
  border-left-color: var(--hot);
  padding: 24px 22px 22px;
  box-shadow: var(--shadow);
}
.mod.mid  { border-left-color: var(--watch); }
.mod.tail { border-left-color: var(--rule-strong); padding: 14px 20px; }

.mod-head {
  display: flex;
  align-items: baseline;
  justify-content: space-between;
  gap: 10px 18px;
  flex-wrap: wrap;
}

.mod h2 {
  font-family: var(--serif);
  font-weight: 500;
  font-size: 21px;
  letter-spacing: -.01em;
  margin: 0;
  text-wrap: balance;
}
.mod.lead h2 { font-size: 25px; }
.mod.tail h2 { font-size: 17.5px; font-family: var(--sans); font-weight: 600; }

.meta {
  display: flex;
  align-items: center;
  gap: 8px;
  font-family: var(--mono);
  font-size: 10.5px;
  letter-spacing: .06em;
  text-transform: uppercase;
  color: var(--ink-3);
  white-space: nowrap;
}

.chip {
  display: inline-flex;
  align-items: center;
  gap: 5px;
  padding: 2px 7px;
  border-radius: 3px;
  background: var(--surface-sunk);
  color: var(--ink-2);
  font-size: 10.5px;
}
.chip.hot   { background: var(--hot-soft);   color: var(--hot); }
.chip.watch { background: var(--watch-soft); color: var(--watch); }
.chip.cool  { background: var(--cool-soft);  color: var(--cool); }

/* The score bar makes the ranking legible rather than asking for trust. */
.score {
  display: inline-flex;
  align-items: center;
  gap: 6px;
}
.score .bar {
  width: 42px; height: 4px;
  background: var(--surface-sunk);
  border-radius: 2px;
  overflow: hidden;
}
.score .bar i { display: block; height: 100%; background: var(--ink-3); }
.mod.lead .score .bar i { background: var(--hot); }
.mod.mid  .score .bar i { background: var(--watch); }

.why {
  margin: 10px 0 0;
  padding: 0;
  list-style: none;
  display: flex;
  flex-direction: column;
  gap: 5px;
}
.why li {
  position: relative;
  padding-left: 15px;
  font-size: 14px;
  color: var(--ink-2);
  line-height: 1.5;
}
.why li::before {
  content: "";
  position: absolute;
  left: 0; top: .62em;
  width: 5px; height: 5px;
  border-radius: 50%;
  background: var(--accent);
}

.detail {
  font-family: var(--serif);
  font-size: 16px;
  line-height: 1.62;
  color: var(--ink);
  margin: 14px 0 0;
  max-width: 70ch;
}
.mod.tail .detail { font-size: 14.5px; color: var(--ink-2); }

.caveat {
  margin-top: 12px;
  font-size: 13px;
  color: var(--ink-2);
  padding: 9px 12px;
  background: var(--surface-sunk);
  border-radius: 4px;
}
.caveat b { color: var(--ink); }

/* ---- data blocks --------------------------------------------------- */

.figs {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(140px, 1fr));
  gap: 14px 20px;
  margin-top: 16px;
  padding-top: 14px;
  border-top: 1px solid var(--rule);
}
.fig .l { font-size: 11.5px; color: var(--ink-3); }
.fig .v {
  font-family: var(--mono);
  font-size: 17px;
  font-weight: 500;
  font-variant-numeric: tabular-nums;
}
.fig .c { font-size: 11.5px; color: var(--ink-2); }
.fig .c.hot { color: var(--hot); }
.fig .c.cool { color: var(--cool); }

table.grid {
  width: 100%;
  border-collapse: collapse;
  margin-top: 16px;
  font-size: 14px;
}
table.grid th, table.grid td {
  text-align: left;
  padding: 8px 10px;
  border-bottom: 1px solid var(--rule);
}
table.grid th {
  font-family: var(--mono);
  font-size: 10.5px;
  letter-spacing: .07em;
  text-transform: uppercase;
  color: var(--ink-3);
  font-weight: 500;
  border-bottom-color: var(--rule-strong);
}
table.grid td.num {
  font-family: var(--mono);
  font-variant-numeric: tabular-nums;
  text-align: right;
  white-space: nowrap;
}
table.grid tr:last-child td { border-bottom: none; }
.scroll-x { overflow-x: auto; }

/* ---- charts -------------------------------------------------------- */

figure.chart {
  margin: 18px 0 0;
  padding: 16px 4px 8px;
  border-top: 1px solid var(--rule);
}
figure.chart figcaption {
  font-family: var(--mono);
  font-size: 10.5px;
  letter-spacing: .07em;
  text-transform: uppercase;
  color: var(--ink-3);
  margin-bottom: 12px;
}
figure.chart svg { display: block; width: 100%; height: auto; overflow: visible; }
.chart-note {
  font-size: 12px;
  color: var(--ink-3);
  margin-top: 10px;
}

/* ---- regions ------------------------------------------------------- */

.regions {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(268px, 1fr));
  gap: 14px;
  margin-top: 10px;
}
.region {
  background: var(--surface);
  border: 1px solid var(--rule);
  border-radius: 5px;
  padding: 16px 17px;
  display: flex;
  flex-direction: column;
  gap: 9px;
}
.region-head { display: flex; align-items: center; gap: 8px; }
.region h3 {
  margin: 0;
  font-size: 15px;
  font-weight: 600;
  letter-spacing: .01em;
}
.dot { width: 7px; height: 7px; border-radius: 50%; flex: none; }
.dot.critical { background: var(--hot); }
.dot.watch { background: var(--watch); }
.dot.calm { background: var(--cool); }

.region .head-line {
  font-family: var(--serif);
  font-size: 15px;
  line-height: 1.45;
  color: var(--ink);
  margin: 0;
}
.region ul {
  margin: 0; padding: 0; list-style: none;
  display: flex; flex-direction: column; gap: 6px;
}
.region ul li {
  font-size: 13.5px;
  color: var(--ink-2);
  line-height: 1.45;
  padding-left: 13px;
  position: relative;
}
.region ul li::before {
  content: "";
  position: absolute; left: 0; top: .6em;
  width: 4px; height: 1.5px; background: var(--ink-3);
}
.region .read {
  margin-top: auto;
  padding-top: 9px;
  border-top: 1px solid var(--rule);
  font-size: 13px;
  color: var(--ink-2);
}
.region .read b {
  color: var(--ink-3);
  font-family: var(--mono);
  font-size: 10px;
  letter-spacing: .08em;
  text-transform: uppercase;
  display: block;
  margin-bottom: 3px;
}

/* ---- speak --------------------------------------------------------- */

.speak { display: flex; flex-direction: column; gap: 12px; margin-top: 10px; }
.quote {
  background: var(--surface);
  border: 1px solid var(--rule);
  border-radius: 5px;
  padding: 16px 18px;
  display: flex;
  flex-direction: column;
  gap: 8px;
}
.quote .who {
  display: flex; align-items: baseline; gap: 9px; flex-wrap: wrap;
}
.quote .name { font-weight: 600; font-size: 15px; }
.quote .role, .quote .when { font-size: 12px; color: var(--ink-3); }
.quote blockquote {
  margin: 0;
  font-family: var(--serif);
  font-size: 16px;
  line-height: 1.55;
  color: var(--ink);
  padding-left: 13px;
  border-left: 2px solid var(--rule-strong);
}
.quote.hawkish blockquote { border-left-color: var(--hot); }
.quote .impact { font-size: 13px; color: var(--ink-2); }

/* ---- calendar ------------------------------------------------------ */

.cal { display: flex; flex-direction: column; gap: 1px; background: var(--rule);
       border: 1px solid var(--rule); border-radius: 5px; overflow: hidden; margin-top: 10px; }
.cal-row {
  background: var(--surface);
  display: grid;
  grid-template-columns: 92px 1fr auto;
  gap: 14px;
  align-items: baseline;
  padding: 12px 15px;
}
.cal-row .d {
  font-family: var(--mono);
  font-size: 12px;
  font-variant-numeric: tabular-nums;
  color: var(--ink-2);
}
.cal-row .e { font-size: 14.5px; }
.cal-row .e small { display: block; color: var(--ink-3); font-size: 12px; }
.cal-row.high { border-left: 3px solid var(--hot); padding-left: 12px; }

/* ---- sources / footer ---------------------------------------------- */

.srcs {
  margin-top: 14px;
  padding-top: 11px;
  border-top: 1px solid var(--rule);
  display: flex;
  flex-wrap: wrap;
  gap: 6px 14px;
}
.srcs a {
  font-size: 12px;
  color: var(--ink-3);
  text-decoration: none;
  border-bottom: 1px solid var(--rule-strong);
}
.srcs a:hover, .srcs a:focus-visible { color: var(--accent); border-bottom-color: var(--accent); }

.colophon {
  margin-top: 44px;
  padding: 18px 20px;
  background: var(--surface-sunk);
  border-radius: 5px;
  font-size: 13px;
  color: var(--ink-2);
  line-height: 1.6;
}
.colophon h4 {
  margin: 0 0 8px;
  font-family: var(--mono);
  font-size: 10.5px;
  letter-spacing: .1em;
  text-transform: uppercase;
  color: var(--ink-3);
  font-weight: 500;
}
.colophon ul { margin: 8px 0 0; padding-left: 18px; }
.colophon code {
  font-family: var(--mono);
  font-size: 12px;
  background: var(--surface);
  padding: 1px 5px;
  border-radius: 3px;
  border: 1px solid var(--rule);
}

a:focus-visible, button:focus-visible {
  outline: 2px solid var(--accent);
  outline-offset: 2px;
}

@media (max-width: 640px) {
  .masthead { padding-block: 22px 14px; }
  .stamp { text-align: left; }
  .cal-row { grid-template-columns: 1fr; gap: 4px; }
  .mod.lead { padding: 18px 16px; }
  .mod { padding: 15px 16px; }
}

@media (prefers-reduced-motion: reduce) {
  * { animation: none !important; transition: none !important; }
}
"""


def esc(s) -> str:
    return html.escape(str(s if s is not None else ""))


# ──────────────────────────────────────────────────────────────────────
#  Charts — hand-drawn SVG, one scale, theme-token colours
# ──────────────────────────────────────────────────────────────────────

def chart_path(spec: dict) -> str:
    """Annotated line chart for a short, sourced path (e.g. hike odds)."""
    pts = spec.get("series", [])
    if len(pts) < 2:
        return ""

    w, h = 720, 230
    pad_l, pad_r, pad_t, pad_b = 46, 112, 52, 50

    vals = [p["value"] for p in pts]
    lo, hi = min(vals), max(vals)
    span = max(hi - lo, 1e-6)
    lo, hi = lo - span * 0.28, hi + span * 0.28

    def x(i: int) -> float:
        return pad_l + (w - pad_l - pad_r) * i / (len(pts) - 1)

    def y(v: float) -> float:
        return pad_t + (h - pad_t - pad_b) * (1 - (v - lo) / (hi - lo))

    # Gridlines at values the data actually reaches.
    ticks = [round(min(vals)), round((min(vals) + max(vals)) / 2), round(max(vals))]
    ticks = sorted(set(ticks))

    grid = "".join(
        f'<line x1="{pad_l}" y1="{y(t):.1f}" x2="{w - pad_r}" y2="{y(t):.1f}" '
        f'stroke="var(--rule)" stroke-width="1"/>'
        f'<text x="{pad_l - 9}" y="{y(t) + 4:.1f}" text-anchor="end" '
        f'font-family="var(--mono)" font-size="11" fill="var(--ink-3)">{t}%</text>'
        for t in ticks
    )

    line = " ".join(f"{x(i):.1f},{y(p['value']):.1f}" for i, p in enumerate(pts))
    area = (f"{pad_l},{h - pad_b} " + line +
            f" {x(len(pts) - 1):.1f},{h - pad_b}")

    dots, labels = [], []
    for i, p in enumerate(pts):
        px, py = x(i), y(p["value"])
        last = i == len(pts) - 1
        r = 5 if last else 3.5
        dots.append(
            f'<circle cx="{px:.1f}" cy="{py:.1f}" r="{r}" fill="var(--hot)" '
            f'stroke="var(--surface)" stroke-width="2"/>'
        )
        d = datetime.strptime(p["date"], "%Y-%m-%d").date()
        labels.append(
            f'<text x="{px:.1f}" y="{h - pad_b + 17:.1f}" text-anchor="middle" '
            f'font-family="var(--mono)" font-size="10" fill="var(--ink-3)">'
            f'{d:%d %b}</text>'
        )
        if p.get("note"):
            anchor = "end" if i > len(pts) * 0.6 else "start"
            dx = -10 if anchor == "end" else 10
            # Alternate sides: adjacent points sit at similar heights, so
            # same-side labels would overlap.
            dy = -13 if i % 2 == 0 else 21
            labels.append(
                f'<text x="{px + dx:.1f}" y="{py + dy:.1f}" text-anchor="{anchor}" '
                f'font-family="var(--sans)" font-size="11" fill="var(--ink-2)">'
                f'{esc(p["note"])}</text>'
            )

    # The final value gets a direct label; no number on every point.
    lx, ly = x(len(pts) - 1), y(pts[-1]["value"])
    labels.append(
        f'<text x="{lx + 12:.1f}" y="{ly + 5:.1f}" font-family="var(--mono)" '
        f'font-size="17" font-weight="500" fill="var(--hot)">'
        f'{pts[-1]["value"]:.0f}%</text>'
    )

    # 50% reference: the line between "priced" and "not priced".
    fifty = ""
    if lo < 50 < hi:
        fifty = (
            f'<line x1="{pad_l}" y1="{y(50):.1f}" x2="{w - pad_r}" y2="{y(50):.1f}" '
            f'stroke="var(--ink-3)" stroke-width="1" stroke-dasharray="4 4"/>'
            f'<text x="{w - pad_r + 6}" y="{y(50) + 4:.1f}" font-family="var(--mono)" '
            f'font-size="10" fill="var(--ink-3)">coin flip</text>'
        )

    return f"""
<figure class="chart">
  <figcaption>{esc(spec.get('title', ''))}</figcaption>
  <svg viewBox="0 0 {w} {h}" role="img"
       aria-label="{esc(spec.get('title', ''))}: rising from
       {vals[0]:.0f}% to {vals[-1]:.0f}%">
    {grid}{fifty}
    <polygon points="{area}" fill="var(--hot)" opacity=".07"/>
    <polyline points="{line}" fill="none" stroke="var(--hot)" stroke-width="2"
              stroke-linejoin="round" stroke-linecap="round"/>
    {''.join(dots)}{''.join(labels)}
  </svg>
  <p class="chart-note">{esc(spec.get('source', ''))}</p>
</figure>"""


def chart_surprise(rows: list[dict]) -> str:
    """Actual against consensus, on one shared scale per row."""
    if not rows:
        return ""

    out = ['<table class="grid"><thead><tr>'
           '<th>Release</th><th class="num">Consensus</th>'
           '<th class="num">Actual</th><th class="num">Surprise</th>'
           '<th style="width:34%">&nbsp;</th></tr></thead><tbody>']

    span = max(
        (abs(r["actual"] - r["consensus"]) for r in rows
         if r.get("consensus") is not None), default=1.0
    ) or 1.0

    for r in rows:
        a, c = r.get("actual"), r.get("consensus")
        unit = r.get("unit", "")
        miss = None if c is None else a - c
        tone = "flat"
        if miss is not None and abs(miss) > 1e-9:
            tone = "hot" if miss > 0 else "cool"

        bar = ""
        if miss is not None:
            frac = min(abs(miss) / span, 1.0)
            width = 46 * frac
            left = 50 - (width if miss < 0 else 0)
            colour = "var(--hot)" if miss > 0 else "var(--cool)"
            bar = (
                f'<svg viewBox="0 0 100 16" height="16" style="width:100%" '
                f'role="img" aria-label="surprise {miss:+.1f}{unit}">'
                f'<line x1="50" y1="1" x2="50" y2="15" stroke="var(--rule-strong)" '
                f'stroke-width="1"/>'
                f'<rect x="{left:.1f}" y="4" width="{width:.1f}" height="8" rx="2" '
                f'fill="{colour}"/></svg>'
            )

        out.append(
            f'<tr><td>{esc(r["metric"])}</td>'
            f'<td class="num">{"—" if c is None else f"{c:,.1f}{unit}"}</td>'
            f'<td class="num"><b>{a:,.1f}{unit}</b></td>'
            f'<td class="num" style="color:var(--{tone})">'
            f'{"—" if miss is None else f"{miss:+,.1f}"}</td>'
            f'<td>{bar}</td></tr>'
        )
    out.append("</tbody></table>")
    return "".join(out)


def chart_gap(ratio_value: float, versus_value: float) -> str:
    """Copper/gold against the 10-year on one numeric axis.

    Both series are conventionally plotted on the same scale, so this is a
    single-axis comparison — never two y-scales.
    """
    w, h = 720, 148
    pad_l, pad_r = 120, 60
    top = 34
    axis_y = h - 34
    hi = max(ratio_value, versus_value) * 1.35

    def x(v: float) -> float:
        return pad_l + (w - pad_l - pad_r) * (v / hi)

    ticks = [i for i in range(0, int(hi) + 2) if i <= hi]
    grid = "".join(
        f'<line x1="{x(t):.1f}" y1="{top - 8}" x2="{x(t):.1f}" y2="{axis_y}" '
        f'stroke="var(--rule)" stroke-width="1"/>'
        f'<text x="{x(t):.1f}" y="{axis_y + 16}" text-anchor="middle" '
        f'font-family="var(--mono)" font-size="10" fill="var(--ink-3)">{t}</text>'
        for t in ticks
    )

    rows = [
        ("Copper / gold ×1000", ratio_value, "var(--cool)", top + 4),
        ("10-year yield %", versus_value, "var(--hot)", top + 40),
    ]
    bars = []
    for label, val, colour, ry in rows:
        bars.append(
            f'<text x="{pad_l - 12}" y="{ry + 13}" text-anchor="end" '
            f'font-family="var(--sans)" font-size="12" fill="var(--ink-2)">'
            f'{esc(label)}</text>'
            f'<rect x="{pad_l}" y="{ry}" width="{x(val) - pad_l:.1f}" height="18" '
            f'rx="3" fill="{colour}"/>'
            f'<text x="{x(val) + 9:.1f}" y="{ry + 13}" font-family="var(--mono)" '
            f'font-size="13" font-weight="500" fill="{colour}">{val:.2f}</text>'
        )

    # The gap is the story, so it gets drawn explicitly.
    gx1, gx2 = x(min(ratio_value, versus_value)), x(max(ratio_value, versus_value))
    gap = (
        f'<line x1="{gx1:.1f}" y1="{top + 26}" x2="{gx2:.1f}" y2="{top + 26}" '
        f'stroke="var(--ink-3)" stroke-width="1" stroke-dasharray="3 3"/>'
        f'<text x="{(gx1 + gx2) / 2:.1f}" y="{top + 22}" text-anchor="middle" '
        f'font-family="var(--mono)" font-size="11" fill="var(--ink-3)">'
        f'{abs(versus_value - ratio_value):.2f} apart</text>'
    )

    return f"""
<figure class="chart">
  <figcaption>The two normally track. Today they do not.</figcaption>
  <svg viewBox="0 0 {w} {h}" role="img"
       aria-label="Copper gold ratio {ratio_value:.2f} against 10-year yield
       {versus_value:.2f}, on one scale">
    {grid}
    <line x1="{pad_l}" y1="{top - 8}" x2="{pad_l}" y2="{axis_y}"
          stroke="var(--rule-strong)" stroke-width="1"/>
    {''.join(bars)}{gap}
  </svg>
  <p class="chart-note">Plotted on one shared numeric axis, which is the
     convention for this pair — the ratio is scaled ×1000 so it reads directly
     against a yield in percent.</p>
</figure>"""


def sparkline(values: list[float], width: int = 132, height: int = 30) -> str:
    """Compact trend for a level module, when the pipeline has history."""
    if len(values) < 8:
        return ""
    lo, hi = min(values), max(values)
    span = max(hi - lo, 1e-9)
    step = width / (len(values) - 1)
    pts = " ".join(
        f"{i * step:.1f},{height - (v - lo) / span * (height - 4) - 2:.1f}"
        for i, v in enumerate(values)
    )
    last_x = width
    last_y = height - (values[-1] - lo) / span * (height - 4) - 2
    return (
        f'<svg viewBox="0 0 {width + 4} {height}" width="{width + 4}" '
        f'height="{height}" role="img" aria-label="trend, last {len(values)} '
        f'observations"><polyline points="{pts}" fill="none" '
        f'stroke="var(--spark)" stroke-width="1.5" stroke-linejoin="round"/>'
        f'<circle cx="{last_x:.1f}" cy="{last_y:.1f}" r="2.6" '
        f'fill="var(--spark)"/></svg>'
    )


# ──────────────────────────────────────────────────────────────────────
#  Module rendering — weight tracks salience
# ──────────────────────────────────────────────────────────────────────

def _weight_class(score: float) -> str:
    if score >= 80:
        return "lead"
    if score >= 62:
        return "mid"
    return "tail"


def _bucket_label(bucket: str) -> str:
    return {
        "event": "catalyst", "policy": "policy", "curve": "rates",
        "fiscal": "fiscal", "fx": "currency", "commodity": "commodity",
        "equity": "equity", "credit": "credit", "activity": "data",
        "ratio": "cross-asset",
    }.get(bucket, bucket)


def render_module(m: dict) -> str:
    score = m.get("score", 0.0)
    cls = _weight_class(score)
    kind = m.get("kind", "level")

    chips = [f'<span class="chip">{esc(_bucket_label(m.get("bucket", "")))}</span>']
    if kind == "event" and m.get("days_out") is not None:
        d = m["days_out"]
        when = "today" if d == 0 else "tomorrow" if d == 1 else f"in {d} days"
        chips.append(f'<span class="chip hot">{esc(when)}</span>')

    head = f"""
  <div class="mod-head">
    <h2>{esc(m.get('label', ''))}</h2>
    <div class="meta">
      {''.join(chips)}
      <span class="score" title="Salience score {score:.0f} of 100">
        <span class="bar"><i style="width:{min(score, 100):.0f}%"></i></span>
        {score:.0f}
      </span>
    </div>
  </div>"""

    why = ""
    if m.get("reasons"):
        why = ('<ul class="why">'
               + "".join(f"<li>{esc(r)}</li>" for r in m["reasons"])
               + "</ul>")

    detail = f'<p class="detail">{esc(m["detail"])}</p>' if m.get("detail") else ""

    body = ""

    if kind == "event" and m.get("chart"):
        body += chart_path(m["chart"])

    if m.get("expectations"):
        rows = "".join(
            f'<tr><td>{esc(e["metric"])}</td>'
            f'<td class="num">{esc(e.get("consensus", "—"))}</td>'
            f'<td class="num">{esc(e.get("prior", "—"))}</td></tr>'
            for e in m["expectations"]
        )
        body += ('<div class="scroll-x"><table class="grid"><thead><tr>'
                 '<th>Metric</th><th class="num">Consensus</th>'
                 f'<th class="num">Prior</th></tr></thead><tbody>{rows}'
                 '</tbody></table></div>')

    if m.get("surprises"):
        body += f'<div class="scroll-x">{chart_surprise(m["surprises"])}</div>'

    if kind == "ratio" and m.get("ratio_value") is not None:
        body += chart_gap(m["ratio_value"], m.get("versus_value", 0.0))

    if m.get("components"):
        body += ('<div class="figs">' + "".join(
            f'<div class="fig"><div class="l">{esc(c["label"])}</div>'
            f'<div class="v">{esc(c["value"])}</div>'
            f'<div class="c {esc(c.get("tone", ""))}">{esc(c.get("change", ""))}</div>'
            f'</div>' for c in m["components"]
        ) + "</div>")

    if m.get("figures"):
        body += ('<div class="figs">' + "".join(
            f'<div class="fig"><div class="l">{esc(f["label"])}</div>'
            f'<div class="v">{esc(f["value"])}</div></div>'
            for f in m["figures"]
        ) + "</div>")

    if m.get("spark") and len(m["spark"]) >= 8:
        body += f'<div style="margin-top:14px">{sparkline(m["spark"])}</div>'

    if m.get("watch"):
        body += ('<ul class="why" style="margin-top:14px">' + "".join(
            f"<li>{esc(w)}</li>" for w in m["watch"]
        ) + "</ul>")

    caveat = ""
    if m.get("caveat"):
        caveat = f'<p class="caveat"><b>Caveat.</b> {esc(m["caveat"])}</p>'

    srcs = ""
    if m.get("sources"):
        srcs = ('<div class="srcs">' + "".join(
            f'<a href="{esc(s["url"])}" target="_blank" rel="noopener">'
            f'{esc(s["label"])} &nearr;</a>' for s in m["sources"]
        ) + "</div>")

    return (f'<article class="mod {cls}">{head}{why}{detail}{body}'
            f'{caveat}{srcs}</article>')


# ──────────────────────────────────────────────────────────────────────
#  Page sections
# ──────────────────────────────────────────────────────────────────────

def render_tape(ticks: list[dict]) -> str:
    if not ticks:
        return ""
    cells = "".join(
        f'<div class="tick {esc(t.get("tone", "neutral"))}">'
        f'<span class="k">{esc(t["label"])}</span>'
        f'<span class="v">{esc(t["value"])}</span>'
        f'<span class="s">{esc(t.get("sub", ""))}</span></div>'
        for t in ticks
    )
    return f'<div class="tape">{cells}</div>'


def render_regions(regions: list[dict]) -> str:
    if not regions:
        return ""
    cards = []
    for r in regions:
        items = "".join(f"<li>{esc(i)}</li>" for i in r.get("items", []))
        read = ""
        if r.get("market_read"):
            read = (f'<div class="read"><b>Market read</b>'
                    f'{esc(r["market_read"])}</div>')
        cards.append(
            f'<div class="region">'
            f'<div class="region-head">'
            f'<span class="dot {esc(r.get("status", "calm"))}"></span>'
            f'<h3>{esc(r["name"])}</h3></div>'
            f'<p class="head-line">{esc(r.get("headline", ""))}</p>'
            f'<ul>{items}</ul>{read}</div>'
        )
    return f'<div class="regions">{"".join(cards)}</div>'


def render_speak(entries: list[dict]) -> str:
    if not entries:
        return ""
    out = []
    for e in entries:
        tone = esc(e.get("tone", ""))
        impact = ""
        if e.get("impact"):
            impact = f'<div class="impact">{esc(e["impact"])}</div>'
        out.append(
            f'<div class="quote {tone}"><div class="who">'
            f'<span class="name">{esc(e["who"])}</span>'
            f'<span class="role">{esc(e.get("role", ""))}</span>'
            f'<span class="when">{esc(e.get("when", ""))}</span></div>'
            f'<blockquote>{esc(e.get("quote", ""))}</blockquote>{impact}</div>'
        )
    return f'<div class="speak">{"".join(out)}</div>'


def render_calendar(events: list[dict], today: date) -> str:
    if not events:
        return ""
    rows = []
    for e in events:
        d = datetime.strptime(e["date"], "%Y-%m-%d").date()
        days = (d - today).days
        rel = ("today" if days == 0 else "tomorrow" if days == 1
               else f"{days}d" if days > 0 else "past")
        cls = "high" if e.get("weight") == "high" else ""
        cons = (f'<small>{esc(e["consensus"])}</small>'
                if e.get("consensus") else "")
        rows.append(
            f'<div class="cal-row {cls}">'
            f'<span class="d">{d:%a %d %b}<br>{esc(e.get("time", ""))}</span>'
            f'<span class="e">{esc(e["event"])}{cons}</span>'
            f'<span class="d">{esc(rel)} &middot; {esc(e.get("agency", ""))}</span>'
            f'</div>'
        )
    return f'<div class="cal">{"".join(rows)}</div>'


def section(label: str, content: str) -> str:
    if not content:
        return ""
    return (f'<div class="tape-head"><span class="section-label">{esc(label)}'
            f'</span><span class="hr"></span></div>{content}')


# ──────────────────────────────────────────────────────────────────────
#  Page
# ──────────────────────────────────────────────────────────────────────

def render(snap: dict) -> str:
    as_of = datetime.strptime(snap["as_of"], "%Y-%m-%d").date()
    gen = snap.get("generated_at", "")
    thesis = snap.get("thesis", {})
    modules = snap.get("modules", [])
    prov = snap.get("provenance", {})

    scored = [m for m in modules if m.get("score", 0) > 0]
    floor = min((m["score"] for m in scored), default=0)

    kicker = ""
    if thesis.get("positioning_note"):
        kicker = f'<p class="kicker">{esc(thesis["positioning_note"])}</p>'

    thesis_html = ""
    if thesis:
        thesis_html = f"""
<section class="thesis">
  <p class="lede">{esc(thesis.get('headline', ''))}</p>
  <p class="body">{esc(thesis.get('body', ''))}</p>
  {kicker}
</section>"""

    mods_html = "".join(render_module(m) for m in modules)

    conflicts = ""
    if prov.get("conflicts"):
        conflicts = ("<ul>" + "".join(f"<li>{esc(c)}</li>"
                                      for c in prov["conflicts"]) + "</ul>")

    blocked = ""
    if snap.get("collection_mode") == "research":
        hosts = ", ".join(f"<code>{esc(h)}</code>"
                          for h in prov.get("primary_sources_blocked", []))
        blocked = (f'<p style="margin-top:10px">{esc(snap.get("collection_note", ""))}'
                   f'</p><p style="margin-top:8px">Blocked hosts: {hosts}</p>')

    return f"""<title>Rates Desk Morning Brief</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@400;500&family=IBM+Plex+Sans:wght@400;500;600&family=Newsreader:opsz,wght@6..72,400;6..72,500&display=swap">
<style>{CSS}</style>

<div class="wrap">
  <header class="masthead">
    <h1>Rates Desk Morning Brief</h1>
    <div class="stamp">
      <b>{as_of:%A %d %B %Y}</b><br>
      {len(modules)} modules cleared &middot; floor {floor:.0f}/100<br>
      built {esc(gen[:16].replace('T', ' '))}
    </div>
  </header>

  {thesis_html}

  {section('The tape', render_tape(snap.get('tape', [])))}

  {section('Ranked by what moved', f'<div class="modules">{mods_html}</div>')}

  {section('By region', render_regions(snap.get('regions', [])))}

  {section('On the record', render_speak(snap.get('speak', [])))}

  {section('Ahead', render_calendar(snap.get('calendar', []), as_of))}

  <div class="colophon">
    <h4>How this page was built</h4>
    <p style="margin:0">Modules are scored 0&ndash;100 on move size in trailing
    standard deviations, how extreme the level is against its own history,
    moving-average crosses, surprise against consensus, proximity to a scheduled
    catalyst, and divergence between a ratio and the series it normally tracks.
    Anything below the floor is dropped, no asset class takes more than three
    slots, and modules that led recent runs are decayed &mdash; so the page
    changes shape day to day rather than printing the same grid.</p>
    {blocked}
    <p style="margin-top:10px">{esc(prov.get('note', ''))}</p>
    {conflicts}
    <p style="margin-top:10px">Regenerate with
    <code>python -m dashboard build</code>.</p>
  </div>
</div>"""


def write(snap: dict, path: str | Path) -> Path:
    out = Path(path)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(render(snap), encoding="utf-8")
    return out


def load(path: str | Path) -> dict:
    return json.loads(Path(path).read_text(encoding="utf-8"))
