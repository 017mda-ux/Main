#!/usr/bin/env python3
"""
Set the Custom scenario in models/Alphabet_Bottom_Up_Model.xlsx from plain answers, recalc, print results.

    python scripts/alphabet_custom.py search_g1=0 search_g2=0.02 cloud_m=0.40 price=290
    python scripts/alphabet_custom.py --show          # print current Custom drivers and results
    python scripts/alphabet_custom.py --reset         # Custom = Base again

Percentages are fractions (0.05 = 5%). Unknown keys are rejected.
"""

import json
import subprocess
import sys
from pathlib import Path

from openpyxl import load_workbook

ROOT = Path(__file__).resolve().parent.parent
BOOK = ROOT / "models" / "Alphabet_Bottom_Up_Model.xlsx"
RECALC = Path("/root/.claude/skills/synced/af3caaac-b849-4225-a8db-183a8a20dc9e_eb07bd91-0acb-401e-b5c5-b6fcec84f31f/xlsx/scripts/recalc.py")

# answer key -> Scenarios row label (Custom column G)
DRIVERS = {
    "search_g1": "Search growth yrs 1-3", "search_g2": "Search growth yrs 4-5", "search_g3": "Search growth yrs 6-10",
    "search_m": "Search terminal margin",
    "yt_g1": "YouTube ads growth yrs 1-3", "yt_g2": "YouTube ads growth yrs 4-10", "yt_m": "YouTube ads terminal margin",
    "subs_g1": "Subs/platforms/devices growth yrs 1-3", "subs_g2": "Subs/platforms/devices growth yrs 4-10",
    "subs_m": "Subs/platforms/devices terminal margin",
    "net_g": "Network growth (all years)", "net_m": "Network terminal margin",
    "cloud_g1": "Cloud growth yr 1", "cloud_g2": "Cloud growth yr 2", "cloud_g3": "Cloud growth yr 3",
    "cloud_g4": "Cloud growth yrs 4-5", "cloud_g5": "Cloud growth yrs 6-10", "cloud_m": "Cloud terminal margin",
    "other_bets": "Other Bets operating income ($bn/yr)",
    "capex27": "Capex 2027 ($bn)", "capex28": "Capex 2028 ($bn)", "capex29": "Capex 2029 ($bn)",
    "capex_pct": "Capex % of revenue from 2030", "capex_term": "Terminal capex % of revenue (after forecast)", "dilution": "Share count change / yr",
    "waymo": "Waymo / Other Bets value ($bn)", "waymo10": "Waymo / Other Bets value in year 10 ($bn)", "exit": "Exit P/FCF multiple (year 10)",
    "mx_search": "SOTP multiple: Search (x FY26E OI)", "mx_yt": "SOTP multiple: YouTube + Subs",
    "mx_cloud": "SOTP multiple: Cloud",
}
# keys now derived on the Drivers sheet (Custom column links there) -> set the drivers instead
LINKED = {"search_g1", "search_g2", "search_g3", "yt_g1", "yt_g2", "subs_g1", "subs_g2", "cloud_g1", "waymo", "waymo10"}
# answer key -> Drivers row label (column C)
DRIVER_SHEET = {
    "clicks1": "Paid clicks growth 2027-29", "cpc1": "CPC growth 2027-29", "clicks2": "Paid clicks growth 2030-31",
    "cpc2": "CPC growth 2030-31", "clicks3": "Paid clicks growth 2032-36", "cpc3": "CPC growth 2032-36",
    "watch1": "Watch-time growth 2027-29", "rph1": "Revenue per hour growth 2027-29",
    "watch2": "Watch-time growth 2030-36", "rph2": "Revenue per hour growth 2030-36",
    "subs1": "Paid subscriptions growth 2027-29", "arpu1": "Revenue per subscription growth 2027-29",
    "subs2": "Paid subscriptions growth 2030-36", "arpu2": "Revenue per subscription growth 2030-36",
    "backlog": "Cloud backlog ($bn)", "conv": "Share of backlog recognised over next 24 months",
    "newbiz": "New business recognised in 2027 (% of FY26E Cloud revenue)",
    "rides31": "Weekly paid rides in 2031 (millions)", "fare": "Average fare ($)", "wmult31": "EV / revenue multiple in 2031",
    "rides36": "Weekly paid rides in 2036 (millions)", "fare36": "Average fare in 2036 ($)", "wmult36": "EV / revenue multiple in 2036",
    "own": "Alphabet ownership of Waymo",
}
# answer key -> Inputs row label (column C)
INPUTS = {"price": "Share price ($)", "shares": "Diluted shares (bn)", "netcash": "Net cash ($bn)",
          "stakes": "Equity stakes ($bn)", "disc": "Discount rate", "tg": "Terminal growth",
          "nyrs": "DCF explicit forecast years"}


