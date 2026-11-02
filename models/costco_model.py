"""Costco three-stage FCFE model, built the CFA way (forecast from sales).

    python models/costco_model.py                      # your case
    python models/costco_model.py k=0.07 s2_years=20   # change any input

Stage 1 (FY27-31): your revenue growth and net margin path.
Stage 2 (FY32 onward, s2_years long): growth fades linearly to terminal g; margin drifts to a long-run level.
FCFE = net income - (incremental fixed capital rate - working-capital release rate) x sales increase.
  Maintenance capex ~ depreciation is already inside net income; only growth capex is subtracted.
  Costco history (FY26): growth capex 13.7% of the sales increase; working capital released 14.3%.
Terminal: net income x (1 + g) x (1 - g / ROIC) / (k - g), so reinvestment matches growth.
Inputs from Bloomberg (FY26, $bn): revenue 303.154, net income 9.226, EPS 20.76, market cap 448.571,
cash 21.301, debt 11.110. Fiscal years end late August.
"""
import json
import sys

A = dict(
    price=1009.4, shares=0.4444, net_cash=10.191, rev0=303.154,
    g1=0.075,                 # stage-1 revenue growth (consensus)
    m0=0.030, m1=0.033,       # net margin today -> FY31 (fee increase ~2030)
    s2_years=15, s2_start=None, m2=0.033,   # stage 2: fade length, starting growth (default g1), long-run margin
    fc_rate=0.137, wc_rate=0.143,           # growth capex and working-capital release, % of sales increase
    g=0.035, roic=0.25, k=0.075,
    exit_pe=38.0, div0=5.20, special=15.0, special_year=2028,
)


def run(a=A):
    rows, rev = [], a["rev0"]
    n = 5 + int(a["s2_years"])
    s2 = a["g1"] if a["s2_start"] is None else a["s2_start"]
    for t in range(1, n + 1):
        if t <= 5:
            g, m = a["g1"], a["m0"] + (a["m1"] - a["m0"]) * t / 5
        else:
            f = (t - 5) / a["s2_years"]
            g, m = s2 + (a["g"] - s2) * f, a["m1"] + (a["m2"] - a["m1"]) * f
        prev, rev = rev, rev * (1 + g)
        ni = rev * m
        reinv = (a["fc_rate"] - a["wc_rate"]) * (rev - prev)
        rows.append(dict(y=2026 + t, t=t, g=g, rev=rev, margin=m, ni=ni, reinv=reinv, fcfe=ni - reinv, eps=ni / a["shares"]))
    return rows


def value(a=A, rows=None, k=None, g=None):
    rows = rows or run(a)
    k = a["k"] if k is None else k
    g = a["g"] if g is None else g
    n = len(rows)
    pv = sum(r["fcfe"] / (1 + k) ** r["t"] for r in rows)
    tv = rows[-1]["ni"] * (1 + g) * (1 - g / a["roic"]) / (k - g)
    eq = pv + tv / (1 + k) ** n + a["net_cash"]
    # value at end of FY31 (for the 5-year return if price meets value)
    pv31 = sum(r["fcfe"] / (1 + k) ** (r["t"] - 5) for r in rows if r["t"] > 5)
    v31 = (pv31 + tv / (1 + k) ** (n - 5) + a["net_cash"]) / a["shares"]
    return dict(pv=pv, tv=tv, pvtv=tv / (1 + k) ** n, eq=eq, ps=eq / a["shares"], tv_share=tv / (1 + k) ** n / (eq - a["net_cash"]), v31=v31)


def irr(cf):
    lo, hi = -0.9, 2.0
    for _ in range(200):
        m = (lo + hi) / 2
        lo, hi = (m, hi) if sum(c / (1 + m) ** i for i, c in enumerate(cf)) > 0 else (lo, m)
    return m


def analyse(a=A):
    rows, v = run(a), value(a)
    eps26 = 20.76
    divs = [a["div0"] * r["eps"] / eps26 + (a["special"] if r["y"] == a["special_year"] else 0) for r in rows[:5]]
    eps32 = rows[5]["eps"]
    out = dict(value_per_share=v["ps"], upside=v["ps"] / a["price"] - 1, terminal_share=v["tv_share"],
               value_fy31=v["v31"], justified_pe_fy31=v["v31"] / eps32, eps_fy31=rows[4]["eps"], eps_fy32=eps32)
    out["ret_5y_exit_pe"] = irr([-a["price"]] + divs[:-1] + [divs[-1] + a["exit_pe"] * eps32])
    out["ret_5y_to_value"] = irr([-a["price"]] + divs[:-1] + [divs[-1] + v["v31"]])
    lo, hi = a["g"] + 0.001, 0.3
    for _ in range(100):
        m = (lo + hi) / 2
        lo, hi = (m, hi) if value(a, rows, k=m)["ps"] > a["price"] else (lo, m)
    out["implied_return"] = m
    out["grid"] = {f"k={kk*100:.1f}%": {f"g={gg*100:.1f}%": round(value(a, rows, kk, gg)["ps"]) for gg in (0.025, 0.03, 0.035, 0.04, 0.045)}
                   for kk in (0.065, 0.07, 0.075, 0.08, 0.085)}
    return rows, v, divs, out


if __name__ == "__main__":
    a = dict(A)
    for arg in sys.argv[1:]:
        key, val = arg.split("=", 1)
        if key not in a:
            sys.exit(f"Unknown input {key}. Valid: {', '.join(a)}")
        a[key] = None if val == "None" else float(val)
    rows, v, divs, out = analyse(a)
    for r in rows[:6] + rows[-1:]:
        print(r["y"], f"g={r['g']*100:.1f}% rev={r['rev']:.0f} margin={r['margin']*100:.2f}% ni={r['ni']:.2f} reinv={r['reinv']:.2f} fcfe={r['fcfe']:.2f} eps={r['eps']:.2f}")
    print(json.dumps({k: (round(x, 4) if isinstance(x, float) else x) for k, x in out.items()}, indent=1))
