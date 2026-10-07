import { S, DAY, ms, ds, addDays, mondayOf, fmtDate, fmtTime, monthName, n1, casesInRange, casesOnDate, alertsInRange, measureName } from '../store.js';
import { h, card, chip, legend, icon } from '../ui.js';
import { mount, palette, base, timeAxis, valueAxis, glucoseLayers } from '../charts.js';
import { alertsTable, caseCard, mealLabel } from './shared.js';

export function render(root, [start]) {
  const monday = mondayOf(start || S.last);
  const days = Array.from({ length: 7 }, (_, i) => addDays(monday, i));
  const from = ms(monday), to = from + 7 * DAY;
  const cases = casesInRange(from, to);
  const alerts = alertsInRange(from, to);
  const prev = addDays(monday, -7), next = addDays(monday, 7);
  const hasPrev = monday > mondayOf(S.first), hasNext = monday < mondayOf(S.last);

  root.append(h('div', { class: 'page-head' },
    h('div', {}, h('h1', {}, `Week of ${fmtDate(monday, { year: true })}`), h('p', {}, `${fmtDate(days[0])} – ${fmtDate(days[6], { year: true })} · ${alerts.length} alerts · ${cases.length} cases`)),
    h('div', { class: 'row' },
      hasPrev && h('a', { class: 'btn icon', href: `#/week/${prev}`, title: 'Previous week' }, icon('left')),
      h('a', { class: 'btn', href: `#/month/${monday.slice(0, 7)}` }, monthName(monday.slice(0, 7), true)),
      hasNext && h('a', { class: 'btn icon', href: `#/week/${next}`, title: 'Next week' }, icon('right')))));

  if (cases.length) root.append(h('div', { class: 'row' }, h('span', { class: 'muted' }, 'Cases:'), cases.map((c) => h('a', { href: `#/case/${encodeURIComponent(c.id)}` }, h('span', { class: 'chip ep wrap' }, `${fmtDate(c.date)} · ${c.headline}`)))));

  const P = palette();
  const chartEl = h('div', { class: 'chart', style: { height: '470px' } });
  root.append(card('Glucose and activity', 'Dashed vertical lines mark meals (B/L/D/S) — hover for food. Pins are glucose alerts, orange diamonds are alerts on other measures, violet is a case.',
    h('div', {}, chartEl, h('div', { class: 'row', style: { marginTop: '10px' } }, legend([[P.primary, 'Glucose (15-min)'], [P.bad, 'Glucose alert'], [P.warn, 'Other alert'], [P.ep, 'Case'], [P.low, 'Steps per hour']])))));
  setTimeout(() => {
    const L = glucoseLayers({ from, to, cases, alerts, meals: undefined });
    const hours = [];
    days.forEach((d) => (S.hourly_steps[d] || []).forEach((v, hh) => hours.push([ms(d) + hh * 3600000 + 1800000, v])));
    const dayLabel = { formatter: (v) => (v >= to ? '' : fmtDate(ds(v), { dow: true })), color: P.muted, align: 'left' };
    chart(chartEl, {
      ...base(),
      axisPointer: { link: [{ xAxisIndex: 'all' }] },
      grid: [{ left: 8, right: 14, top: 30, height: '54%', containLabel: true }, { left: 8, right: 14, top: '72%', height: '17%', containLabel: true }],
      tooltip: {
        ...base().tooltip, trigger: 'axis', axisPointer: { type: 'line', lineStyle: { color: P.muted } },
        formatter: (ps) => {
          let html = L.formatter(ps);
          const s = ps.find((p) => p.seriesName === 'Steps per hour');
          if (s) html += `<br>Steps this hour <b>${n1(s.value[1], 0)}</b>`;
          return html;
        },
      },
      xAxis: [
        timeAxis({ gridIndex: 0, min: from, max: to, maxInterval: DAY, minInterval: DAY, axisLabel: { show: false }, splitLine: { show: true, lineStyle: { color: P.line } } }),
        timeAxis({ gridIndex: 1, min: from, max: to, maxInterval: DAY, minInterval: DAY, axisLabel: { ...dayLabel, showMaxLabel: false }, splitLine: { show: true, lineStyle: { color: P.line } } }),
      ],
      yAxis: [
        valueAxis({ gridIndex: 0, min: L.yMin, max: L.yMax, name: 'mg/dL', nameTextStyle: { color: P.muted, align: 'left' } }),
        valueAxis({ gridIndex: 1, name: 'steps/h', nameTextStyle: { color: P.muted, align: 'left' }, splitNumber: 2 }),
      ],
      series: [
        ...L.series.map((s) => ({ ...s, xAxisIndex: 0, yAxisIndex: 0 })),
        { name: 'Steps per hour', type: 'bar', xAxisIndex: 1, yAxisIndex: 1, data: hours, barWidth: 4, itemStyle: { color: P.low, opacity: 0.85, borderRadius: [2, 2, 0, 0] } },
      ],
    });
  }, 0);

  // day cards
  const wrap = h('div', { class: 'week-days' });
  days.forEach((d) => wrap.append(dayCard(d)));
  root.append(card('Day by day', 'Everything recorded for each day — sleep, activity, mood, medications, diary', wrap));

  if (alerts.length) root.append(card('Alerts this week', 'Click a row to open its case', alertsTable(alerts, { pageSize: 12 })));
  return [['Full year', '#/year'], [monthName(monday.slice(0, 7), true), `#/month/${monday.slice(0, 7)}`], [`Week of ${fmtDate(monday)}`]];
}

