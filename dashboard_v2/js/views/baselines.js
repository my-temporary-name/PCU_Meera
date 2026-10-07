// Baseline: what is usual for her, where a week or month stands against it, and how her usual moved through the year.
// Everything shown is read from the Baseline Engine's own windows (values, her usual as of that day, the size of each change); nothing is recomputed here
// except presentation: a z-style position inside her usual range and a few sentences built from those numbers.
import { S, DAY, ms, fmtDate, n1, addDays, monthName } from '../store.js';
import { h, card } from '../ui.js';
import { mount, palette, base, valueAxis, timeAxis, cssVar } from '../charts.js';
import { pointsBlock } from './trace_ui.js';

const LEARN = 14;                       // days of history before the engine trusts her usual
const sel = { tier: 'week', i: 0, m: 'cgm_glucose_reading' };
const GIST = { gist_ok: 'gist worded by the model', gist_retry_ok: 'gist worded by the model after a retry', code_line_early: 'short line written by code: too little history to compare', code_line_quiet: 'short line written by code: nothing material changed', code_line_fallback: 'short line written by code: the model\'s text failed its checks' };
const MN = ['January', 'February', 'March', 'April', 'May', 'June', 'July', 'August', 'September', 'October', 'November', 'December'];

const meas = () => S.baseline_meta.measures;
const mOf = (k) => meas().find((x) => x.key === k);
const wins = (tier = sel.tier) => S.baselines.filter((b) => b.tier === tier).sort((a, b) => a.end.localeCompare(b.end));
const fmt = (m, v) => (v == null ? '—' : n1(v, m.decimals));
const withUnit = (m, v) => `${fmt(m, v)} ${m.unit}`;
const signed = (m, v) => `${v > 0 ? '+' : v < 0 ? '−' : ''}${n1(Math.abs(v), m.decimals)}`;
const learning = (P) => !P || P[0] < LEARN || P[2] == null || P[2] === 0;
const periodWord = () => (sel.tier === 'week' ? 'last week' : 'the previous checkpoint');

// where a value sits relative to her usual range, and whether that is the wrong way for her
function stand(m, w) {
  const v = w.vals[m.key], P = w.prof[m.key];
  if (v == null) return { none: true };
  if (learning(P)) return { learning: true, n: P ? P[0] : 0 };
  const z = (v - P[1]) / P[2];
  const out = Math.abs(z) > 1;
  const dir = z > 0 ? 'above' : 'below';
  const cls = !out ? 'in' : m.adverse ? (dir === m.adverse ? 'bad' : 'good') : 'mid';
  return { v, u: P[1], s: P[2], z, out, dir, cls, n: P[0], pos: Math.max(3, Math.min(97, 50 + (100 * (v - P[1])) / (6 * P[2]))), status: P[4], share: P[5] };
}
const clinicalText = (st) => {
  if (!st || st.status == null) return null;
  const pct = Math.round((st.share || 0) * 100);
  if (st.status === 'normal') return pct >= 15 ? `usually within the clinical range, but outside it on ${pct}% of days` : 'usually within the clinical range';
  return `usually ${st.status.replace(/_/g, ' ')} for the clinical range (${pct}% of days)`;
};

// ------------------------------------------------------------------------------------------------------------------------------------------------------------

