#!/usr/bin/env python3
"""Build models/Alphabet_Bottom_Up_Model.xlsx: segment history, scenario drivers, 10-year model, DCF, IRR, SOTP."""

from pathlib import Path

from openpyxl import Workbook
from openpyxl.comments import Comment
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter as L

OUT = Path(__file__).resolve().parent.parent / "models" / "Alphabet_Bottom_Up_Model.xlsx"

F = "Arial"
BLUE, BLACK, GREEN = "0000FF", "000000", "008000"
YELLOW = PatternFill("solid", fgColor="FFFF00")
HEAD = PatternFill("solid", fgColor="1F3864")
SUB = PatternFill("solid", fgColor="D9E1F2")
THIN = Border(bottom=Side(style="thin", color="999999"))
USD = '$#,##0.0;($#,##0.0);-'
USD0 = '$#,##0;($#,##0);-'
PCT = '0.0%;(0.0%);-'
MULT = '0.0x'

SRC = {
    "Q4_25": "Source: Alphabet Q4 2025 earnings release, https://s206.q4cdn.com/479360582/files/doc_financials/2025/q4/2025q4-alphabet-earnings-release.pdf (via press coverage)",
    "Q1_26": "Source: Alphabet Q1 2026 8-K Ex.99.1, https://www.sec.gov/Archives/edgar/data/0001652044/000165204426000043/googexhibit991q12026.htm",
    "Q2_26": "Source: Alphabet Q2 2026 8-K Ex.99.1, https://www.sec.gov/Archives/edgar/data/0001652044/000165204426000066/googexhibit991q22026.htm",
    "Q3_26": "Source: Alphabet Q3 2026 8-K Ex.99.1 and 10-Q, https://www.sec.gov/Archives/edgar/data/0001652044/000165204426000080/googexhibit991q32026.htm",
}


def font(color=BLACK, bold=False, size=10, italic=False):
    return Font(name=F, color=color, bold=bold, size=size, italic=italic)


def put(ws, ref, value, fmt=None, color=BLACK, bold=False, fill=None, comment=None, italic=False):
    c = ws[ref]
    c.value = value
    c.font = font(color, bold, italic=italic)
    if fmt:
        c.number_format = fmt
    if fill:
        c.fill = fill
    if comment:
        c.comment = Comment(comment, "Model")
    return c


def header(ws, row, labels, start_col=2):
    for i, lab in enumerate(labels):
        c = ws.cell(row=row, column=start_col + i, value=lab)
        c.font = Font(name=F, bold=True, color="FFFFFF", size=10)
        c.fill = HEAD
        c.alignment = Alignment(horizontal="center", wrap_text=True)


def title(ws, text, sub=None):
    ws["B2"].value = text
    ws["B2"].font = Font(name=F, bold=True, size=14, color="1F3864")
    if sub:
        ws["B3"].value = sub
        ws["B3"].font = font(italic=True, size=9)


wb = Workbook()

# ─────────────────────────── Guide ───────────────────────────
g = wb.active
g.title = "Guide"
title(g, "Alphabet bottom-up model: guide", "All $ in billions unless noted. Built Oct 31, 2026 from Q4'25-Q3'26 reported segments.")
rows = [
    ("What this is", "A unit-by-unit model of Alphabet: recent history, scenario drivers, a 10-year projection, DCF, 10-year IRR and sum-of-the-parts."),
    ("Sheets", "History (reported quarters) -> Inputs (base year, balance sheet, market) -> Scenarios (drivers by case) -> Model (10-year projections for every case) -> Summary (outputs side by side)."),
    ("Edit these", "Yellow cells: the Custom scenario column on Scenarios, and key inputs on Inputs (price, shares, net cash, discount rate). Blue text = hardcoded input; black = formula; green = link from another sheet."),
    ("Example edit", "To test 'Search -3% a year for 3 years': on Scenarios, set Custom > Search growth yrs 1-3 to -3.0%. Summary updates the Custom column."),
    ("Scenarios", "Bear: Search flat 5 yrs, margin falls, AI capex earns weak returns. Flat Search/Capex pays: Search flat 5 yrs but Cloud compounds strongly. Base: steady Search, Cloud strong then fading. Bull: Search grows, Cloud very strong, buybacks resume. Custom: starts equal to Base."),
    ("Method", "Segment revenue x growth; segment operating margin glides linearly from FY26E to the scenario's terminal margin over 5 years (margins include each unit's depreciation). EBIT less tax plus D&A less capex = FCF. D&A = average of the last 6 years' capex. DCF at the discount rate with a terminal growth value. IRR (headline, 5-year hold): buy at price, receive FCF/share 2027-31, sell at end-2031 at the year-5 exit P/FCF multiple, plus net cash, stakes and Waymo's 2031 value per share. A 10-year IRR is kept for reference."),
    ("Estimates", "Segment margins below the Services/Cloud level, Q4'26 estimates, net cash, equity stakes, Waymo value and pre-2026 capex are model estimates, marked with comments. Replace them as better data arrives."),
    ("Disclosure", "Alphabet's equity stakes include a holding in Anthropic, the company that makes Claude (the model that built this). It is included in a lump-sum estimate only and not separately valued."),
    ("Not advice", "Illustrative model for research. Not financial advice."),
]
for i, (k, v) in enumerate(rows):
    put(g, f"B{5+i*2}", k, bold=True)
    c = put(g, f"C{5+i*2}", v)
    c.alignment = Alignment(wrap_text=True, vertical="top")
    g.row_dimensions[5 + i * 2].height = 45
g.column_dimensions["B"].width = 16
g.column_dimensions["C"].width = 110

