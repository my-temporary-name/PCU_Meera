import { S, DAY, ms, ds, fmtDate, monthName, n1, baselineAt, episodesOnDate, mondayOf } from '../store.js';
import { h, link, card, chip, stat, toggle, segmented, legend, STATUS } from '../ui.js';
import { mount, palette, base, timeAxis, valueAxis, gridDefault, sparkline, statusColor } from '../charts.js';

export function render(root) {
  root.append(patientHeader(), kpiRow(), yearCard(), monthsGrid(), calendarCard());
  return [['Full year']];
}

function patientHeader() {
  const p = S.meta.patient;
  const initials = p.name.split(' ').map((w) => w[0]).join('');
  const meds = S.meta.medications;
  return h('section', { class: 'card patient' },
    h('div', { class: 'avatar' }, initials),
    h('div', {},
      h('h1', {}, p.name),
      h('div', { class: 'facts' },
        h('span', {}, `${p.age} years · ${p.sex}`),
        h('span', {}, p.menopause_status === 'peri' ? 'Perimenopausal' : p.menopause_status),
        h('span', {}, `DOB ${fmtDate(p.dob, { year: true })}`),
        h('span', {}, `Record: ${fmtDate(S.first, { year: true })} → ${fmtDate(S.last, { year: true })}`)),
      h('div', { class: 'tags' },
        meds.map((m) => h('span', { class: 'chip primary' }, 'Rx ', m)),
        S.meta.allergies.map((a) => h('span', { class: `chip ${a.status.startsWith('active') ? 'bad' : ''}`, title: a.reaction_type }, 'Allergy: ', a.allergen, a.status.startsWith('active') ? '' : ' (resolved)')),
        S.meta.vaccinations.map((v) => h('span', { class: 'chip ok', title: fmtDate(v.date_administered, { year: true }) }, '✓ ', v.vaccine_name.split(' (')[0])))));
}

function kpiRow() {
  const P = palette();
  const lab = (k) => (S.labs[k] || []).map((x) => ({ d: x.d, v: x.v, s: x.s }));
  const body = (key, sk) => S.body.filter((b) => b[key] != null).map((b) => ({ d: b.d, v: b[key], s: b[sk] }));
  const defs = [
    { label: 'HbA1c', unit: '%', data: lab('hba1c'), dec: 1 },
    { label: 'Fasting glucose (lab)', unit: 'mg/dL', data: lab('fasting_glucose'), dec: 0 },
    { label: 'LDL-C', unit: 'mg/dL', data: lab('ldl_c'), dec: 0 },
    { label: 'eGFR', unit: 'mL/min', data: lab('egfr'), dec: 1 },
    { label: 'BMI', unit: 'kg/m²', data: body('bmi', 'bmi_s'), dec: 1 },
    { label: 'Weight', unit: 'kg', data: body('weight'), dec: 1 },
    { label: 'Blood pressure', unit: 'mmHg', bp: true },
    { label: 'Resting heart rate', unit: 'bpm', data: S.vitals.hr.map((x) => ({ d: ds(x.t), v: x.v, s: x.s })), dec: 0 },
  ];
  const wrap = h('div', { class: 'grid g4' });
  defs.forEach((k) => {
    const spark = h('div', { class: 'spark' });
    let value, sub, status;
    let vals;
    if (k.bp) {
      const bp = S.vitals.bp;
      const last = bp[bp.length - 1], prev = bp[bp.length - 2];
      value = `${last.sys}/${last.dia}`;
      status = h('span', {}, chip(last.ss, 'SYS'), ' ', chip(last.ds, 'DIA'));
      sub = `Latest ${fmtDate(ds(last.t))} · previous ${prev.sys}/${prev.dia}`;
      vals = bp.map((x) => x.sys);
    } else {
      const last = k.data[k.data.length - 1], prev = k.data[k.data.length - 2];
      value = Number(last.v).toFixed(k.dec);
      status = last.s ? chip(last.s) : null;
      sub = `Latest ${fmtDate(last.d, { year: true })}` + (prev ? ` · previous ${Number(prev.v).toFixed(k.dec)}` : '');
      vals = k.data.map((x) => x.v);
    }
    wrap.append(h('div', { class: 'card kpi' }, h('span', { class: 'label' }, k.label), h('span', { class: 'value num' }, value, h('small', {}, k.unit)), h('div', {}, status), h('span', { class: 'sub' }, sub), spark));
    setTimeout(() => sparkline(spark, vals, P.primary), 0);
  });
  return wrap;
}

