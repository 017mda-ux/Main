/* ============================================================
   config.js — what this dashboard considers worth knowing.
   Edit this file to change the dashboard. Nothing else needs to change.
   ============================================================ */

/* Formats: 'px' price · 'yld' yield in % · 'idx' index level · 'fx' 4dp
   `hist: true` pulls daily history (sparkline, percentile, z-score).      */

export const TAPE = [
  { s: '^spx',    k: 'S&P 500',        f: 'idx', hist: true },
  { s: '^ndx',    k: 'Nasdaq 100',     f: 'idx', hist: true },
  { s: '^sx5e',   k: 'Euro Stoxx 50',  f: 'idx', hist: true },
  { s: '^nkx',    k: 'Nikkei 225',     f: 'idx', hist: true },
  { s: '10usy.b', k: 'US 10Y',         f: 'yld', hist: true },
  { s: '2usy.b',  k: 'US 2Y',          f: 'yld', hist: true },
  { s: '10dey.b', k: 'Bund 10Y',       f: 'yld', hist: true },
  { s: '10jpy.b', k: 'JGB 10Y',        f: 'yld', hist: true },
  { s: 'dx.f',    k: 'Dollar Index',   f: 'px',  hist: true },
  { s: 'xauusd',  k: 'Gold',           f: 'px',  hist: true },
  { s: 'cl.f',    k: 'WTI Crude',      f: 'px',  hist: true },
  { s: '^vix',    k: 'VIX',            f: 'px',  hist: true },
];

export const FX = [
  { s: 'eurusd', k: 'EUR/USD', f: 'fx', hist: true },
  { s: 'usdjpy', k: 'USD/JPY', f: 'px', hist: true },
  { s: 'gbpusd', k: 'GBP/USD', f: 'fx', hist: true },
  { s: 'usdchf', k: 'USD/CHF', f: 'fx', hist: true },
  { s: 'usdcnh', k: 'USD/CNH', f: 'fx', hist: true },
  { s: 'audusd', k: 'AUD/USD', f: 'fx', hist: true },
  { s: 'usdkrw', k: 'USD/KRW', f: 'px', hist: true },
  { s: 'usdmxn', k: 'USD/MXN', f: 'fx', hist: true },
  { s: 'usdinr', k: 'USD/INR', f: 'px', hist: true },
  { s: 'usdbrl', k: 'USD/BRL', f: 'fx', hist: true },
  { s: 'usdcad', k: 'USD/CAD', f: 'fx', hist: true },
  { s: 'eurjpy', k: 'EUR/JPY', f: 'px', hist: true },
];

/* Extra series needed only to compute crosses / credit proxies. */
export const SUPPORT = [
  { s: 'xagusd',  k: 'Silver',   f: 'px',  hist: true },
  { s: 'hg.f',    k: 'Copper',   f: 'px',  hist: true },
  { s: '30usy.b', k: 'US 30Y',   f: 'yld', hist: true },
  { s: '5usy.b',  k: 'US 5Y',    f: 'yld', hist: true },
  { s: 'hyg.us',  k: 'HYG',      f: 'px',  hist: true },
  { s: 'lqd.us',  k: 'LQD',      f: 'px',  hist: true },
  { s: 'ief.us',  k: 'IEF',      f: 'px',  hist: true },
  { s: 'tlt.us',  k: 'TLT',      f: 'px',  hist: true },
];

/* World indices measured against their own 5-year distribution.
   Forward multiples are not available from any free, keyless, CORS-open
   source — those are link-outs in the source rail, never invented here. */
export const WORLD = [
  { s: '^spx',  k: 'S&P 500',       m: 'United States' },
  { s: '^ndx',  k: 'Nasdaq 100',    m: 'United States' },
  { s: '^rut',  k: 'Russell 2000',  m: 'US small cap' },
  { s: '^sx5e', k: 'Euro Stoxx 50', m: 'Euro area' },
  { s: '^dax',  k: 'DAX',           m: 'Germany' },
  { s: '^ukx',  k: 'FTSE 100',      m: 'United Kingdom' },
  { s: '^nkx',  k: 'Nikkei 225',    m: 'Japan' },
  { s: '^hsi',  k: 'Hang Seng',     m: 'Hong Kong' },
  { s: '^kospi',k: 'KOSPI',         m: 'Korea' },
  { s: '^bvsp', k: 'Bovespa',       m: 'Brazil' },
];

/* ------------------------------------------------------------------
   Macro from the micro — Druckenmiller's premise: the tape of the
   right companies tells you what the economy is doing before the
   statistical agencies do. Each name earns its slot by being a clean,
   single-variable read on one thing.
   ------------------------------------------------------------------ */
