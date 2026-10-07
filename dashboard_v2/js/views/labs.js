import { S, ms, ds, fmtDate, n1, NAMES } from '../store.js';
import { h, card, chip } from '../ui.js';
import { mount, palette, base, timeAxis, valueAxis, gridDefault, statusColor } from '../charts.js';
import { bandAreas } from './shared.js';

const TESTS = ['hba1c', 'fasting_glucose', 'total_cholesterol', 'ldl_c', 'hdl_c', 'triglycerides', 'alt', 'ast', 'ggt', 'creatinine', 'egfr', 'tsh'];

// pts: [{t, v, s}]; bio selects reference bands (optional)
function trendChart(el, pts, bio, { labels = false, line = true, size = 8 } = {}) {
  const P = palette();
  const vals = pts.map((p) => p.v);
  const lo = Math.min(...vals), hi = Math.max(...vals);
  const pad = (hi - lo) * 0.3 || Math.abs(hi) * 0.15 || 1;
  const yMin = lo - pad, yMax = hi + pad;
  return mount(el, base({
    grid: gridDefault({ top: 22, bottom: 4, left: 4, right: 18 }),
    tooltip: {
      ...base().tooltip, trigger: 'item',
      formatter: (p) => `<b>${fmtDate(ds(p.value[0]), { year: true })}</b><br>${n1(p.value[1], 2)} ${(S.bands[bio] || {}).unit || ''}${p.data.s ? '<br>' + p.data.s.replace('_', ' ') : ''}`,
    },
    xAxis: timeAxis({ min: ms('2025-09-01'), max: ms('2026-09-30'), splitNumber: 3, axisLabel: { color: P.muted, hideOverlap: true, formatter: (v) => { const d = new Date(v); return ['Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec'][d.getUTCMonth()] + " '" + String(d.getUTCFullYear()).slice(2); } } }),
    yAxis: valueAxis({ min: yMin, max: yMax, splitNumber: 3 }),
    series: [{
      type: 'line', symbol: 'circle', symbolSize: size, showSymbol: true, lineStyle: { width: line ? 1.6 : 0, color: P.muted, opacity: 0.8 },
      label: labels ? { show: true, position: 'top', color: P.ink2, fontSize: 11, formatter: (p) => n1(p.value[1], 2) } : { show: false },
      data: pts.map((p) => ({ value: [p.t, p.v], s: p.s, itemStyle: { color: p.s ? statusColor(p.s) : P.primary, borderColor: P.surface, borderWidth: 1.5 } })),
      markArea: { silent: true, data: bandAreas(bio, yMin, yMax) },
    }],
  }));
}

export function render(root) {
  root.append(h('div', { class: 'page-head' }, h('div', {}, h('h1', {}, 'Labs & body'), h('p', {}, 'Quarterly lab panels, body measurements and vitals. Dot colour = reference status; shaded bands show normal (green), borderline (amber) and abnormal (red) ranges.'))));

  // lab cards
  const grid = h('div', { class: 'grid g4' });
  TESTS.forEach((t) => {
    const pts = (S.labs[t] || []).map((x) => ({ t: ms(x.d), v: x.v, s: x.s }));
    if (!pts.length) return;
    const last = (S.labs[t] || [])[S.labs[t].length - 1];
    const el = h('div', { class: 'chart mini', style: { height: '130px' } });
    grid.append(h('div', { class: 'card kpi' }, h('span', { class: 'label' }, NAMES[t] || t), h('span', { class: 'value num' }, n1(last.v, 2), h('small', {}, last.u)), last.s ? chip(last.s) : h('span', { class: 'muted' }, 'no reference range'), el));
    setTimeout(() => trendChart(el, pts, t, { labels: true }), 0);
  });
  root.append(card('Laboratory results', `${(S.labs.hba1c || []).length} draws: ${[...new Set(Object.values(S.labs).flat().map((x) => x.d))].sort().map((d) => fmtDate(d, { year: true })).join(' · ')}`, grid));

  // pivot
  const dates = [...new Set(Object.values(S.labs).flat().map((x) => x.d))].sort();
  const rows = TESTS.filter((t) => S.labs[t]);
  const tbl = h('table', { class: 'tbl' },
    h('thead', {}, h('tr', {}, h('th', {}, 'Test'), h('th', {}, 'Unit'), dates.map((d) => h('th', { class: 'r' }, fmtDate(d, { year: true }))))),
    h('tbody', {}, rows.map((t) => h('tr', {}, h('td', {}, h('b', {}, NAMES[t] || t)), h('td', { class: 'muted' }, S.labs[t][0].u),
      dates.map((d) => { const x = S.labs[t].find((y) => y.d === d); return h('td', { class: 'r num' }, x ? h('span', { class: `heat-cell ${x.s || ''}` }, n1(x.v, 2)) : '—'); })))));
  root.append(card('Lab results by date', null, h('div', { class: 'table-wrap' }, tbl)));

  // body
  const bodyGrid = h('div', { class: 'grid g3' });
  [['weight', 'Weight', 'kg', null], ['bmi', 'BMI', 'kg/m²', 'bmi'], ['whr', 'Waist-hip ratio', 'ratio', 'waist_hip_ratio']].forEach(([key, label, unit, bio]) => {
    const pts = S.body.filter((b) => b[key] != null).map((b) => ({ t: ms(b.d), v: b[key], s: key === 'bmi' ? b.bmi_s : key === 'whr' ? b.whr_s : null }));
    const el = h('div', { class: 'chart mini', style: { height: '170px' } });
    bodyGrid.append(h('div', { class: 'card flat' }, h('h3', {}, label, h('span', { class: 'muted' }, ` (${unit}) · weekly`)), el));
    setTimeout(() => trendChart(el, pts, bio || 'weight', { size: 4 }), 0);
  });
  root.append(card('Body measurements', null, bodyGrid));

  // vitals
  const vit = h('div', { class: 'grid g3' });
  [
    ['Systolic blood pressure', 'mmHg', 'blood_pressure_systolic', S.vitals.bp.map((x) => ({ t: x.t, v: x.sys, s: x.ss }))],
    ['Diastolic blood pressure', 'mmHg', 'blood_pressure_diastolic', S.vitals.bp.map((x) => ({ t: x.t, v: x.dia, s: x.ds }))],
    ['Resting heart rate', 'bpm', 'resting_heart_rate', S.vitals.hr.map((x) => ({ t: x.t, v: x.v, s: x.s }))],
  ].forEach(([label, unit, bio, pts]) => {
    const el = h('div', { class: 'chart mini', style: { height: '190px' } });
    vit.append(h('div', { class: 'card flat' }, h('h3', {}, label, h('span', { class: 'muted' }, ` (${unit}) · ${pts.length} readings`)), el));
    setTimeout(() => trendChart(el, pts, bio, { size: 4 }), 0);
  });
  root.append(card('Vitals', 'Home blood-pressure readings (about every 3 days) and daily resting heart rate', vit));
  return [['Labs & body']];
}
