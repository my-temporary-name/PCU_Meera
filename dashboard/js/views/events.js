import { S, ms, fmtDate, n1, monthName } from '../store.js';
import { h, card, legend } from '../ui.js';
import { mount, palette, base, timeAxis, valueAxis, gridDefault, statusColor } from '../charts.js';
import { eventsTable, mealLabel } from './shared.js';

export function render(root) {
  const P = palette();
  const f = { month: '', type: '', status: '', diary: '', q: '', sort: 'date' };

  const select = (key, label, opts) => {
    const el = h('select', { onchange: (e) => { f[key] = e.target.value; apply(); }, 'aria-label': label }, h('option', { value: '' }, label), opts.map(([v, t]) => h('option', { value: v }, t)));
    return el;
  };
  const search = h('input', { type: 'search', placeholder: 'Search food or diary…', oninput: (e) => { f.q = e.target.value.toLowerCase(); apply(); } });
  const count = h('span', { class: 'muted' });
  const chartEl = h('div', { class: 'chart' });
  const tableHost = h('div', {});

  root.append(h('div', { class: 'page-head' }, h('div', {}, h('h1', {}, 'Glucose events'), h('p', {}, 'Every grouped glucose excursion (readings tagged high or low), with the context recorded for that day.'))));
  root.append(card(null, null, h('div', { class: 'row' },
    select('month', 'All months', S.months.map((m) => [m, monthName(m, true)])),
    select('type', 'All types', [['meal_linked', 'Meal-linked'], ['non_meal', 'No meal nearby'], ['non_glucose_biomarker', 'Other biomarker']]),
    select('status', 'All statuses', [['high', 'High'], ['low', 'Low']]),
    select('diary', 'Any diary context', [['yes', 'Has diary note'], ['no', 'No diary note']]),
    select('sort', 'Sort: date', [['peak', 'Sort: highest peak'], ['readings', 'Sort: most readings']]),
    search, count)));
  root.append(card('Events across the year', 'Each dot is one event, sized by number of readings. Click a dot to open it.', h('div', {}, chartEl, h('div', { style: { marginTop: '8px' } }, legend([[P.bad, 'High'], [P.low, 'Low']])))));
  root.append(card('Event list', null, tableHost));

  let chart;
  function filtered() {
    let list = S.events.filter((e) => {
      if (f.month && e.month !== f.month) return false;
      if (f.type && e.type !== f.type) return false;
      if (f.status && e.status !== f.status) return false;
      if (f.diary === 'yes' && !e.short_term_context.has_diary_context) return false;
      if (f.diary === 'no' && e.short_term_context.has_diary_context) return false;
      if (f.q) {
        const hay = `${e.food_description || ''} ${e.short_term_context.diary_note || ''}`.toLowerCase();
        if (!hay.includes(f.q)) return false;
      }
      return true;
    });
    if (f.sort === 'peak') list = [...list].sort((a, b) => (b.glucose_peak ?? 0) - (a.glucose_peak ?? 0));
    if (f.sort === 'readings') list = [...list].sort((a, b) => (b.n_readings ?? 0) - (a.n_readings ?? 0));
    return list;
  }
  function apply() {
    const list = filtered();
    count.textContent = `${list.length} of ${S.events.length} events`;
    tableHost.replaceChildren(eventsTable(list, { pageSize: 20 }));
    const pts = list.filter((e) => e.win && e.glucose_peak != null).map((e) => ({ value: [e.win[0], Math.min(e.glucose_peak, 320), e.n_readings], ev: e, itemStyle: { color: statusColor(e.status), opacity: 0.75 } }));
    const opt = base({
      grid: gridDefault({ top: 16, bottom: 40 }),
      tooltip: {
        ...base().tooltip, trigger: 'item',
        formatter: (p) => { const e = p.data.ev; return `<b>${fmtDate(e.ist_date, { dow: true })}</b> · ${e.meal_label ? mealLabel(e.meal_label) : 'no meal'}<br>Peak <b>${n1(e.glucose_peak)}</b> mg/dL · ${e.n_readings} readings<br>${e.food_description || ''}`; },
      },
      xAxis: timeAxis({ min: ms(S.first), max: ms(S.last) + 86400000 }),
      yAxis: valueAxis({ name: 'peak mg/dL', nameTextStyle: { color: P.muted, align: 'left' }, scale: true }),
      dataZoom: [{ type: 'inside' }, { type: 'slider', height: 18, bottom: 6, borderColor: 'transparent', fillerColor: 'rgba(14,124,112,.14)' }],
      series: [{ type: 'scatter', data: pts, symbolSize: (v) => 6 + Math.sqrt(v[2]) * 1.6 }],
    });
    if (chart) chart.setOption(opt, true);
    else {
      chart = mount(chartEl, opt);
      chart.on('click', (p) => { if (p.data && p.data.ev) location.hash = `#/event/${p.data.ev.event_id}`; });
    }
  }
  setTimeout(apply, 0);
  return [['Glucose events']];
}
