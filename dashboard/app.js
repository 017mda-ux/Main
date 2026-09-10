/* ============================================================
   app.js — Vantage
   Two data paths, both optional, neither able to break the page:
     1. data.json   — committed by the refresh job. Paints instantly.
     2. Stooq CSV   — fetched live in the browser. Upgrades the numbers.
   If both fail the page still renders and says exactly what is missing.
   ============================================================ */

import { TAPE, FX, SUPPORT, WORLD, THEMES, RAIL, FOMC_FALLBACK } from './config.js';

const $  = (s, r = document) => r.querySelector(s);
const $$ = (s, r = document) => [...r.querySelectorAll(s)];
const el = (t, c, txt) => { const n = document.createElement(t); if (c) n.className = c; if (txt != null) n.textContent = txt; return n; };

const BELLWETHERS = THEMES.flatMap(t => t.n.map(n => ({ s: n[0], k: n[1], f: 'px', hist: true })));
const UNIVERSE = [...TAPE, ...FX, ...SUPPORT, ...WORLD.map(w => ({ ...w, f: 'idx', hist: true })), ...BELLWETHERS]
  .filter((v, i, a) => a.findIndex(x => x.s === v.s) === i);

const META = Object.fromEntries(UNIVERSE.map(u => [u.s, u]));

/* State: symbol -> { d: [dates], c: [closes] } */
const H = {};
let LIVE = false;
let STAMP = null;

/* ---------------- formatting ---------------- */

const fmt = (v, f) => {
  if (v == null || !isFinite(v)) return '—';
  if (f === 'yld') return v.toFixed(2) + '%';
  if (f === 'fx')  return v.toFixed(4);
  if (f === 'idx') return v.toLocaleString('en-US', { maximumFractionDigits: v > 1000 ? 0 : 2 });
  return v.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
};

/* Direction always carries a sign glyph — colour is never the only cue. */
const sign = n => (n > 0 ? '+' : n < 0 ? '−' : '±');
const dirClass = n => (Math.abs(n) < 1e-9 ? 'flat' : n > 0 ? 'up' : 'down');

/* Round before choosing the sign, so a move that displays as zero never
   renders as "−0bp". */
const fmtChange = (cur, prev, f) => {
  if (cur == null || prev == null) return { txt: '—', cls: 'flat', pct: 0, dir: 0 };
  if (f === 'yld') {
    const bp = (cur - prev) * 100;
    const r = Math.round(bp);
    return { txt: r === 0 ? 'unch' : `${sign(r)}${Math.abs(r)}bp`, cls: dirClass(r), pct: bp, dir: r };
  }
  const pc = ((cur - prev) / Math.abs(prev)) * 100;
  const r = Number(pc.toFixed(2));
  return { txt: r === 0 ? 'unch' : `${sign(r)}${Math.abs(r).toFixed(2)}%`, cls: dirClass(r), pct: pc, dir: r };
};

const nfmt = new Intl.DateTimeFormat('en-GB', { day: 'numeric', month: 'short' });
const prettyDate = s => { const d = new Date(s + 'T00:00:00Z'); return isNaN(d) ? s : nfmt.format(d); };

/* ---------------- series maths ---------------- */

const last  = s => (s && s.c.length ? s.c[s.c.length - 1] : null);
const prior = s => (s && s.c.length > 1 ? s.c[s.c.length - 2] : null);

const returns = (c, n) => {
  const out = [];
  for (let i = Math.max(1, c.length - n); i < c.length; i++) {
    if (c[i - 1] > 0) out.push((c[i] - c[i - 1]) / Math.abs(c[i - 1]));
  }
  return out;
};

const stdev = a => {
  if (a.length < 2) return 0;
  const m = a.reduce((x, y) => x + y, 0) / a.length;
  return Math.sqrt(a.reduce((x, y) => x + (y - m) ** 2, 0) / (a.length - 1));
};

/* How large is today's move relative to this instrument's own recent noise? */
const zScore = s => {
  if (!s || s.c.length < 25) return 0;
  const r = returns(s.c, 61);
  const sd = stdev(r.slice(0, -1));
  return sd > 0 ? r[r.length - 1] / sd : 0;
};

const percentile = (s, v = null, lookback = 1260) => {
  if (!s || s.c.length < 60) return null;
  const win = s.c.slice(-lookback);
  const x = v == null ? win[win.length - 1] : v;
  return (win.filter(y => y <= x).length / win.length) * 100;
};

/* The snapshot carries ~1y of history, a live fetch carries ~5y. Label the
   percentile with the window actually available rather than a fixed claim. */
const pctWindow = s => Math.min(1260, s ? s.c.length : 0);
const pctLabel = s => {
  const n = pctWindow(s);
  if (n >= 1150) return '5y';
  if (n >= 680)  return '3y';
  if (n >= 430)  return '2y';
  if (n >= 200)  return '1y';
  return `${n}d`;
};
const pctWords = s => ({ '5y': 'five years', '3y': 'three years', '2y': 'two years', '1y': 'the past year' }[pctLabel(s)] || 'the available history');

