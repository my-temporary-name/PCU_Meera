import { S, DAY, ms, fmtDate, fmtTime, monthName, n1, NAMES, eventsInRange } from '../store.js';
import { h, card, chip, stat, segmented, legend, icon } from '../ui.js';
import { mount, glucoseOption, palette } from '../charts.js';
import { mealLabel } from './shared.js';

const FACTOR_KEY = { sleep_duration: 'sleep', step_count: 'steps', hydration: 'hydration', sedentary_time: 'sedentary', screen_time: 'screen' };

export function render(root, [id]) {
  const e = S.eventById.get(id);
  if (!e) {
    root.append(card('Event not found', null, h('a', { href: '#/events' }, 'Browse all events')));
    return [['Events', '#/events'], [id || '—']];
  }
  const idx = S.events.indexOf(e);
  const ctx = e.short_term_context || {};
  const ep = e.ep ? S.epById.get(e.ep) : null;
  const factors = new Map((ctx.other_disturbed_factors || []).map((f) => [f.biomarker, f]));

  const prev = S.events[idx - 1], next = S.events[idx + 1];
  root.append(h('div', { class: 'page-head' },
    h('div', {},
      h('div', { class: 'row', style: { gap: '8px', marginBottom: '6px' } }, chip(e.status), e.type === 'meal_linked' ? h('span', { class: 'chip primary' }, `After ${mealLabel(e.meal_label).toLowerCase()}`) : e.type === 'non_meal' ? h('span', { class: 'chip' }, 'No meal nearby') : h('span', { class: 'chip' }, 'Other biomarker'),
        ep && h('a', { href: `#/episode/${ep.episode_id}` }, h('span', { class: 'chip ep' }, 'Episode: ', ep.title))),
      h('h1', {}, e.type === 'non_glucose_biomarker' ? `${NAMES[e.biomarker] || e.biomarker} event` : 'Glucose event'),
      h('p', {}, e.win ? `${fmtDate(e.ist_date, { dow: true, year: true })} · ${fmtTime(e.win[0])}${e.win[1] > e.win[0] ? ' – ' + fmtTime(e.win[1]) : ''} IST · ${e.event_id}` : `${fmtDate(e.date, { dow: true, year: true })} · ${e.event_id}`)),
    h('div', { class: 'row' },
      prev && h('a', { class: 'btn icon', href: `#/event/${prev.event_id}`, title: 'Previous event' }, icon('left')),
      h('a', { class: 'btn', href: `#/week/${e.ist_date}` }, 'Open week'),
      next && h('a', { class: 'btn icon', href: `#/event/${next.event_id}`, title: 'Next event' }, icon('right')))));

  if (e.type === 'non_glucose_biomarker') {
    root.append(h('div', { class: 'grid g4' }, stat(NAMES[e.biomarker] || e.biomarker, n1(e.value), e.unit), stat('Status', e.status.replace('_', ' '))));
  } else {
    root.append(h('div', { class: 'grid g4' },
      stat('Peak glucose', n1(e.glucose_peak), 'mg/dL'),
      stat('Average glucose', n1(e.glucose_avg), 'mg/dL'),
      stat('Readings in event', e.n_readings, 'x 15 min'),
      stat('Meal', e.meal_label ? mealLabel(e.meal_label) : '—', mealTime(e))));
    root.append(chartCard(e, ep));
  }

  if (e.food_description) root.append(card('What she ate', null, h('div', { style: { fontSize: '16px' } }, e.food_description)));

  // context
  const tile = (label, valueNodes, key) => {
    const f = key && [...factors.values()].find((x) => FACTOR_KEY[x.biomarker] === key);
    return h('div', { class: 'stat' }, h('span', { class: 'k' }, label), h('span', { class: 'v num' }, valueNodes), f ? chip(f.status) : null);
  };
  const mood = ctx.mood && h('div', { class: 'mood' }, ['morning', 'afternoon', 'evening'].map((b) => (ctx.mood[b] ? h('span', { title: b, class: moodClass(ctx.mood[b]) }, `${b[0].toUpperCase()}: ${ctx.mood[b].replace(/_/g, ' ')}`) : null)));
  root.append(card('Same-day context', `Everything else recorded for ${fmtDate(e.date, { dow: true, year: true })}`,
    h('div', { class: 'stack' },
      h('div', { class: 'grid g4' },
        tile('Sleep', [`${n1(ctx.sleep_hours)}`, h('small', {}, ` h${ctx.sleep_quality ? ' · ' + ctx.sleep_quality : ''}`)], 'sleep'),
        tile('Steps', n1(ctx.steps, 0), 'steps'),
        tile('Hydration', [n1(ctx.hydration_ml, 0), h('small', {}, ' ml')], 'hydration'),
        tile('Screen time', [n1(ctx.screen_time_hours), h('small', {}, ' h')], 'screen'),
        tile('Sedentary', [n1(ctx.sedentary_minutes, 0), h('small', {}, ' min')], 'sedentary'),
        tile('Medication adherence', [n1(ctx.adherence_pct, 0), h('small', {}, ' %')]),
        tile('Location', (ctx.location || '—').replace(/_/g, ' ')),
        h('div', { class: 'stat' }, h('span', { class: 'k' }, 'Mood'), mood || '—')),
      factors.size ? h('div', {}, h('h3', { style: { marginBottom: '8px' } }, 'Other measures outside their reference range that day'),
        h('div', { class: 'row', style: { gap: '8px' } }, [...factors.values()].map((f) => h('span', { class: 'row', style: { gap: '6px' } }, h('span', {}, NAMES[f.biomarker] || f.biomarker, ' ', h('b', { class: 'num' }, n1(f.value), ' ', S.bands[f.biomarker] ? S.bands[f.biomarker].unit : '')), chip(f.status))))) : h('div', { class: 'muted' }, 'No other measure was outside its reference range that day.'))));

  // diary
  const diary = S.diaryByDate.get(e.date);
  root.append(card('Diary', diary ? `${fmtDate(e.date, { dow: true, year: true })}${diary.title ? ' · ' + diary.title : ''}` : null,
    h('div', { class: 'stack', style: { gap: '8px' } },
      ctx.diary_note ? h('blockquote', { style: { margin: 0, padding: '8px 14px', borderLeft: '3px solid var(--primary)', fontSize: '15px' } }, ctx.diary_note) : h('div', { class: 'muted' }, 'No diary note was attached to this event.'),
      diary && diary.lines.length ? h('details', { class: 'diary' }, h('summary', {}, 'Full diary entry for the day'), diary.lines.map((l) => h('p', {}, l))) : null)));

  if (e.ist_date !== e.date) root.append(h('div', { class: 'callout' }, `Note: the event window falls on ${fmtDate(e.ist_date, { year: true })} (IST) while its context data is recorded against ${fmtDate(e.date, { year: true })}.`));
  return [['Full year', '#/year'], [monthName(e.month, true), `#/month/${e.month}`], [e.event_id]];
}

