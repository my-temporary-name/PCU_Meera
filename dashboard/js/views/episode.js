import { S, DAY, ms, ds, fmtDate, monthName, n1, eventsInRange, addDays } from '../store.js';
import { h, card, stat, legend, icon } from '../ui.js';
import { mount, glucoseOption, palette } from '../charts.js';
import { eventsTable, dailyBars } from './shared.js';

export function render(root, [id]) {
  const ep = S.epById.get(id);
  if (!ep) {
    root.append(card('Episode not found', null, h('a', { href: '#/episodes' }, 'Browse all episodes')));
    return [['Episodes', '#/episodes'], [id || '—']];
  }
  const P = palette();
  const { start, end } = ep.date_range;
  const days = [];
  for (let d = start; d <= end; d = addDays(d, 1)) days.push(d);
  const list = S.episodeList;
  const i = list.indexOf(ep);
  const prev = list[i - 1], next = list[i + 1];
  const events = ep.linked_event_ids.map((x) => S.eventById.get(x)).filter(Boolean);

  root.append(h('div', { class: 'page-head' },
    h('div', {},
      h('div', { class: 'row', style: { gap: '8px', marginBottom: '6px' } }, h('span', { class: 'chip ep' }, ep.type === 'risk_convergence' ? 'Risk convergence' : 'Diary-led episode'), h('span', { class: 'chip' }, ep.episode_id)),
      h('h1', {}, ep.title),
      h('p', {}, start === end ? fmtDate(start, { dow: true, year: true }) : `${fmtDate(start, { dow: true })} → ${fmtDate(end, { dow: true, year: true })} · ${days.length} days`)),
    h('div', { class: 'row' },
      prev && h('a', { class: 'btn icon', href: `#/episode/${prev.episode_id}`, title: 'Previous episode' }, icon('left')),
      h('a', { class: 'btn', href: `#/week/${start}` }, 'Open week'),
      next && h('a', { class: 'btn icon', href: `#/episode/${next.episode_id}`, title: 'Next episode' }, icon('right')))));

  root.append(h('div', { class: 'grid g4' },
    stat('Glucose events', ep.n_events),
    stat('Average glucose', n1(ep.glucose_avg_across_episode), 'mg/dL'),
    stat('Peak glucose', n1(ep.glucose_peak_across_episode), 'mg/dL'),
    stat('Average sleep', n1(ep.sleep_avg_across_episode), 'h'),
    stat('Medication adherence', n1(ep.adherence_avg_across_episode), '%'),
    ep.steps_avg_across_episode != null ? stat('Average steps', n1(ep.steps_avg_across_episode, 0)) : null));

  const pad = days.length < 3 ? DAY : 0;
  const from = ms(start) - pad, to = ms(end) + DAY + pad;
  const chartEl = h('div', { class: 'chart tall' });
  root.append(card('Glucose across the episode', 'Violet = the episode · red = its glucose events · dashed = meals · green band = her usual range',
    h('div', {}, chartEl, h('div', { style: { marginTop: '8px' } }, legend([[P.primary, 'Glucose'], [P.ep, 'Episode window'], [P.bad, 'Glucose event']])))));
  setTimeout(() => mount(chartEl, glucoseOption({ from, to, episodes: [ep], focusEpisode: ep.episode_id, events: eventsInRange(from, to), zoom: days.length > 3 })), 0);

  if (days.length > 1) {
    const grid = h('div', { class: 'grid g3' });
    [['sleep', 'Sleep', 'h', 1], ['steps', 'Steps', '', 0], ['screen', 'Screen time', 'h', 1]].forEach(([key, label, unit, dec]) => {
      const el = h('div', { class: 'chart mini' });
      grid.append(h('div', { class: 'card flat' }, h('h3', {}, label), el));
      setTimeout(() => dailyBars(el, days, key, { unit, decimals: dec }), 0);
    });
    root.append(card('Daily context during the episode', null, grid));
  }

  root.append(h('div', { class: 'grid', style: { gridTemplateColumns: 'minmax(0,1fr) minmax(0,1fr)' } },
    card('Diary notes', 'Entries within this episode, in order', ep.diary_notes && ep.diary_notes.length ? h('ol', { class: 'notes' }, ep.diary_notes.map((n) => h('li', {}, n))) : h('div', { class: 'muted' }, 'No diary notes.')),
    contextCard(start, end)));

  root.append(card(`Linked glucose events (${events.length})`, 'Click a row for the full event', eventsTable(events, { pageSize: 12 })));
  return [['Episodes', '#/episodes'], [monthName(ep.month, true), `#/month/${ep.month}`], [ep.title]];
}

function contextCard(start, end) {
  const rows = S.context.filter((c) => c.date >= start && c.date <= end);
  return card('Recorded life & symptom events', 'From the context log during these dates',
    rows.length ? h('div', { class: 'stack', style: { gap: '8px' } }, rows.map((c) => h('div', {}, h('div', {}, h('span', { class: 'chip' }, c.category.replace(/_/g, ' ')), ' ', h('span', { class: 'muted' }, fmtDate(c.date))), h('div', { class: 'ink2' }, c.description, c.note ? ` — ${c.note}` : '')))) : h('div', { class: 'muted' }, 'Nothing logged.'));
}