# ─────────────────────────── History ───────────────────────────
h = wb.create_sheet("History")
title(h, "Reported segment history ($bn) and growth", "Blue = reported or estimate (see comments). FY26E = Q1-Q3 actual + Q4 estimate.")
cols = ["Line", "Q4'25", "Q1'26", "Q2'26", "Q3'26", "Q4'26E", "FY26E", "YoY Q1'26", "YoY Q2'26", "YoY Q3'26"]
header(h, 5, cols)
hist = [
    # label, Q4'25, Q1, Q2, Q3, Q4'26E, yoy1, yoy2, yoy3, comments
    ("Search & other", 63.1, 60.4, 63.3, 63.35, "=C6*1.05", 0.19, 0.17, 0.12, "Q3'26 derived: Services $96.3bn less YouTube ads, Subs/devices, Network. Q4'26E = Q4'25 +5% (decel from +12%)."),
    ("YouTube ads", 11.4, 9.9, 11.1, 11.21, "=C7*1.08", 0.11, 0.13, 0.092, "Q4'26E = Q4'25 +8%."),
    ("Subscriptions, platforms & devices", 13.6, 12.4, 12.9, 14.29, "=C8*1.10", 0.19, 0.15, 0.11, "Includes YouTube subscriptions, Google One, Pixel. Q4'26E = Q4'25 +10%."),
    ("Google Network", 7.8, None, None, 7.46, "=C9*0.99", None, None, 0.01, "Q1/Q2'26 derived as Services revenue less the other three lines (see formulas). Q4'26E = Q4'25 -1%."),
    ("Google Cloud", 17.7, 20.03, 24.8, 30.7, "=F11*1.12", 0.63, 0.82, 1.03, "Q4'26E = Q3'26 +12% sequential (backlog $561bn)."),
]
r = 6
for lab, q4, q1, q2, q3, q4e, y1, y2, y3, com in hist:
    put(h, f"B{r}", lab)
    for col, v, src in (("C", q4, "Q4_25"), ("D", q1, "Q1_26"), ("E", q2, "Q2_26"), ("F", q3, "Q3_26")):
        if v is not None:
            put(h, f"{col}{r}", v, USD, BLUE, comment=SRC[src])
    put(h, f"G{r}", q4e, USD, BLUE, comment="Estimate. " + com)
    for col, v in (("I", y1), ("J", y2), ("K", y3)):
        if v is not None:
            put(h, f"{col}{r}", v, PCT, BLUE)
    r += 1
# Cloud is row 10; fix the Q4'26E reference written above (F11 placeholder) to Q3'26 Cloud
h["G10"].value = "=F10*1.12"
# Network Q1/Q2 derived from Services totals (row 12)
put(h, "D9", "=D12-D6-D7-D8", USD, comment="Derived: Q1'26 Services revenue $89.6bn less the other Services lines.")
put(h, "E9", "=E12-E6-E7-E8", USD, comment="Derived: Q2'26 Services revenue (total $119.8bn less Cloud $24.8bn less ~$0.4bn Other Bets) less other lines.")
put(h, "B11", "Other Bets revenue")
for col, v in (("C", 0.4), ("D", 0.4), ("E", 0.4), ("F", 0.372), ("G", 0.4)):
    put(h, f"{col}11", v, USD, BLUE, comment="Q3'26 reported $372m; other quarters estimated ~$0.4bn.")
put(h, "B12", "Google Services revenue", bold=True)
put(h, "C12", "=SUM(C6:C9)", USD, bold=True)
put(h, "D12", 89.6, USD, BLUE, comment=SRC["Q1_26"] + " (Services revenue $89.6bn, +16%).")
put(h, "E12", 94.6, USD, BLUE, comment="Estimate: Q2'26 total $119.8bn less Cloud $24.8bn less ~$0.4bn Other Bets.")
put(h, "F12", 96.3, USD, BLUE, comment=SRC["Q3_26"] + " (Services $96.3bn, +11%).")
put(h, "G12", "=SUM(G6:G9)", USD, bold=True)
put(h, "B13", "Total revenue", bold=True)
for col in "CDEFG":
    put(h, f"{col}13", f"={col}12+{col}10+{col}11", USD, bold=True)
for rr in range(6, 14):
    put(h, f"H{rr}", f"=SUM(D{rr}:G{rr})", USD, bold=(rr >= 12))
put(h, "B15", "Operating income", bold=True)
oi = [
    ("Google Services operating income", None, 40.6, None, 39.16, None, "Q1: $40.6bn (45.3% margin). Q3: $39.16bn. Q2 and Q4 not captured; FY26E on Inputs is an estimate."),
    ("Google Cloud operating income", 5.3, 6.6, 8.81, 11.1, "=F17*1.12", "Reported Q4'25 $5.3bn, Q1 $6.6bn, Q2 $8.81bn, Q3 $11.1bn."),
    ("Other Bets operating income", None, None, None, -2.0, -2.0, "Q3'26 loss ~$2bn."),
    ("Total operating income", None, 39.7, 40.8, "=0.318*F13", None, "Q1 $39.7bn (36.1%), Q2 $40.8bn (34%), Q3 31.8% margin on $127.6bn."),
]
for i, (lab, q4, q1, q2, q3, q4e, com) in enumerate(oi):
    rr = 16 + i
    put(h, f"B{rr}", lab)
    for col, v in (("C", q4), ("D", q1), ("E", q2), ("F", q3), ("G", q4e)):
        if v is not None:
            isf = isinstance(v, str)
            put(h, f"{col}{rr}", v, USD, BLACK if isf else BLUE, comment=None if isf else com)
put(h, "H17", "=SUM(D17:G17)", USD)
put(h, "H18", "=-2.0*4", USD, comment="Estimate: ~-$2bn a quarter.")
put(h, "B21", "Margins", bold=True)
put(h, "B22", "Cloud operating margin")
for col in "CDEFG":
    put(h, f"{col}22", f"=IFERROR({col}17/{col}10,0)", PCT)
put(h, "B23", "Services operating margin")
for col in "DF":
    put(h, f"{col}23", f"=IFERROR({col}16/{col}12,0)", PCT)
put(h, "B24", "Total operating margin")
for col in "DEF":
    put(h, f"{col}24", f"=IFERROR({col}19/{col}13,0)", PCT)
put(h, "B26", "Cash flow", bold=True)
put(h, "B27", "Capital expenditure")
put(h, "F27", 51.4, USD, BLUE, comment=SRC["Q3_26"] + " Capex $51.4bn. 2026 guide $195-205bn; 2027 guided above $300bn.")
put(h, "B28", "Free cash flow")
put(h, "F28", -9.1, USD, BLUE, comment=SRC["Q3_26"] + " FCF -$9.1bn.")
put(h, "B30", "Notes", bold=True)
put(h, "B31", "Search growth decelerated from +19% (Q1'26) to +12% (Q3'26); Cloud accelerated from +48% to +103%. Q3 query growth was the highest in five years.", italic=True)
h.column_dimensions["B"].width = 34
for c in "CDEFGHIJK":
    h.column_dimensions[c].width = 11

# ─────────────────────────── Long-term history ───────────────────────────
lt = wb.create_sheet("Long-term")
title(lt, "Long-term history ($bn) with growth rates",
      "Annual from Alphabet 10-Ks (2019-2024); 2025 segments via secondary sources citing the FY2025 10-K; TTM = Q4'25-Q3'26.")