def rows_by_label(ws, col="B"):
    return {ws[f"{col}{r}"].value: r for r in range(1, ws.max_row + 1) if ws[f"{col}{r}"].value}


def read_results():
    wb = load_workbook(BOOK, data_only=True)
    sm, sc = wb["Summary"], wb["Scenarios"]
    lab = rows_by_label(sm)
    names = [sm[f"{c}5"].value for c in "CDEFGH"]
    out = {}
    for key in ("DCF value per share ($)", "Upside vs price", "5-year IRR from today's price",
                "Year-5 exit value per share ($)", "Exit value / 2032 EPS (x)", "SOTP value per share ($)", "EBIT 2031",
                "Free cash flow 2027", "Free cash flow 2031", "FCF per share 2031 ($)",
                "Cumulative FCF 2027-31", "For reference: 10-year IRR (2036 exit)"):
        out[key] = {n: sm[f"{c}{lab[key]}"].value for n, c in zip(names, "CDEFGH")}
    drivers = {k: sc[f"G{rows_by_label(sc)[v]}"].value for k, v in DRIVERS.items()}
    dv = wb["Drivers"]
    dl = {dv[f"B{r}"].value: r for r in range(1, dv.max_row + 1) if dv[f"B{r}"].value}
    drivers.update({k: dv[f"C{dl[v]}"].value for k, v in DRIVER_SHEET.items()})
    drivers.update({lab.strip("-> "): dv[f"E{r}"].value for lab, r in dl.items() if str(lab).startswith("->")})
    return out, drivers


def main(argv):
    wb = load_workbook(BOOK)
    sc, inp, dv = wb["Scenarios"], wb["Inputs"], wb["Drivers"]
    srow, irow, drow = rows_by_label(sc), rows_by_label(inp), rows_by_label(dv)
    changed = {}
    if "--reset" in argv:
        for k, label in DRIVERS.items():
            if k in LINKED:
                continue
            r = srow[label]
            sc[f"G{r}"].value = sc[f"E{r}"].value
        changed["reset"] = "Custom = Base"
    for arg in argv:
        if "=" not in arg:
            continue
        k, v = arg.split("=", 1)
        val = float(v)
        if k in LINKED:
            sys.exit(f"{k} is now derived on the Drivers sheet; set its drivers instead ({', '.join(DRIVER_SHEET)})")
        if k in DRIVER_SHEET:
            dv[f"C{drow[DRIVER_SHEET[k]]}"].value = val
        elif k in DRIVERS:
            sc[f"G{srow[DRIVERS[k]]}"].value = val
        elif k in INPUTS:
            inp[f"C{irow[INPUTS[k]]}"].value = val
        else:
            sys.exit(f"Unknown key {k}. Valid: {', '.join(list(DRIVER_SHEET) + [d for d in DRIVERS if d not in LINKED] + list(INPUTS))}")
        changed[k] = val
    if changed:
        wb.save(BOOK)
        res = subprocess.run([sys.executable, str(RECALC), str(BOOK), "90"], capture_output=True, text=True)
        status = json.loads(res.stdout or "{}")
        if status.get("status") != "success":
            sys.exit(f"Recalc problem: {res.stdout or res.stderr}")
    out, drivers = read_results()
    print(json.dumps({"changed": changed, "custom_drivers": drivers, "results": out}, indent=1, default=str))


if __name__ == "__main__":
    main(sys.argv[1:])