/* A percentile of exactly 0 or 100 is an artefact of a finite window; the
   extreme reads as "1st" / "99th" rather than an impossible "0th". */
const pctText = p => ordinal(Math.min(99, Math.max(1, p)));

const ordinal = n => {
  const r = Math.round(n), t = r % 100;
  if (t >= 11 && t <= 13) return r + 'th';
  return r + ({ 1: 'st', 2: 'nd', 3: 'rd' }[r % 10] || 'th');
};

/* A derived series (ratio, spread) built from two symbols on aligned dates. */
const derive = (a, b, fn) => {
  const A = H[a], B = H[b];
  if (!A || !B) return null;
  const map = new Map(B.d.map((d, i) => [d, B.c[i]]));
  const d = [], c = [];
  for (let i = 0; i < A.d.length; i++) {
    const bv = map.get(A.d[i]);
    if (bv == null) continue;
    const v = fn(A.c[i], bv);
    if (isFinite(v)) { d.push(A.d[i]); c.push(v); }
  }
  return c.length > 30 ? { d, c } : null;
};

/* ---------------- data loading ---------------- */

const CACHE_KEY = 'vantage.hist.v1';

function readCache() {
  try {
    const raw = localStorage.getItem(CACHE_KEY);
    if (!raw) return null;
    const o = JSON.parse(raw);
    if (Date.now() - o.t > 12 * 3600 * 1000) return null;
    return o.h;
  } catch { return null; }
}

function writeCache(h) {
  try { localStorage.setItem(CACHE_KEY, JSON.stringify({ t: Date.now(), h })); }
  catch { try { localStorage.removeItem(CACHE_KEY); } catch {} }
}

/* Path 1 — same-origin snapshot committed by the refresh job. */
async function loadSnapshot() {
  try {
    const r = await fetch('./data.json', { cache: 'no-cache' });
    if (!r.ok) return null;
    return await r.json();
  } catch { return null; }
}

/* Path 2 — live daily history straight from the browser. */
const STOOQ = 'https://stooq.com/q/d/l/';

function parseDaily(csv) {
  const rows = csv.trim().split('\n');
  if (rows.length < 30 || !/^Date/i.test(rows[0])) return null;
  const d = [], c = [];
  for (let i = 1; i < rows.length; i++) {
    const p = rows[i].split(',');
    const close = parseFloat(p[4]);
    if (p[0] && isFinite(close) && close !== 0) { d.push(p[0]); c.push(close); }
  }
  return c.length > 30 ? { d, c } : null;
}

async function fetchOne(sym, from) {
  const url = `${STOOQ}?s=${encodeURIComponent(sym)}&d1=${from}&i=d`;
  const r = await fetch(url, { cache: 'no-cache' });
  if (!r.ok) throw new Error('http ' + r.status);
  return parseDaily(await r.text());
}

async function pool(items, n, worker) {
  const q = [...items];
  const runners = Array.from({ length: n }, async () => {
    while (q.length) {
      const it = q.shift();
      try { await worker(it); } catch {}
    }
  });
  await Promise.all(runners);
}

async function loadLive() {
  const from = (() => {
    const d = new Date(); d.setFullYear(d.getFullYear() - 6);
    return d.toISOString().slice(0, 10).replace(/-/g, '');
  })();

  let ok = 0;
  await pool(UNIVERSE, 6, async u => {
    const s = await fetchOne(u.s, from);
    if (s) { H[u.s] = s; ok++; }
  });
  return ok;
}

/* ---------------- drawing ---------------- */

const TIP = () => $('#tip');

function showTip(evt, html) {
  const t = TIP();
  t.innerHTML = html;
  t.style.opacity = '1';
  const pad = 14, w = t.offsetWidth, h = t.offsetHeight;
  let x = evt.clientX + pad, y = evt.clientY - h - pad;
  if (x + w > innerWidth - 8) x = evt.clientX - w - pad;
  if (y < 8) y = evt.clientY + pad;
  t.style.left = x + 'px';
  t.style.top = y + 'px';
}
const hideTip = () => { TIP().style.opacity = '0'; };

const SVGNS = 'http://www.w3.org/2000/svg';
const svgEl = (t, a = {}) => { const n = document.createElementNS(SVGNS, t); for (const k in a) n.setAttribute(k, a[k]); return n; };

/* Charts are drawn at their measured pixel width, so the viewBox scale is
   always 1:1 — no sheared text, no elliptical dots on a narrow screen. */
const FIT = [];
function registerFit(svg, draw) { svg.__draw = draw; FIT.push(svg); }
function fitAll() {
  for (const s of FIT) {
    const w = Math.round(s.getBoundingClientRect().width);
    if (w > 0 && w !== s.__w) { s.__w = w; s.__draw(w); }
  }
}
let fitTimer = null;
addEventListener('resize', () => { clearTimeout(fitTimer); fitTimer = setTimeout(fitAll, 120); });

