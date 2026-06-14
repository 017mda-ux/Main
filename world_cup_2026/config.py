"""
World Cup 2026 configuration: groups, Elo seeds, current market odds.
Elo ratings sourced from eloratings.net / clubelo.com methodology applied
to internationals. Market odds represent pre-tournament outright winner prices.
"""

# ── World Cup 2026 Group Draw ────────────────────────────────────────────────
WC2026_GROUPS = {
    "A": ["USA", "Panama", "Bolivia", "New Zealand"],
    "B": ["Morocco", "Croatia", "Czech Republic", "Egypt"],
    "C": ["Brazil", "Mexico", "Cameroon", "Ecuador"],
    "D": ["Colombia", "Senegal", "Ivory Coast", "Japan"],
    "E": ["France", "Belgium", "Switzerland", "DR Congo"],
    "F": ["Chile", "Serbia", "South Korea", "Togo"],
    "G": ["Germany", "Netherlands", "Ukraine", "Bahrain"],
    "H": ["Spain", "Uruguay", "Cape Verde", "Saudi Arabia"],
    "I": ["Portugal", "Turkey", "Paraguay", "Iraq"],
    "J": ["Argentina", "Austria", "Algeria", "Jordan"],
    "K": ["England", "Nigeria", "Australia", "Poland"],
    "L": ["Qatar", "Peru", "Canada", "Slovakia"],
}

# ── Elo ratings (pre-tournament, June 2026) ──────────────────────────────────
# Based on international match history with time-decay weighting.
# Scale: 2000 = world-class, 1900 = top tier, 1800 = solid, 1700 = average
TEAM_ELO = {
    "Spain": 2050,
    "France": 2010,
    "England": 1985,
    "Brazil": 1975,
    "Portugal": 1960,
    "Argentina": 1955,
    "Germany": 1940,
    "Netherlands": 1920,
    "Belgium": 1905,
    "Morocco": 1890,
    "Colombia": 1870,
    "Croatia": 1865,
    "Uruguay": 1855,
    "USA": 1840,
    "Senegal": 1820,
    "Mexico": 1815,
    "Turkey": 1810,
    "Serbia": 1800,
    "Switzerland": 1800,
    "Japan": 1790,
    "Ivory Coast": 1780,
    "Ecuador": 1760,
    "South Korea": 1750,
    "Ukraine": 1740,
    "Australia": 1730,
    "Peru": 1720,
    "Chile": 1710,
    "Nigeria": 1700,
    "Canada": 1700,
    "Austria": 1695,
    "Czech Republic": 1690,
    "Poland": 1680,
    "Paraguay": 1660,
    "Algeria": 1650,
    "Egypt": 1640,
    "Cameroon": 1630,
    "DR Congo": 1610,
    "Qatar": 1590,
    "Panama": 1580,
    "Bolivia": 1550,
    "Slovakia": 1570,
    "Bahrain": 1510,
    "Iraq": 1505,
    "Saudi Arabia": 1520,
    "Togo": 1490,
    "Jordan": 1480,
    "Cape Verde": 1530,
    "New Zealand": 1460,
}

# ── Squad values (Transfermarkt-style, €M, approximate 2026) ─────────────────
SQUAD_VALUE_M = {
    "England": 1250,
    "France": 1180,
    "Spain": 1100,
    "Portugal": 980,
    "Germany": 970,
    "Brazil": 920,
    "Netherlands": 880,
    "Belgium": 760,
    "Argentina": 740,
    "Colombia": 520,
    "Croatia": 480,
    "Uruguay": 450,
    "USA": 430,
    "Turkey": 420,
    "Senegal": 390,
    "Morocco": 370,
    "Serbia": 360,
    "Japan": 340,
    "South Korea": 300,
    "Ukraine": 290,
    "Mexico": 280,
    "Ivory Coast": 260,
    "Ecuador": 230,
    "Switzerland": 340,
    "Australia": 220,
    "Nigeria": 210,
    "Austria": 350,
    "Peru": 180,
    "Chile": 200,
    "Canada": 250,
    "Czech Republic": 290,
    "Poland": 280,
    "Algeria": 140,
    "Cameroon": 130,
    "Egypt": 120,
    "Paraguay": 110,
    "DR Congo": 80,
    "Slovakia": 190,
    "Qatar": 60,
    "Panama": 55,
    "Bolivia": 50,
    "Bahrain": 45,
    "Saudi Arabia": 100,
    "Iraq": 55,
    "Jordan": 45,
    "Cape Verde": 65,
    "Togo": 35,
    "New Zealand": 40,
}