LT_YEARS = ["2019", "2020", "2021", "2022", "2023", "2024", "2025"]
header(lt, 5, ["Line"] + LT_YEARS + ["TTM Q3'26", "6-yr CAGR 19-25", "3-yr CAGR 22-25", "2025 growth", "TTM vs 2025 pace", "Latest quarter YoY"])
LT = [
    ("Search & other", [98.1, 104.1, 148.95, 162.45, 175.03, 198.08, 224.53], "=History!C6+History!D6+History!E6+History!F6", "=History!K6"),
    ("YouTube ads", [15.15, 19.77, 28.85, 29.24, 31.51, 36.15, 40.4], "=History!C7+History!D7+History!E7+History!F7", "=History!K7"),
    ("Subscriptions, platforms & devices", [17.0, 21.7, 28.03, 29.06, 34.69, 40.34, 48.1], "=History!C8+History!D8+History!E8+History!F8", "=History!K8"),
    ("Google Network", [21.55, 23.09, 31.70, 32.78, 31.31, 30.36, 29.8], "=History!C9+History!D9+History!E9+History!F9", "=History!K9"),
    ("Google Cloud", [8.92, 13.06, 19.21, 26.28, 33.09, 43.23, 58.7], "=History!C10+History!D10+History!E10+History!F10", "=History!K10"),
    ("Total revenue", [161.86, 182.53, 257.64, 282.84, 307.39, 350.02, 402.8], "=History!C13+History!D13+History!E13+History!F13", None),
    ("Cloud operating income", [-4.6, -5.6, -3.1, -2.97, 1.72, 6.11, 13.9], "=History!C17+History!D17+History!E17+History!F17", None),
    ("Capital expenditure", [23.55, 22.28, 24.64, 31.49, 32.25, 52.54, 91.4], None, None),
    ("Free cash flow", [30.97, 42.84, 67.01, 60.01, 69.50, 72.76, 73.3], None, None),
]
for i, (lab, vals, ttm, lq) in enumerate(LT):
    rr = 6 + i
    put(lt, f"B{rr}", lab, bold=lab == "Total revenue")
    for j, v in enumerate(vals):
        put(lt, f"{L(3+j)}{rr}", v, USD, BLUE,
            comment="Alphabet 10-K. 2025 segment values via secondary sources citing the FY2025 10-K; Cloud OI 2025 = sum of quarters (Q4 $5.3bn)." if j == 6 else None)
    if ttm:
        put(lt, f"J{rr}", ttm, USD, GREEN)
    if lab not in ("Cloud operating income",):
        put(lt, f"K{rr}", f"=IFERROR((I{rr}/C{rr})^(1/6)-1,0)", PCT)
        put(lt, f"L{rr}", f"=IFERROR((I{rr}/F{rr})^(1/3)-1,0)", PCT)
        put(lt, f"M{rr}", f"=IFERROR(I{rr}/H{rr}-1,0)", PCT)
        if ttm:
            put(lt, f"N{rr}", f"=IFERROR(J{rr}/I{rr}-1,0)", PCT)
    if lq:
        put(lt, f"O{rr}", lq, PCT, GREEN)
put(lt, "B16", "Cloud operating margin", italic=True)
for j in range(7):
    c = L(3 + j)
    put(lt, f"{c}16", f"=IFERROR({c}12/{c}10,0)", PCT)
put(lt, "J16", "=IFERROR(J12/J10,0)", PCT)
put(lt, "B17", "Capex as % of revenue", italic=True)
for j in range(7):
    c = L(3 + j)
    put(lt, f"{c}17", f"=IFERROR({c}13/{c}11,0)", PCT)
put(lt, "B19", "Driver history", bold=True)
drivers_hist = [
    ("Paid clicks growth", "2021 +23%; 2025 +6%; 9M'26 +11%; Q3'26 +8%", "Alphabet 10-K FY2021, FY2025; Q3'26 10-Q"),
    ("Cost-per-click growth", "2021 +15%; 2025 +7%; Q3'26 +4%", "Alphabet 10-K FY2021, FY2025; Q3'26 10-Q"),
    ("Paid subscriptions (all Google)", "270m (Q4'24) -> 325m+ (Q4'25) -> 350m (Q1'26)", "Alphabet earnings releases"),
    ("YouTube Music & Premium subs", "~100m (early 2024) -> 125m (2025) -> 150m+ incl. trials (Q3'26)", "Alphabet releases; YouTube"),
    ("Cloud backlog", "~$155bn (Q3'25) -> $240bn (Q4'25) -> $561bn (Q3'26)", "Alphabet releases / calls"),
    ("Waymo paid rides per week", "50k (May'24) -> 150k (Oct'24) -> 250k (Apr'25) -> 400k (Feb'26) -> 500k (Mar'26, ~flat to Jul'26)", "Waymo / press"),
    ("Gemini app users", "950m (Q2'26) -> 1bn (Q3'26)", "Alphabet Q3'26 call"),
]
header(lt, 20, ["Driver", "History"])
put(lt, "M20", "Source", bold=True)
for i, (a, b, c) in enumerate(drivers_hist):
    put(lt, f"B{21+i}", a)
    put(lt, f"C{21+i}", b, color=BLUE)
    put(lt, f"M{21+i}", c, italic=True)
lt.column_dimensions["B"].width = 34
for j in range(3, 16):
    lt.column_dimensions[L(j)].width = 11

# ─────────────────────────── Inputs ───────────────────────────
inp = wb.create_sheet("Inputs")
title(inp, "Base year, market and balance sheet inputs ($bn)", "Yellow = key assumptions you may want to change.")
header(inp, 5, ["Input", "Value", "Note"])
I = {}
inputs = [
    ("price", "Share price ($)", 283.5, '$#,##0.00', True, "Bloomberg market cap $3,431bn / 12.1bn shares. Update to live."),
    ("shares", "Diluted shares (bn)", 12.1, '0.00', True, "Estimate. Check latest 10-Q cover."),
    ("netcash", "Net cash ($bn)", 100.0, USD0, True, "Bloomberg LTM: cash $265bn less debt $147bn less preferred & other $18bn."),
    ("stakes", "Equity stakes ($bn)", 100.0, USD0, True, "Estimate: non-marketable stakes incl. SpaceX and Anthropic (see Guide disclosure)."),
    ("tax", "Tax rate", 0.17, PCT, False, "Approx. effective rate."),
    ("disc", "Discount rate", 0.09, PCT, True, "Cost of equity used for DCF."),
    ("tg", "Terminal growth", 0.03, PCT, True, "Perpetual FCF growth after the explicit forecast."),
    ("nyrs", "DCF explicit forecast years", 5, "0", True, "Years of explicit FCF (1-10); terminal value on the last year. 5 = 2027-2031."),
    ("unalloc", "Unallocated costs FY26E ($bn)", -28.0, USD, False, "Estimate: total OI less Services, Cloud and Other Bets OI (AI/DeepMind, corporate)."),
    ("unalloc_g", "Unallocated cost growth / yr", 0.04, PCT, False, "Assumption."),
    ("capex26", "Capex FY26E ($bn)", 200.0, USD0, False, "Guide $195-205bn."),
]
for i, (k, lab, v, fmt, key, note) in enumerate(inputs):
    rr = 6 + i
    I[k] = f"Inputs!$C${rr}"
    put(inp, f"B{rr}", lab)
    put(inp, f"C{rr}", v, fmt, BLUE, fill=YELLOW if key else None)
    put(inp, f"D{rr}", note, italic=True)
