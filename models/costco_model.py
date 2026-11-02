"""Costco DCF on the user's assumptions (Nov 2026). $bn unless per share. Fiscal years end late August.

Inputs from Bloomberg (FY26): revenue 303.154, net income 9.226, EBITDA 14.359, CFO 15.817,
capex 6.435, FCF 9.382, cash 21.301, debt 11.110, market cap 448.571, EPS 20.76.
"""
import json, sys

A = dict(
    rev0=303.154, growth=0.075,          # Q1: consensus revenue growth FY27-31
    net_margin0=0.030, net_margin=0.033,  # Q2 revised: 3.0% today rising to 3.3% by FY31 (fee increase ~2030)
    roic=0.25,                            # terminal reinvestment = g / ROIC (incremental ROIC ~29% FY22-26)
    capex_pct=0.025,                      # Q3: faster build-out
    da_pct=0.0085,                        # FY26 D&A ~ $2.6bn (EBITDA less operating income)
    wc_pct_of_rev_growth=0.12,            # members pay before Costco pays suppliers (FY26 implied ~14%)
    shares=0.4444, special=15.0, special_year=2028, div0=5.20,   # Q4: flat shares, one $15 special
    k=0.075, g=0.035,                     # Q5, Q6
    net_cash=10.191, price=1009.4,
)


def run(a=A):
    rows, rev = [], a["rev0"]
    for t, y in enumerate(range(2027, 2032), 1):
        prev, rev = rev, rev * (1 + a["growth"])
        ni = rev * (a["net_margin0"] + (a["net_margin"] - a["net_margin0"]) * t / 5)
        da = rev * a["da_pct"]
        wc = (rev - prev) * a["wc_pct_of_rev_growth"]
        capex = rev * a["capex_pct"]
        fcf = ni + da + wc - capex
        rows.append(dict(y=y, t=t, rev=rev, ni=ni, da=da, wc=wc, capex=capex, fcf=fcf, eps=ni / a["shares"]))
    return rows


def value(a=A, rows=None, k=None):
    rows = rows or run(a); k = k or a["k"]; g = a["g"]
    pv = sum(r["fcf"] / (1 + k) ** r["t"] for r in rows)
    tv = rows[-1]["ni"] * (1 + g) * (1 - g / a["roic"]) / (k - g)
    eq = pv + tv / (1 + k) ** 5 + a["net_cash"]
    return dict(pv=pv, tv=tv, pvtv=tv / (1 + k) ** 5, eq=eq, ps=eq / a["shares"], tv31_ps=(tv + a["net_cash"]) / a["shares"])


def irr(cf):
    lo, hi = -0.9, 2.0
    for _ in range(200):
        m = (lo + hi) / 2
        lo, hi = (m, hi) if sum(c / (1 + m) ** i for i, c in enumerate(cf)) > 0 else (lo, m)
    return m


def returns(a=A):
    rows, v = run(a), value(a)
    divs = [a["div0"] * r["eps"] / (9.226 / a["shares"]) + (a["special"] if r["y"] == a["special_year"] else 0) for r in rows]
    eps32 = rows[-1]["eps"] * (1 + a["growth"])
    out = {"dcf_converge": irr([-a["price"]] + divs[:-1] + [divs[-1] + v["tv31_ps"]])}
    for pe in (44.3, 40, 35, 30, 25):
        out[f"pe_{pe}"] = irr([-a["price"]] + divs[:-1] + [divs[-1] + pe * eps32])
    lo, hi = a["g"] + 0.001, 0.3
    for _ in range(100):
        m = (lo + hi) / 2
        lo, hi = (m, hi) if value(a, rows, m)["ps"] > a["price"] else (lo, m)
    out["hold_forever"] = m
    return rows, v, divs, eps32, out


if __name__ == "__main__":
    rows, v, divs, eps32, out = returns()
    for r in rows:
        print(r["y"], *(f"{k}={r[k]:.2f}" for k in ("rev", "ni", "da", "wc", "capex", "fcf", "eps")))
    print("divs/share", [round(d, 2) for d in divs], "EPS FY32", round(eps32, 2))
    print({k: round(x, 2) for k, x in v.items()})
    print({k: round(x * 100, 1) for k, x in out.items()})