/* Sparkline: pure shape. No axes, no grid, no numbers on points. */
function sparkline(series, opts = {}) {
  const Hh = 30, pad = 3;
  const c = series.c.slice(-130), d = series.d.slice(-130);
  const s = svgEl('svg', { class: 'spark', role: 'img', 'aria-label': `${opts.label || 'price'} trend, last ${c.length} sessions` });
  if (c.length < 2) return s;

  const lo = Math.min(...c), hi = Math.max(...c), rng = hi - lo || 1;
  const dir = opts.dir != null ? opts.dir : (c[c.length - 1] - c[0]);
  const stroke = dir < 0 ? 'var(--down-mark)' : dir > 0 ? 'var(--up-mark)' : 'var(--flat)';
  const Y = v => Hh - pad - ((v - lo) / rng) * (Hh - pad * 2);

  const path = svgEl('path', { fill: 'none', stroke, 'stroke-width': 2, 'stroke-linejoin': 'round', 'stroke-linecap': 'round', 'vector-effect': 'non-scaling-stroke' });
  const dot = svgEl('circle', { r: 4, fill: stroke, stroke: 'var(--surface)', 'stroke-width': 2 });
  const cur = svgEl('line', { y1: 0, y2: Hh, stroke: 'var(--ink-3)', 'stroke-width': 1, opacity: 0, 'vector-effect': 'non-scaling-stroke' });
  s.append(path, dot, cur);

  let X = i => i;
  registerFit(s, W => {
    s.setAttribute('viewBox', `0 0 ${W} ${Hh}`);
    X = i => 3 + (i / (c.length - 1)) * (W - 6);
    path.setAttribute('d', c.map((v, i) => `${i ? 'L' : 'M'}${X(i).toFixed(1)} ${Y(v).toFixed(1)}`).join(' '));
    dot.setAttribute('cx', X(c.length - 1).toFixed(1));
    dot.setAttribute('cy', Y(c[c.length - 1]).toFixed(1));
  });

  /* hover layer — a chart is interactive by default */
  s.style.pointerEvents = 'all';
  s.addEventListener('pointermove', e => {
    const b = s.getBoundingClientRect();
    const i = Math.max(0, Math.min(c.length - 1, Math.round(((e.clientX - b.left) / b.width) * (c.length - 1))));
    cur.setAttribute('x1', X(i)); cur.setAttribute('x2', X(i)); cur.setAttribute('opacity', '0.5');
    showTip(e, `<b>${fmt(c[i], opts.f)}</b><div class="t2">${prettyDate(d[i])}</div>`);
  });
  s.addEventListener('pointerleave', () => { cur.setAttribute('opacity', '0'); hideTip(); });
  return s;
}

/* ---------------- section: the read ---------------- */

function buildRead() {
  const out = [];
  const named = new Set();   /* an instrument earns at most one line */
  const scored = TAPE.concat(FX).map(u => ({ u, s: H[u.s] })).filter(x => x.s)
    .map(x => ({ ...x, z: zScore(x.s) }))
    .sort((a, b) => Math.abs(b.z) - Math.abs(a.z));

  for (const it of scored) {
    if (Math.abs(it.z) < 1.6 || out.length >= 3) break;
    named.add(it.u.s);
    const ch = fmtChange(last(it.s), prior(it.s), it.u.f);
    const p = percentile(it.s);
    const sig = `${Math.abs(it.z).toFixed(1)}σ`;
    const move = `<b>${it.u.k}</b> ${ch.pct > 0 ? 'up' : 'down'} <span class="${ch.cls}">${ch.txt}</span>`;
    /* The first line carries the explanation; the rest stay terse rather
       than repeating the same sentence three times. */
    out.push(out.length === 0
      ? `${move} — a ${sig} move against its own 60-day noise${p != null ? `, and the ${pctText(p)} percentile of ${pctWords(it.s)}` : ''}.`
      : `${move} <span class="q">(${sig})</span>${p != null ? `, ${pctText(p)} percentile` : ''}.`);
  }

  /* Curve is always worth a line when it actually moved. */
  const c2 = H['2usy.b'], c10 = H['10usy.b'];
  if (c2 && c10) {
    const now = (last(c10) - last(c2)) * 100, was = (prior(c10) - prior(c2)) * 100;
    const dbp = now - was;
    if (Math.abs(dbp) >= 3) {
      out.push(`Curve <b>${dbp > 0 ? 'steepened' : 'flattened'}</b> ${Math.abs(dbp).toFixed(0)}bp — 2s10s at <span class="q">${sign(now)}${Math.abs(now).toFixed(0)}bp</span>.`);
    }
  }

  const vix = H['^vix'];
  if (vix && !named.has('^vix') && out.length < 5) {
    const v = last(vix), z = zScore(vix);
    if (v > 22 || Math.abs(z) > 2) {
      out.push(`VIX at <b>${v.toFixed(1)}</b>${v > 22 ? ' — above the level where cross-asset correlation usually rises' : ', a sharp repricing of near-term risk'}.`);
    }
  }

  const hl = derive('hyg.us', 'ief.us', (a, b) => a / b);
  if (hl && !named.has('hyg.us') && out.length < 5) {
    const z = zScore(hl);
    if (Math.abs(z) > 1.6) {
      out.push(`High yield ${z > 0 ? 'outperforming' : 'lagging'} duration by ${Math.abs(z).toFixed(1)}σ — credit is ${z > 0 ? 'leaning risk-on' : 'the one to watch'}.`);
    }
  }

  const ul = $('#read-list');
  ul.innerHTML = '';
  if (!out.length) {
    const li = el('li', 'empty', 'Quiet tape. Nothing moved beyond its own noise today — the signal is the absence of one.');
    ul.appendChild(li);
    return;
  }
  out.slice(0, 5).forEach(t => { const li = el('li'); li.innerHTML = t; ul.appendChild(li); });
}