rr = 6 + len(inputs) + 1
put(inp, f"B{rr}", "Historical capex for D&A ($bn)", bold=True)
cap_hist = [(2021, 24.6), (2022, 31.5), (2023, 32.3), (2024, 52.5), (2025, 91.4)]
I["caphist"] = {}
for j, (y, v) in enumerate(cap_hist):
    put(inp, f"B{rr+1+j}", str(y))
    put(inp, f"C{rr+1+j}", v, USD, BLUE, comment="Approximate reported capex; 2025 estimated from FCF $73.3bn and OCF $164.7bn.")
    I["caphist"][y] = f"Inputs!$C${rr+1+j}"
rr = rr + 1 + len(cap_hist) + 1
put(inp, f"B{rr}", "FY26E segment base year", bold=True)
header(inp, rr + 1, ["Segment", "Revenue FY26E", "Op margin FY26E", "Op income FY26E", "Note"])
segs = [
    ("search", "Search & other", "=History!H6", 0.52, "Margin estimate: Search carries Services' highest margin."),
    ("yt", "YouTube ads", "=History!H7", 0.30, "Margin estimate."),
    ("subs", "Subscriptions, platforms & devices", "=History!H8", 0.15, "Margin estimate (devices low margin)."),
    ("net", "Google Network", "=History!H9", 0.15, "Margin estimate (most revenue paid to partners)."),
    ("cloud", "Google Cloud", "=History!H10", "=History!H17/History!H10", "Reported quarterly OI; Q4 estimated."),
]
I["seg"] = {}
for j, (k, lab, rev, m, note) in enumerate(segs):
    r2 = rr + 2 + j
    put(inp, f"B{r2}", lab)
    put(inp, f"C{r2}", rev, USD, GREEN)
    put(inp, f"D{r2}", m, PCT, GREEN if isinstance(m, str) else BLUE)
    put(inp, f"E{r2}", f"=C{r2}*D{r2}", USD)
    put(inp, f"F{r2}", note, italic=True)
    I["seg"][k] = (f"Inputs!$C${r2}", f"Inputs!$D${r2}")
r2 = rr + 2 + len(segs)
put(inp, f"B{r2}", "Other Bets operating income FY26E")
put(inp, f"E{r2}", -8.0, USD, BLUE, comment="Estimate: ~-$2bn a quarter.")
I["ob26"] = f"Inputs!$E${r2}"
put(inp, f"B{r2+1}", "Check: segment Services OI vs estimate", italic=True)
put(inp, f"E{r2+1}", f"=SUM(E{rr+2}:E{rr+5})", USD)
put(inp, f"F{r2+1}", "Compare with History Services OI (Q1 $40.6bn, Q3 $39.2bn; ~$160bn a year).", italic=True)
inp.column_dimensions["B"].width = 36
inp.column_dimensions["C"].width = 14
inp.column_dimensions["D"].width = 14
inp.column_dimensions["E"].width = 14
inp.column_dimensions["F"].width = 70

# ─────────────────────────── Scenarios ───────────────────────────
s = wb.create_sheet("Scenarios")
title(s, "Scenario drivers", "Columns C-F are preset cases; G (yellow) is yours to edit. Growth rates are annual.")
SC = ["Bear", "Flat Search / Capex pays", "Base", "Bull", "Custom"]
SCOL = dict(zip(SC, "CDEFG"))
header(s, 5, ["Driver"] + SC + ["What it means"])
drivers = [
    # key, label, fmt, bear, flatpays, base, bull, note
    ("sg1", "Search growth yrs 1-3", PCT, 0.0, 0.0, 0.05, 0.08, "2027-2029"),
    ("sg2", "Search growth yrs 4-5", PCT, 0.0, 0.0, 0.04, 0.06, "2030-2031"),
    ("sg3", "Search growth yrs 6-10", PCT, 0.03, 0.03, 0.04, 0.05, "2032-2036"),
    ("sm", "Search terminal margin", PCT, 0.45, 0.50, 0.52, 0.54, "Reached by year 5 (AI serving costs, ad pricing)"),
    ("yg1", "YouTube ads growth yrs 1-3", PCT, 0.09, 0.11, 0.11, 0.13, ""),
    ("yg2", "YouTube ads growth yrs 4-10", PCT, 0.06, 0.07, 0.07, 0.08, ""),
    ("ym", "YouTube ads terminal margin", PCT, 0.28, 0.30, 0.30, 0.32, ""),
    ("ug1", "Subs/platforms/devices growth yrs 1-3", PCT, 0.09, 0.11, 0.11, 0.13, ""),
    ("ug2", "Subs/platforms/devices growth yrs 4-10", PCT, 0.06, 0.08, 0.08, 0.09, ""),
    ("um", "Subs/platforms/devices terminal margin", PCT, 0.15, 0.18, 0.18, 0.22, ""),
    ("ng", "Network growth (all years)", PCT, -0.03, -0.01, -0.01, 0.0, ""),
    ("nm", "Network terminal margin", PCT, 0.15, 0.15, 0.15, 0.15, ""),
    ("cg1", "Cloud growth yr 1", PCT, 0.40, 0.60, 0.50, 0.60, "2027 (backlog $561bn)"),
    ("cg2", "Cloud growth yr 2", PCT, 0.30, 0.40, 0.35, 0.40, "2028"),
    ("cg3", "Cloud growth yr 3", PCT, 0.20, 0.30, 0.25, 0.30, "2029"),
    ("cg4", "Cloud growth yrs 4-5", PCT, 0.13, 0.22, 0.18, 0.22, "2030-2031"),
    ("cg5", "Cloud growth yrs 6-10", PCT, 0.07, 0.10, 0.09, 0.10, "2032-2036"),
    ("cm", "Cloud terminal margin", PCT, 0.30, 0.42, 0.38, 0.42, "Reached by year 5"),
    ("ob", "Other Bets operating income ($bn/yr)", USD, -8.0, -8.0, -8.0, -6.0, ""),
    ("cx1", "Capex 2027 ($bn)", USD0, 310, 320, 310, 320, "Guide: above $300bn"),
    ("cx2", "Capex 2028 ($bn)", USD0, 280, 310, 300, 320, ""),
    ("cx3", "Capex 2029 ($bn)", USD0, 250, 300, 280, 310, ""),
    ("cxp", "Capex % of revenue from 2030", PCT, 0.27, 0.27, 0.28, 0.28, "Long-run intensity"),
    ("dsh", "Share count change / yr", PCT, 0.01, 0.0, 0.005, -0.01, "+ = dilution (buybacks suspended in 2026)"),
    ("waymo", "Waymo / Other Bets value ($bn)", USD0, 50, 150, 100, 200, "Alphabet's share, today (Waymo $126bn post-money Feb 2026)"),
    ("waymo10", "Waymo / Other Bets value in year 10 ($bn)", USD0, 50, 150, 100, 200, "Alphabet's share at the 2036 exit"),
    ("exit", "Exit P/FCF multiple (year 10)", MULT, 14, 20, 18, 22, ""),
    ("exit5", "Exit P/FCF multiple (year 5, end-2031)", MULT, 14, 20, 18, 22, "Sale price for the 5-year hold"),
    ("mx_s", "SOTP multiple: Search (x FY26E OI)", MULT, 10, 12, 14, 16, ""),
    ("mx_y", "SOTP multiple: YouTube + Subs", MULT, 16, 20, 20, 26, ""),
    ("mx_n", "SOTP multiple: Network", MULT, 6, 6, 6, 6, ""),
    ("mx_c", "SOTP multiple: Cloud", MULT, 18, 35, 30, 40, ""),
    ("mx_u", "SOTP multiple: unallocated costs", MULT, 12, 12, 12, 12, ""),
]
D = {}
for i, (k, lab, fmt, *vals, note) in enumerate(drivers):
    rr = 6 + i
    D[k] = rr
    put(s, f"B{rr}", lab)
    for sc, v in zip(SC[:4], vals):
        put(s, f"{SCOL[sc]}{rr}", v, fmt, BLUE)
    put(s, f"G{rr}", f"=E{rr}", fmt, BLACK, fill=YELLOW, comment=None)
    put(s, f"H{rr}", note, italic=True)
