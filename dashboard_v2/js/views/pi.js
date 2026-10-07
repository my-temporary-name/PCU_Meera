// PI: weekly memories and the long-term notes. #/pi is the overview; #/pi/<relationship key> is one relationship.
import { S, fmtDate, n1, monthName } from '../store.js';
import { h, card, table, stat } from '../ui.js';
import { mount, palette, base, valueAxis, cssVar } from '../charts.js';
import { labelChip, countBar, STATUS_COLOR } from './trace_ui.js';
import { caseCard } from './shared.js';

const CODE = { insufficient: 0, not_supported: 1, suggestive: 2, supported: 3 };
const short = (m) => `${m.phrase} → ${m.outcome}`;
const enc = (k) => encodeURIComponent(k);

const MN = ['January', 'February', 'March', 'April', 'May', 'June', 'July', 'August', 'September', 'October', 'November', 'December'];
const isoMon = (w) => { const [y, n] = w.split('-W').map(Number); const j4 = Date.UTC(y, 0, 4); const dow = (new Date(j4).getUTCDay() + 6) % 7; return j4 - dow * 864e5 + (n - 1) * 7 * 864e5; };
const dayTxt = (t) => fmtDate(new Date(t).toISOString().slice(0, 10), { year: true });
// month names centred under their weeks and a clear line at every month boundary (a week belongs to the month in which most of its days fall)
function attachMonths(chart, weeks, top, bottom) {
  const monthOf = weeks.map((w) => { const d = new Date(isoMon(w) + 3 * 864e5); return d.getUTCFullYear() * 12 + d.getUTCMonth(); });
  let lastSig = null;
  const place = () => {
    const hgt = chart.getHeight(), n = weeks.length, x0 = chart.convertToPixel({ xAxisIndex: 0 }, 0), x1 = chart.convertToPixel({ xAxisIndex: 0 }, n - 1);
    if (x0 == null || x1 == null || Number.isNaN(x0) || Number.isNaN(x1)) return;
    const cw = (x1 - x0) / (n - 1), pal = palette(), els = [];
    let start = 0;
    for (let c = 1; c <= n; c++) {
      if (c === n || monthOf[c] !== monthOf[start]) {
        const left = x0 + start * cw - cw / 2, right = x0 + (c - 1) * cw + cw / 2, mi = monthOf[start] % 12, yr = Math.floor(monthOf[start] / 12);
        els.push({ type: 'text', silent: true, x: (left + right) / 2, y: hgt - bottom + 8, style: { text: ((right - left) < 72 ? MN[mi].slice(0, 3) : MN[mi]) + (mi === 0 || start === 0 ? `\n${yr}` : ''), fill: pal.ink2, font: `600 12px ${pal.font || 'sans-serif'}`, textAlign: 'center', lineHeight: 14 } });
        if (c < n) els.push({ type: 'line', silent: true, z: 20, shape: { x1: right, y1: top, x2: right, y2: hgt - bottom }, style: { stroke: pal.ink2, lineWidth: 1.4, opacity: 0.55 } });
        start = c;
      }
    }
    const sig = els.map((e) => Math.round(e.x ?? e.shape.x1)).join(',');
    if (sig === lastSig) return;
    lastSig = sig; chart.setOption({ graphic: { elements: els } });
  };
  chart.on('finished', place);
}


