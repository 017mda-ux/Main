"""Analytics checks on synthetic series.

Live sources are unreachable from CI, so the maths is exercised against
constructed data where the right answer is known by hand.
"""

import math
import sys
from datetime import date, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from dashboard.analytics.movingavg import ma_state
from dashboard.analytics.ratios import build_ratio, divergence_score
from dashboard.analytics.salience import rank, score_series, Signal
from dashboard.analytics.series import TimeSeries, correlation
from dashboard.config import Ratio, SERIES_BY_KEY

START = date(2022, 1, 3)
FAILS: list[str] = []


def check(name: str, cond: bool, detail: str = "") -> None:
    print(f"  {'ok  ' if cond else 'FAIL'} {name}" + (f"  — {detail}" if detail else ""))
    if not cond:
        FAILS.append(name)


def mkseries(values, key="TEST", unit="pct"):
    pairs = [(START + timedelta(days=i), v) for i, v in enumerate(values)]
    return TimeSeries.from_pairs(key, pairs, unit=unit, label=key)


print("series statistics")
flat = mkseries([2.0] * 300)
check("flat series has no volatility", flat.vol() is None)
check("flat series change is zero", flat.change(1) == 0.0)

ramp = mkseries([float(i) for i in range(300)])
check("ramp last value", ramp.last == 299.0)
check("ramp 1d change", ramp.change(1) == 1.0)
check("ramp streak is the full run", ramp.streak() == 299, f"got {ramp.streak()}")
check("ramp percentile at the top", ramp.percentile(300) > 99)
check("ramp is highest in sample", ramp.extreme_since("high") is None)

# A quiet series with one large jump: the jump must read as a big sigma move.
quiet = [10.0 + (0.01 if i % 2 else -0.01) for i in range(300)]
quiet.append(11.0)
jump = mkseries(quiet)
z = jump.zscore(1, 252)
check("one-day jump scores a large z", z is not None and abs(z) > 10, f"z={z:.1f}")

print("\nmoving averages")
# Rising then falling: forces a golden cross and then a death cross.
up = [100.0 + i * 0.5 for i in range(260)]
down = [up[-1] - i * 1.6 for i in range(1, 90)]
turn = mkseries(up + down, key="TURN")
mc = ma_state(turn)
check("cross detected", mc is not None)
if mc:
    check("downtrend gives a death cross or fast below slow",
          mc.state in ("death", "below"), f"state={mc.state}")
    check("fast is below slow after the turn", mc.gap_pct < 0, f"gap={mc.gap_pct:.2f}%")
    check("headline is human readable", "TURN" in mc.headline, mc.headline)

pure_up = mkseries([100.0 + i * 0.4 for i in range(300)], key="UP")
mu = ma_state(pure_up)
check("sustained uptrend has fast above slow", mu is not None and mu.gap_pct > 0)
check("no cross in a monotonic series", mu is not None and mu.crossed_on is None)

short = mkseries([1.0] * 50)
check("too-short series returns no cross", ma_state(short) is None)

print("\nratios and divergence")
copper = mkseries([4.0 + i * 0.002 for i in range(400)], key="COPPER", unit="usd")
gold = mkseries([2000.0 + i * 2.0 for i in range(400)], key="GOLD", unit="usd")
store = {"COPPER": copper, "GOLD": gold}
spec = Ratio("CG", "Copper / gold", "COPPER", "GOLD", scale=1000.0, versus="DGS10")
cg = build_ratio(spec, store)
check("ratio builds", cg is not None and len(cg) == 400)
if cg:
    expected = (copper.values[-1] / gold.values[-1]) * 1000.0
    check("ratio value is numerator/denominator × scale",
          math.isclose(cg.last, expected, rel_tol=1e-9), f"{cg.last:.4f}")

# A benchmark that tracks, then parts company: divergence must rise.
tracking = mkseries([cg.values[i] for i in range(400)], key="DGS10")
score_track, div_track = divergence_score(cg, tracking)
parting = mkseries([cg.values[i] + (0 if i < 300 else (i - 300) * 0.05)
                    for i in range(400)], key="DGS10")
score_part, div_part = divergence_score(cg, parting)
check("perfect tracking scores near zero", score_track < 5, f"score={score_track:.1f}")
check("a parting benchmark scores higher", score_part > score_track,
      f"{score_part:.1f} > {score_track:.1f}")

check("correlation of a series with itself is 1",
      math.isclose(correlation(cg.values, cg.values), 1.0, rel_tol=1e-9))
check("correlation with the negation is -1",
      math.isclose(correlation(cg.values, [-v for v in cg.values]), -1.0, rel_tol=1e-9))

print("\nsalience and ranking")
spec10 = SERIES_BY_KEY["DGS10"]
boring = score_series(spec10, mkseries([4.0] * 300, key="DGS10"))
exciting = score_series(spec10, jump)
check("a flat series scores low", boring.score < 25, f"{boring.score:.1f}")
check("a jumping series scores high", exciting.score > 60, f"{exciting.score:.1f}")
check("a high scorer explains itself", len(exciting.reasons) > 0,
      exciting.top_reason)

sigs = [
    Signal("A", "A", "curve", 90.0), Signal("B", "B", "curve", 85.0),
    Signal("C", "C", "curve", 80.0), Signal("D", "D", "curve", 75.0),
    Signal("E", "E", "fx", 70.0),    Signal("F", "F", "fx", 10.0),
]
ranked = rank([Signal(s.key, s.label, s.bucket, s.score) for s in sigs])
check("below-floor modules are dropped", all(s.key != "F" for s in ranked))
check("bucket cap holds", sum(1 for s in ranked if s.bucket == "curve") <= 3,
      f"curve slots={sum(1 for s in ranked if s.bucket == 'curve')}")
check("other buckets still get in", any(s.bucket == "fx" for s in ranked))
check("ordered by score", [s.score for s in ranked] ==
      sorted([s.score for s in ranked], reverse=True))

# Yesterday's leader must be decayed so the page rotates.
fresh = rank([Signal("A", "A", "curve", 90.0), Signal("Z", "Z", "fx", 80.0)])
stale = rank([Signal("A", "A", "curve", 90.0), Signal("Z", "Z", "fx", 80.0)],
             previous_leaders=[["A"]])
check("a repeat leader is decayed", stale[0].key == "Z" and fresh[0].key == "A",
      f"fresh={fresh[0].key} after-repeat={stale[0].key}")

print("\nrendering")
from dashboard import render as renderer
snap = renderer.load(Path(__file__).parents[1] / "dashboard/data/snapshot-2026-09-10.json")
html = renderer.render(snap)
check("page renders", len(html) > 20_000, f"{len(html):,} bytes")
check("every module reaches the page",
      all(m["label"][:18] in html for m in snap["modules"]))
check("light palette is declared on bare :root",
      "--ink:" in html.split("@media")[0])
check("dark tokens exist under both scopes",
      html.count('--ground:') >= 3)
check("no unescaped snapshot text breaks markup", "<script" not in html)

print()
if FAILS:
    print(f"{len(FAILS)} check(s) failed: {', '.join(FAILS)}")
    sys.exit(1)
print("all checks passed")
