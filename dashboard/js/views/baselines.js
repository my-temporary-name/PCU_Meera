import { S, ms, fmtDate, n1, NAMES } from '../store.js';
import { h, card, chip, stat, toggle, legend, table } from '../ui.js';
import { mount, palette, base, timeAxis, valueAxis, gridDefault } from '../charts.js';
import { bandAreas } from './shared.js';

const TREND = { rising: ['▲ rising', 'warn'], falling: ['▼ falling', 'low'], stable: ['▬ stable', 'ok'], insufficient_history: ['not enough history', ''] };
const trendChip = (t) => { const [txt, cls] = TREND[t] || [t, '']; return h('span', { class: `chip ${cls}` }, txt); };

const decOf = (b) => (b === 'waist_hip_ratio' ? 3 : b === 'bmi' ? 2 : 1);

export function render(root, [bioArg]) {
  const all = S.baseline.biomarker_baselines;
  const bios = Object.keys(all);
  const bio = bios.includes(bioArg) ? bioArg : bios[0];
  const series = all[bio];
  const unit = (S.bands[bio] && S.bands[bio].unit) || '';
  const last = series[series.length - 1];
  const dec = bio === 'waist_hip_ratio' ? 3 : bio === 'bmi' ? 2 : 1;
  const f = (x, d = dec) => n1(x, d);
  const P = palette();

  root.append(h('div', { class: 'page-head' }, h('div', {}, h('h1', {}, 'Baselines'), h('p', {}, 'What is normal for her — a running weekly average and ±1 standard deviation band, computed from all history up to each week. The cleaner “episode-excluded” version leaves out days inside crises, festivals or illness.'))));
  root.append(h('div', { class: 'tabs' }, bios.map((b) => h('a', { href: `#/baselines/${b}`, class: b === bio ? 'on' : '' }, NAMES[b] || b))));

  root.append(h('div', { class: 'grid g4' },
    stat('Usual value (ordinary days)', f(last.mean_episode_excluded), unit),
    stat('Usual range (ordinary days)', `${f(last.typical_low_episode_excluded)} – ${f(last.typical_high_episode_excluded)}`, unit),
    stat('Average incl. every day', f(last.mean), unit),
    h('div', { class: 'stat' }, h('span', { class: 'k' }, `Trend vs 1 month ago · as of ${fmtDate(last.as_of_date, { year: true })}`), trendChip(last.trend_vs_1_month_ago))));

  const state = { ref: false, all: false };
  const chartEl = h('div', { class: 'chart tall' });
  let chart;
  const draw = () => {
    const x = (c) => ms(c.as_of_date);
    const lowConf = series.filter((c) => c.confidence === 'low');
    const refAreas = state.ref ? bandAreas(bio, Math.min(...series.map((c) => c.typical_low_episode_excluded)) * 0.8, Math.max(...series.map((c) => c.typical_high_episode_excluded)) * 1.2) : [];
    const lows = series.map((c) => c.typical_low_episode_excluded), highs = series.map((c) => c.typical_high_episode_excluded);
    const lo = Math.min(...lows), hi = Math.max(...highs);
    const pad = (hi - lo) * 0.35 || 1;
    const opt = base({
      grid: gridDefault({ top: 20, bottom: 16 }),
      tooltip: {
        ...base().tooltip, trigger: 'axis', axisPointer: { type: 'line', lineStyle: { color: P.muted } },
        formatter: (ps) => {
          const c = series.find((s) => ms(s.as_of_date) === ps[0].axisValue);
          if (!c) return '';
          return `<b>As of ${fmtDate(c.as_of_date, { year: true })}</b><br>Ordinary days: <b>${f(c.mean_episode_excluded)}</b> (${f(c.typical_low_episode_excluded)} – ${f(c.typical_high_episode_excluded)}) ${unit}<br>Every day: ${f(c.mean)} (${f(c.typical_low)} – ${f(c.typical_high)})<br><span style="color:${P.muted}">${c.n_episode_excluded.toLocaleString()} ordinary-day readings · confidence ${c.confidence} · ${(TREND[c.trend_vs_1_month_ago] || [c.trend_vs_1_month_ago])[0]}</span>`;
        },
      },
      xAxis: timeAxis({ min: ms(S.first), max: ms(S.last) + 86400000 }),
      yAxis: valueAxis({ min: Math.max(0, lo - pad * 2), max: hi + pad * 2, name: unit, nameTextStyle: { color: P.muted, align: 'left' } }),
      series: [
        { name: 'low', type: 'line', stack: 'band', symbol: 'none', lineStyle: { opacity: 0 }, data: series.map((c) => [x(c), c.typical_low_episode_excluded]), silent: true },
        { name: 'Usual range', type: 'line', stack: 'band', symbol: 'none', lineStyle: { opacity: 0 }, areaStyle: { color: P.primary, opacity: 0.16 }, data: series.map((c) => [x(c), +(c.typical_high_episode_excluded - c.typical_low_episode_excluded).toFixed(2)]), silent: true },
        state.all ? { name: 'Every-day average', type: 'line', symbol: 'none', lineStyle: { width: 1.6, type: 'dashed', color: P.muted }, data: series.map((c) => [x(c), c.mean]), z: 3 } : null,
        {
          name: 'Ordinary-day average', type: 'line', symbol: 'circle', symbolSize: 5, lineStyle: { width: 2.4, color: P.primary }, itemStyle: { color: P.primary }, data: series.map((c) => [x(c), c.mean_episode_excluded]), z: 4,
          markArea: { silent: true, data: [
            ...(lowConf.length ? [[{ xAxis: x(lowConf[0]), name: 'Low confidence', itemStyle: { color: P.muted, opacity: 0.12 }, label: { show: true, position: 'insideTop', color: P.muted, fontSize: 11 } }, { xAxis: x(lowConf[lowConf.length - 1]) }]] : []),
            ...refAreas,
          ] },
        },
      ].filter(Boolean),
    });
    if (chart) chart.setOption(opt, true); else chart = mount(chartEl, opt);
  };
  setTimeout(draw, 0);
  root.append(card(`${NAMES[bio] || bio} — weekly baseline`, `${series.length} weekly checkpoints`,
    h('div', {}, chartEl, h('div', { class: 'row', style: { marginTop: '8px' } }, legend([[P.primary, 'Ordinary-day average'], [P.primary, 'Usual range (±1 SD, ordinary days)'], [P.muted, 'Every-day average (optional)']]))),
    h('div', { class: 'row' }, toggle('Include every-day average', false, (v) => { state.all = v; draw(); }), S.bands[bio] ? toggle('Show reference ranges', false, (v) => { state.ref = v; draw(); }) : null)));

  root.append(card('All checkpoints', 'Newest first. “Low confidence” weeks have under 21 days of history.', table(
    [
      { label: 'As of', render: (c) => fmtDate(c.as_of_date, { year: true }) },
      { label: 'Ordinary-day avg', right: true, render: (c) => f(c.mean_episode_excluded) },
      { label: 'Usual range', right: true, render: (c) => `${f(c.typical_low_episode_excluded)} – ${f(c.typical_high_episode_excluded)}` },
      { label: 'Every-day avg', right: true, render: (c) => f(c.mean) },
      { label: 'Readings', right: true, render: (c) => c.n.toLocaleString() },
      { label: 'Confidence', render: (c) => h('span', { class: `chip ${c.confidence === 'high' ? 'ok' : c.confidence === 'moderate' ? 'warn' : ''}` }, c.confidence) },
      { label: 'Trend', render: (c) => trendChip(c.trend_vs_1_month_ago) },
    ], [...series].reverse())));

  root.append(card('Every biomarker at a glance', 'Latest checkpoint — click a row to switch', table(
    [
      { label: 'Biomarker', render: (b) => NAMES[b] || b },
      { label: 'Ordinary-day avg', right: true, render: (b) => `${n1(all[b][all[b].length - 1].mean_episode_excluded, decOf(b))} ${(S.bands[b] || {}).unit || ''}` },
      { label: 'Usual range', right: true, render: (b) => { const c = all[b][all[b].length - 1]; return `${n1(c.typical_low_episode_excluded, decOf(b))} – ${n1(c.typical_high_episode_excluded, decOf(b))}`; } },
      { label: 'Trend', render: (b) => trendChip(all[b][all[b].length - 1].trend_vs_1_month_ago) },
    ], bios, { onRow: (b) => { location.hash = `#/baselines/${b}`; } })));

  return [['Baselines', '#/baselines'], [NAMES[bio] || bio]];
}