function chart(el, option) { return mount(el, option); }

function kv(k, ...v) { return [h('span', { class: 'k' }, k), h('span', { class: 'v num' }, ...v)]; }

function dayCard(d) {
  const day = S.daily[d];
  const diary = S.diaryByDate.get(d);
  if (!day) return h('div', { class: 'daycard' }, h('h3', {}, fmtDate(d, { dow: true })), h('span', { class: 'muted' }, 'No data'));
  const st = day.st || {};
  const g = S.gDaily.get(d);
  const eps = casesOnDate(d);
  const evs = S.alerts.filter((a) => a.date === d);
  const rows = [
    g && kv('Glucose', `${n1(g[2])} avg`, h('div', { class: 'muted', style: { fontWeight: 500 } }, `${n1(g[1])}–${n1(g[3])} mg/dL`)),
    kv('Sleep', `${n1(day.sleep)} h${day.sleep_q ? ' · ' + day.sleep_q : ''} `, st.sleep && chip(st.sleep)),
    kv('Steps', n1(day.steps, 0), ' ', st.steps && chip(st.steps)),
    kv('Hydration', `${n1(day.hydration, 0)} ml `, st.hydration && chip(st.hydration)),
    kv('Screen time', `${n1(day.screen)} h `, st.screen && chip(st.screen)),
    kv('Sedentary', `${n1(day.sedentary, 0)} min `, st.sedentary && chip(st.sedentary)),
    day.loc && kv('Location', day.loc.replace(/_/g, ' ')),
    day.bp && kv('Blood pressure', `${day.bp[0]}/${day.bp[1]} mmHg`),
    day.hr != null && kv('Resting HR', `${n1(day.hr, 0)} bpm`),
    day.cycle && kv('Cycle', `day ${day.cycle.day} · ${day.cycle.phase.replace(/_/g, ' ')}`),
  ].filter(Boolean);
  const mood = day.mood && h('div', { class: 'mood' }, ['morning', 'afternoon', 'evening'].map((b) => (day.mood[b] ? h('span', { class: day.mood[b][1], title: `${b}: ${day.mood[b][0]}` }, day.mood[b][0].replace(/_/g, ' ')) : null)));
  const meds = day.adh && h('div', { class: 'meds' }, day.adh.map((a) => h('span', { class: `med ${a.taken ? 'yes' : 'no'}` }, a.taken ? '✓ ' : '✗ ', a.m)));
  const ctx = (S.ctxByDate.get(d) || []).map((c) => h('div', { class: 'muted', style: { fontSize: '12px' } }, h('b', { style: { color: 'var(--ink-2)' } }, c.category.replace(/_/g, ' ')), ' · ', c.description));
  const meals = (S.mealsByDate.get(d) || []).map((m) => h('div', { style: { fontSize: '12px' }, class: 'muted' }, h('b', { style: { color: 'var(--ink-2)' } }, `${fmtTime(m.t)} ${mealLabel(m.label)}`), ' · ', m.food));
  return h('div', { class: 'daycard' },
    h('div', {}, h('h3', {}, fmtDate(d, { dow: true })), h('div', { class: 'dtitle' }, diary && diary.title)),
    eps.length ? h('div', { class: 'row', style: { gap: '4px' } }, eps.map((c) => h('a', { href: `#/case/${encodeURIComponent(c.id)}` }, h('span', { class: 'chip ep wrap' }, 'Case · ', c.headline)))) : null,
    h('div', { class: 'kv' }, rows),
    mood, meds,
    meals.length ? h('details', { class: 'diary' }, h('summary', {}, `Meals (${meals.length})`), meals) : null,
    diary && diary.lines.length ? h('details', { class: 'diary' }, h('summary', {}, 'Diary'), diary.lines.map((l) => h('p', {}, l))) : null,
    ctx.length ? h('div', { class: 'stack', style: { gap: '4px' } }, ctx) : null,
    evs.length ? h('div', { class: 'row', style: { gap: '4px' } }, evs.slice(0, 6).map((a) => h('a', { href: a.case ? `#/case/${encodeURIComponent(a.case)}` : '#/cases' }, h('span', { class: 'chip bad' }, fmtTime(a.t), ' ', measureName(a.measure)))), evs.length > 6 ? h('span', { class: 'muted' }, `+${evs.length - 6}`) : null) : null);
}