function rulesCard() {
  const sw = (c, t, d) => h('div', { class: 'wk-k' }, h('i', { style: `background: var(${c})` }), h('div', {}, h('b', {}, t), h('span', { class: 'muted' }, d)));
  const row = (a, b, c) => h('tr', {}, h('td', {}, a), h('td', {}, b), h('td', {}, c));
  return card('How to read the chart: the rules', 'A square\'s colour is judged on its own and has no waiting period; durations apply only to a note\'s status (the ▲ markers).',
    h('div', { class: 'wk-rules' },
      h('div', { class: 'wk-col' }, h('div', { class: 'ex-k' }, '1. The colour of a square (one week)'),
        h('p', { class: 'wk-p' }, 'Each week is judged on its own from that week\'s 7 daily Evidence labels, against a fixed threshold:'),
        sw('--ok', 'Green: supported', 'at least 5 of the 7 days were supported'),
        sw('--warn', 'Amber: suggestive', 'not green, but at least 5 days were supported or suggestive'),
        sw('--line', 'Grey: insufficient or not tracked yet', 'at least 5 days had too little history, or the note did not exist yet'),
        sw('--low', 'Blue: not supported', 'none of the above: it was tested and the link did not show up'),
        h('p', { class: 'wk-p muted' }, 'There is no "must stay N weeks" rule: a relationship can be green one week and blue the next. The 5-of-7 threshold is fixed (a partial week at the edge of the data is scaled in proportion). Whether a given day counts as supported depends on the data, because it comes from the daily statistical test.')),
      h('div', { class: 'wk-col' }, h('div', { class: 'ex-k' }, '2. The status of a note (the ▲ markers)'),
        h('p', { class: 'wk-p' }, 'The status changes only after a run of decisive weeks (green or blue). These durations are static placeholder values from the spec, never tuned to produce statuses:'),
        h('table', { class: 'tbl wk-tbl' }, h('thead', {}, h('tr', {}, h('th', {}, 'From'), h('th', {}, 'To'), h('th', {}, 'What it takes'))),
          h('tbody', {}, row('candidate', 'supported', '2 consecutive supported (green) weeks'), row('supported', 'weakened', '2 consecutive not-supported (blue) weeks'),
            row('weakened', 'retracted', '6 more not-supported weeks, or the contrary flag on 5 days a week for 4 weeks'), row('weakened', 'supported', '2 consecutive supported weeks'), row('retracted', 'candidate', '2 consecutive supported weeks'))),
        h('p', { class: 'wk-p muted' }, 'A run is reset by a week of the opposite colour. Amber and grey weeks neither promote nor demote nor reset a count. A relationship whose placebo test fired on more than half of the days cannot be promoted. A candidate has no path to weakened, so a long blue stretch on a candidate changes nothing.'))));
}