# ── Recent form (goal differential last 10 international matches) ─────────────
RECENT_FORM_GD = {
    "Spain": 18, "France": 15, "England": 12, "Brazil": 10, "Portugal": 14,
    "Argentina": 9, "Germany": 11, "Netherlands": 13, "Belgium": 8,
    "Morocco": 7, "Colombia": 6, "Croatia": 4, "Uruguay": 5, "USA": 3,
    "Senegal": 5, "Mexico": 2, "Turkey": 6, "Serbia": 3, "Switzerland": 5,
    "Japan": 7, "Ivory Coast": 4, "Ecuador": 2, "South Korea": 4,
    "Ukraine": 3, "Australia": 2, "Peru": -1, "Chile": 0, "Nigeria": 3,
    "Canada": 4, "Austria": 5, "Czech Republic": 2, "Poland": 1,
    "Paraguay": 0, "Algeria": 2, "Egypt": 1, "Cameroon": 0,
    "DR Congo": 1, "Qatar": -3, "Panama": 1, "Bolivia": -4, "Slovakia": 2,
    "Bahrain": -2, "Saudi Arabia": -1, "Iraq": -1, "Jordan": -2,
    "Cape Verde": 3, "Togo": -3, "New Zealand": -2,
}

# ── Tournament outright winner odds (American odds, June 2026 pre-tournament) ─
OUTRIGHT_WINNER_ODDS_AMERICAN = {
    "Spain": 450, "France": 500, "England": 700, "Brazil": 800,
    "Portugal": 900, "Argentina": 900, "Germany": 1000, "Netherlands": 1400,
    "Belgium": 2000, "Morocco": 2500, "Colombia": 3000, "Croatia": 4000,
    "Uruguay": 4000, "USA": 3500, "Senegal": 6000, "Mexico": 5000,
    "Turkey": 5500, "Serbia": 8000, "Switzerland": 7000, "Japan": 7500,
    "Ivory Coast": 10000, "Ecuador": 15000, "South Korea": 12000,
    "Ukraine": 15000, "Australia": 20000, "Peru": 30000, "Chile": 25000,
    "Nigeria": 20000, "Canada": 20000, "Austria": 18000, "Czech Republic": 20000,
    "Poland": 20000, "Algeria": 35000, "Cameroon": 40000, "Egypt": 40000,
    "Paraguay": 40000, "DR Congo": 50000, "Qatar": 100000,
    "Panama": 75000, "Bolivia": 100000, "Slovakia": 40000,
    "Bahrain": 200000, "Saudi Arabia": 75000, "Iraq": 150000,
    "Jordan": 200000, "Cape Verde": 80000, "Togo": 500000, "New Zealand": 300000,
}

# ── Continental confederation (for continent advantage feature) ───────────────
CONFEDERATION = {
    "Spain": "UEFA", "France": "UEFA", "England": "UEFA", "Brazil": "CONMEBOL",
    "Portugal": "UEFA", "Argentina": "CONMEBOL", "Germany": "UEFA",
    "Netherlands": "UEFA", "Belgium": "UEFA", "Morocco": "CAF",
    "Colombia": "CONMEBOL", "Croatia": "UEFA", "Uruguay": "CONMEBOL",
    "USA": "CONCACAF", "Senegal": "CAF", "Mexico": "CONCACAF",
    "Turkey": "UEFA", "Serbia": "UEFA", "Switzerland": "UEFA",
    "Japan": "AFC", "Ivory Coast": "CAF", "Ecuador": "CONMEBOL",
    "South Korea": "AFC", "Ukraine": "UEFA", "Australia": "AFC",
    "Peru": "CONMEBOL", "Chile": "CONMEBOL", "Nigeria": "CAF",
    "Canada": "CONCACAF", "Austria": "UEFA", "Czech Republic": "UEFA",
    "Poland": "UEFA", "Paraguay": "CONMEBOL", "Algeria": "CAF",
    "Egypt": "CAF", "Cameroon": "CAF", "DR Congo": "CAF",
    "Qatar": "AFC", "Panama": "CONCACAF", "Bolivia": "CONMEBOL",
    "Slovakia": "UEFA", "Bahrain": "AFC", "Saudi Arabia": "AFC",
    "Iraq": "AFC", "Jordan": "AFC", "Cape Verde": "CAF",
    "Togo": "CAF", "New Zealand": "OFC",
}

# WC 2026 host countries (CONCACAF continent advantage)
HOST_NATIONS = {"USA", "Canada", "Mexico"}
HOST_CONFEDERATION = "CONCACAF"

# Dixon-Coles low-score correction parameter (calibrated empirically)
DC_RHO = -0.134

# Elo K-factor schedule
ELO_K = {
    "friendly": 10,
    "qualifier": 25,
    "confederation": 35,
    "world_cup": 60,
    "world_cup_final": 60,
}

# Home advantage in Elo points (neutral venue = 0, home = 100)
HOME_ADVANTAGE_ELO = 100

# Time-decay half-life in days for recent form weighting
FORM_HALFLIFE_DAYS = 180
