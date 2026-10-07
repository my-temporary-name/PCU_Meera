// Small presentational pieces shared by the pipeline pages.
import { h } from '../ui.js';
import { n1 } from '../store.js';

export const LABEL_TEXT = { supported: 'Supported', suggestive: 'Suggestive', not_supported: 'Not supported', insufficient: 'Insufficient', not_applicable: 'n/a', not_yet_available: 'Not yet available',
  candidate: 'Candidate', weakened: 'Weakened', retracted: 'Retracted' };
export const labelChip = (l, title) => h('span', { class: `lab ${l}`, title }, LABEL_TEXT[l] || l);

export const WORDING = {
  asserted: ['Stated as a pattern', 'The text may say it has tended to move together with the outcome'], asserted_same_day: ['Pattern, same day', 'As above, and the text must say it was the same day'],
  hedged: ['May be linked', 'The text may only say it may be linked'], hedged_same_day: ['May be linked, same day', 'May be linked, and the text must say same day'],
  exposure_only: ['Present, no link', 'The text may only say it was present'], exposure_only_history: ['Present, little history', 'Present with no link; there is not enough history yet'],
  contrary_note: ['Contrary note', 'On days with this, the outcome has tended to be lower'], event_unusual: ['Unusual event', 'How unusual this event was, in words'], artifact_note: ['Possible artifact', 'May be a sensor artifact'],
  not_mentioned: ['Not mentioned', 'Not said in the text'], not_known_yet: ['Not known yet', 'The data for it is not yet available'],
  present_only: ['Present, no link', 'The text may only say it was present'], present_only_history: ['Present, little history', 'Present, with no link; not enough history yet'],
};
export const wordingChip = (w) => h('span', { class: `wc ${w}`, title: (WORDING[w] || [])[1] }, (WORDING[w] || [w])[0]);
export const flagChips = (flags) => (flags || []).map((f) => h('span', { class: 'flag', title: f }, f.replace(/_/g, ' ')));

export function refChip(id) {
  return h('span', { class: `ref ${id[0]}`, 'data-ref': id, title: 'Hover to highlight what this sentence rests on' }, id);
}

// Hovering a reference chip highlights every element that carries that id in data-refs.
export function wireRefs(container) {
  const on = (id, add) => container.querySelectorAll(`[data-refs~="${id}"]`).forEach((el) => el.classList.toggle('hl', add));
  container.addEventListener('mouseover', (e) => { const r = e.target.closest && e.target.closest('.ref'); if (r) on(r.dataset.ref, true); });
  container.addEventListener('mouseout', (e) => { const r = e.target.closest && e.target.closest('.ref'); if (r) on(r.dataset.ref, false); });
  container.addEventListener('click', (e) => {
    const r = e.target.closest && e.target.closest('.ref');
    if (!r) return;
    const t = container.querySelector(`[data-refs~="${r.dataset.ref}"]`);
    if (t) t.scrollIntoView({ behavior: 'smooth', block: 'center' });
  });
}

// A plain definition list from an object (values rendered as text or nodes).
export function kvlist(obj, { skip = [] } = {}) {
  const rows = [];
  Object.entries(obj || {}).forEach(([k, v]) => {
    if (skip.includes(k) || v == null || v === '') return;
    if (typeof v === 'string' && v.includes('\n')) {
      rows.push(h('span', { class: 'k' }, k.replace(/_/g, ' ')), h('span', { class: 'v' }, ''), h('div', { class: 'kv-block' }, pointsBlock(v)));
      return;
    }
    rows.push(h('span', { class: 'k' }, k.replace(/_/g, ' ')), h('span', { class: 'v' }, show(v)));
  });
  return h('div', { class: 'kvlist' }, rows);
}
// Multi-line text ("HEADING:" lines followed by "  - point" lines) as headed bullet lists.
export function pointsBlock(text) {
  const out = []; let list = null;
  text.split('\n').forEach((raw) => {
    const line = raw.trimEnd(); if (!line.trim()) return;
    const m = line.match(/^\s+[-•]\s+(.*)$/);
    if (m) {
      if (!list) { list = h('ul', { class: 'points' }); out.push(list); }
      const t = m[1], c = t.match(/^([^:"]{2,40}):\s+(.*)$/);
      list.append(h('li', {}, c ? [h('b', {}, c[1] + ': '), c[2]] : t));
    } else {
      list = null;
      out.push(line.endsWith(':') ? h('div', { class: 'points-head' }, line.slice(0, -1).toLowerCase()) : h('p', { class: 'points-p' }, line));
    }
  });
  return out;
}
export function show(v) {
  if (v == null) return '—';
  if (typeof v === 'number') return n1(v, 3);
  if (typeof v === 'boolean') return v ? 'yes' : 'no';
  if (Array.isArray(v)) return v.length ? v.map((x) => (typeof x === 'object' ? JSON.stringify(x) : String(x))).join(' · ') : '—';
  if (typeof v === 'object') return Object.entries(v).map(([k, x]) => `${k.replace(/_/g, ' ')}: ${show(x)}`).join(' · ');
  return String(v);
}

export const countBar = (parts) => {
  const total = parts.reduce((a, p) => a + p.n, 0) || 1;
  return h('div', {}, h('div', { class: 'countbar' }, parts.map((p) => h('i', { style: { width: `${(100 * p.n) / total}%`, background: p.color }, title: `${p.label}: ${p.n}` }))),
    h('div', { class: 'legend-line', style: { marginTop: '6px' } }, parts.filter((p) => p.n).map((p) => h('span', {}, h('i', { style: { background: p.color } }), `${p.label} ${p.n}`))));
};

export const STATUS_COLOR = { supported: 'var(--ok)', suggestive: 'var(--warn)', not_supported: 'var(--low)', insufficient: '#b9c5c2', candidate: 'var(--ep)', weakened: 'var(--warn)', retracted: 'var(--bad)' };