function yearCard() {
  const state = { range: true, base: true, eps: true };
  const chartEl = h('div', { class: 'chart tall' });
  const selection = h('div', { class: 'selection' }, h('span', { class: 'muted' }, 'Click anywhere on the chart to inspect a day and jump to its week.'));
  const body = h('div', {}, chartEl, selection);
  let chart;

  const draw = () => {
    const P = palette();
    const yMax = 300;
    const daily = S.glucose_daily;
    const x = (r) => ms(r[0]) + DAY / 2;
    const bl = (S.baseline.biomarker_baselines.cgm_glucose_reading || []);
    const series = [];
    if (state.range) {
      series.push({ name: 'min', type: 'line', stack: 'r', data: daily.map((r) => [x(r), r[1]]), symbol: 'none', lineStyle: { opacity: 0 }, silent: true });
      series.push({ name: 'Daily range', type: 'line', stack: 'r', data: daily.map((r) => [x(r), +(r[3] - r[1]).toFixed(1)]), symbol: 'none', lineStyle: { opacity: 0 }, areaStyle: { color: P.primary, opacity: 0.17 }, silent: true });
    }
    series.push({
      name: 'Daily mean', type: 'line', data: daily.map((r) => [x(r), r[2]]), symbol: 'none', z: 4, lineStyle: { width: 2, color: P.primary },
      markArea: state.eps ? { silent: true, data: S.episodeList.map((ep) => [{ xAxis: ms(ep.date_range.start), itemStyle: { color: P.ep, opacity: 0.1 } }, { xAxis: ms(ep.date_range.end) + DAY }]) } : undefined,
    });
    if (state.base) {
      series.push({ name: 'Usual range (low)', type: 'line', step: 'end', symbol: 'none', data: bl.map((c) => [ms(c.as_of_date), c.typical_low_episode_excluded]), lineStyle: { width: 1.2, type: 'dashed', color: P.muted }, z: 2 });
      series.push({ name: 'Usual range (high)', type: 'line', step: 'end', symbol: 'none', data: bl.map((c) => [ms(c.as_of_date), c.typical_high_episode_excluded]), lineStyle: { width: 1.2, type: 'dashed', color: P.muted }, z: 2 });
    }
    series.push({ name: 'Rejected', type: 'scatter', symbol: 'diamond', symbolSize: 12, z: 6, itemStyle: { color: P.bad, borderColor: P.surface, borderWidth: 1.5 }, data: S.glucose.rejected.map((r) => [r.t, yMax - 6, r.v]) });
    series.push({ name: 'Off scale', type: 'scatter', symbol: 'triangle', symbolSize: 10, z: 6, itemStyle: { color: P.warn }, data: daily.filter((r) => r[3] > yMax).map((r) => [x(r), yMax - 14, r[3]]) });

    const option = base({
      grid: gridDefault({ top: 30, bottom: 48 }),
      tooltip: {
        ...base().tooltip, trigger: 'axis', axisPointer: { type: 'line', lineStyle: { color: P.muted } },
        formatter: (ps) => {
          const t = ps[0].axisValue;
          const d = ds(t);
          const r = S.gDaily.get(d);
          if (!r) return fmtDate(d);
          const eps = episodesOnDate(d).map((e) => `<span style="color:${P.ep}">${e.title}</span>`).join('<br>');
          const rej = S.glucose.rejected.filter((q) => ds(q.t) === d).map((q) => `<span style="color:${P.bad}">Rejected ${n1(q.v)} mg/dL</span>`).join('<br>');
          return `<b>${fmtDate(d, { dow: true, year: true })}</b><br>Mean <b>${n1(r[2])}</b> · min ${n1(r[1])} · max ${n1(r[3])} mg/dL${eps ? '<br>' + eps : ''}${rej ? '<br>' + rej : ''}`;
        },
      },
      xAxis: timeAxis({ min: ms(S.first), max: ms(S.last) + DAY }),
      yAxis: valueAxis({ min: 50, max: yMax, name: 'mg/dL', nameTextStyle: { color: P.muted, align: 'left' } }),
      dataZoom: [{ type: 'inside' }, { type: 'slider', height: 20, bottom: 8, borderColor: 'transparent', fillerColor: 'rgba(14,124,112,.14)' }],
      series,
    });
    if (chart) chart.setOption(option, true);
    else {
      chart = mount(chartEl, option);
      chart.getZr().on('click', (e) => {
        const p = [e.offsetX, e.offsetY];
        if (!chart.containPixel('grid', p)) return;
        const d = ds(chart.convertFromPixel({ gridIndex: 0 }, p)[0]);
        showSelection(d);
      });
    }
  };

  const showSelection = (d) => {
    const r = S.gDaily.get(d);
    if (!r) return;
    const diary = S.diaryByDate.get(d);
    selection.replaceChildren(
      h('b', {}, fmtDate(d, { dow: true, year: true })),
      h('span', {}, `Mean ${n1(r[2])} · min ${n1(r[1])} · max ${n1(r[3])} mg/dL`),
      diary && diary.title && h('span', { class: 'muted' }, diary.title),
      episodesOnDate(d).map((e) => link(`#/episode/${e.episode_id}`, h('span', { class: 'chip ep' }, e.title))),
      h('a', { class: 'btn primary', href: `#/week/${mondayOf(d)}` }, 'Open week'),
      h('a', { class: 'btn', href: `#/month/${d.slice(0, 7)}` }, 'Open month'));
  };

  const head = h('div', { class: 'row' },
    toggle('Daily range', true, (v) => { state.range = v; draw(); }),
    toggle('Her usual range', true, (v) => { state.base = v; draw(); }),
    toggle('Episodes', true, (v) => { state.eps = v; draw(); }));
  const P0 = palette();
  const el = card('Glucose across the year', 'Daily mean with min–max range from the 15-minute CGM stream (rejected sensor spikes excluded)', body, head);
  el.append(h('div', { style: { marginTop: '10px' } }, legend([[P0.primary, 'Daily mean / range'], [P0.muted, 'Her usual range (episode-excluded baseline)'], [P0.ep, 'Episode'], [P0.bad, 'Rejected reading'], [P0.warn, 'Value above chart scale']])));
  setTimeout(draw, 0);
  return el;
}