export function render(root, [key, wk]) {
  if (key && key !== 'week') return detail(root, key);
  const P = S.pi;
  const fin = {};
  P.memories.forEach((m) => { fin[m.status] = (fin[m.status] || 0) + 1; });
  const versions = P.memories.reduce((a, m) => a + m.versions.length, 0);
  root.append(h('div', { class: 'page-head' }, h('div', {}, h('h1', {}, 'PI: what keeps coming up'), h('p', {}, 'Every version is put into its calendar week. Each week, PI looks at how well her own history supports every relationship that appeared, and keeps a long-term note for each with a status: candidate, supported, weakened or retracted.'))));
  root.append(h('div', { class: 'grid g3' }, stat('Weekly jobs', P.weeks.length), stat('Relationships with a note', P.memories.length), stat('Note versions written', versions)));
  root.append(card('Status of the notes at the end', null, countBar(Object.entries(fin).map(([k, n]) => ({ label: k, n, color: STATUS_COLOR[k] })))));

  // heatmap
  const mems = [...P.memories].sort((a, b) => a.created_week.localeCompare(b.created_week) || a.key.localeCompare(b.key));
  const weeks = P.weeks.map((w) => w.week), monOf = weeks.map(isoMon);
  const TOP = 8, BOTTOM = 52;
  const el = h('div', { class: 'chart', style: { height: `${mems.length * 24 + TOP + BOTTOM + 40}px` } });
  root.append(card('Weekly label of every relationship', 'One row for each relationship PI keeps a note on, one column for each week of the year (Monday to Sunday), grouped by month. A square\'s colour is that week\'s label and ▲ marks the week the note changed status; both are explained in the rules card below the chart. Click a row to open its history.', el));
  root.append(rulesCard());
  setTimeout(() => {
    const p = palette();
    const cells = [], marks = [];
    mems.forEach((m, r) => {
      const have = new Map(m.weekly_labels.map((x) => [x[0], x]));
      weeks.forEach((w, c) => { const x = have.get(w); cells.push(x ? [c, r, CODE[x[1]] ?? 0, x[1], x[2], x[3]] : [c, r, 0, 'not_tracked', 0, 0]); });
      m.status_history.forEach((t) => { const c = weeks.indexOf(t.week); if (c >= 0) marks.push({ value: [c, r], t, m }); });
    });
    const chart = mount(el, base({
      grid: { left: 8, right: 14, top: TOP, bottom: BOTTOM, containLabel: true },
      tooltip: { ...base().tooltip, trigger: 'item', formatter: (q) => {
        const c = q.value[0], when = `Week of ${dayTxt(monOf[c])} (${weeks[c]})`;
        if (q.seriesType !== 'heatmap') return `<b>${short(q.data.m)}</b><br>${when}<br>status changed: ${q.data.t.from} → ${q.data.t.to}`;
        const lab = q.value[3];
        return `<b>${short(mems[q.value[1]])}</b><br>${when}<br>${lab === 'not_tracked' ? 'not tracked yet: the relationship had no label this week' : `${lab.replace(/_/g, ' ')} · her history backed it on ${q.value[4]} of ${q.value[5]} days`}`; } },
      xAxis: { type: 'category', data: weeks, axisLabel: { show: false }, axisTick: { show: false }, axisLine: { show: false }, splitArea: { show: false } },
      yAxis: { type: 'category', inverse: true, data: mems.map((m) => short(m)), axisLabel: { color: p.ink2, width: 430, overflow: 'truncate', fontSize: 11 }, axisLine: { show: false }, axisTick: { show: false } },
      visualMap: { show: false, type: 'piecewise', orient: 'horizontal', left: 'center', bottom: 0, itemWidth: 14, itemHeight: 14, textStyle: { color: p.ink2 }, pieces: [{ value: 3, label: 'supported', color: cssVar('--ok') }, { value: 2, label: 'suggestive', color: cssVar('--warn') }, { value: 1, label: 'not supported', color: cssVar('--low') }, { value: 0, label: 'insufficient / not tracked yet', color: p.line }], dimension: 2 },
      series: [{ type: 'heatmap', data: cells, itemStyle: { borderColor: p.surface, borderWidth: 1, borderRadius: 2 } },
        { type: 'scatter', symbol: 'triangle', symbolSize: 11, data: marks, itemStyle: { color: p.ink, borderColor: p.surface, borderWidth: 1 }, z: 5 }],
    }));
    attachMonths(chart, weeks, TOP, BOTTOM);
    chart.on('click', (q) => { const m = q.seriesType === 'heatmap' ? mems[q.value[1]] : q.data.m; location.hash = `#/pi/${enc(m.key)}`; });
  }, 0);

  root.append(card('The long-term notes', 'Latest version of each. Click one for its whole history.', h('div', { class: 'itemlist' }, mems.map((m) => {
    const v = m.versions[m.versions.length - 1];
    return h('a', { class: 'pnote', href: `#/pi/${enc(m.key)}`, style: { color: 'var(--ink)', borderLeftColor: STATUS_COLOR[m.status] } },
      h('div', { class: 'row', style: { gap: '8px' } }, labelChip(m.status), h('b', {}, short(m)), h('span', { class: 'muted' }, `${m.versions.length} version${m.versions.length === 1 ? '' : 's'} · seen on ${m.counters.case_days} day${m.counters.case_days === 1 ? '' : 's'}`)),
      h('div', { class: 'assoc' }, v.association), v.situations ? h('div', { class: 'sit' }, h('b', {}, 'Situations noted: '), v.situations) : null);
  }))));

  root.append(card('Week by week', 'What each calendar week received and what PI wrote',
    table([{ label: 'Week', render: (w) => h('b', {}, w.week) }, { label: 'Findings', right: true, render: (w) => w.entries }, { label: 'Cases', render: (w) => (w.cases.length ? w.cases.map((c, i) => h('a', { class: 'chip ep', href: `#/case/${enc(c)}`, style: { marginRight: '4px' } }, `case ${i + 1}`)) : h('span', { class: 'muted' }, '—')) },
      { label: 'Notes written', right: true, render: (w) => w.written }, { label: 'New notes', render: (w) => w.created.length || '' }, { label: 'Status changes', render: (w) => w.changes.map((c) => h('span', { class: `lab ${c.to}`, style: { marginRight: '4px' } }, `${c.from} → ${c.to}`)) }], P.weeks)));
  if (key === 'week' && wk) {
    setTimeout(() => {
      const tr = [...root.querySelectorAll('tbody tr')].find((r) => r.firstElementChild && r.firstElementChild.textContent.trim() === wk);
      if (tr) { tr.classList.add('flash'); tr.scrollIntoView({ block: 'center', behavior: 'smooth' }); }
    }, 350);
    return [['Pipeline', '#/pipeline'], ['PI', '#/pi'], [wk]];
  }
  return [['Pipeline', '#/pipeline'], ['PI']];
}