/* ---------------- section: tape ---------------- */

function tile(u) {
  const s = H[u.s];
  if (!s) return null;
  const cur = last(s), prev = prior(s);
  const ch = fmtChange(cur, prev, u.f);

  const t = el('div', 'tile');
  t.appendChild(el('div', 'k', u.k));
  const row = el('div', 'row');
  row.appendChild(el('div', 'v num', fmt(cur, u.f)));
  row.appendChild(el('div', `d num ${ch.cls}`, ch.txt));
  t.appendChild(row);
  t.appendChild(sparkline(s, { f: u.f, label: u.k, dir: ch.dir }));
  return t;
}

/* Never replace the container itself — a later re-render still needs to find
   it. Empty state goes inside, and the grid collapses to a plain block. */
function buildGrid(sel, list) {
  const g = $(sel);
  if (!g) return 0;
  g.innerHTML = '';
  let n = 0;
  list.forEach(u => { const t = tile(u); if (t) { g.appendChild(t); n++; } });
  g.classList.toggle('is-empty', n === 0);
  if (!n) g.appendChild(failCard('No series in this block resolved.'));
  return n;
}

/* ---------------- section: movers ---------------- */

function buildMovers() {
  const wrap = $('#movers');
  wrap.innerHTML = '';
  const pool = [...TAPE, ...FX, ...BELLWETHERS];
  const rows = pool.map(u => ({ u, s: H[u.s] })).filter(x => x.s)
    .map(x => ({ ...x, z: zScore(x.s) }))
    .filter(x => Math.abs(x.z) >= 1.5)
    .sort((a, b) => Math.abs(b.z) - Math.abs(a.z))
    .slice(0, 9);

  $('#movers-note').textContent = rows.length
    ? `${rows.length} of ${pool.length} tracked instruments moved more than 1.5σ against their own 60-day volatility.`
    : '';

  if (!rows.length) {
    const anyData = pool.some(u => H[u.s]);
    wrap.appendChild(anyData
      ? el('p', 'read empty', 'Nothing cleared the 1.5σ bar. On a day like this the tape is telling you to stand still.')
      : failCard('No series resolved, so nothing can be ranked.'));
    return;
  }

  const cap = Math.max(3, Math.min(4, Math.max(...rows.map(r => Math.abs(r.z)))));
  rows.forEach(r => {
    const ch = fmtChange(last(r.s), prior(r.s), r.u.f);
    const row = el('div', 'mover');

    const nm = el('div', 'name', r.u.k);
    nm.appendChild(el('em', null, `${Math.abs(r.z).toFixed(1)}σ · ${r.u.s}`));
    row.appendChild(nm);
    row.appendChild(el('div', 'val num', fmt(last(r.s), r.u.f)));

    /* diverging bar around a zero centre — magnitude and polarity together */
    const bar = el('div', 'zbar');
    const i = el('i');
    const w = Math.min(50, (Math.abs(r.z) / cap) * 50);
    if (r.z >= 0) { i.style.left = '50%'; i.style.width = w + '%'; i.style.background = 'var(--up-mark)'; }
    else { i.style.right = '50%'; i.style.width = w + '%'; i.style.background = 'var(--down-mark)'; }
    bar.appendChild(i);
    bar.title = `${r.z.toFixed(2)}σ`;
    row.appendChild(bar);

    row.appendChild(el('div', `chg num ${ch.cls}`, ch.txt));
    wrap.appendChild(row);
  });
}

/* ---------------- section: signals ---------------- */

function signalCard({ k, series, f, read, invert }) {
  if (!series) return null;
  const cur = last(series), prev = prior(series);
  const p = percentile(series);
  const ch = fmtChange(cur, prev, f === 'bp' ? 'px' : f);

  const c = el('div', 'signal');
  c.appendChild(el('div', 'k', k));
  const line = el('div', 'line');
  line.appendChild(el('div', 'v num', f === 'bp' ? `${sign(cur)}${Math.abs(cur).toFixed(0)}bp` : fmt(cur, f)));
  const dch = el('div', `d num ${dirClass(cur - prev)}`, f === 'bp'
    ? `${sign(cur - prev)}${Math.abs(cur - prev).toFixed(0)}bp`
    : ch.txt);
  line.appendChild(dch);
  c.appendChild(line);

  if (p != null) {
    const m = el('div', 'pct');
    const tr = el('div', 'track');
    const mk = el('i'); mk.style.left = p + '%';
    tr.appendChild(mk);
    m.appendChild(tr);
    m.appendChild(el('div', 'lab', `${pctText(p)} pctile · ${pctLabel(series)}`));
    c.appendChild(m);
  }

  const rl = el('div', 'read-line');
  rl.innerHTML = read(cur, p, cur - prev);
  c.appendChild(rl);
  return c;
}

