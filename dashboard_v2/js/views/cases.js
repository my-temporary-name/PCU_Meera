// All cases (and, as a second tab, all alerts): filter, see the year, open a case.
import { S, DAY, ms, fmtDate, fmtTime, monthName, measureName } from '../store.js';
import { h, card, pager } from '../ui.js';
import { mount, palette, base, timeAxis, valueAxis } from '../charts.js';
import { caseCard, alertsTable } from './shared.js';

export function render(root, [tab]) {
  const showAlerts = tab === 'alerts';
  root.append(h('div', { class: 'page-head' },
    h('div', {}, h('h1', {}, showAlerts ? 'Alerts' : 'Cases'), h('p', {}, showAlerts
      ? `${S.alerts.length} alerts the State Engine handed on. Each one with a packet is written up in a case.`
      : `${S.cases.length} cases: alerts that arrive close in time are written up together, with a new version whenever something new arrives.`)),
    h('div', { class: 'tabs' }, h('a', { href: '#/cases', class: showAlerts ? '' : 'on' }, 'Cases'), h('a', { href: '#/cases/alerts', class: showAlerts ? 'on' : '' }, 'Alerts'))));
  return showAlerts ? alertsPage(root) : casesPage(root);
}

const F = { q: '', mode: '', source: '', month: '', measure: '' };

