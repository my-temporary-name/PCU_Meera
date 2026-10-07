import { S, DAY, ms, ds, addDays, mondayOf, fmtDate, monthName, n1 } from '../store.js';
import { h, card, stat, legend, icon } from '../ui.js';
import { mount, glucoseOption, palette } from '../charts.js';
import { alertsTable, caseCard, dailyBars } from './shared.js';

function nextMonth(ym, delta) {
  const [y, m] = ym.split('-').map(Number);
  const d = new Date(Date.UTC(y, m - 1 + delta, 1));
  return d.toISOString().slice(0, 7);
}

export function render(root, [ym]) {
  if (!S.months.includes(ym)) ym = S.months[S.months.length - 1];
  const from = ms(ym + '-01');
  const to = ms(nextMonth(ym, 1) + '-01');
  const dates = S.dates.filter((d) => d.startsWith(ym));
  const alerts = S.alertsByMonth.get(ym) || [];
  const cases = S.casesByMonth.get(ym) || [];
  const idx = S.months.indexOf(ym);

  const nav = h('div', { class: 'row' },
    idx > 0 ? h('a', { class: 'btn icon', href: `#/month/${S.months[idx - 1]}`, title: 'Previous month' }, icon('left')) : null,
    idx < S.months.length - 1 ? h('a', { class: 'btn icon', href: `#/month/${S.months[idx + 1]}`, title: 'Next month' }, icon('right')) : null);
  root.append(h('div', { class: 'page-head' }, h('div', {}, h('h1', {}, monthName(ym)), h('p', {}, `${dates.length} days of data · ${alerts.length} alerts · ${cases.length} cases`)), nav));
  root.append(h('div', { class: 'tabs' }, S.months.map((m) => h('a', { href: `#/month/${m}`, class: m === ym ? 'on' : '' }, monthName(m, true)))));

  // summary tiles
  const rows = S.glucose_daily.filter((r) => r[0].startsWith(ym));
  const n = rows.reduce((a, r) => a + r[4], 0);
  const mean = rows.reduce((a, r) => a + r[2] * r[4], 0) / n;
  const nVersions = cases.reduce((a, c) => a + c.versions, 0);
  root.append(h('div', { class: 'grid g4' },
    stat('Mean glucose', n1(mean), 'mg/dL'),
    stat('Lowest · highest reading', `${n1(Math.min(...rows.map((r) => r[1])))} · ${n1(Math.max(...rows.map((r) => r[3])))}`, 'mg/dL'),
    stat('Alerts', alerts.length, `${alerts.filter((a) => a.measure === 'glucose').length} glucose`),
    stat('Cases written up', cases.length, `${nVersions} versions`)));

  // glucose chart
  const chartEl = h('div', { class: 'chart tall' });
  const P = palette();
  const weeks = [];
  for (let w = mondayOf(dates[0]); w <= dates[dates.length - 1]; w = addDays(w, 7)) weeks.push(w);
  root.append(card('Glucose through the month', 'Every 15-minute reading. Pins are glucose alerts, orange diamonds are alerts on other measures, violet bands are cases. Click a day to open its week.',
    h('div', {}, chartEl, h('div', { style: { marginTop: '10px' }, class: 'row' }, legend([[P.primary, 'Glucose'], [P.bad, 'Glucose alert (pin)'], [P.warn, 'Other alert (heart rate, medication, sleep...)'], [P.ep, 'Case']]),
      h('span', { class: 'muted' }, 'Weeks:'), weeks.map((w) => h('a', { class: 'chip primary', href: `#/week/${w}` }, fmtDate(w)))))));
  setTimeout(() => {
    const chart = mount(chartEl, glucoseOption({ from, to, cases, alerts, meals: [], zoom: true }));
    chart.getZr().on('click', (e) => {
      const p = [e.offsetX, e.offsetY];
      if (chart.containPixel('grid', p)) location.hash = `#/week/${mondayOf(ds(chart.convertFromPixel({ gridIndex: 0 }, p)[0]))}`;
    });
  }, 0);

  // lifestyle small multiples
  const charts = [['sleep', 'Sleep', 'h', 1], ['steps', 'Steps per day', '', 0], ['hydration', 'Hydration', 'ml', 0], ['screen', 'Screen time', 'h', 1], ['sedentary', 'Sedentary time', 'min', 0]];
  const grid = h('div', { class: 'grid g3' });
  charts.forEach(([key, label, unit, dec]) => {
    const el = h('div', { class: 'chart mini' });
    grid.append(h('div', { class: 'card flat' }, h('h3', {}, label, unit && h('span', { class: 'muted' }, ` (${unit})`)), el));
    setTimeout(() => dailyBars(el, dates, key, { unit, decimals: dec }), 0);
  });
  const medsEl = h('div', { class: 'chart mini' });
  grid.append(h('div', { class: 'card flat' }, h('h3', {}, 'Medications taken', h('span', { class: 'muted' }, ' (of 3 daily)')), medsEl));
  setTimeout(() => dailyBars(medsEl, dates, 'meds', { getter: (d) => (S.daily[d].adh || []).filter((a) => a.taken).length, unit: 'of 3' }), 0);
  root.append(card('Daily lifestyle', 'Bars are coloured by their reference status (green normal · amber borderline · red high · blue low). Green band = normal range.', grid));

  // cases and alerts
  if (cases.length) root.append(card('Cases this month', 'Alerts close in time are written up together — click one to follow it from the reading to the context', h('div', { class: 'grid g-auto' }, cases.map(caseCard))));
  root.append(card('Alerts', 'Every alert the State Engine handed on this month. Click a row to open its case.', alertsTable(alerts)));

  return [['Full year', '#/year'], [monthName(ym)]];
}