function detail(root, key) {
  const m = S.memByKey.get(key);
  if (!m) { root.append(card('Relationship not found', null, h('a', { href: '#/pi' }, 'Back to PI'))); return [['PI', '#/pi'], [key]]; }
  const cases = S.cases.filter((c) => c.keys.includes(key));
  root.append(h('div', { class: 'page-head' }, h('div', {}, h('div', { class: 'row', style: { gap: '8px', marginBottom: '6px' } }, labelChip(m.status), m.same_day_only ? h('span', { class: 'chip ep' }, 'same-day only') : null), h('h1', {}, short(m)), h('p', { class: 'mono muted' }, key)),
    h('a', { class: 'btn', href: '#/pi' }, '← All notes')));
  root.append(h('div', { class: 'grid g4' }, stat('First seen', fmtDate(m.counters.first_seen, { year: true })), stat('Last seen', fmtDate(m.counters.last_seen, { year: true })), stat('Days it appeared', m.counters.case_days, `${m.counters.exposed_case_days} with it present`), stat('Weeks seen', m.counters.weeks_seen)));

  const el = h('div', { class: 'chart', style: { height: '260px' } });
  root.append(card('Weekly label', `One bar for each of the ${S.pi.weeks.length} weeks, grouped by month. Colour = the label that week (green supported, amber suggestive, blue not supported, grey insufficient or not tracked yet). Height = how many of that week's 7 days her history supported it; a week with none shows a short stub so it stays visible. ▲ marks a change of status.`, el));
  setTimeout(() => {
    const p = palette();
    const col = { supported: cssVar('--ok'), suggestive: cssVar('--warn'), not_supported: cssVar('--low'), insufficient: p.line, not_tracked: p.line };
    const wk = S.pi.weeks.map((w) => w.week), have = new Map(m.weekly_labels.map((x) => [x[0], x]));
    const rows = wk.map((w) => { const x = have.get(w); return { w, l: x ? x[1] : 'not_tracked', d: x ? x[2] : 0, n: x ? x[3] : 0 }; });
    const chart = mount(el, base({
      grid: { left: 8, right: 14, top: 28, bottom: 56, containLabel: true },
      tooltip: { ...base().tooltip, trigger: 'item', formatter: (q) => {
        if (q.seriesType === 'scatter') return `<b>${dayTxt(isoMon(q.data.w))}</b><br>status changed: ${q.data.t.from} → ${q.data.t.to}`;
        const r = q.data; return `<b>Week of ${dayTxt(isoMon(r.w))}</b> (${r.w})<br>${r.l === 'not_tracked' ? 'not tracked yet: no label this week' : `${r.l.replace(/_/g, ' ')} · her history backed it on ${r.d} of ${r.n} days`}`; } },
      xAxis: { type: 'category', data: wk, axisLabel: { show: false }, axisTick: { show: false }, axisLine: { lineStyle: { color: p.line } } },
      yAxis: valueAxis({ max: 8, interval: 1, axisLabel: { color: p.muted, formatter: (v) => (v <= 7 ? v : '') }, name: 'days supported', nameTextStyle: { color: p.muted, align: 'left' } }),
      series: [
        { type: 'bar', barWidth: '78%', data: rows.map((r) => ({ ...r, value: Math.max(r.d, 0.55), itemStyle: { color: col[r.l], borderRadius: [3, 3, 0, 0], opacity: r.l === 'not_tracked' ? 0.5 : 1 } })) },
        { type: 'scatter', symbol: 'triangle', symbolSize: 13, z: 6, data: m.status_history.map((t) => ({ value: [wk.indexOf(t.week), 7.5], t, w: t.week })).filter((x) => x.value[0] >= 0), itemStyle: { color: p.ink, borderColor: p.surface, borderWidth: 1 } }],
    }));
    attachMonths(chart, wk, 28, 56);
  }, 0);

  root.append(card('Every version of the note', 'A new version is written only when something changes. The association sentence is built by code; the situations line is written from the diary.',
    h('div', { class: 'itemlist' }, [...m.versions].reverse().map((v) => h('div', { class: 'pnote', style: { borderLeftColor: STATUS_COLOR[v.status] } },
      h('div', { class: 'row', style: { gap: '8px' } }, labelChip(v.status), h('b', {}, `version ${v.version}`), h('span', { class: 'muted' }, `written ${fmtDate(v.written_at.slice(0, 10), { year: true })} · ${v.case_days} days so far`)),
      h('div', { class: 'assoc' }, v.association), v.situations ? h('div', { class: 'sit' }, h('b', {}, 'Situations noted: '), v.situations) : h('div', { class: 'muted' }, 'No situations line.'))))));
  if (m.status_history.length) root.append(card('Status changes', null, table([{ label: 'Week', render: (t) => t.week }, { label: 'From', render: (t) => labelChip(t.from) }, { label: 'To', render: (t) => labelChip(t.to) }], m.status_history)));
  root.append(card(`Cases that mention it (${cases.length})`, 'Cases whose text could discuss this relationship', cases.length ? h('div', { class: 'grid g-auto' }, cases.map(caseCard)) : h('div', { class: 'muted' }, 'None.')));
  return [['Pipeline', '#/pipeline'], ['PI', '#/pi'], [short(m)]];
}