function buildSignals() {
  const g = $('#signals');
  if (!g) return;
  g.innerHTML = '';
  const defs = [];

  const gs = derive('xauusd', 'xagusd', (a, b) => a / b);
  defs.push({
    k: 'Gold / Silver', series: gs, f: 'px',
    read: (v, p) => p == null ? '' : p > 75
      ? 'Stretched. Silver’s industrial leg is lagging gold’s monetary one — historically a defensive tell.'
      : p < 25
        ? 'Compressed. Silver leading gold usually accompanies a live industrial cycle.'
        : 'Mid-range. No strong message from the precious metals ratio.',
  });

  const cg = derive('hg.f', 'xauusd', (a, b) => (a / b) * 10000);
  defs.push({
    k: 'Copper / Gold', series: cg, f: 'px',
    read: (v, p) => p == null ? '' : p > 70
      ? 'Growth impulse firm. This ratio and the 10-year normally travel together — check the chart below for divergence.'
      : p < 30
        ? 'Growth impulse weak. If the 10-year has not followed it lower, one of the two is wrong.'
        : 'Neutral. Watch the direction rather than the level.',
  });

  const s2s10 = derive('10usy.b', '2usy.b', (a, b) => (a - b) * 100);
  defs.push({
    k: '2s10s slope', series: s2s10, f: 'bp',
    read: (v, p, d) => v < 0
      ? 'Inverted. The front end is still pricing more restriction than the long end will accept.'
      : `Positive and ${d > 0 ? 'steepening' : d < 0 ? 'flattening' : 'unchanged'}. ${p != null && p > 80 ? 'Near the steep end of its range — bear-steepening is a fiscal signal as much as a growth one.' : 'Direction matters more than level here.'}`,
  });

  const s5s30 = derive('30usy.b', '5usy.b', (a, b) => (a - b) * 100);
  defs.push({
    k: '5s30s slope', series: s5s30, f: 'bp',
    read: (v, p) => p == null ? '' : p > 75
      ? 'Long end cheapening relative to the belly — supply and term premium, not growth.'
      : 'Belly holding against the long end.',
  });

  const hyief = derive('hyg.us', 'ief.us', (a, b) => a / b);
  defs.push({
    k: 'High yield / duration', series: hyief, f: 'px',
    read: (v, p) => p == null ? '' : p > 70
      ? 'Credit is paying to take risk. Spread compression proxy at the wide end of its range.'
      : p < 30
        ? 'Credit is charging for risk. This proxy leads equity drawdowns more often than it lags them.'
        : 'Credit neutral — no confirmation either way for equities.',
    note: 'Proxy for CDX HY. True CDX and OAS series are link-outs below.',
  });

  const hylqd = derive('hyg.us', 'lqd.us', (a, b) => a / b);
  defs.push({
    k: 'High yield / investment grade', series: hylqd, f: 'px',
    read: (v, p) => p == null ? '' : p > 70
      ? 'Quality curve flat — the market is not discriminating between HY and IG.'
      : p < 30 ? 'Quality is being bid. Down-in-quality is being punished.' : 'Ordinary quality spread.',
  });

  defs.push({
    k: 'Equity volatility (VIX)', series: H['^vix'], f: 'px',
    read: (v, p) => v == null ? '' : v < 14
      ? 'Complacent. Convexity is cheap here; that is a statement about price, not about timing.'
      : v > 24 ? 'Stressed. Correlation across assets typically rises from this level.'
        : `Ordinary. ${p != null ? `${pctText(p)} percentile of ${pctWords(H['^vix'])}.` : ''}`,
  });

  defs.push({
    k: 'US 10-year', series: H['10usy.b'], f: 'yld',
    read: (v, p) => p == null ? '' : `${pctText(p)} percentile of ${pctWords(H['10usy.b'])}. Decompose it: the real rate is the growth signal, term premium is the fiscal one.`,
  });

  let n = 0;
  defs.forEach(d => {
    const c = signalCard(d);
    if (!c) return;
    if (d.note) { const nn = el('div', 'lab'); nn.style.cssText = 'font-size:11px;color:var(--ink-3)'; nn.textContent = d.note; c.appendChild(nn); }
    g.appendChild(c); n++;
  });
  g.classList.toggle('is-empty', n === 0);
  if (!n) g.appendChild(failCard('Signal crosses need their underlying series; none resolved.'));
}

/* ---------------- section: copper/gold vs 10y ---------------- */