export const THEMES = [
  {
    h: 'The consumer, top to bottom',
    tell: 'Trade-down shows up in the spread between the discounters and the mid-market long before it shows up in retail sales.',
    n: [
      ['wmt.us', 'Walmart', 'grocery share, trade-down'],
      ['cost.us','Costco', 'affluent staples demand'],
      ['dg.us',  'Dollar General', 'low-income stress'],
      ['dri.us', 'Darden', 'discretionary dining'],
    ],
  },
  {
    h: 'Freight & the real supply chain',
    tell: 'Trucking and parcel volumes lead industrial production by roughly a quarter. Weakness here is rarely a false alarm.',
    n: [
      ['odfl.us','Old Dominion', 'LTL tonnage, pricing'],
      ['jbht.us','J.B. Hunt', 'intermodal volumes'],
      ['fdx.us', 'FedEx', 'global B2B parcel'],
      ['ups.us', 'UPS', 'domestic ground volume'],
    ],
  },
  {
    h: 'Goods, inventory & the housing chain',
    tell: 'Big-ticket durables are the purest read on credit availability and the housing turnover cycle.',
    n: [
      ['whr.us','Whirlpool', 'durables, input costs'],
      ['dhi.us','D.R. Horton', 'entry-level housing'],
      ['hd.us', 'Home Depot', 'remodel, big-ticket'],
      ['shw.us','Sherwin-Williams', 'construction volume'],
    ],
  },
  {
    h: 'Capex & industrial pulse',
    tell: 'Rental and distribution names turn first because they sit closest to the marginal project decision.',
    n: [
      ['cat.us', 'Caterpillar', 'global heavy capex'],
      ['uri.us', 'United Rentals', 'non-resi construction'],
      ['fast.us','Fastenal', 'factory-floor activity'],
      ['ge.us',  'GE Aerospace', 'aero cycle, services'],
    ],
  },
  {
    h: 'Power, datacentre & the AI build',
    tell: 'The electrical supply chain is the physical constraint on AI capex — a cleaner signal than the chip names themselves.',
    n: [
      ['nvda.us','NVIDIA', 'accelerator demand'],
      ['vrt.us', 'Vertiv', 'datacentre thermal/power'],
      ['etn.us', 'Eaton', 'electrical equipment'],
      ['ceg.us', 'Constellation', 'baseload power pricing'],
    ],
  },
  {
    h: 'Credit at the household level',
    tell: 'Card and subprime lenders mark consumer credit to market daily — well ahead of the delinquency releases.',
    n: [
      ['cof.us', 'Capital One', 'card credit normalisation'],
      ['syf.us', 'Synchrony', 'private-label subprime'],
      ['ally.us','Ally', 'auto credit, used values'],
      ['axp.us', 'Amex', 'affluent spend'],
    ],
  },
];

/* ------------------------------------------------------------------
   Primary sources only. Deep links to the page that actually holds
   the data — not to a homepage, and not to secondary commentary.
   ------------------------------------------------------------------ */
