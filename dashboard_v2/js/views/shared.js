// Components reused across several views.
import { S, DAY, ms, ds, fmtDate, fmtTime, n1, NAMES, measureName } from '../store.js';
import { h, chip, table, pager } from '../ui.js';
import { palette, base, timeAxis, valueAxis, gridDefault, mount, statusColor } from '../charts.js';

export const MEAL = { breakfast: 'Breakfast', lunch: 'Lunch', dinner: 'Dinner', snack: 'Snack', light_dinner: 'Light dinner' };
export const mealLabel = (l) => MEAL[l] || (l ? l.replace(/_/g, ' ') : '');

export const alertValue = (a) => (a.value == null ? '—' : typeof a.value === 'object' ? (a.value.taken != null && a.value.expected != null ? `${a.value.taken} of ${a.value.expected} doses` : Object.values(a.value).filter((x) => typeof x === 'number').map((x) => n1(x, 0)).join('/')) : n1(a.value));
const SIZE_CLS = { far: 'bad', clearly: 'warn', slightly: '' };
export const sizeChip = (s) => h('span', { class: `chip ${SIZE_CLS[s] ?? ''}` }, s);
export const alertWhen = (a) => `${fmtDate(a.date)} · ${fmtTime(a.t)}`;

export function alertsTable(list, { pageSize = 15, empty = 'No alerts match.' } = {}) {
  const wrap = h('div', {});
  let page = 0;
  const draw = () => {
    const pages = Math.max(1, Math.ceil(list.length / pageSize));
    page = Math.min(page, pages - 1);
    const slice = list.slice(page * pageSize, (page + 1) * pageSize);
    const cols = [
      { label: 'When (IST)', render: (a) => alertWhen(a) },
      { label: 'Measure', render: (a) => h('span', {}, h('b', {}, measureName(a.measure)), ' ', h('span', { class: 'muted' }, a.direction === 'above' ? '▲ above usual' : '▼ below usual')) },
      { label: 'How far', render: (a) => sizeChip(a.size) },
      { label: 'Trigger', render: (a) => a.trigger },
      { label: 'Value', right: true, render: alertValue },
      { label: 'Rulebook rule', render: (a) => h('span', { class: 'mono' }, a.rule || '—') },
      { label: 'Packet', render: (a) => h('span', { class: `chip ${a.packet === 'ok' ? 'ok' : 'warn'}` }, a.packet || '—') },
      { label: 'Case', render: (a) => (a.case ? h('span', { class: 'chip ep' }, 'open case →') : h('span', { class: 'muted' }, a.packet === 'ok' ? '—' : 'not written up')) },
    ];
    wrap.replaceChildren(
      table(cols, slice, { onRow: (a) => { if (a.case) location.hash = `#/case/${encodeURIComponent(a.case)}`; }, empty }),
      list.length > pageSize ? pager(page, pages, (p) => { page = p; draw(); }) : null);
  };
  draw();
  return wrap;
}

export const SOURCE = { llm: ['model', 'Model text'], code_line: ['fallback', 'Code line'] };
export function sourceBadge(source, fromPrompt) {
  if (source !== 'llm') return h('span', { class: 'badge fallback', title: 'The model text failed its checks twice, so the text built by code from the structured layer is shown' }, 'Code-line fallback');
  return fromPrompt ? h('span', { class: 'badge kept', title: `Written under an earlier prompt (${fromPrompt}) and re-checked under the final checks` }, 'Model text · kept') : h('span', { class: 'badge model' }, 'Model text');
}

export function caseCard(c) {
  return h('a', { class: `card case-card ${c.mode === 'relationship' ? 'violet' : 'teal'}`, href: `#/case/${encodeURIComponent(c.id)}` },
    h('div', { class: 'row', style: { justifyContent: 'space-between', gap: '8px' } }, h('span', { class: 'muted num' }, `${fmtDate(c.date, { dow: true })} · ${fmtTime(c.t0)}`), sourceBadge(c.source)),
    h('b', {}, c.headline),
    h('div', { class: 'row', style: { gap: '6px' } },
      h('span', { class: 'chip' }, `${c.alerts} alert${c.alerts === 1 ? '' : 's'}`),
      h('span', { class: 'chip' }, `${c.versions} version${c.versions === 1 ? '' : 's'}`),
      h('span', { class: `chip ${c.mode === 'relationship' ? 'ep' : 'teal'}` }, c.mode === 'relationship' ? 'May discuss links' : 'Describes only'),
      c.p_notes ? h('span', { class: 'chip ok' }, `${c.p_notes} PI note${c.p_notes === 1 ? '' : 's'}`) : null));
}

const BAR_BIO = { sleep: 'sleep_duration', steps: 'step_count', hydration: 'hydration', screen: 'screen_time', sedentary: 'sedentary_time' };

// Daily bar chart for a lifestyle metric across a list of dates, coloured by reference status.
export function dailyBars(el, dates, key, { unit = '', decimals = 0, getter } = {}) {
  const P = palette();
  const get = getter || ((d) => S.daily[d] && S.daily[d][key]);
  const data = dates.map((d) => {
    const v = get(d);
    const st = S.daily[d] && S.daily[d].st && S.daily[d].st[key];
    return { value: [ms(d) + DAY / 2, v == null ? null : v], itemStyle: { color: st ? statusColor(st) : P.primary, borderRadius: [3, 3, 0, 0], opacity: 0.9 }, st };
  });
  const bio = BAR_BIO[key];
  const normal = bio && S.bands[bio] ? S.bands[bio].bands.find((b) => b[2] === 'normal') : null;
  const dataMax = Math.max(0, ...data.map((d) => d.value[1] || 0));
  const yTop = Math.ceil(Math.max(dataMax, normal && normal[1] != null ? normal[1] : 0) * 1.12) || 1;
  return mount(el, base({
    grid: gridDefault({ top: 12, bottom: 4 }),
    tooltip: {
      ...base().tooltip, trigger: 'axis', axisPointer: { type: 'shadow' },
      formatter: (ps) => {
        const p = ps[0];
        const d = ds(p.value[0]);
        return `<b>${fmtDate(d, { dow: true })}</b><br>${n1(p.value[1], decimals)} ${unit}${p.data.st ? ' · ' + p.data.st.replace('_', ' ') : ''}`;
      },
    },
    xAxis: timeAxis({ min: ms(dates[0]), max: ms(dates[dates.length - 1]) + DAY }),
    yAxis: valueAxis({ splitNumber: 3, min: 0, max: yTop }),
    series: [{
      type: 'bar', data, barMaxWidth: 18,
      markArea: normal ? { silent: true, data: [[{ yAxis: normal[0] ?? 0, itemStyle: { color: P.ok, opacity: 0.09 } }, { yAxis: Math.min(normal[1] ?? yTop, yTop) }]] } : undefined,
    }],
  }));
}

// Reference-band shading for a biomarker, clamped to [lo, hi] so it never stretches the axis.
export function bandAreas(bio, lo, hi) {
  const P = palette();
  const spec = S.bands[bio];
  if (!spec) return [];
  const colors = { normal: [P.ok, 0.11], borderline: [P.warn, 0.14], abnormal: [P.bad, 0.07] };
  return spec.bands
    .map(([a, b, kind]) => [Math.max(a ?? lo, lo), Math.min(b ?? hi, hi), kind])
    .filter(([a, b]) => b > a)
    .map(([a, b, kind]) => [{ yAxis: a, itemStyle: { color: colors[kind][0], opacity: colors[kind][1] } }, { yAxis: b }]);
}