# Custom column: hard inputs (copy of Base) so the user overwrites values, not formulas
for k, rr in D.items():
    s[f"G{rr}"].value = s[f"E{rr}"].value
    s[f"G{rr}"].font = font(BLUE)
s["G5"].comment = Comment("Custom starts as a copy of Base. Overwrite any yellow cell to build your own case.", "Model")
s.column_dimensions["B"].width = 40
for c in "CDEFG":
    s.column_dimensions[c].width = 15
s.column_dimensions["H"].width = 44

# ─────────────────────────── Drivers (feeds the Custom column) ───────────────────────────
dv = wb.create_sheet("Drivers", 3)
title(dv, "Key business drivers -> Custom scenario",
      "Yellow cells are your driver assumptions. Derived growth rates flow into Scenarios > Custom (green links there).")
header(dv, 5, ["Driver", "Value", "Latest data point", "Derived"])
DR = {}


def drow(r, key, label, value, fmt, latest):
    DR[key] = f"Drivers!$C${r}"
    put(dv, f"B{r}", label)
    put(dv, f"C{r}", value, fmt, BLUE, fill=YELLOW)
    put(dv, f"D{r}", latest, italic=True)


def dsec(r, text):
    c = put(dv, f"B{r}", text, bold=True)
    for col in "BCDE":
        dv[f"{col}{r}"].fill = SUB


def dout(r, key, label, formula, fmt):
    DR[key] = f"Drivers!$E${r}"
    put(dv, f"B{r}", label, italic=True)
    put(dv, f"E{r}", formula, fmt, bold=True)


r = 6
dsec(r, "Search = paid clicks x price per click (CPC)"); r += 1
drow(r, "clk1", "Paid clicks growth 2027-29", 0.03, PCT, "Q3'26: +8% (9M'26: +11%)"); r += 1
drow(r, "cpc1", "CPC growth 2027-29", 0.02, PCT, "Q3'26: +4%; AI Mode monetises less per query so far"); r += 1
drow(r, "clk2", "Paid clicks growth 2030-31", 0.025, PCT, ""); r += 1
drow(r, "cpc2", "CPC growth 2030-31", 0.015, PCT, ""); r += 1
drow(r, "clk3", "Paid clicks growth 2032-36", 0.025, PCT, ""); r += 1
drow(r, "cpc3", "CPC growth 2032-36", 0.015, PCT, ""); r += 1
dout(r, "sg1", "-> Search growth 2027-29", f"=(1+{DR['clk1']})*(1+{DR['cpc1']})-1", PCT); r += 1
dout(r, "sg2", "-> Search growth 2030-31", f"=(1+{DR['clk2']})*(1+{DR['cpc2']})-1", PCT); r += 1
dout(r, "sg3", "-> Search growth 2032-36", f"=(1+{DR['clk3']})*(1+{DR['cpc3']})-1", PCT); r += 2
dsec(r, "YouTube ads = watch time x revenue per hour watched"); r += 1
drow(r, "wt1", "Watch-time growth 2027-29", 0.06, PCT, "Q3'26 YouTube ads +9%"); r += 1
drow(r, "mon1", "Revenue per hour growth 2027-29", 0.047, PCT, "Ad load, pricing, CTV/Shorts monetisation"); r += 1
drow(r, "wt2", "Watch-time growth 2030-36", 0.04, PCT, ""); r += 1
drow(r, "mon2", "Revenue per hour growth 2030-36", 0.029, PCT, ""); r += 1
dout(r, "yg1", "-> YouTube ads growth 2027-29", f"=(1+{DR['wt1']})*(1+{DR['mon1']})-1", PCT); r += 1
dout(r, "yg2", "-> YouTube ads growth 2030-36", f"=(1+{DR['wt2']})*(1+{DR['mon2']})-1", PCT); r += 2
dsec(r, "Subscriptions & devices = paid subscriptions x revenue per subscription"); r += 1
drow(r, "sub1", "Paid subscriptions growth 2027-29", 0.08, PCT, "350m paid subs (Q1'26); YouTube Music/Premium 150m+"); r += 1
drow(r, "arpu1", "Revenue per subscription growth 2027-29", 0.028, PCT, "Price rises, Google One AI plans"); r += 1
drow(r, "sub2", "Paid subscriptions growth 2030-36", 0.05, PCT, ""); r += 1
drow(r, "arpu2", "Revenue per subscription growth 2030-36", 0.029, PCT, ""); r += 1
dout(r, "ug1", "-> Subs/devices growth 2027-29", f"=(1+{DR['sub1']})*(1+{DR['arpu1']})-1", PCT); r += 1
dout(r, "ug2", "-> Subs/devices growth 2030-36", f"=(1+{DR['sub2']})*(1+{DR['arpu2']})-1", PCT); r += 2
dsec(r, "Cloud 2027 = backlog converting + new business"); r += 1
drow(r, "blog", "Cloud backlog ($bn)", 561, USD0, "Q3'26: $561bn"); r += 1
drow(r, "conv", "Share of backlog recognised over next 24 months", 0.55, PCT, "Management: just over 55%"); r += 1
drow(r, "newb", "New business recognised in 2027 (% of FY26E Cloud revenue)", 0.40, PCT, "Orders booked and delivered within the year, TPU system sales"); r += 1
dout(r, "cl27", "-> Cloud revenue 2027 ($bn)", f"={DR['blog']}*{DR['conv']}/2+{DR['newb']}*{I['seg']['cloud'][0]}", USD); r += 1
dout(r, "cg1", "-> Cloud growth 2027", f"={DR['cl27']}/{I['seg']['cloud'][0]}-1", PCT); r += 1
put(dv, f"B{r}", "Cloud growth after 2027 and margins stay on Scenarios > Custom.", italic=True); r += 2
dsec(r, "Waymo = weekly paid rides x fare x 52 x revenue multiple x Alphabet share"); r += 1
drow(r, "wr31", "Weekly paid rides in 2031 (millions)", 10.0, '0.0', "~0.5m a week (spring 2026); target 1m by end-2026"); r += 1
drow(r, "fare", "Average fare ($)", 22.0, '$#,##0.00', "Assumption"); r += 1
drow(r, "wm31", "EV / revenue multiple in 2031", 33.0, MULT, "High-growth platform multiple"); r += 1
drow(r, "wr36", "Weekly paid rides in 2036 (millions)", 30.0, '0.0', ""); r += 1
drow(r, "fare36", "Average fare in 2036 ($)", 20.0, '$#,##0.00', "Cheaper as costs fall"); r += 1
drow(r, "wm36", "EV / revenue multiple in 2036", 19.5, MULT, ""); r += 1
drow(r, "own", "Alphabet ownership of Waymo", 0.80, PCT, "Assumption; Waymo valued $126bn post-money Feb 2026"); r += 1
dout(r, "wrev31", "-> Waymo revenue 2031 ($bn)", f"={DR['wr31']}*{DR['fare']}*52/1000", USD); r += 1
dout(r, "wval31", "-> Waymo value 2031, Alphabet share ($bn)", f"={DR['wrev31']}*{DR['wm31']}*{DR['own']}", USD0); r += 1
dout(r, "waymo", "-> Value today: 2031 value discounted ($bn)", f"={DR['wval31']}/(1+{I['disc']})^5", USD0); r += 1
dout(r, "waymo10", "-> Value in 2036, Alphabet share ($bn)",
     f"={DR['wr36']}*{DR['fare36']}*52/1000*{DR['wm36']}*{DR['own']}", USD0); r += 1