export function render(root, [tier, end, measure]) {
  const all = S.baselines;
  if (tier === 'week' || tier === 'month') sel.tier = tier;
  if (measure && mOf(measure)) sel.m = mOf(measure).key;
  const ws0 = wins();
  sel.i = Math.max(0, ws0.findIndex((w) => w.end === end));
  if (!end || ws0[sel.i].end !== end) sel.i = ws0.length - 1;

  root.append(h('div', { class: 'page-head' }, h('div', {}, h('h1', {}, 'Her baseline'),
    h('p', {}, 'What is usual for her, where this week or month stands against it, and how her usual moved through the year. Every number is computed by code from her own earlier days; there is no population average anywhere on this page.'))));

  // ---- what a baseline is --------------------------------------------------------------------------------------------------------------------------------
  const mini = (kind) => h('span', { class: `bl-mini ${kind}` }, h('i', { class: 'band' }), h('i', { class: 'tick' }), kind === 'dot' ? h('i', { class: 'dotm' }) : null);
  const defBox = (sw, title, text) => h('div', { class: 'cl-key bl-defbox' }, sw, h('div', {}, h('b', {}, title), h('div', { class: 'muted' }, text)));
  root.append(h('div', { class: 'bl-defs' },
    defBox(mini('usual'), 'Her usual', 'The middle value (median) of her own earlier days for that measure. It is her normal, whatever the textbook says.'),
    defBox(mini('range'), 'Her usual range', 'The band of about one standard deviation around her usual: how much she normally varies. Inside it, nothing is unusual.'),
    defBox(mini('dot'), 'A window', 'A week (7 days, one ending every day) or a month checkpoint (30 days). Her usual is computed only from the days before the window.'),
    defBox(h('span', { class: 'bl-mini learn' }, h('i', {})), 'Learning period', 'For the first 14 days there is too little history to know her usual, so nothing is judged yet.')));

  // ---- controls --------------------------------------------------------------------------------------------------------------------------------------------
  const holder = { score: h('div', {}), summary: h('div', {}), chartHead: h('div', {}) };
  const label = h('div', { class: 'bl-when' }), totals = h('div', { class: 'bl-totals muted' });
  const slider = h('input', { type: 'range', class: 'bl-slider', min: 0, max: ws0.length - 1, value: sel.i, oninput: (e) => setIndex(+e.target.value) });
  const seg = h('div', { class: 'seg' }, [['week', 'Weeks'], ['month', 'Months']].map(([t, lb]) => h('button', { type: 'button', class: sel.tier === t ? 'on' : '', onclick: () => setTier(t) }, lb)));
  const btn = (txt, fn, title) => h('button', { type: 'button', class: 'bl-btn', title, onclick: fn }, txt);
  const jump = (dir) => { const ws = wins(); for (let k = sel.i + dir; k >= 0 && k < ws.length; k += dir) if (ws[k].notable) return setIndex(k); };
  const ctl = h('div', { class: 'bl-ctl' },
    h('div', { class: 'bl-ctl-top' }, seg, h('div', { class: 'bl-nav' }, btn('◀', () => setIndex(sel.i - 1), 'Previous'), label, btn('▶', () => setIndex(sel.i + 1), 'Next')),
      h('div', { class: 'bl-jump' }, btn('◀ notable', () => jump(-1), 'Previous notable window'), btn('notable ▶', () => jump(1), 'Next notable window'), btn('latest', () => setIndex(wins().length - 1), 'Jump to the latest window'))),
    slider, totals);
  root.append(ctl);

  // ---- scorecard + summary -----------------------------------------------------------------------------------------------------------------------------
  root.append(card('Where she stands in this window', 'The big number is this window. Under it: her usual, how much she normally varies, and a bar where the shaded middle third is her usual range and the dot is this window. Click a measure to follow it through the year below.', h('div', { class: 'stack', style: { gap: '14px' } }, holder.score,
    h('div', { class: 'bl-legend' }, h('span', { class: 'lg in' }, h('i', {}), 'within her usual range'), h('span', { class: 'lg bad' }, h('i', {}), 'outside it, the wrong way for her'), h('span', { class: 'lg good' }, h('i', {}), 'outside it, the other way')))));
  root.append(holder.summary);

  // ---- the measure over the year -----------------------------------------------------------------------------------------------------------------------
  const chartEl = h('div', { class: 'chart', style: { height: '400px', cursor: 'pointer' } });
  const refToggle = h('label', { class: 'toggle' }, h('input', { type: 'checkbox', onchange: (e) => { sel.ref = e.target.checked; drawChart(); } }), 'show the clinical reference range');
  const picker = h('div', { class: 'bl-picker' });
  root.append(card('How her baseline moved', null, h('div', { class: 'stack', style: { gap: '12px' } }, picker, holder.chartHead, chartEl,
    h('div', { class: 'bl-legend' }, h('span', { class: 'lg val' }, h('i', {}), 'the window\'s value'), h('span', { class: 'lg usual' }, h('i', {}), 'her usual (median of the earlier days)'), h('span', { class: 'lg rng' }, h('i', {}), 'her usual range'),
      h('span', { class: 'lg note' }, h('i', {}), 'notable window'), h('span', { class: 'lg learn' }, h('i', {}), 'learning period'), refToggle))));

  root.append(driftCard());

  // ---- behaviour ---------------------------------------------------------------------------------------------------------------------------------------------
  let chart = null;
  const curW = () => wins()[sel.i];
  function whenText(w) {
    return sel.tier === 'week' ? `Week ending ${fmtDate(w.end, { dow: true, year: true })}` : `Month ending ${fmtDate(w.end, { year: true })}`;
  }
  function setIndex(i) {
    const ws = wins(); sel.i = Math.max(0, Math.min(ws.length - 1, i)); slider.value = sel.i;
    drawWindow(); updateMarker(); remember();
  }
  function setTier(t) {
    const end = curW().end; sel.tier = t;
    const ws = wins(); let k = ws.length - 1; while (k > 0 && ws[k].end > end) k--;
    sel.i = k; slider.max = ws.length - 1; slider.value = k;
    seg.querySelectorAll('button').forEach((b, j) => b.classList.toggle('on', ['week', 'month'][j] === t));
    drawWindow(); drawChart(); remember();
  }
  function remember() { try { history.replaceState(null, '', `#/baselines/${sel.tier}/${curW().end}/${sel.m}`); } catch (e) { /* ignore */ } }
  function selectMeasure(k) { sel.m = k; drawWindow(); drawChart(); remember(); }

  function drawWindow() {
    const w = curW();
    label.replaceChildren(h('b', {}, whenText(w)), h('span', { class: 'muted' }, sel.tier === 'week' ? `${fmtDate(w.start)} → ${fmtDate(w.end)}` : `last 30 days: ${fmtDate(addDays(w.end, -29))} → ${fmtDate(w.end)}`));
    // one grid of cards, each tagged with its domain
    holder.score.replaceChildren(h('div', { class: 'bl-cards' }, meas().map((m) => scoreCard(m, w))));
    // picker chips
    picker.replaceChildren(h('span', { class: 'muted' }, 'Measure:'), ...meas().map((m) => h('button', { type: 'button', class: `bl-chip ${m.key === sel.m ? 'on' : ''}`, onclick: () => selectMeasure(m.key) }, m.label)));
    drawTotals();
    drawSummary(w);
    drawChartHead(w);
  }

  function drawTotals() {
    const ws = wins(), word = sel.tier === 'week' ? 'week windows' : 'month checkpoints';
    const by = (f) => ws.filter(f).length;
    totals.textContent = `${n1(ws.length, 0)} ${word} · ${by((x) => x.notable)} notable · ${by((x) => x.reliable)} reliable · ${by((x) => (x.status || '').startsWith('gist'))} with a gist worded by the model, the rest short lines written by code`;
  }

  function scoreCard(m, w) {
    const st = stand(m, w), v = w.vals[m.key], prev = w.prev[m.key], tag = w.tags[m.key];
    const pieces = [];
    if (st.none) pieces.push(h('div', { class: 'bl-learn' }, 'No data in this window'));
    else if (st.learning) pieces.push(h('div', { class: 'bl-learn' }, `Still learning her usual (${st.n} day${st.n === 1 ? '' : 's'} so far)`));
    else {
      pieces.push(h('div', { class: `bl-bar ${st.cls}`, title: `Her usual range is the shaded middle third. This window is ${st.out ? `${Math.abs(st.z).toFixed(1)} standard deviations ${st.dir}` : 'inside'} it.` },
        h('i', { class: 'band' }), h('i', { class: 'tick' }), h('i', { class: 'dot', style: `left:${st.pos}%` })));
      pieces.push(h('div', { class: 'bl-scale', title: 'The two numbers are the ends of her usual range: her usual minus and plus one spread' }, h('span', { style: 'left:33.3%' }, fmt(m, m.unit === '%' ? Math.max(0, st.u - st.s) : st.u - st.s)), h('span', { class: 'mid', style: 'left:50%' }, fmt(m, st.u)), h('span', { style: 'left:66.7%' }, fmt(m, m.unit === '%' ? Math.min(100, st.u + st.s) : st.u + st.s))));
      pieces.push(h('div', { class: 'bl-usual' }, h('span', {}, `usual ${fmt(m, st.u)}`), h('span', { class: 'muted' }, `± ${fmt(m, st.s)} · ${st.n} days`)));
      pieces.push(h('div', { class: `bl-status ${st.cls}` }, st.out ? `${Math.abs(st.z) >= 2 ? 'well ' : ''}${st.dir} her usual range` : 'within her usual range'));
    }
    if (prev != null && v != null) {
      const d = v - prev, noCmp = !tag || tag[0] === 'not_enough_data', flat = tag && tag[0] === 'flat';
      const arrow = d > 0 ? '▲' : d < 0 ? '▼' : '•';
      if (noCmp) pieces.push(h('div', { class: 'bl-vs' }, h('span', { class: 'bl-arrow' }, '•'), `not enough history yet to compare with ${periodWord()}`));
      else pieces.push(h('div', { class: 'bl-vs' }, h('span', { class: 'bl-arrow' }, flat ? '•' : arrow), flat ? `about the same as ${periodWord()}` : `${signed(m, d)} ${m.unit} vs ${periodWord()} · ${tag[1]}`));
    }
    const ct = clinicalText(st.learning ? null : st);
    if (ct) pieces.push(h('div', { class: 'bl-clin', title: 'How her usual compares with the clinical reference range' }, ct));
    return h('button', { type: 'button', class: `bl-card ${m.key === sel.m ? 'on' : ''}`, onclick: () => selectMeasure(m.key) },
      h('div', { class: `bl-dtag d-${m.domain.split(' ')[0].toLowerCase()}` }, m.domain), h('div', { class: 'bl-name' }, m.label), h('div', { class: 'bl-val num' }, fmt(m, v), h('small', {}, ' ' + m.unit)), ...pieces);
  }

  function drawSummary(w) {
    const g = w.glucose || {};
    const chip = (t, c) => h('span', { class: `chip ${c || ''}` }, t);
    const tiles = [['Average glucose', g.mean != null ? `${n1(g.mean, 0)} mg/dL` : '—'], ['Estimated HbA1c (GMI)', g.gmi_pct != null ? `${n1(g.gmi_pct, 1)}%` : '—'], ['Time in range', g.tir_pct != null ? `${n1(g.tir_pct, 1)}%` : '—'],
      ['Above range', g.tar_pct != null ? `${n1(g.tar_pct, 1)}%` : '—'], ['Below range', g.tbr_pct != null ? `${n1(g.tbr_pct, 1)}%` : '—'], ['Variability', g.cv_pct != null ? `${n1(g.cv_pct, 1)}%` : '—'],
      ['Lowest – highest', g.min_value != null ? `${n1(g.min_value, 0)} – ${n1(g.max_value, 0)}` : '—'], ['Readings', g.n_readings != null ? `${n1(g.n_readings, 0)} · ${n1(g.completeness_pct, 0)}% complete` : '—']];
    holder.summary.replaceChildren(card(`What the engine wrote for this ${sel.tier}`, whenText(w), h('div', { class: 'stack', style: { gap: '14px' } },
      h('div', { class: 'row', style: { gap: '8px', flexWrap: 'wrap' } }, w.notable ? chip('notable', 'bad') : chip('ordinary', 'teal'), w.reliable ? chip('reliable', 'ok') : chip('less reliable', 'warn'), chip(`confidence ${w.confidence}`), h('span', { class: 'chip', title: 'How the gist below was produced' }, GIST[w.status] || (w.status || '').replace(/_/g, ' '))),
      h('div', { class: 'bl-head' }, w.headline || '—'),
      w.sentences.length ? h('ul', { class: 'points' }, w.sentences.map((x) => h('li', {}, x))) : null,
      w.notable && w.reason ? h('div', { class: 'bl-why' }, h('b', {}, 'Why it is notable: '), w.reason) : null,
      h('div', { class: 'bl-gtiles' }, tiles.map(([k, v]) => h('div', { class: 'bl-gt' }, h('span', { class: 'muted' }, k), h('b', { class: 'num' }, v)))),
      w.deviation ? h('details', { class: 'bl-details' }, h('summary', {}, 'Everything the code listed for this window'), h('div', { class: 'kv-block', style: { marginTop: '8px' } }, pointsBlock(w.deviation))) : null)));
  }

  // ---- the big chart ------------------------------------------------------------------------------------------------------------------------------------
  function series(m) {
    const ws = wins();
    const lo = [], rng = [], usual = [], val = [], out = [];
    ws.forEach((w) => {
      const t = ms(w.end), P = w.prof[m.key], ok = !learning(P), v = w.vals[m.key];
      lo.push([t, ok ? P[1] - P[2] : null]); rng.push([t, ok ? 2 * P[2] : null]); usual.push([t, ok ? P[1] : null]); val.push([t, v]);
      const st = stand(m, w);
      if (st.out) out.push({ value: [t, v], cls: st.cls });
    });
    return { ws, lo, rng, usual, val, out };
  }
  function chartHead(w, S2, m) {
    const ok = S2.ws.filter((x) => !learning(x.prof[m.key]));
    if (!ok.length) return h('div', { class: 'muted' }, 'Not enough history yet.');
    const a = ok[0].prof[m.key][1], b = ok[ok.length - 1].prof[m.key][1];
    const d = b - a, st = stand(m, w);
    const move = Math.abs(d) < (ok[ok.length - 1].prof[m.key][2] || 0) * 0.25 ? 'has barely moved' : `${d > 0 ? 'rose' : 'fell'} from ${fmt(m, a)} to ${fmt(m, b)} ${m.unit}`;
    return h('div', { class: 'bl-sentence' }, h('b', {}, `${m.label}: `), `her usual ${move} between ${fmtDate(ok[0].end, { year: true })} and ${fmtDate(ok[ok.length - 1].end, { year: true })}.`,
      st.learning || st.none ? null : ` In this ${sel.tier} it was ${withUnit(m, st.v)} — ${st.out ? `${Math.abs(st.z) >= 2 ? 'well ' : ''}${st.dir}` : 'within'} her usual range of ${fmt(m, st.u - st.s)} to ${fmt(m, st.u + st.s)}.`);
  }
  function drawChartHead(w) { const m = mOf(sel.m); holder.chartHead.replaceChildren(chartHead(w, series(m), m)); }

  function option() {
    const m = mOf(sel.m), p = palette(), S2 = series(m), ws = S2.ws, w = curW();
    const teal = cssVar('--primary'), bad = cssVar('--bad'), good = cssVar('--orange'), warn = cssVar('--ep');
    const firstOk = ws.find((x) => !learning(x.prof[m.key]));
    const monthStarts = []; for (let d = new Date(Date.UTC(+S.first.slice(0, 4), +S.first.slice(5, 7), 1)); d.getTime() <= ms(S.last); d = new Date(Date.UTC(d.getUTCFullYear(), d.getUTCMonth() + 1, 1))) monthStarts.push(d.getTime());
    const years = [...new Set(ws.map((x) => x.end.slice(0, 4)))];
    const yearBands = years.map((y, i) => [{ xAxis: Math.max(ms(S.first), ms(`${y}-01-01`)), name: y, itemStyle: { color: i % 2 ? 'rgba(120,140,135,.10)' : 'rgba(120,140,135,.03)' }, label: { show: true, position: 'insideTop', color: p.muted, fontSize: 13, fontWeight: 700, distance: 6 } }, { xAxis: Math.min(ms(S.last) + DAY, ms(`${+y + 1}-01-01`)) }]);
    const noteAreas = sel.tier === 'week' ? ws.filter((x) => x.notable).map((x) => [{ xAxis: ms(x.end) - DAY / 2 }, { xAxis: ms(x.end) + DAY / 2 }]) : ws.filter((x) => x.notable).map((x) => [{ xAxis: ms(x.end) - 6 * DAY }, { xAxis: ms(x.end) + 6 * DAY }]);
    const learnArea = firstOk ? [[{ xAxis: ms(ws[0].start), name: 'learning her usual', itemStyle: { color: 'rgba(120,140,135,.16)' }, label: { show: true, position: 'insideTop', color: p.muted, fontSize: 11.5, distance: 28 } }, { xAxis: ms(firstOk.end) }]] : [];
    const refLines = sel.ref && m.ref ? m.ref.filter((x) => x != null).map((y) => ({ yAxis: y, lineStyle: { color: warn, type: 'dashed', width: 1.5 }, label: { show: true, formatter: `reference ${n1(y, m.decimals)}`, color: warn, position: 'insideEndTop', fontSize: 11 } })) : [];
    return {
      animationDuration: 300,
      grid: { left: 8, right: 22, top: 48, bottom: 48, containLabel: true },
      tooltip: { ...base().tooltip, trigger: 'axis', axisPointer: { type: 'line', lineStyle: { color: p.muted, type: 'dashed' } },
        formatter: (ps) => { const q = ps.find((x) => x.seriesId === 'val'); if (!q) return ''; const x = ws[q.dataIndex]; const st = stand(m, x), tag = x.tags[m.key];
          const lines = [`<b>${whenText(x)}</b>`, `${m.label}: <b>${withUnit(m, x.vals[m.key])}</b>`];
          if (st.learning) lines.push('<span style="opacity:.7">still learning her usual</span>');
          else if (!st.none) { lines.push(`her usual: ${fmt(m, st.u)} (range ${fmt(m, st.u - st.s)} – ${fmt(m, st.u + st.s)}, ${st.n} days)`); lines.push(st.out ? `${Math.abs(st.z) >= 2 ? 'well ' : ''}${st.dir} her usual range` : 'within her usual range'); }
          if (tag && tag[0] !== 'flat' && tag[0] !== 'not_enough_data') lines.push(`vs ${periodWord()}: ${tag[0]} · ${tag[1]}`);
          if (x.notable) lines.push(`<span style="color:${bad}">notable: ${x.reason || ''}</span>`);
          lines.push('<span style="opacity:.6">click to select</span>'); return lines.join('<br>'); } },
      xAxis: { ...timeAxis({ min: ms(S.first), max: ms(S.last) + DAY }), axisLabel: { show: false }, splitLine: { show: false } },
      yAxis: { ...valueAxis({ scale: true, name: m.unit, nameTextStyle: { color: p.muted, align: 'left' } }), splitLine: { lineStyle: { color: p.line, type: [4, 6], opacity: 0.5 } } },
      series: [
        { id: 'lo', type: 'line', data: S2.lo, stack: 'rng', symbol: 'none', lineStyle: { opacity: 0 }, silent: true, tooltip: { show: false }, markArea: { silent: true, data: yearBands } },
        { id: 'rng', type: 'line', data: S2.rng, stack: 'rng', symbol: 'none', lineStyle: { opacity: 0 }, areaStyle: { color: teal, opacity: 0.2 }, silent: true, tooltip: { show: false } },
        { id: 'usual', type: 'line', data: S2.usual, symbol: 'none', lineStyle: { color: teal, width: 1.6, type: 'dashed', opacity: 0.9 }, silent: true, tooltip: { show: false }, connectNulls: false,
          markLine: { silent: true, symbol: 'none', animation: false, label: { show: false }, lineStyle: { color: p.ink2, width: 1.3, type: 'solid', opacity: 0.42 }, data: monthStarts.map((t) => ({ xAxis: t })) } },
        { id: 'val', type: 'line', data: S2.val, symbol: sel.tier === 'month' ? 'circle' : 'none', symbolSize: 9, showSymbol: sel.tier === 'month', lineStyle: { color: p.ink, width: 2.2 }, itemStyle: { color: p.ink }, z: 4,
          markArea: { silent: true, data: [...learnArea, ...noteAreas.map((a) => a.map((o, k) => (k === 0 ? { ...o, itemStyle: { color: 'rgba(238,148,165,.16)' } } : o)))] },
          markLine: { silent: true, symbol: 'none', animation: false, data: [{ xAxis: ms(w.end), lineStyle: { color: p.ink, width: 1.5, type: 'solid', opacity: 0.8 }, label: { show: true, formatter: fmtDate(w.end), color: p.ink, position: 'end', fontSize: 11.5, fontWeight: 650 } }, ...refLines] } },
        { id: 'out', type: 'scatter', z: 5, silent: true, tooltip: { show: false }, symbolSize: sel.tier === 'month' ? 12 : 7, data: S2.out.map((o) => ({ value: o.value, itemStyle: { color: o.cls === 'bad' ? bad : o.cls === 'good' ? good : warn, opacity: 0.95, borderColor: p.surface, borderWidth: 1 } })) },
      ],
    };
  }
  let lastSig = null;
  function placeMonths() {
    if (!chart) return;
    const p = palette(), hgt = chart.getHeight(), items = [];
    for (let d = new Date(Date.UTC(+S.first.slice(0, 4), +S.first.slice(5, 7) - 1, 1)); d.getTime() <= ms(S.last); d = new Date(Date.UTC(d.getUTCFullYear(), d.getUTCMonth() + 1, 1))) {
      const t0 = Math.max(d.getTime(), ms(S.first)), t1 = Math.min(Date.UTC(d.getUTCFullYear(), d.getUTCMonth() + 1, 1), ms(S.last) + DAY);
      const x0 = chart.convertToPixel({ xAxisIndex: 0 }, t0), x1 = chart.convertToPixel({ xAxisIndex: 0 }, t1);
      if (x0 == null || x1 == null || Number.isNaN(x0) || Number.isNaN(x1)) continue;
      const jan = d.getUTCMonth() === 0;
      items.push({ type: 'text', silent: true, x: (x0 + x1) / 2, y: hgt - 38, style: { text: MN[d.getUTCMonth()] + (jan || items.length === 0 ? `\n${d.getUTCFullYear()}` : ''), fill: p.ink2, font: `600 12px ${p.font || 'sans-serif'}`, textAlign: 'center', lineHeight: 14 } });
    }
    const sig = items.map((i) => Math.round(i.x)).join(',');
    if (sig === lastSig) return;
    lastSig = sig; chart.setOption({ graphic: { elements: items } });
  }
  function drawChart() {
    lastSig = null;
    if (!chart) {
      chart = mount(chartEl, option());
      chart.on('finished', placeMonths);
      chart.getZr().on('click', (e) => {
        const pt = [e.offsetX, e.offsetY]; if (!chart.containPixel('grid', pt)) return;
        const t = chart.convertFromPixel({ xAxisIndex: 0, yAxisIndex: 0 }, pt)[0], ws = wins(); let best = 0;
        ws.forEach((x, k) => { if (Math.abs(ms(x.end) - t) < Math.abs(ms(ws[best].end) - t)) best = k; });
        setIndex(best);
      });
    } else chart.setOption(option(), true);
  }
  function updateMarker() {
    if (!chart) return;
    const p = palette(), w = curW(), m = mOf(sel.m);
    const ref = sel.ref && m.ref ? m.ref.filter((x) => x != null).map((y) => ({ yAxis: y, lineStyle: { color: cssVar('--warn'), type: 'dashed', width: 1.5 }, label: { show: true, formatter: `reference ${n1(y, m.decimals)}`, color: cssVar('--warn'), position: 'insideEndTop', fontSize: 11 } })) : [];
    chart.setOption({ series: [{ id: 'val', markLine: { silent: true, symbol: 'none', animation: false, data: [{ xAxis: ms(w.end), lineStyle: { color: p.ink, width: 1.5, type: 'solid', opacity: 0.8 }, label: { show: true, formatter: fmtDate(w.end), color: p.ink, position: 'end', fontSize: 11.5, fontWeight: 650 } }, ...ref] } }] });
  }

  drawWindow();
  setTimeout(drawChart, 0);
  return [['Pipeline', '#/pipeline'], ['Her baseline']];
}

