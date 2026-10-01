import { S, DAY, ms, fmtDate, monthName, n1 } from '../store.js';
import { h, card, legend } from '../ui.js';
import { mount, palette, base, timeAxis, gridDefault } from '../charts.js';
import { episodeCard } from './shared.js';

export function render(root) {
  const P = palette();
  const eps = [...S.episodeList].sort((a, b) => a.date_range.start.localeCompare(b.date_range.start));
  const laneEnd = [];
  const data = eps.map((e) => {
    const s = ms(e.date_range.start), t = ms(e.date_range.end) + DAY;
    let lane = laneEnd.findIndex((end) => end <= s);
    if (lane < 0) { lane = laneEnd.length; laneEnd.push(0); }
    laneEnd[lane] = t;
    return { value: [s, t, lane, e.title, e.episode_id], ep: e };
  });
  const lanes = laneEnd.length;

  root.append(h('div', { class: 'page-head' }, h('div', {}, h('h1', {}, 'Episodes'), h('p', {}, `${eps.length} stories drawn from the diary, each linking the glucose events that happened inside it.`))));

  const chartEl = h('div', { class: 'chart', style: { height: `${90 + lanes * 36}px` } });
  root.append(card('Timeline of the year', 'Each bar is one episode. Click a bar to open it.', h('div', {}, chartEl, h('div', { style: { marginTop: '8px' } }, legend([[P.ep, 'Diary-led episode'], [P.bad, 'Risk convergence']])))));
  setTimeout(() => {
    const chart = mount(chartEl, base({
      grid: gridDefault({ top: 8, bottom: 42 }),
      tooltip: { ...base().tooltip, trigger: 'item', formatter: (p) => { const e = p.data.ep; return `<b>${e.title}</b><br>${fmtDate(e.date_range.start)} → ${fmtDate(e.date_range.end, { year: true })}<br>${e.n_events} events · avg glucose ${n1(e.glucose_avg_across_episode)} mg/dL`; } },
      xAxis: timeAxis({ min: ms(S.first), max: ms(S.last) + DAY, splitLine: { show: true, lineStyle: { color: P.line } } }),
      yAxis: { type: 'value', min: -0.6, max: lanes - 0.4, inverse: true, show: false },
      dataZoom: [{ type: 'inside', yAxisIndex: [] }, { type: 'slider', height: 18, bottom: 6, borderColor: 'transparent', fillerColor: 'rgba(14,124,112,.14)' }],
      series: [{
        type: 'custom', data, encode: { x: [0, 1], y: 2 },
        renderItem: (params, api) => {
          const a = api.coord([api.value(0), api.value(2)]);
          const b = api.coord([api.value(1), api.value(2)]);
          const hgt = api.size([0, 1])[1] * 0.74;
          const w = Math.max(b[0] - a[0], 4);
          const ep = data[params.dataIndex].ep;
          const color = ep.type === 'risk_convergence' ? P.bad : P.ep;
          const rect = { type: 'rect', shape: { x: a[0], y: a[1] - hgt / 2, width: w, height: hgt, r: 5 }, style: { fill: color, opacity: 0.85 } };
          const children = [rect];
          if (w > 70) children.push({ type: 'text', style: { x: a[0] + 8, y: a[1], text: api.value(3), fill: '#fff', fontSize: 11, fontWeight: 600, width: w - 12, overflow: 'truncate', verticalAlign: 'middle' } });
          return { type: 'group', children };
        },
      }],
    }));
    chart.on('click', (p) => { location.hash = `#/episode/${p.data.value[4]}`; });
  }, 0);

  S.months.forEach((ym) => {
    const list = S.episodesByMonth.get(ym) || [];
    if (!list.length) return;
    root.append(card(monthName(ym), `${list.length} episodes · ${(S.unlinked[ym] || {}).count ?? 0} glucose events were outside any episode`, h('div', { class: 'grid g-auto' }, list.map(episodeCard))));
  });
  return [['Episodes']];
}
