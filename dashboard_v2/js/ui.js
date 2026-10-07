// Tiny DOM helpers + shared presentational components.
import { n1 } from './store.js';

export function h(tag, props, ...kids) {
  const el = document.createElement(tag);
  for (const [k, v] of Object.entries(props || {})) {
    if (v == null || v === false) continue;
    if (k === 'class') el.className = v;
    else if (k === 'html') el.innerHTML = v;
    else if (k.startsWith('on')) el.addEventListener(k.slice(2), v);
    else if (k === 'style' && typeof v === 'object') Object.assign(el.style, v);
    else el.setAttribute(k, v === true ? '' : v);
  }
  append(el, kids);
  return el;
}
export function append(el, kids) {
  for (const k of kids.flat(Infinity)) {
    if (k == null || k === false) continue;
    el.append(k.nodeType ? k : document.createTextNode(String(k)));
  }
  return el;
}
export const link = (href, ...kids) => h('a', { href }, ...kids);

export const ICON = {
  year: '<path d="M3 12h4l3-8 4 16 3-8h4"/>',
  month: '<rect x="3" y="5" width="18" height="16" rx="3"/><path d="M8 3v4M16 3v4M3 10h18"/>',
  week: '<rect x="3" y="5" width="18" height="16" rx="3"/><path d="M3 10h18M8 14h2M12 14h2M16 14h2"/>',
  episode: '<path d="M3 7h10M3 12h18M3 17h13"/>',
  event: '<circle cx="12" cy="12" r="8"/><path d="M12 8v4l3 2"/>',
  base: '<path d="M3 17c3-8 6-8 9-3s6 3 9-6"/><path d="M3 21h18"/>',
  lab: '<path d="M9 3h6M10 3v6l-5 9a2 2 0 0 0 2 3h10a2 2 0 0 0 2-3l-5-9V3"/>',
  data: '<ellipse cx="12" cy="6" rx="8" ry="3"/><path d="M4 6v6c0 1.7 3.6 3 8 3s8-1.3 8-3V6M4 12v6c0 1.7 3.6 3 8 3s8-1.3 8-3v-6"/>',
  flow: '<circle cx="5" cy="6" r="2.5"/><circle cx="19" cy="12" r="2.5"/><circle cx="5" cy="18" r="2.5"/><path d="M7.5 6h4a3 3 0 0 1 3 3v0M7.5 18h4a3 3 0 0 0 3-3v0"/>',
  case: '<rect x="4" y="4" width="16" height="16" rx="3"/><path d="M8 9h8M8 13h8M8 17h5"/>',
  pi: '<path d="M4 7c4-4 8-4 16 0M7 7v12M17 7v12"/>',
  check: '<circle cx="12" cy="12" r="9"/><path d="M8 12.5l3 3 5-6"/>',
  moon: '<path d="M20 14.5A8 8 0 0 1 9.5 4 8 8 0 1 0 20 14.5z"/>',
  sun: '<circle cx="12" cy="12" r="4"/><path d="M12 2v2M12 20v2M2 12h2M20 12h2M5 5l1.5 1.5M17.5 17.5L19 19M5 19l1.5-1.5M17.5 6.5L19 5"/>',
  print: '<path d="M7 9V3h10v6M7 17H4v-6h16v6h-3M7 14h10v7H7z"/>',
  left: '<path d="M15 5l-7 7 7 7"/>',
  right: '<path d="M9 5l7 7-7 7"/>',
};
export function icon(name) {
  const s = document.createElementNS('http://www.w3.org/2000/svg', 'svg');
  s.setAttribute('viewBox', '0 0 24 24');
  s.setAttribute('fill', 'none');
  s.setAttribute('stroke', 'currentColor');
  s.setAttribute('stroke-width', '1.8');
  s.setAttribute('stroke-linecap', 'round');
  s.setAttribute('stroke-linejoin', 'round');
  s.innerHTML = ICON[name] || '';
  return s;
}

export const STATUS = {
  normal: { label: 'Normal', cls: 'ok', mark: '●' },
  borderline_high: { label: 'Borderline high', cls: 'warn', mark: '▲' },
  borderline_low: { label: 'Borderline low', cls: 'warn', mark: '▼' },
  high: { label: 'High', cls: 'bad', mark: '▲' },
  low: { label: 'Low', cls: 'low', mark: '▼' },
};
export function chip(status, text) {
  const s = STATUS[status];
  if (!s) return h('span', { class: 'chip' }, text || '—');
  return h('span', { class: `chip ${s.cls}` }, s.mark, ' ', text || s.label);
}
export const statusClass = (status) => (STATUS[status] ? STATUS[status].cls : '');

export function card(title, sub, body, headRight) {
  return h('section', { class: 'card' },
    (title || headRight) && h('div', { class: 'card-head' },
      h('div', {}, title && h('h2', {}, title), sub && h('div', { class: 'sub' }, sub)),
      headRight),
    body);
}

export function stat(k, v, unit) {
  return h('div', { class: 'stat' }, h('span', { class: 'k' }, k), h('span', { class: 'v num' }, v, unit && h('small', {}, ' ' + unit)));
}

export function segmented(options, value, onChange) {
  const wrap = h('div', { class: 'seg' });
  options.forEach(([val, label]) => {
    const b = h('button', { class: val === value ? 'on' : '', type: 'button', onclick: () => {
      wrap.querySelectorAll('button').forEach((x) => x.classList.remove('on'));
      b.classList.add('on');
      onChange(val);
    } }, label);
    wrap.append(b);
  });
  return wrap;
}

export function toggle(label, checked, onChange) {
  const input = h('input', { type: 'checkbox', onchange: (e) => onChange(e.target.checked) });
  input.checked = checked;
  return h('label', { class: 'toggle' }, input, label);
}

export function legend(items) {
  return h('div', { class: 'legend' }, items.map(([color, label]) => h('span', {}, h('i', { style: { background: color } }), label)));
}

export function pager(page, pages, onPage) {
  return h('div', { class: 'pager' },
    h('span', { class: 'muted' }, `Page ${page + 1} of ${pages}`),
    h('button', { class: 'btn icon', disabled: page === 0 || null, onclick: () => onPage(page - 1) }, icon('left')),
    h('button', { class: 'btn icon', disabled: page >= pages - 1 || null, onclick: () => onPage(page + 1) }, icon('right')));
}

export function table(cols, rows, { onRow, empty = 'Nothing to show.' } = {}) {
  if (!rows.length) return h('div', { class: 'muted', style: { padding: '12px 0' } }, empty);
  const tbl = h('table', { class: 'tbl' },
    h('thead', {}, h('tr', {}, cols.map((c) => h('th', { class: c.right ? 'r' : '' }, c.label)))),
    h('tbody', {}, rows.map((r) => {
      const tr = h('tr', { class: onRow ? 'click' : '', onclick: onRow ? () => onRow(r) : null },
        cols.map((c) => h('td', { class: c.right ? 'r num' : '' }, c.render(r))));
      return tr;
    })));
  return h('div', { class: 'table-wrap' }, tbl);
}

export { n1 };