export const RAIL = [
  {
    h: 'Monetary policy',
    l: [
      ['FOMC calendar & statements', 'https://www.federalreserve.gov/monetarypolicy/fomccalendars.htm'],
      ['Fed speeches & testimony',   'https://www.federalreserve.gov/newsevents/speeches.htm'],
      ['Beige Book',                 'https://www.federalreserve.gov/monetarypolicy/beige-book-default.htm'],
      ['SEP dot plot',               'https://www.federalreserve.gov/monetarypolicy/fomccalendars.htm'],
      ['H.4.1 balance sheet',        'https://www.federalreserve.gov/releases/h41/'],
      ['ECB press & decisions',      'https://www.ecb.europa.eu/press/govcdec/html/index.en.html'],
      ['BoJ statements',             'https://www.boj.or.jp/en/mopo/mpmdeci/index.htm'],
    ],
  },
  {
    h: 'Rates & fiscal plumbing',
    l: [
      ['Daily Treasury yield curve', 'https://home.treasury.gov/resource-center/data-chart-center/interest-rates/TextView?type=daily_treasury_yield_curve'],
      ['Quarterly Refunding',        'https://home.treasury.gov/policy-issues/financing-the-government/quarterly-refunding'],
      ['ACM term premium (NY Fed)',  'https://www.newyorkfed.org/research/data_indicators/term-premia-tabs'],
      ['SOFR & reference rates',     'https://www.newyorkfed.org/markets/reference-rates/sofr'],
      ['Fed funds futures (CME)',    'https://www.cmegroup.com/markets/interest-rates/cme-fedwatch-tool.html'],
      ['Treasury auction results',   'https://www.treasurydirect.gov/auctions/announcements-data-results/'],
      ['CBO budget & outlook',       'https://www.cbo.gov/data/budget-economic-data'],
    ],
  },
  {
    h: 'Credit, vol & liquidity',
    l: [
      ['ICE BofA HY/IG OAS (FRED)',  'https://fred.stlouisfed.org/graph/?g=1eTMH'],
      ['CDX index composition',      'https://www.spglobal.com/spdji/en/index-family/fixed-income/cds/'],
      ['Cboe VIX term structure',    'https://www.cboe.com/tradable_products/vix/term_structure/'],
      ['Cboe volume & put/call',     'https://www.cboe.com/us/options/market_statistics/daily/'],
      ['OFR financial stress index', 'https://www.financialresearch.gov/financial-stress-index/'],
      ['NY Fed primary dealer stats','https://www.newyorkfed.org/markets/primarydealer_statistics'],
      ['FINRA short interest',       'https://www.finra.org/finra-data/browse-catalog/short-interest'],
    ],
  },
  {
    h: 'Valuation (forward multiples)',
    l: [
      ['S&P Dow Jones index earnings','https://www.spglobal.com/spdji/en/indices/equity/sp-500/#data'],
      ['MSCI index factsheets',       'https://www.msci.com/end-of-day-data-search'],
      ['Damodaran data & ERP',        'https://pages.stern.nyu.edu/~adamodar/New_Home_Page/data.html'],
      ['Shiller CAPE dataset',        'https://shillerdata.com/'],
    ],
  },
  {
    h: 'Research — peer reviewed & central bank',
    l: [
      ['NBER new working papers',    'https://www.nber.org/papers?page=1&perPage=50&sortBy=public_date'],
      ['BIS working papers',         'https://www.bis.org/wppubl.htm'],
      ['IMF working papers',         'https://www.imf.org/en/Publications/WP'],
      ['Fed FEDS working papers',    'https://www.federalreserve.gov/econres/feds/index.htm'],
      ['ECB working paper series',   'https://www.ecb.europa.eu/pub/research/working-papers/html/index.en.html'],
      ['Brookings Papers (BPEA)',    'https://www.brookings.edu/collection/brookings-papers-on-economic-activity/'],
      ['Jackson Hole proceedings',   'https://www.kansascityfed.org/research/jackson-hole-economic-symposium/'],
    ],
  },
  {
    h: 'Private markets & allocators',
    l: [
      ['SEC EDGAR Form D (new raises)','https://www.sec.gov/cgi-bin/browse-edgar?action=getcompany&type=D&dateb=&owner=include&count=40'],
      ['EDGAR full-text search',      'https://efts.sec.gov/LATEST/search-index?q=&forms=D'],
      ['13F filings browser',         'https://www.sec.gov/cgi-bin/browse-edgar?action=getcompany&type=13F-HR'],
      ['Form ADV adviser search',     'https://adviserinfo.sec.gov/'],
      ['CalPERS board agendas',       'https://www.calpers.ca.gov/page/about/board/board-agendas'],
      ['CalSTRS board meetings',      'https://www.calstrs.com/board-meeting-materials'],
      ['NY Common Retirement Fund',   'https://www.osc.ny.gov/common-retirement-fund'],
      ['Norges Bank IM holdings',     'https://www.nbim.no/en/investments/'],
    ],
  },
  {
    h: 'Data releases & geopolitics',
    l: [
      ['BLS release schedule',       'https://www.bls.gov/schedule/news_release/'],
      ['BEA release schedule',       'https://www.bea.gov/news/schedule'],
      ['Census economic indicators', 'https://www.census.gov/economic-indicators/'],
      ['Federal Register (live)',    'https://www.federalregister.gov/documents/search?conditions%5Btype%5D%5B%5D=PRESDOCU'],
      ['USTR press & actions',       'https://ustr.gov/about-us/policy-offices/press-office/press-releases'],
      ['OFAC sanctions actions',     'https://ofac.treasury.gov/recent-actions'],
      ['EIA weekly petroleum',       'https://www.eia.gov/petroleum/supply/weekly/'],
    ],
  },
];

/* FOMC decision dates — fallback only. refresh.py overwrites this list
   from the Fed's own calendar page whenever it runs. */
export const FOMC_FALLBACK = [
  '2026-01-28', '2026-03-18', '2026-04-29', '2026-06-17',
  '2026-07-29', '2026-09-16', '2026-10-28', '2026-12-09',
];