dout(r, "wx", "-> Multiple of Waymo's Feb-2026 valuation by 2031", f"={DR['wval31']}/{DR['own']}/126", MULT); r += 1
dv.column_dimensions["B"].width = 58
dv.column_dimensions["C"].width = 12
dv.column_dimensions["D"].width = 52
dv.column_dimensions["E"].width = 12

# Custom column: driver-derived items become links to Drivers
for key in ("sg1", "sg2", "sg3", "yg1", "yg2", "ug1", "ug2", "cg1", "waymo", "waymo10"):
    c = s[f"G{D[key]}"]
    c.value = f"={DR[key]}"
    c.font = font(GREEN)
    c.fill = PatternFill(fill_type=None)

# ─────────────────────────── Model ───────────────────────────
m = wb.create_sheet("Model")
title(m, "10-year projections by scenario ($bn)", "Each block is one scenario. All cells are formulas driven by Scenarios and Inputs.")
YEARS = list(range(2021, 2037))           # C..R
YC = {y: L(3 + i) for i, y in enumerate(YEARS)}
FIRST, LAST = YC[2027], YC[2036]
BLOCK = 50
OUT_ROWS = {}


def sv(sc, key):
    return f"Scenarios!${SCOL[sc]}${D[key]}"


for bi, sc in enumerate(SC):
    top = 5 + bi * BLOCK
    m[f"B{top}"].value = f"Scenario: {sc}"
    m[f"B{top}"].font = Font(name=F, bold=True, size=12, color="1F3864")
    header(m, top + 1, ["Line"] + [str(y) for y in YEARS])
    R = {}
    labels = ["t (year index)", "Search & other revenue", "YouTube ads revenue", "Subs/platforms/devices revenue",
              "Network revenue", "Cloud revenue", "Total revenue", "Revenue growth",
              "Search margin", "YouTube margin", "Subs margin", "Network margin", "Cloud margin",
              "Search operating income", "YouTube operating income", "Subs operating income", "Network operating income",
              "Cloud operating income", "Other Bets operating income", "Unallocated costs", "EBIT", "EBIT margin",
              "Taxes", "NOPAT", "Capex", "D&A (6-yr avg capex)", "Free cash flow", "Shares (bn)", "FCF per share ($)"]
    for i, lab in enumerate(labels):
        R[lab] = top + 2 + i
        put(m, f"B{top+2+i}", lab, bold=lab in ("Total revenue", "EBIT", "Free cash flow"))
    h26 = YC[2026]
    # base year 2026E column
    base = {"Search & other revenue": I["seg"]["search"][0], "YouTube ads revenue": I["seg"]["yt"][0],
            "Subs/platforms/devices revenue": I["seg"]["subs"][0], "Network revenue": I["seg"]["net"][0],
            "Cloud revenue": I["seg"]["cloud"][0]}
    margins0 = {"Search margin": I["seg"]["search"][1], "YouTube margin": I["seg"]["yt"][1],
                "Subs margin": I["seg"]["subs"][1], "Network margin": I["seg"]["net"][1], "Cloud margin": I["seg"]["cloud"][1]}
    for lab, ref in {**base, **margins0}.items():
        put(m, f"{h26}{R[lab]}", f"={ref}", PCT if "margin" in lab else USD, GREEN)
    put(m, f"{h26}{R['t (year index)']}", 0, "0")
    put(m, f"{h26}{R['Total revenue']}", f"=SUM({h26}{R['Search & other revenue']}:{h26}{R['Cloud revenue']})", USD, bold=True)
    put(m, f"{h26}{R['Shares (bn)']}", f"={I['shares']}", '0.00', GREEN)
    put(m, f"{h26}{R['Capex']}", f"={I['capex26']}", USD, GREEN)
    for y in range(2021, 2026):
        put(m, f"{YC[y]}{R['Capex']}", f"={I['caphist'][y]}", USD, GREEN)
    # projection years
    for y in range(2027, 2037):
        c, p = YC[y], YC[y - 1]
        t = f"{c}{R['t (year index)']}"
        put(m, t, f"={p}{R['t (year index)']}+1", "0")
        gs = f"IF({t}<=3,{sv(sc,'sg1')},IF({t}<=5,{sv(sc,'sg2')},{sv(sc,'sg3')}))"
        gy = f"IF({t}<=3,{sv(sc,'yg1')},{sv(sc,'yg2')})"
        gu = f"IF({t}<=3,{sv(sc,'ug1')},{sv(sc,'ug2')})"
        gc = (f"IF({t}=1,{sv(sc,'cg1')},IF({t}=2,{sv(sc,'cg2')},IF({t}=3,{sv(sc,'cg3')},"
              f"IF({t}<=5,{sv(sc,'cg4')},{sv(sc,'cg5')}))))")
        put(m, f"{c}{R['Search & other revenue']}", f"={p}{R['Search & other revenue']}*(1+{gs})", USD)
        put(m, f"{c}{R['YouTube ads revenue']}", f"={p}{R['YouTube ads revenue']}*(1+{gy})", USD)
        put(m, f"{c}{R['Subs/platforms/devices revenue']}", f"={p}{R['Subs/platforms/devices revenue']}*(1+{gu})", USD)
        put(m, f"{c}{R['Network revenue']}", f"={p}{R['Network revenue']}*(1+{sv(sc,'ng')})", USD)
        put(m, f"{c}{R['Cloud revenue']}", f"={p}{R['Cloud revenue']}*(1+{gc})", USD)
        put(m, f"{c}{R['Total revenue']}", f"=SUM({c}{R['Search & other revenue']}:{c}{R['Cloud revenue']})", USD, bold=True)
        put(m, f"{c}{R['Revenue growth']}", f"={c}{R['Total revenue']}/{p}{R['Total revenue']}-1", PCT)
        for mlab, key in (("Search margin", "sm"), ("YouTube margin", "ym"), ("Subs margin", "um"),
                          ("Network margin", "nm"), ("Cloud margin", "cm")):
            put(m, f"{c}{R[mlab]}", f"=${h26}{R[mlab]}+({sv(sc,key)}-${h26}{R[mlab]})*MIN(1,{t}/5)", PCT)
        for oil, rl, ml in (("Search operating income", "Search & other revenue", "Search margin"),
                            ("YouTube operating income", "YouTube ads revenue", "YouTube margin"),
                            ("Subs operating income", "Subs/platforms/devices revenue", "Subs margin"),
                            ("Network operating income", "Network revenue", "Network margin"),
                            ("Cloud operating income", "Cloud revenue", "Cloud margin")):
            put(m, f"{c}{R[oil]}", f"={c}{R[rl]}*{c}{R[ml]}", USD)
        put(m, f"{c}{R['Other Bets operating income']}", f"={sv(sc,'ob')}", USD)
        put(m, f"{c}{R['Unallocated costs']}", f"={I['unalloc']}*(1+{I['unalloc_g']})^{t}", USD)
        put(m, f"{c}{R['EBIT']}", f"=SUM({c}{R['Search operating income']}:{c}{R['Unallocated costs']})", USD, bold=True)
        put(m, f"{c}{R['EBIT margin']}", f"={c}{R['EBIT']}/{c}{R['Total revenue']}", PCT)
        put(m, f"{c}{R['Taxes']}", f"=-MAX(0,{c}{R['EBIT']})*{I['tax']}", USD)
        put(m, f"{c}{R['NOPAT']}", f"={c}{R['EBIT']}+{c}{R['Taxes']}", USD)
        cap = (f"IF({t}=1,{sv(sc,'cx1')},IF({t}=2,{sv(sc,'cx2')},IF({t}=3,{sv(sc,'cx3')},"
               f"{sv(sc,'cxp')}*{c}{R['Total revenue']})))")
        put(m, f"{c}{R['Capex']}", f"={cap}", USD)
        put(m, f"{c}{R['D&A (6-yr avg capex)']}", f"=AVERAGE({YC[y-5]}{R['Capex']}:{c}{R['Capex']})", USD)
        put(m, f"{c}{R['Free cash flow']}", f"={c}{R['NOPAT']}+{c}{R['D&A (6-yr avg capex)']}-{c}{R['Capex']}", USD, bold=True)
        put(m, f"{c}{R['Shares (bn)']}", f"={p}{R['Shares (bn)']}*(1+{sv(sc,'dsh')})", '0.00')
        put(m, f"{c}{R['FCF per share ($)']}", f"={c}{R['Free cash flow']}/{c}{R['Shares (bn)']}", '$#,##0.00;($#,##0.00);-')
    # valuation block
    v0 = top + 2 + len(labels) + 1
    put(m, f"B{v0}", "Valuation", bold=True)
    rows_v = [
        ("PV of FCF, explicit years", f"=SUMPRODUCT(({FIRST}{R['t (year index)']}:{LAST}{R['t (year index)']}<={I['nyrs']})*{FIRST}{R['Free cash flow']}:{LAST}{R['Free cash flow']}/(1+{I['disc']})^{FIRST}{R['t (year index)']}:{LAST}{R['t (year index)']})", USD),
        ("PV of terminal value", f"=INDEX({FIRST}{R['Free cash flow']}:{LAST}{R['Free cash flow']},{I['nyrs']})*(1+{I['tg']})/({I['disc']}-{I['tg']})/(1+{I['disc']})^{I['nyrs']}", USD),
        ("Net cash + stakes + Waymo", f"={I['netcash']}+{I['stakes']}+{sv(sc,'waymo')}", USD),
        ("Equity value", f"=SUM(C{v0+1}:C{v0+3})", USD),
        ("DCF value per share ($)", f"=C{v0+4}/{I['shares']}", '$#,##0;($#,##0);-'),
        ("Upside vs price", f"=C{v0+5}/{I['price']}-1", PCT),
        ("Year-10 exit value per share ($)", f"={LAST}{R['FCF per share ($)']}*{sv(sc,'exit')}+({I['netcash']}+{I['stakes']}+{sv(sc,'waymo10')})/{LAST}{R['Shares (bn)']}", '$#,##0;($#,##0);-'),
        ("Year-5 exit value per share ($)", f"={YC[2031]}{R['FCF per share ($)']}*{sv(sc,'exit5')}+({I['netcash']}+{I['stakes']}+{sv(sc,'waymo')}*(1+{I['disc']})^5)/{YC[2031]}{R['Shares (bn)']}", '$#,##0;($#,##0);-'),
    ]
    for j, (lab, f, fmt) in enumerate(rows_v):
        put(m, f"B{v0+1+j}", lab)
        put(m, f"C{v0+1+j}", f, fmt, bold=lab.startswith("DCF"))
    # IRR cash flows per share: year0 -price, yrs1-9 FCF/share, yr10 FCF/share + exit
    irr_row = v0 + 10
    put(m, f"B{irr_row}", "Cash flows per share for IRR")
    put(m, f"{YC[2026]}{irr_row}", f"=-{I['price']}", '$#,##0.00;($#,##0.00);-')
    for y in range(2027, 2037):
        c = YC[y]
        extra = f"+C{v0+7}" if y == 2036 else ""
        put(m, f"{c}{irr_row}", f"={c}{R['FCF per share ($)']}{extra}", '$#,##0.00;($#,##0.00);-')
    put(m, f"B{irr_row+1}", "10-year IRR", bold=True)
    put(m, f"C{irr_row+1}", f"=IRR({YC[2026]}{irr_row}:{LAST}{irr_row})", PCT, bold=True)
    put(m, f"B{irr_row+2}", "Cumulative FCF 2027-36")
    put(m, f"C{irr_row+2}", f"=SUM({FIRST}{R['Free cash flow']}:{LAST}{R['Free cash flow']})", USD)
    # 5-year hold: buy at price, FCF/share 2027-30, 2031 FCF/share + year-5 exit
    i5 = irr_row + 3
    put(m, f"B{i5}", "Cash flows per share, 5-year hold")
    put(m, f"{YC[2026]}{i5}", f"=-{I['price']}", '$#,##0.00;($#,##0.00);-')
    for y in range(2027, 2032):
        c = YC[y]
        extra = f"+C{v0+8}" if y == 2031 else ""
        put(m, f"{c}{i5}", f"={c}{R['FCF per share ($)']}{extra}", '$#,##0.00;($#,##0.00);-')
    put(m, f"B{i5+1}", "5-year IRR", bold=True)
    put(m, f"C{i5+1}", f"=IRR({YC[2026]}{i5}:{YC[2031]}{i5})", PCT, bold=True)
    put(m, f"B{i5+2}", "Cumulative FCF 2027-31")
    put(m, f"C{i5+2}", f"=SUM({FIRST}{R['Free cash flow']}:{YC[2031]}{R['Free cash flow']})", USD)
    OUT_ROWS[sc] = dict(R=R, v0=v0, irr=irr_row + 1, cum=irr_row + 2, irr5=i5 + 1, cum5=i5 + 2)
