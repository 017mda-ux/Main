"""Costco bottom-up valuation (Nov 2026): warehouses x productivity, members x fees, margins -> FCFE -> 3-stage DCF.

    python models/costco_bottomup.py            # your answers
    python models/costco_bottomup.py k=0.07     # change any input

FY26 base (company 10-K / Q4 release): 939 warehouses, net sales $297.2bn, membership fees $5.907bn,
84.1m paid members, net income $9.2bn, EPS $20.76 (Bloomberg adjusted). Operating income ~$11.8bn is an
estimate (net income grossed up for ~25% tax less ~$0.4bn interest income).
"""
import json
import sys

A = dict(
    price=1009.4, shares=0.4444, net_cash=10.191,
    wh0=939, net_new=30,                 # Q1: net new warehouses per year
    comps=0.06,                          # Q2: same-store sales growth (ex gas/FX)
    ramp=(0.65, 0.85),                   # new warehouse productivity in years 1 and 2 vs mature
    fees0=5.907, members_g=0.035, mix_g=0.01, fee_hike=0.08, hike_year=2030,   # Q3
    mm0=0.020, mm1=0.022,                # Q4: merchandise margin (sales - COGS - SG&A) FY26 -> FY31
    interest=0.4, tax=0.25,
    s2_years=15, g=0.04, k=0.075, roic=0.25,   # Q5, Q6
    fc_rate=0.137, wc_rate=0.143,        # growth capex / working capital released, % of sales increase
    exit_pe=38.0, div0=5.20, special=15.0,
)


def run(a=A):
    sales0 = 297.2
    spw = sales0 / a["wh0"]             # mature sales per warehouse ($bn), FY26
    cohorts = []                         # opening years of new warehouses
    rows, prev_rev = [], sales0 + a["fees0"]
    fees_base = a["fees0"]
    for t, y in enumerate(range(2027, 2032), 1):
        spw *= 1 + a["comps"]
        cohorts.append(y)
        mature = a["wh0"] + a["net_new"] * sum(1 for c in cohorts if y - c >= 2)
        new = {c: a["net_new"] for c in cohorts if y - c < 2}
        sales = spw * mature + sum(n * spw * a["ramp"][y - c] for c, n in new.items())
        fees_base *= (1 + a["members_g"]) * (1 + a["mix_g"])
        hike = 1 + (a["fee_hike"] / 2 if y == a["hike_year"] else a["fee_hike"] if y > a["hike_year"] else 0)
        fees = fees_base * hike
        mm = a["mm0"] + (a["mm1"] - a["mm0"]) * t / 5
        ebit = sales * mm + fees
        ni = (ebit + a["interest"]) * (1 - a["tax"])
        rev = sales + fees
        fcfe = ni - (a["fc_rate"] - a["wc_rate"]) * (rev - prev_rev)
        rows.append(dict(y=y, t=t, warehouses=a["wh0"] + a["net_new"] * t, spw=spw * 1000, sales=sales, fees=fees,
                         rev=rev, growth=rev / prev_rev - 1, mm=mm, ebit=ebit, ni=ni, fcfe=fcfe, eps=ni / a["shares"]))
        prev_rev = rev
    # stage 2: revenue growth fades linearly to g; net margin held at FY31 level
    g0, nm, rev = rows[-1]["growth"], rows[-1]["ni"] / rows[-1]["rev"], rows[-1]["rev"]
    for i in range(1, int(a["s2_years"]) + 1):
        gr = g0 + (a["g"] - g0) * i / a["s2_years"]
        prev, rev = rev, rev * (1 + gr)
        ni = rev * nm
        rows.append(dict(y=2031 + i, t=5 + i, rev=rev, growth=gr, ni=ni,
                         fcfe=ni - (a["fc_rate"] - a["wc_rate"]) * (rev - prev), eps=ni / a["shares"]))
    return rows


def value(a=A, rows=None, k=None):
    rows = rows or run(a)
    k = a["k"] if k is None else k
    n, g = len(rows), a["g"]
    pv = sum(r["fcfe"] / (1 + k) ** r["t"] for r in rows)
    tv = rows[-1]["ni"] * (1 + g) * (1 - g / a["roic"]) / (k - g)
    eq = pv + tv / (1 + k) ** n + a["net_cash"]
    pv31 = sum(r["fcfe"] / (1 + k) ** (r["t"] - 5) for r in rows[5:])
    v31 = (pv31 + tv / (1 + k) ** (n - 5) + a["net_cash"]) / a["shares"]
    return dict(ps=eq / a["shares"], v31=v31, pv_stage1=sum(r["fcfe"] / (1 + k) ** r["t"] for r in rows[:5]),
                pv_stage2=sum(r["fcfe"] / (1 + k) ** r["t"] for r in rows[5:]), pv_tv=tv / (1 + k) ** n)


def irr(cf):
    lo, hi = -0.9, 2.0
    for _ in range(200):
        m = (lo + hi) / 2
        lo, hi = (m, hi) if sum(c / (1 + m) ** i for i, c in enumerate(cf)) > 0 else (lo, m)
    return m


def analyse(a=A):
    rows, v = run(a), value(a)
    divs = [a["div0"] * r["eps"] / 20.76 + (a["special"] if r["y"] == 2028 else 0) for r in rows[:5]]
    eps32 = rows[5]["eps"]
    lo, hi = a["g"] + 0.001, 0.3
    for _ in range(100):
        m = (lo + hi) / 2
        lo, hi = (m, hi) if value(a, rows, m)["ps"] > a["price"] else (lo, m)
    out = dict(value_per_share=v["ps"], upside=v["ps"] / a["price"] - 1, implied_return=m, value_fy31=v["v31"],
               justified_pe_fy31=v["v31"] / eps32, eps_fy31=rows[4]["eps"], eps_fy32=eps32,
               pv_split={k: round(v[k], 1) for k in ("pv_stage1", "pv_stage2", "pv_tv")})
    for pe in (a["exit_pe"], 30.0, 35.0, 44.0):
        out[f"ret5y_exit_{pe:g}x"] = irr([-a["price"]] + divs[:-1] + [divs[-1] + pe * eps32])
    out["ret5y_to_value"] = irr([-a["price"]] + divs[:-1] + [divs[-1] + v["v31"]])
    return rows, out


if __name__ == "__main__":
    a = dict(A)
    for arg in sys.argv[1:]:
        k, val = arg.split("=", 1)
        if k not in a:
            sys.exit(f"Unknown input {k}")
        a[k] = float(val)
    rows, out = analyse(a)
    for r in rows[:5]:
        print(r["y"], f"wh={r['warehouses']} spw=${r['spw']:.0f}m sales={r['sales']:.1f} fees={r['fees']:.2f} rev={r['rev']:.1f} "
              f"g={r['growth']*100:.1f}% mm={r['mm']*100:.2f}% ebit={r['ebit']:.2f} ni={r['ni']:.2f} fcfe={r['fcfe']:.2f} eps={r['eps']:.2f}")
    print(json.dumps({k: (round(x, 4) if isinstance(x, float) else x) for k, x in out.items()}, indent=1))
