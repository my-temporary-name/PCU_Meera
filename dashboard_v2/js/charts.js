// ECharts helpers: theme tokens, mounting, and the shared glucose chart layers.
import { S, DAY, ds, ms, fmtTime, fmtDate, n1, glucoseSlice, alertsInRange, casesInRange, measureName } from './store.js';

const registry = new Set();

export const cssVar = (n) => getComputedStyle(document.documentElement).getPropertyValue(n).trim();
export function palette() {
  return {
    ink: cssVar('--ink'), ink2: cssVar('--ink-2'), muted: cssVar('--muted'), line: cssVar('--line'), surface: cssVar('--surface'), surface2: cssVar('--surface-2'),
    primary: cssVar('--primary'), ok: cssVar('--ok'), warn: cssVar('--warn'), bad: cssVar('--bad'), low: cssVar('--low'), ep: cssVar('--ep'), font: cssVar('--font'),
  };
}
export function statusColor(s) {
  const P = palette();
  return { normal: P.ok, borderline_high: P.warn, borderline_low: P.warn, high: P.bad, low: P.low }[s] || P.muted;
}

export function mount(el, option) {
  const chart = echarts.init(el, null, { renderer: 'canvas' });
  chart.setOption(option);
  registry.add(chart);
  return chart;
}
export function disposeAll() {
  registry.forEach((c) => c.dispose());
  registry.clear();
}
window.addEventListener('resize', () => registry.forEach((c) => c.resize()));

export function base(extra = {}) {
  const P = palette();
  return {
    useUTC: true,
    animationDuration: 450,
    textStyle: { fontFamily: P.font, color: P.ink2 },
    tooltip: {
      confine: true, backgroundColor: P.surface, borderColor: P.line, borderWidth: 1, padding: [8, 10],
      textStyle: { color: P.ink, fontSize: 12.5 }, extraCssText: 'box-shadow:0 8px 24px rgba(0,0,0,.18);border-radius:10px;',
    },
    ...extra,
  };
}
export const timeAxis = (extra = {}) => {
  const P = palette();
  return { type: 'time', axisLine: { lineStyle: { color: P.line } }, axisTick: { show: false }, axisLabel: { color: P.muted, hideOverlap: true }, splitLine: { show: false }, ...extra };
};
export const valueAxis = (extra = {}) => {
  const P = palette();
  return { type: 'value', axisLine: { show: false }, axisTick: { show: false }, axisLabel: { color: P.muted, formatter: (v) => Number(v.toPrecision(6)).toLocaleString('en-US', { maximumFractionDigits: 3 }) }, splitLine: { lineStyle: { color: P.line, type: 'dashed' } }, ...extra };
};
export const gridDefault = (extra = {}) => ({ left: 8, right: 14, top: 28, bottom: 8, containLabel: true, ...extra });

export function sparkline(el, values, color, { area = true } = {}) {
  const P = palette();
  return mount(el, {
    animation: false,
    grid: { left: 4, right: 4, top: 4, bottom: 4 },
    xAxis: { type: 'category', show: false, data: values.map((_, i) => i) },
    yAxis: { type: 'value', show: false, scale: true },
    series: [{ type: 'line', data: values, smooth: 0.25, showSymbol: false, lineStyle: { width: 2, color: color || P.primary }, areaStyle: area ? { color: color || P.primary, opacity: 0.12 } : undefined }],
  });
}

// ---- Glucose layers --------------------------------------------------------------------------
function mealAt(t) {
  let best = null;
  for (const m of S.meals) { if (m.t <= t && t - m.t <= 150 * 60000 && (!best || m.t > best.t)) best = m; }
  return best;
}