/* One axis. Both series indexed to 100 at the start — never a second y-scale. */
function buildCross() {
  const host = $('#cross');
  host.innerHTML = '';
  const cg = derive('hg.f', 'xauusd', (a, b) => (a / b) * 10000);
  const ty = H['10usy.b'];
  if (!cg || !ty) { host.appendChild(failCard('Copper, gold or the 10-year did not resolve.')); return; }

  const N = 500;
  const map = new Map(ty.d.map((d, i) => [d, ty.c[i]]));
  const d = [], A = [], B = [];
  const cd = cg.d.slice(-N), cc = cg.c.slice(-N);
  for (let i = 0; i < cd.length; i++) {
    const b = map.get(cd[i]);
    if (b == null) continue;
    d.push(cd[i]); A.push(cc[i]); B.push(b);
  }
  if (d.length < 40) { host.appendChild(failCard('Not enough overlapping history between copper, gold and the 10-year.')); return; }

  const ix = a => a.map(v => (v / a[0]) * 100);
  const a = ix(A), b = ix(B);

  const Hh = 216, T = 12, Bm = 24;
  const lo = Math.min(...a, ...b), hi = Math.max(...a, ...b), rng = (hi - lo) || 1;
  const Y = v => T + (1 - (v - lo) / rng) * (Hh - T - Bm);

  const s = svgEl('svg', { class: 'chart', role: 'img', 'aria-label': 'Copper to gold ratio and the US 10-year yield, both indexed to 100' });
  const grid = [0, 0.5, 1].map(() => svgEl('line', { stroke: 'var(--hairline-soft)', 'stroke-width': 1, 'vector-effect': 'non-scaling-stroke' }));
  grid.forEach(g => s.appendChild(g));
  const pB = svgEl('path', { fill: 'none', stroke: 'var(--ink-3)', 'stroke-width': 2, 'stroke-linejoin': 'round', 'vector-effect': 'non-scaling-stroke' });
  const pA = svgEl('path', { fill: 'none', stroke: 'var(--accent)', 'stroke-width': 2, 'stroke-linejoin': 'round', 'vector-effect': 'non-scaling-stroke' });
  s.append(pB, pA);

  /* selective direct labels: the endpoint only, never a value per point */
  const lA = svgEl('text', { fill: 'var(--accent)', 'font-size': 11, 'font-weight': 550 }); lA.textContent = 'Cu/Au';
  const lB = svgEl('text', { fill: 'var(--ink-2)', 'font-size': 11, 'font-weight': 550 }); lB.textContent = '10Y';
  const t0 = svgEl('text', { fill: 'var(--ink-3)', 'font-size': 10, 'text-anchor': 'start' });
  const t1 = svgEl('text', { fill: 'var(--ink-3)', 'font-size': 10, 'text-anchor': 'end' });
  t0.textContent = `${prettyDate(d[0])} ${d[0].slice(0, 4)}`;
  t1.textContent = `${prettyDate(d[d.length - 1])} ${d[d.length - 1].slice(0, 4)}`;
  const cur = svgEl('line', { y1: T, y2: Hh - Bm, stroke: 'var(--ink-3)', 'stroke-width': 1, opacity: 0, 'vector-effect': 'non-scaling-stroke' });
  s.append(lA, lB, t0, t1, cur);

  let X = i => i;
  registerFit(s, W => {
    const R = 46, L = 4;
    s.setAttribute('viewBox', `0 0 ${W} ${Hh}`);
    X = i => L + (i / (d.length - 1)) * (W - L - R);
    grid.forEach((g, k) => {
      const y = T + (k / 2) * (Hh - T - Bm);
      g.setAttribute('x1', L); g.setAttribute('x2', W - R);
      g.setAttribute('y1', y); g.setAttribute('y2', y);
    });
    const dd = arr => arr.map((v, i) => `${i ? 'L' : 'M'}${X(i).toFixed(1)} ${Y(v).toFixed(1)}`).join(' ');
    pA.setAttribute('d', dd(a)); pB.setAttribute('d', dd(b));
    lA.setAttribute('x', W - R + 6); lA.setAttribute('y', Y(a[a.length - 1]) + 4);
    lB.setAttribute('x', W - R + 6); lB.setAttribute('y', Y(b[b.length - 1]) + 4);
    t0.setAttribute('x', L); t0.setAttribute('y', Hh - 6);
    t1.setAttribute('x', W - R); t1.setAttribute('y', Hh - 6);
    /* keep the two endpoint labels from colliding */
    const ya = +lA.getAttribute('y'), yb = +lB.getAttribute('y');
    if (Math.abs(ya - yb) < 12) lB.setAttribute('y', ya < yb ? yb + (12 - (yb - ya)) : yb - (12 - (ya - yb)));
  });

  s.addEventListener('pointermove', e => {
    const r = s.getBoundingClientRect();
    const i = Math.max(0, Math.min(d.length - 1, Math.round(((e.clientX - r.left) / r.width) * (d.length - 1))));
    cur.setAttribute('x1', X(i)); cur.setAttribute('x2', X(i)); cur.setAttribute('opacity', '0.45');
    showTip(e, `<b>${prettyDate(d[i])}</b><div class="t2">Cu/Au ${a[i].toFixed(1)} · 10Y ${b[i].toFixed(1)} (indexed)</div><div class="t2">10-year ${B[i].toFixed(2)}%</div>`);
  });
  s.addEventListener('pointerleave', () => { cur.setAttribute('opacity', '0'); hideTip(); });

  const card = el('div', 'chart-card');
  card.appendChild(el('h3', null, 'Copper/gold against the 10-year'));
  card.appendChild(el('p', 'note', `Both indexed to 100 at ${prettyDate(d[0])} ${d[0].slice(0, 4)} so they share one axis. When they separate, the bond market and the industrial economy disagree — and one of them is early.`));
  const lg = el('div', 'legend');
  [['Copper / gold', 'var(--accent)'], ['US 10-year yield', 'var(--ink-3)']].forEach(([t, c]) => {
    const sp = el('span'); const ic = el('i'); ic.style.background = c;
    sp.appendChild(ic); sp.appendChild(document.createTextNode(t)); lg.appendChild(sp);
  });
  card.appendChild(lg);
  const wrap = el('div', 'chart-wrap'); wrap.appendChild(s); card.appendChild(wrap);
  host.appendChild(card);
}