function moodClass(label) {
  const m = { content: 'calm_stable', calm: 'calm_stable', focused: 'calm_stable', tired: 'tired_low_energy', low_energy: 'tired_low_energy', foggy: 'tired_low_energy', happy: 'positive_uplifted', relieved: 'positive_uplifted', proud: 'positive_uplifted', grateful: 'positive_uplifted', mild_stress: 'mild_stress', distracted: 'mild_stress', irritable: 'mild_stress', worried: 'anxious', anxious: 'anxious', mild_anxiety: 'anxious', stressed_acute: 'overwhelmed_high_distress', overwhelmed: 'overwhelmed_high_distress', frightened: 'overwhelmed_high_distress' };
  return m[label] || '';
}

function mealTime(e) {
  if (!e.meal_label || !e.win) return '';
  const m = S.meals.filter((x) => x.label === e.meal_label && x.t <= e.win[0] && e.win[0] - x.t <= 150 * 60000).pop();
  return m ? `at ${fmtTime(m.t)}` : '';
}

function chartCard(e, ep) {
  const P = palette();
  const chartEl = h('div', { class: 'chart' });
  let mode = 'window';
  let chart;
  const draw = () => {
    const dayStart = ms(e.ist_date);
    const from = mode === 'window' ? e.win[0] - 3 * 3600000 : dayStart;
    const to = mode === 'window' ? e.win[1] + 3 * 3600000 : dayStart + DAY;
    const evs = eventsInRange(from, to);
    const opt = glucoseOption({ from, to, episodes: ep ? [ep] : [], events: evs, focusEvent: e.event_id, zoom: false });
    if (chart) chart.setOption(opt, true);
    else chart = mount(chartEl, opt);
  };
  setTimeout(draw, 0);
  const seg = segmented([['window', 'Around the event'], ['day', 'Full day']], mode, (v) => { mode = v; draw(); });
  return card('Glucose around this event', 'Highlighted red = this event · dashed lines = meals · green band = her usual range', h('div', {}, chartEl, h('div', { style: { marginTop: '8px' } }, legend([[P.primary, 'Glucose'], [P.bad, 'This event'], [P.ep, 'Episode']]))), seg);
}
