// Clinical trend charts (Apache ECharts): straight lines between dated values, reference lines labelled with their rule ID, her baseline window shaded,
// hollow markers for best-guess values, and an event timeline (medicine bars, visits, diagnoses, diary) aligned under the same date axis.
import { fmtDate, ms, MON } from './ui.js';

const css = (n) => getComputedStyle(document.documentElement).getPropertyValue(n).trim();
export const palette = () => ({
  ink: css('--ink'), ink2: css('--ink-2'), muted: css('--muted'), line: css('--line'), surface: css('--surface'), surface2: css('--surface-2'),
  primary: css('--primary'), primaryInk: css('--primary-ink'), ep: css('--ep'), warn: css('--warn'), bad: css('--bad'), low: css('--low'), ok: css('--ok'), c4: css('--c4'), c5: css('--c5'), font: css('--font'),
});

const LEFT0 = 132, RIGHT0 = 150, TOP0 = 30, BOTTOM0 = 46, ROW = 20, LEFT_LANES = 132;

function lanesOf(lanes, xmin, xmax) {
  const rows = [];
  (lanes.meds || []).forEach((m) => rows.push({ type: 'med', label: m.label, m }));
  if (lanes.visits) rows.push({ type: 'visit', label: 'Clinic visits' });
  if (lanes.dx) rows.push({ type: 'dx', label: 'Diagnoses · imaging' });
  if (lanes.diary) rows.push({ type: 'diary', label: 'Diary: symptoms · care' });
  return rows;
}