// ------------------------------------------------------------------------------------------------------------------------------------------------------------
// How her usual shifted: her usual as known at each month checkpoint, shaded by the drift from where it started.
function driftCard() {
  const months = wins('month');
  const first = (m) => months.find((w) => !learning(w.prof[m.key]));
  const head = h('tr', {}, h('th', {}, 'Measure'), months.map((w, i) => h('th', { class: 'r' }, h('span', {}, MN[+w.end.slice(5, 7) - 1].slice(0, 3)), h('small', {}, w.end.slice(0, 4)))), h('th', { class: 'r' }, 'Change'));
  const rows = meas().map((m) => {
    const f = first(m), P0 = f ? f.prof[m.key] : null;
    const cells = months.map((w) => {
      const P = w.prof[m.key];
      if (learning(P)) return h('td', { class: 'r muted' }, '·');
      const d = P0 ? (P[1] - P0[1]) / P0[2] : 0, a = Math.min(60, Math.abs(d) * 34);
      const dir = d > 0 ? 'above' : 'below', cls = Math.abs(d) < 0.25 ? '' : m.adverse ? (dir === m.adverse ? 'bad' : 'good') : 'mid';
      const colr = cls === 'bad' ? '--bad' : cls === 'good' ? '--orange' : '--ep';
      return h('td', { class: 'r num bl-dcell', title: `${m.label}: her usual as of ${fmtDate(w.end, { year: true })} was ${withUnit(m, P[1])} (range ${fmt(m, P[1] - P[2])} – ${fmt(m, P[1] + P[2])}, from ${P[0]} days)`, style: cls ? `background: color-mix(in srgb, var(${colr}) ${a}%, transparent)` : '' }, fmt(m, P[1]));
    });
    const last = months.filter((w) => !learning(w.prof[m.key])).pop(), d = last && P0 ? last.prof[m.key][1] - P0[1] : null;
    const small = d != null && Math.abs(d) < P0[2] * 0.25;
    return h('tr', {}, h('th', { scope: 'row' }, h('b', {}, m.label), h('small', {}, m.unit)), cells, h('td', { class: 'r num' }, d == null ? '—' : small ? h('span', { class: 'muted' }, 'about the same') : `${d > 0 ? '▲' : '▼'} ${signed(m, d)}`));
  });
  return card('How her usual shifted, checkpoint by checkpoint', 'Each cell is her usual (median of her earlier days) as known at that month checkpoint. Shading shows how far it has drifted from where it started: rose = moved the wrong way for her, orange = the other way, blank = about the same, · = still learning her usual.',
    h('div', { class: 'table-wrap' }, h('table', { class: 'tbl bl-drift' }, h('thead', {}, head), h('tbody', {}, rows))));
}