m.column_dimensions["B"].width = 34
for y in YEARS:
    m.column_dimensions[YC[y]].width = 10
m.freeze_panes = "C5"

# ─────────────────────────── Summary ───────────────────────────
sm = wb.create_sheet("Summary", 1)
title(sm, "Alphabet: scenario summary", "Outputs by scenario. Edit Scenarios (Custom column) or Inputs and these update.")
header(sm, 5, ["Output"] + SC)
summary_rows = [
    ("DCF value per share ($)", lambda o: f"=Model!C{o['v0']+5}", '$#,##0;($#,##0);-'),
    ("Upside vs price", lambda o: f"=Model!C{o['v0']+6}", PCT),
    ("5-year IRR from today's price", lambda o: f"=Model!C{o['irr5']}", PCT),
    ("Year-5 exit value per share ($)", lambda o: f"=Model!C{o['v0']+8}", '$#,##0;($#,##0);-'),
    ("Total revenue 2031", lambda o: f"=Model!{YC[2031]}{o['R']['Total revenue']}", USD0),
    ("Search operating income 2031", lambda o: f"=Model!{YC[2031]}{o['R']['Search operating income']}", USD0),
    ("Cloud operating income 2031", lambda o: f"=Model!{YC[2031]}{o['R']['Cloud operating income']}", USD0),
    ("EBIT 2031", lambda o: f"=Model!{YC[2031]}{o['R']['EBIT']}", USD0),
    ("Free cash flow 2027", lambda o: f"=Model!{YC[2027]}{o['R']['Free cash flow']}", USD0),
    ("Free cash flow 2031", lambda o: f"=Model!{YC[2031]}{o['R']['Free cash flow']}", USD0),
    ("FCF per share 2031 ($)", lambda o: f"=Model!{YC[2031]}{o['R']['FCF per share ($)']}", '$#,##0.00;($#,##0.00);-'),
    ("Cumulative FCF 2027-31", lambda o: f"=Model!C{o['cum5']}", USD0),
    ("For reference: 10-year IRR (2036 exit)", lambda o: f"=Model!C{o['irr']}", PCT),
]
for i, (lab, fn, fmt) in enumerate(summary_rows):
    rr = 6 + i
    put(sm, f"B{rr}", lab, bold=i < 3)
    for sc in SC:
        put(sm, f"{SCOL[sc]}{rr}", fn(OUT_ROWS[sc]), fmt, GREEN, bold=i < 3)