/* ---------------- section: valuation ---------------- */

function buildValuation() {
  const host = $('#vals');
  host.innerHTML = '';
  let n = 0;
  WORLD.forEach(w => {
    const s = H[w.s];
    if (!s) return;
    const win = s.c.slice(-pctWindow(s));
    const lo = Math.min(...win), hi = Math.max(...win), cur = last(s);
    const p = percentile(s);
    const ma200 = s.c.slice(-200).reduce((a, b) => a + b, 0) / Math.min(200, s.c.length);
    const vs = ((cur - ma200) / ma200) * 100;

    const row = el('div', 'valrow');
    const nm = el('div', 'name', w.k);
    nm.appendChild(el('em', null, w.m));
    row.appendChild(nm);
    row.appendChild(el('div', 'px num', fmt(cur, 'idx')));

    const rg = el('div', 'range');
    const u = el('u'); u.style.left = '0%'; u.style.width = Math.max(0, Math.min(100, p)) + '%';
    const i = el('i'); i.style.left = Math.max(0, Math.min(100, p)) + '%';
    rg.appendChild(u); rg.appendChild(i);
    rg.title = `${pctLabel(s)} range ${fmt(lo, 'idx')} – ${fmt(hi, 'idx')}`;
    row.appendChild(rg);

    const lab = el('div', 'pctl num');
    lab.innerHTML = `${pctText(p)} pctile ${pctLabel(s)} · <span class="${dirClass(vs)}">${sign(vs)}${Math.abs(vs).toFixed(1)}% vs 200d</span>`;
    row.appendChild(lab);
    host.appendChild(row);
    n++;
  });
  if (!n) host.appendChild(failCard('No index history resolved.'));
}

/* ---------------- section: bellwethers ---------------- */

function buildThemes() {
  const host = $('#themes');
  host.innerHTML = '';
  THEMES.forEach(t => {
    const box = el('div', 'theme');
    box.appendChild(el('h3', null, t.h));
    box.appendChild(el('p', 'tell', t.tell));
    const ol = el('ol');
    let any = 0;
    t.n.forEach(([sym, name, tell]) => {
      const s = H[sym];
      const li = el('li');
      const a = el('div', 't', name);
      a.appendChild(el('em', null, tell));
      li.appendChild(a);
      if (s) {
        const ch = fmtChange(last(s), prior(s), 'px');
        li.appendChild(el('div', 'p num', fmt(last(s), 'px')));
        li.appendChild(el('div', `c num ${ch.cls}`, ch.txt));
        any++;
      } else {
        li.appendChild(el('div', 'p num', '—'));
        li.appendChild(el('div', 'c num flat', '—'));
      }
      ol.appendChild(li);
    });
    box.appendChild(ol);
    host.appendChild(box);
  });
}

/* ---------------- section: policy ---------------- */

function buildPolicy(snapshot) {
  const dates = (snapshot && snapshot.fomc && snapshot.fomc.length ? snapshot.fomc : FOMC_FALLBACK)
    .filter(d => new Date(d + 'T23:59:59Z') >= new Date())
    .sort();
  const box = $('#countdown');
  box.innerHTML = '';
  box.appendChild(el('div', 'k', 'Next FOMC decision'));
  if (!dates.length) {
    box.appendChild(el('div', 'when', 'No forward dates loaded — see the Fed calendar in the rail below.'));
    return;
  }
  const next = dates[0];
  const days = Math.ceil((new Date(next + 'T18:00:00Z') - Date.now()) / 86400000);
  const n = el('div', 'n num', String(Math.max(0, days)));
  n.appendChild(el('small', null, days === 1 ? 'day' : 'days'));
  box.appendChild(n);
  const d = new Date(next + 'T00:00:00Z');
  box.appendChild(el('div', 'when', d.toLocaleDateString('en-GB', { weekday: 'long', day: 'numeric', month: 'long', year: 'numeric', timeZone: 'UTC' })));
}

/* ---------------- section: feeds ---------------- */

const FEED_BLOCKS = [
  ['policy',     'Policy — Fed, Treasury, Federal Register'],
  ['research',   'Research — peer reviewed & central bank'],
  ['private',    'Private markets — filings & raises'],
  ['allocators', 'Allocators & limited partners'],
  ['geo',        'Geopolitics & trade actions'],
  ['assets',     'Asset-class specific'],
];