function casesPage(root) {
  const nDesc = S.cases.filter((c) => c.mode !== 'relationship').length, nRel = S.cases.length - nDesc, nFb = S.cases.filter((c) => c.source !== 'llm').length;
  const chartEl = h('div', { class: 'chart', style: { height: '350px' } });
  const sw = (cls, style = '') => h('span', { class: `cl-sw ${cls}`, style }, h('i', {}));
  const key = (swatch, title, count, text) => h('div', { class: 'cl-key' }, swatch, h('div', {}, h('div', { class: 'row', style: { gap: '8px', alignItems: 'baseline' } }, h('b', {}, title), count != null ? h('span', { class: 'num muted' }, `${count} cases`) : null), h('div', { class: 'muted' }, text)));
  const legend = h('div', { class: 'cl-legend' },
    h('div', { class: 'cl-col' }, h('div', { class: 'cl-h' }, 'Colour: what the text may say'),
      key(sw('teal'), 'Describes only', nDesc, 'The text only says what happened, for example "evening glucose was clearly above her usual". No factor had enough support in her own history to be named as a link.'),
      key(sw('violet'), 'May discuss links', nRel, 'At least one factor was backed by her history, so the text may say it "may be linked to" what happened, never that it caused it.')),
    h('div', { class: 'cl-col' }, h('div', { class: 'cl-h' }, 'Shape: how big the case grew'),
      key(sw('size'), 'Size = alerts', null, 'How many alerts were grouped into the case. A bigger dot is a longer, busier episode.'),
      key(sw('height'), 'Height = versions', null, 'How many times the case was rewritten as new alerts or late results arrived. Higher means it kept developing.'),
      key(sw('ring'), 'Amber ring = fallback', nFb, 'The model\'s text failed the checks twice, so the plain sentence built by code is shown instead.')));
  root.append(card('The year in cases', 'Each dot is one case, placed on the day it opened. Hover for its headline, click to open it.', h('div', { class: 'stack', style: { gap: '14px' } }, chartEl, legend)));
  setTimeout(() => {
    const p = palette();
    const teal = p.primary, violet = p.ep;
    const short = (d) => { const x = new Date(d + 'T00:00:00Z'); return `${x.getUTCDate()} ${['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'][x.getUTCMonth()]}`; };
    const top = new Set([...S.cases].sort((x, y) => y.versions - x.versions).slice(0, 5).map((c) => c.id));
    // quiet stretch: consecutive months with few cases
    const per = S.months.map((m) => [m, S.cases.filter((c) => c.month === m).length]);
    const quiet = []; let run = [];
    per.forEach(([m, n]) => { if (n <= 3) run.push(m); else { if (run.length >= 2) quiet.push(run); run = []; } }); if (run.length >= 2) quiet.push(run);
    const bands = quiet.map((r) => { const last = r[r.length - 1]; const end = Date.UTC(+last.slice(0, 4), +last.slice(5), 1); return [{ xAxis: ms(r[0] + '-01'), name: 'few cases', itemStyle: { color: 'rgba(120,140,135,.09)' }, label: { show: true, position: 'insideTop', color: p.muted, fontSize: 12, distance: 6 } }, { xAxis: end }]; });
    const chart = mount(chartEl, base({
      grid: { left: 8, right: 18, top: 52, bottom: 8, containLabel: true },
      tooltip: { ...base().tooltip, trigger: 'item', formatter: (q) => { const c = q.data.c; const tag = c.mode === 'relationship' ? 'may discuss links' : 'describes only'; return `<b>${fmtDate(c.date, { dow: true })} · ${fmtTime(c.t0)}</b><br>${c.headline}<br><span style="color:${p.muted}">${c.alerts} alert${c.alerts === 1 ? '' : 's'} · ${c.versions} version${c.versions === 1 ? '' : 's'} · ${tag}${c.source !== 'llm' ? ' · code-line fallback' : ''}</span>`; } },
      xAxis: { ...timeAxis({ min: ms(S.first), max: ms(S.last) + DAY }), splitLine: { show: true, lineStyle: { color: p.line, type: [3, 5], opacity: 0.55 } } },
      yAxis: { ...valueAxis({ name: 'versions (rewrites)', min: 0, max: 13, nameTextStyle: { color: p.muted, align: 'left' } }), minInterval: 2, splitLine: { lineStyle: { color: p.line, type: [4, 6], opacity: 0.5 } } },
      series: [{ type: 'scatter', z: 3, emphasis: { scale: 1.25, itemStyle: { opacity: 1 } }, markArea: { silent: true, data: bands },
        data: S.cases.map((c) => ({ value: [c.t0, c.versions], c, symbolSize: 9 + c.alerts * 2.6,
          itemStyle: { color: c.mode === 'relationship' ? violet : teal, opacity: 0.85, borderColor: c.source !== 'llm' ? p.warn : p.surface, borderWidth: c.source !== 'llm' ? 3.5 : 1.5 },
          label: top.has(c.id) ? { show: true, position: 'top', color: p.ink2, fontSize: 11.5, fontWeight: 600, distance: 6, formatter: () => `${short(c.date)} · ${c.alerts} alerts` } : { show: false } })) }],
    }));
    chart.on('click', (q) => { if (q.data && q.data.c) location.hash = `#/case/${encodeURIComponent(q.data.c.id)}`; });
    chartEl.style.cursor = 'pointer';
  }, 0);

  const list = h('div', { class: 'grid g-auto' }), count = h('span', { class: 'muted' });
  let page = 0;
  const pagerEl = h('div', {});
  const measures = [...new Set(S.cases.flatMap((c) => c.measures))].sort();
  const draw = () => {
    const q = F.q.trim().toLowerCase();
    const rows = S.cases.filter((c) => (!q || c.headline.toLowerCase().includes(q) || c.first_headline.toLowerCase().includes(q) || c.phrases.some((x) => (x || '').toLowerCase().includes(q))) && (!F.mode || c.mode === F.mode)
      && (!F.source || (F.source === 'fallback' ? c.source !== 'llm' : c.source === 'llm')) && (!F.month || c.month === F.month) && (!F.measure || c.measures.includes(F.measure)));
    const size = 24, pages = Math.max(1, Math.ceil(rows.length / size));
    page = Math.min(page, pages - 1);
    count.textContent = `${rows.length} of ${S.cases.length} cases`;
    list.replaceChildren(...rows.slice(page * size, (page + 1) * size).map(caseCard));
    pagerEl.replaceChildren(rows.length > size ? pager(page, pages, (n) => { page = n; draw(); }) : '');
  };
  const sel = (key, opts, label) => { const s = h('select', { onchange: (e) => { F[key] = e.target.value; page = 0; draw(); } }, h('option', { value: '' }, label), opts.map(([v, t]) => h('option', { value: v, selected: F[key] === v || null }, t))); return s; };
  root.append(h('div', { class: 'filters filter-bar' },
    h('input', { type: 'search', placeholder: 'Search headlines or factors…', value: F.q, style: { minWidth: '260px' }, oninput: (e) => { F.q = e.target.value; page = 0; draw(); } }),
    sel('month', S.months.map((m) => [m, monthName(m)]), 'All months'), sel('mode', [['relationship', 'May discuss links'], ['descriptive', 'Describes only']], 'Any mode'),
    sel('source', [['llm', 'Model text'], ['fallback', 'Code-line fallback']], 'Any text source'), sel('measure', measures.map((m) => [m, measureName(m)]), 'Any measure'), count));
  root.append(list, pagerEl);
  draw();
  return [['Pipeline', '#/pipeline'], ['Cases']];
}

function alertsPage(root) {
  const A = { month: '', measure: '', case: '' };
  const holder = h('div', {});
  const draw = () => holder.replaceChildren(alertsTable(S.alerts.filter((a) => (!A.month || a.month === A.month) && (!A.measure || a.measure === A.measure) && (!A.case || (A.case === 'yes' ? a.case : !a.case))), { pageSize: 20 }));
  const sel = (key, opts, label) => h('select', { onchange: (e) => { A[key] = e.target.value; draw(); } }, h('option', { value: '' }, label), opts.map(([v, t]) => h('option', { value: v }, t)));
  root.append(h('div', { class: 'filters filter-bar' }, sel('month', S.months.map((m) => [m, monthName(m)]), 'All months'), sel('measure', [...new Set(S.alerts.map((a) => a.measure))].map((m) => [m, measureName(m)]), 'Any measure'),
    sel('case', [['yes', 'Written up in a case'], ['no', 'Not written up']], 'All alerts')), card(null, null, holder));
  draw();
  return [['Pipeline', '#/pipeline'], ['Alerts']];
}