# SOTP today
s0 = 6 + len(summary_rows) + 1
put(sm, f"B{s0}", "Sum of the parts today (FY26E operating income x multiple)", bold=True)
header(sm, s0 + 1, ["Part"] + SC)
seg_oi = {k: f"Inputs!$E${int(I['seg'][k][0].split('$')[-1])}" for k in I["seg"]}
sotp = [
    ("Search", lambda sc: f"={seg_oi['search']}*{sv(sc,'mx_s')}"),
    ("YouTube ads + Subs/devices", lambda sc: f"=({seg_oi['yt']}+{seg_oi['subs']})*{sv(sc,'mx_y')}"),
    ("Network", lambda sc: f"={seg_oi['net']}*{sv(sc,'mx_n')}"),
    ("Cloud", lambda sc: f"={seg_oi['cloud']}*{sv(sc,'mx_c')}"),
    ("Waymo / Other Bets", lambda sc: f"={sv(sc,'waymo')}"),
    ("Unallocated costs", lambda sc: f"={I['unalloc']}*{sv(sc,'mx_u')}"),
    ("Net cash + equity stakes", lambda sc: f"={I['netcash']}+{I['stakes']}"),
]
for i, (lab, fn) in enumerate(sotp):
    rr = s0 + 2 + i
    put(sm, f"B{rr}", lab)
    for sc in SC:
        put(sm, f"{SCOL[sc]}{rr}", fn(sc), USD0)
tot = s0 + 2 + len(sotp)
put(sm, f"B{tot}", "Equity value", bold=True)
put(sm, f"B{tot+1}", "SOTP value per share ($)", bold=True)
put(sm, f"B{tot+2}", "vs price", bold=True)
for sc in SC:
    c = SCOL[sc]
    put(sm, f"{c}{tot}", f"=SUM({c}{s0+2}:{c}{tot-1})", USD0, bold=True)
    put(sm, f"{c}{tot+1}", f"={c}{tot}/{I['shares']}", '$#,##0;($#,##0);-', bold=True)
    put(sm, f"{c}{tot+2}", f"={c}{tot+1}/{I['price']}-1", PCT, bold=True)
put(sm, f"B{tot+4}", "Price used ($)")
put(sm, f"C{tot+4}", f"={I['price']}", '$#,##0.00', GREEN)
sm.column_dimensions["B"].width = 44
for c in "CDEFG":
    sm.column_dimensions[c].width = 16

for ws in wb.worksheets:
    ws.sheet_view.showGridLines = False

OUT.parent.mkdir(parents=True, exist_ok=True)
wb.save(OUT)
print(OUT)