function buildFeeds(snapshot) {
  const host = $('#feeds');
  host.innerHTML = '';
  const feeds = (snapshot && snapshot.feeds) || {};
  let total = 0;

  FEED_BLOCKS.forEach(([key, title]) => {
    const items = (feeds[key] || []).slice(0, 7);
    total += items.length;
    const box = el('div', 'feed');
    box.appendChild(el('h3', null, title));
    if (!items.length) {
      box.appendChild(el('div', 'empty', 'Nothing new since the last refresh.'));
      host.appendChild(box);
      return;
    }
    const ul = el('ul');
    items.forEach(it => {
      const li = el('li');
      const a = el('a', null, it.t);
      a.href = it.u; a.target = '_blank'; a.rel = 'noopener noreferrer';
      const m = el('div', 'meta', [it.s, it.d ? prettyDate(it.d) : null].filter(Boolean).join(' · '));
      a.appendChild(m);
      li.appendChild(a); ul.appendChild(li);
    });
    box.appendChild(ul);
    host.appendChild(box);
  });

  $('#feeds-note').textContent = total
    ? `${total} items, primary sources only, from the last refresh.`
    : 'No refresh has run yet — see the note at the foot of the page.';
}

/* ---------------- section: rail ---------------- */

function buildRail() {
  const host = $('#rail');
  host.innerHTML = '';
  RAIL.forEach(g => {
    const box = el('div');
    box.appendChild(el('h3', null, g.h));
    const ul = el('ul');
    g.l.forEach(([t, u]) => {
      const li = el('li');
      const a = el('a', null, t);
      a.href = u; a.target = '_blank'; a.rel = 'noopener noreferrer';
      li.appendChild(a); ul.appendChild(li);
    });
    box.appendChild(ul);
    host.appendChild(box);
  });
}

/* ---------------- chrome ---------------- */

function failCard(msg) {
  const d = el('div', 'fail');
  d.innerHTML = `<b>Not available.</b> ${msg}`;
  return d;
}

function setStamp() {
  const s = $('#stamp');
  const dates = Object.values(H).map(x => x.d[x.d.length - 1]).filter(Boolean).sort();
  const asOf = dates.length ? dates[dates.length - 1] : null;
  const parts = [];
  parts.push(new Date().toLocaleDateString('en-GB', { weekday: 'short', day: 'numeric', month: 'short' }));
  if (asOf) parts.push(`close ${prettyDate(asOf)}`);
  parts.push(LIVE ? 'live' : (STAMP ? 'snapshot' : 'no data'));
  s.innerHTML = parts.map((p, i) => (i === parts.length - 1 ? `<b>${p}</b>` : p)).join(' · ');
}

function renderAll(snapshot) {
  FIT.length = 0;
  buildRead();
  buildGrid('#tape', TAPE);
  buildGrid('#fx', FX);
  buildMovers();
  buildSignals();
  buildCross();
  buildValuation();
  buildThemes();
  buildPolicy(snapshot);
  buildFeeds(snapshot);
  buildRail();
  setStamp();
  requestAnimationFrame(fitAll);
}

function noData() {
  $('#read-list').innerHTML = '';
  const li = el('li', 'empty');
  li.innerHTML = 'No market data reached this page. The live feed and the committed snapshot both failed — everything below the fold still works.';
  $('#read-list').appendChild(li);
}

/* ---------------- boot ---------------- */

async function boot() {
  const btn = $('#refresh');
  btn.setAttribute('data-spin', '');

  /* 1. instant paint from cache, then snapshot */
  const cached = readCache();
  if (cached) { Object.assign(H, cached); LIVE = true; renderAll(null); }

  const snap = await loadSnapshot();
  if (snap) {
    STAMP = snap.generated || null;
    if (!cached && snap.market) { Object.assign(H, snap.market); }
    renderAll(snap);
  } else if (!cached) {
    renderAll(null);
  }

  /* 2. live upgrade in the background */
  try {
    const ok = await loadLive();
    if (ok > 0) { LIVE = true; writeCache(H); renderAll(snap); }
    else if (!Object.keys(H).length) noData();
  } catch {
    if (!Object.keys(H).length) noData();
  }

  btn.removeAttribute('data-spin');
}

$('#refresh').addEventListener('click', () => {
  try { localStorage.removeItem(CACHE_KEY); } catch {}
  for (const k in H) delete H[k];
  boot();
});

/* theme toggle — explicit choice wins over the OS in both directions */
const THEME_KEY = 'vantage.theme';
function applyTheme(t) {
  if (t) document.documentElement.setAttribute('data-theme', t);
  else document.documentElement.removeAttribute('data-theme');
  $('#theme').textContent = t === 'dark' ? 'Light' : t === 'light' ? 'Dark' : 'Theme';
}
try { applyTheme(localStorage.getItem(THEME_KEY)); } catch {}
$('#theme').addEventListener('click', () => {
  const cur = document.documentElement.getAttribute('data-theme');
  const isDark = cur ? cur === 'dark' : matchMedia('(prefers-color-scheme: dark)').matches;
  const next = isDark ? 'light' : 'dark';
  applyTheme(next);
  try { localStorage.setItem(THEME_KEY, next); } catch {}
});

boot();