export function trendChart(el, spec, lanes, events) {
  const E = window.echarts, P = palette();
  const cp = !!spec.compact, LEFT = cp ? 46 : LEFT0, RIGHT = cp ? 14 : RIGHT0, TOP = cp ? 12 : TOP0, BOTTOM = cp ? 26 : BOTTOM0;
  const rows = lanesOf(lanes, spec.xmin, spec.xmax);
  const laneH = rows.length ? rows.length * ROW + 10 : 0, gap = rows.length ? 16 : 0;
  const H = el.clientHeight || 400;
  const mainH = H - TOP - BOTTOM - laneH - gap;
  const laneTop = TOP + mainH + gap;

  // y range: the data plus the reference lines that are not far outside it
  const vals = spec.lines.flatMap((l) => l.pts.map((p) => p[1])).concat((spec.extra || []).flatMap((l) => l.pts.map((p) => p[1])));
  let lo = Math.min(...vals), hi = Math.max(...vals);
  const span = hi - lo || Math.abs(hi) * 0.2 || 1;
  // every defined threshold is drawn; one so far from the data that it would flatten the line goes to spec.offscale (listed under the chart)
  const lo0 = lo, hi0 = hi; spec.offscale = [];
  for (const r of spec.refs || []) { if (r.y >= lo0 - 4 * span && r.y <= hi0 + 4 * span) { lo = Math.min(lo, r.y); hi = Math.max(hi, r.y); } else spec.offscale.push(r); }
  if (spec.band) { lo = Math.min(lo, spec.band.lo); hi = Math.max(hi, spec.band.hi); }
  const padY = (hi - lo) * 0.1 || 1;
  const raw = (hi + padY * 1.2 - (lo - padY)) / 5, mag = 10 ** Math.floor(Math.log10(raw)), fr = raw / mag, step = (fr <= 1 ? 1 : fr <= 2 ? 2 : fr <= 2.5 ? 2.5 : fr <= 5 ? 5 : 10) * mag;
  const ymin = spec.yMin != null ? spec.yMin : Math.floor((lo - padY) / step) * step, ymax = Math.ceil((hi + padY * 1.2) / step) * step;

  const markLines = (spec.refs || []).filter((r) => !spec.offscale.includes(r)).map((r, i) => ({
    yAxis: r.y, lineStyle: { color: r.tone === 'goal' ? P.primaryInk : P.ink2, type: 'dashed', width: 1.2, opacity: 0.8 },
    label: { show: !cp, formatter: r.label, position: 'end', align: 'left', color: r.tone === 'goal' ? P.primaryInk : P.ink2, fontSize: 11, fontWeight: 600 },
  }));
  if (spec.dx && spec.dx >= spec.xmin && spec.dx <= spec.xmax) markLines.push({ xAxis: spec.dx, lineStyle: { color: P.ink, type: 'solid', width: 1.3, opacity: 0.7 }, label: { show: !cp, formatter: 'Type 2 diabetes diagnosed', position: 'insideStartTop', rotate: 90, color: P.ink, fontSize: 11, fontWeight: 600, distance: 4 } });
  if (spec.baseline) markLines.push([{ coord: [spec.baseline.from, spec.baseline.value], lineStyle: { color: P.primaryInk, type: 'solid', width: 2, opacity: 0.9 }, label: { show: false } }, { coord: [spec.baseline.to, spec.baseline.value] }]);
  const markAreas = [];
  const ZC = { green: 'rgba(56,160,108,.13)', amber: 'rgba(224,160,42,.17)', red: 'rgba(217,59,43,.13)' };
  (spec.zones || []).forEach((z) => markAreas.push([{ yAxis: z.from == null ? ymin : z.from, itemStyle: { color: ZC[z.signal] }, label: { show: false } }, { yAxis: z.to == null ? ymax : z.to }]));
  if (spec.band) markAreas.push([{ yAxis: spec.band.lo, itemStyle: { color: 'rgba(56,160,108,.10)' }, label: { show: !cp, formatter: spec.band.label, position: 'insideBottomLeft', color: P.ink2, fontSize: 11 } }, { yAxis: spec.band.hi }]);
  (spec.windows || []).forEach((w) => markAreas.push([{ xAxis: w.from, itemStyle: { color: w.color || 'rgba(155,133,144,.16)' }, label: { show: !cp && !!w.label, formatter: w.label, position: 'insideTop', color: P.primaryInk, fontSize: 11, fontWeight: 600 } }, { xAxis: w.to }]));

  const line = (l, i) => ({
    type: 'line', name: l.name, xAxisIndex: 0, yAxisIndex: 0, z: 4, silent: false, smooth: false, connectNulls: false,
    showSymbol: l.kind !== 'daily', symbol: l.symbol || 'circle', symbolSize: l.kind === 'daily' ? 4 : (cp ? 6 : 10),
    lineStyle: { color: l.color, width: l.kind === 'daily' ? 1.5 : 2.2, type: l.dashed ? 'dashed' : 'solid', opacity: l.kind === 'daily' ? 0.95 : 1 }, itemStyle: { color: l.color },
    sampling: l.kind === 'daily' ? 'lttb' : undefined,
    data: l.pts.map((p) => ({ value: [ms(p[0]), p[1]], d: p[0], b: p[2], itemStyle: p[2] && p[2] !== 'data' ? { color: P.surface, borderColor: l.color, borderWidth: 2.4 } : { color: l.color, borderColor: P.surface, borderWidth: 1.5 } })),
    ...(i === 0 ? { markLine: { silent: true, symbol: 'none', animation: false, data: markLines }, markArea: { silent: true, data: markAreas } } : {}),
  });
  const series = spec.lines.map(line).concat((spec.extra || []).map((l, i) => ({ ...line({ ...l, kind: 'lab' }, 99), z: 3, symbolSize: 11, symbol: 'diamond', data: l.pts.map((p) => ({ value: [ms(p[0]), p[1]], d: p[0], b: p[2], extraNote: l.note, itemStyle: { color: P.surface, borderColor: l.color, borderWidth: 2.2 } })) })));

  // ---- the event lanes
  const cats = rows.map((r) => r.label);
  const medColors = [P.ink2, P.low, P.ep, P.c4, P.c5];
  rows.forEach((r, ri) => {
    if (r.type === 'med') {
      const s = Math.max(ms(r.m.start), spec.xmin), e = Math.min(r.m.end ? ms(r.m.end) : spec.xmax, spec.xmax);
      if (e <= spec.xmin || s >= spec.xmax) return;
      const color = medColors[ri % medColors.length];
      series.push({ type: 'custom', xAxisIndex: 1, yAxisIndex: 1, z: 2, silent: false, name: 'medicine',
        renderItem: (params, api) => { const a = api.coord([api.value(1), api.value(0)]), b = api.coord([api.value(2), api.value(0)]), hh = api.size([0, 1])[1] * 0.58;
          const rect = E.graphic.clipRectByRect({ x: a[0], y: a[1] - hh / 2, width: b[0] - a[0], height: hh }, { x: params.coordSys.x, y: params.coordSys.y, width: params.coordSys.width, height: params.coordSys.height });
          return rect && { type: 'rect', shape: { ...rect, r: 4 }, style: api.style({ fill: color, opacity: r.m.end ? 0.55 : 0.85 }) }; },
        data: [{ value: [ri, s, e], tip: `${r.m.label}${r.m.status ? ' · ' + r.m.status : ''}<br>${fmtDate(r.m.start)} to ${r.m.end ? fmtDate(r.m.end) : 'now'}`, b: r.m.b }] });
    } else {
      const pick = { visit: (e) => e.kind === 'visit', dx: (e) => e.kind === 'diagnosis' || e.kind === 'imaging', diary: (e) => e.kind === 'symptom' || e.kind === 'healthcare_interaction' }[r.type];
      const sel = events.filter(pick).filter((e) => ms(e.d) >= spec.xmin && ms(e.d) <= spec.xmax);
      const shape = { visit: ['circle', 9], dx: ['triangle', 11], diary: ['circle', 6] }[r.type];
      series.push({ type: 'scatter', xAxisIndex: 1, yAxisIndex: 1, z: 3, name: r.type, symbol: shape[0], symbolSize: shape[1],
        itemStyle: { color: r.type === 'diary' ? P.muted : r.type === 'dx' ? P.ep : P.primaryInk, borderColor: P.surface, borderWidth: 1 },
        data: sel.map((e) => ({ value: [ms(e.d), ri], tip: `<b>${fmtDate(e.d)}</b><br>${e.text}`, b: e.b, symbol: e.kind === 'imaging' ? 'diamond' : shape[0], symbolSize: e.kind === 'imaging' ? 12 : shape[1], itemStyle: e.kind === 'imaging' ? { color: P.ep } : undefined })) });
    }
  });

  const xAxis = (idx, show) => ({ type: 'time', gridIndex: idx, min: spec.xmin, max: spec.xmax, axisLabel: { show: false }, axisTick: { show: false }, axisLine: { show: idx === 1 || !rows.length, lineStyle: { color: P.line } }, splitLine: { show: false }, axisPointer: { show: idx === 0, lineStyle: { color: P.ink2, opacity: 0.5 }, label: { show: true, color: P.ink, backgroundColor: P.surface2, borderColor: P.line, borderWidth: 1, padding: [4, 8], fontWeight: 600, shadowBlur: 0, formatter: (q) => fmtDate(new Date(q.value).toISOString().slice(0, 10)) } } });
  const option = {
    animation: !spec.still && !(spec.draw && matchMedia('(prefers-reduced-motion: reduce)').matches), animationDuration: spec.draw ? 1000 : 300, animationEasing: 'cubicOut', textStyle: { fontFamily: P.font, color: P.ink2 },
    grid: [{ left: LEFT, right: RIGHT, top: TOP, height: mainH }].concat(rows.length ? [{ left: LEFT, right: RIGHT, top: laneTop, height: laneH }] : []),
    xAxis: [xAxis(0)].concat(rows.length ? [xAxis(1)] : []),
    yAxis: [{ type: 'value', gridIndex: 0, min: ymin, max: ymax, interval: step, name: spec.unit, nameTextStyle: { color: P.muted, align: 'right', padding: [0, 6, 0, 0] }, axisLabel: { color: P.muted, formatter: (v) => Number(v.toFixed(spec.dec + 1)).toString() }, splitLine: { lineStyle: { color: P.line, type: [4, 6], opacity: 0.7 } }, axisLine: { show: false }, axisTick: { show: false } }]
      .concat(rows.length ? [{ type: 'category', gridIndex: 1, data: cats, inverse: true, axisLabel: { color: P.ink2, fontSize: 11, width: LEFT_LANES - 14, overflow: 'break' }, axisTick: { show: false }, axisLine: { show: false }, splitLine: { show: true, lineStyle: { color: P.line, opacity: 0.6 } } }] : []),
    tooltip: { trigger: 'item', confine: true, backgroundColor: P.surface, borderColor: P.line, borderWidth: 1, padding: [8, 10], textStyle: { color: P.ink, fontSize: 12.5 }, extraCssText: `color:${P.ink};background:${P.surface};box-shadow:0 4px 14px rgba(0,0,0,.18);`,
      formatter: (q) => {
        const d = q.data || {};
        if (d.tip) return d.tip;
        if (!d.d) return '';
        const v = Array.isArray(d.value) ? d.value[1] : d.value;
        return `<b>${fmtDate(d.d)}</b><br>${q.seriesName}: <b>${Number(v).toFixed(spec.dec)}</b> ${spec.unit}${d.extraNote ? `<br><span style="opacity:.75">${d.extraNote}</span>` : ''}`;
      } },
    dataZoom: [{ type: 'inside', xAxisIndex: rows.length ? [0, 1] : [0], filterMode: 'none', zoomOnMouseWheel: 'shift', moveOnMouseMove: true, minValueSpan: 45 * 864e5 }],
    series,
  };
  { const f = option.tooltip.formatter; option.tooltip.formatter = (q) => { const o = f(q); return o ? `<div style="color:${P.ink}">${o}</div>` : ''; }; }
  const chart = E.init(el, null, { renderer: 'canvas' });
  chart.setOption(option);

  // ---- years (or months when zoomed in) as visible blocks with a line at every boundary
  const bottomY = rows.length ? laneTop + laneH : TOP + mainH;
  let last = null;
  const place = () => {
    const W = chart.getWidth(), x0 = LEFT, x1 = W - RIGHT;
    const a = chart.convertFromPixel({ xAxisIndex: 0 }, x0), b = chart.convertFromPixel({ xAxisIndex: 0 }, x1);
    if (typeof a !== 'number' || typeof b !== 'number' || Number.isNaN(a) || Number.isNaN(b)) return;
    const months = (b - a) / (30.4 * 864e5), unit = months > 16 ? 'year' : 'month';
    const els = [], pal = palette();
    const A = new Date(a), step = (d) => (unit === 'year' ? new Date(Date.UTC(d.getUTCFullYear() + 1, 0, 1)) : new Date(Date.UTC(d.getUTCFullYear(), d.getUTCMonth() + 1, 1)));
    let cur = unit === 'year' ? new Date(Date.UTC(A.getUTCFullYear(), 0, 1)) : new Date(Date.UTC(A.getUTCFullYear(), A.getUTCMonth(), 1));
    let n = 0;
    while (cur.getTime() < b && n++ < 400) {
      const nxt = step(cur), sx = Math.max(x0, chart.convertToPixel({ xAxisIndex: 0 }, cur.getTime())), ex = Math.min(x1, chart.convertToPixel({ xAxisIndex: 0 }, nxt.getTime()));
      if (ex - sx > 16) {
        const label = unit === 'year' ? String(cur.getUTCFullYear()) : MON[cur.getUTCMonth()] + (cur.getUTCMonth() === 0 || sx === x0 ? ` ${cur.getUTCFullYear()}` : '');
        els.push({ type: 'text', silent: true, x: (sx + ex) / 2, y: bottomY + 10, style: { text: label, fill: pal.ink2, font: `600 12px ${pal.font || 'sans-serif'}`, textAlign: 'center' } });
      }
      const bx = chart.convertToPixel({ xAxisIndex: 0 }, cur.getTime());
      if (bx > x0 + 1 && bx < x1 - 1) els.push({ type: 'line', silent: true, z: 1, shape: { x1: bx, y1: TOP, x2: bx, y2: bottomY }, style: { stroke: pal.ink2, lineWidth: 1, opacity: 0.35 } });
      cur = nxt;
    }
    const sig = els.map((e) => Math.round(e.x ?? e.shape.x1)).join(',') + unit;
    if (sig === last) return;
    last = sig; chart.setOption({ graphic: { elements: els } });
  };
  chart.on('finished', place);
  chart.on('datazoom', () => { last = null; place(); });
  return chart;
}