export function glucoseLayers(o) {
  const P = palette();
  const { from, to } = o;
  const yMin = o.yMin ?? 40, yMax = o.yMax ?? 300;
  const pts = glucoseSlice(from, to);
  const areas = [];

  (o.cases || []).forEach((c) => {
    const focus = o.focusCase === c.id;
    areas.push([
      { xAxis: c.t0 - 450000, itemStyle: { color: P.ep, opacity: focus ? 0.2 : 0.09 } },
      { xAxis: (c.t1 ?? c.t0) + 450000 },
    ]);
  });

  const meals = (o.meals ?? S.meals).filter((m) => m.t >= from && m.t < to);
  const marks = meals.map((m) => ({
    xAxis: m.t,
    label: { show: o.mealLabels !== false, formatter: m.label[0].toUpperCase(), color: P.muted, fontSize: 10, position: 'insideEndTop' },
    lineStyle: { color: P.muted, type: 'dashed', opacity: 0.5, width: 1 },
  }));

  const main = {
    name: 'Glucose', type: 'line', data: pts, showSymbol: false, sampling: 'lttb', z: 3,
    lineStyle: { width: o.lineWidth ?? 1.5, color: P.primary }, itemStyle: { color: P.primary },
    markArea: { silent: true, data: areas }, markLine: { silent: true, symbol: 'none', data: marks },
    emphasis: { disabled: true },
  };

  const rej = S.glucose.rejected.filter((r) => r.t >= from && r.t < to);
  const rejected = { name: 'Rejected reading', type: 'scatter', z: 5, symbol: 'diamond', symbolSize: 11, itemStyle: { color: P.bad, borderColor: P.surface, borderWidth: 1.5 }, data: rej.map((r) => [r.t, yMax - 6, r.v]), tooltip: { show: false } };
  const off = pts.filter((p) => p[1] > yMax).map((p) => [p[0], yMax - 14, p[1]]);
  const offscale = { name: 'Off scale', type: 'scatter', z: 5, symbol: 'triangle', symbolSize: 10, itemStyle: { color: P.warn }, data: off, tooltip: { show: false } };

  const al = (o.alerts || []).filter((a) => a.t >= from && a.t < to);
  const isG = (a) => a.measure === 'glucose';
  const alerts = { name: 'Alert', type: 'scatter', z: 6, symbol: 'pin', symbolSize: 26, itemStyle: { color: P.bad, borderColor: P.surface, borderWidth: 1.5 }, label: { show: true, formatter: (p) => p.data.n, color: '#fff', fontSize: 10, fontWeight: 700 },
    data: al.map((a, i) => ({ value: [a.t, yMax - 20, a.id], n: String(i + 1), a })).filter((d) => isG(d.a)), tooltip: { show: false } };
  const others = { name: 'Other alert', type: 'scatter', z: 6, symbol: 'diamond', symbolSize: 13, itemStyle: { color: P.warn, borderColor: P.surface, borderWidth: 1.5 },
    data: al.map((a, i) => ({ value: [a.t, yMin + 14, a.id], a, n: i + 1 })).filter((d) => !isG(d.a)), tooltip: { show: false } };
  const series = [main, rejected, offscale, alerts, others];

  const formatter = (params) => {
    const g = params.find((p) => p.seriesName === 'Glucose');
    const t = (g ? g.value[0] : params[0].axisValue);
    const lines = [`<b>${fmtDate(ds(t), { dow: true })} · ${fmtTime(t)}</b>`];
    if (g) lines.push(`Glucose <b>${n1(g.value[1])}</b> mg/dL`);
    const m = mealAt(t);
    if (m) lines.push(`<span style="color:${P.muted}">${Math.round((t - m.t) / 60000)} min after ${m.label}: ${m.food}</span>`);
    const al = (o.alerts || []).find((a) => Math.abs(a.t - t) <= 450000);
    if (al) lines.push(`<span style="color:${P.bad}">Alert · ${measureName(al.measure)} ${al.direction === 'above' ? 'above' : 'below'} usual (${al.size})</span>`);
    const rj = S.glucose.rejected.find((r) => Math.abs(r.t - t) < 450000);
    if (rj) lines.push(`<span style="color:${P.bad}">Rejected reading ${n1(rj.v)} mg/dL (implausible)</span>`);
    return lines.join('<br>');
  };

  return { series, formatter, yMin, yMax, points: pts };
}

export function glucoseOption(o) {
  const P = palette();
  const L = glucoseLayers(o);
  return base({
    grid: gridDefault({ top: 30, bottom: o.zoom ? 46 : 8 }),
    tooltip: { ...base().tooltip, trigger: 'axis', axisPointer: { type: 'line', lineStyle: { color: P.muted } }, formatter: L.formatter },
    xAxis: timeAxis({ min: o.from, max: o.to }),
    yAxis: valueAxis({ min: L.yMin, max: L.yMax, name: 'mg/dL', nameTextStyle: { color: P.muted, align: 'left' } }),
    dataZoom: o.zoom ? [{ type: 'inside' }, { type: 'slider', height: 20, bottom: 6, borderColor: 'transparent', fillerColor: 'rgba(14,124,112,.14)' }] : undefined,
    series: L.series,
  });
}