function monthsGrid() {
  const P = palette();
  const grid = h('div', { class: 'grid g-auto' });
  S.months.forEach((ym) => {
    const rows = S.glucose_daily.filter((r) => r[0].startsWith(ym));
    const n = rows.reduce((a, r) => a + r[4], 0);
    const mean = rows.reduce((a, r) => a + r[2] * r[4], 0) / n;
    const evs = (S.eventsByMonth.get(ym) || []).length;
    const eps = (S.episodesByMonth.get(ym) || []).length;
    const spark = h('div', { class: 'spark' });
    grid.append(h('a', { class: 'card month-card', href: `#/month/${ym}` },
      h('span', { class: 'mname' }, monthName(ym)),
      h('div', { class: 'mstats' }, h('span', {}, h('b', { class: 'num' }, n1(mean, 0)), ' mg/dL avg'), h('span', {}, h('b', {}, evs), ' events'), h('span', {}, h('b', {}, eps), ' episodes')),
      spark));
    setTimeout(() => sparkline(spark, rows.map((r) => r[2]), P.primary), 0);
  });
  return card('Month by month', 'Click a month to see its days, events and episodes', grid);
}

const METRICS = {
  glucose: { label: 'Glucose (mean)', unit: 'mg/dL', get: (d) => (S.gDaily.get(d) || [])[2] },
  sleep: { label: 'Sleep', unit: 'h', get: (d) => S.daily[d] && S.daily[d].sleep },
  steps: { label: 'Steps', unit: '', get: (d) => S.daily[d] && S.daily[d].steps },
  hydration: { label: 'Hydration', unit: 'ml', get: (d) => S.daily[d] && S.daily[d].hydration },
  screen: { label: 'Screen time', unit: 'h', get: (d) => S.daily[d] && S.daily[d].screen },
  sedentary: { label: 'Sedentary', unit: 'min', get: (d) => S.daily[d] && S.daily[d].sedentary },
  meds: { label: 'Medications taken', unit: 'of 3', get: (d) => S.daily[d] && S.daily[d].adh && S.daily[d].adh.filter((a) => a.taken).length },
};

function calendarCard() {
  const chartEl = h('div', { class: 'chart', style: { height: '205px' } });
  let metric = 'glucose';
  let chart;
  const draw = () => {
    const P = palette();
    const M = METRICS[metric];
    const data = S.dates.map((d) => [d, M.get(d)]).filter((x) => x[1] != null);
    const vals = data.map((x) => x[1]);
    const dark = document.documentElement.dataset.theme === 'dark';
    const option = base({
      tooltip: {
        ...base().tooltip,
        formatter: (p) => {
          const d = p.value[0];
          const diary = S.diaryByDate.get(d);
          return `<b>${fmtDate(d, { dow: true, year: true })}</b><br>${M.label}: <b>${n1(p.value[1])}</b> ${M.unit}${diary && diary.title ? `<br><span style="color:${P.muted}">${diary.title}</span>` : ''}`;
        },
      },
      visualMap: { min: Math.min(...vals), max: Math.max(...vals), calculable: false, orient: 'horizontal', left: 'right', top: 0, itemWidth: 12, itemHeight: 110, text: ['high', 'low'], textStyle: { color: P.muted }, inRange: { color: dark ? ['#173a36', '#3cc4b3'] : ['#e3f4f1', '#0a665c'] } },
      calendar: {
        range: [S.first, '2026-09-30'], top: 36, left: 34, right: 12, cellSize: ['auto', 19], yearLabel: { show: false },
        dayLabel: { firstDay: 1, color: P.muted, nameMap: ['S', 'M', 'T', 'W', 'T', 'F', 'S'] }, monthLabel: { color: P.ink2 },
        splitLine: { show: false }, itemStyle: { borderWidth: 3, borderColor: P.surface, color: P.surface2 },
      },
      series: [{ type: 'heatmap', coordinateSystem: 'calendar', data, itemStyle: { borderRadius: 4 } }],
    });
    if (chart) chart.setOption(option, true);
    else {
      chart = mount(chartEl, option);
      chart.on('click', (p) => { if (p.value && p.value[0]) location.hash = `#/week/${mondayOf(p.value[0])}`; });
    }
  };
  const seg = segmented(Object.entries(METRICS).map(([k, m]) => [k, m.label]), metric, (v) => { metric = v; draw(); });
  setTimeout(draw, 0);
  return card('Year at a glance', 'Every day of the record — pick a measure; click a day to open its week', chartEl, seg);
}
