// Tiny DOM helpers and shared presentational pieces.
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
  for (const k of kids.flat(Infinity)) {
    if (k == null || k === false) continue;
    el.append(k.nodeType ? k : document.createTextNode(String(k)));
  }
  return el;
}

const SVG = 'http://www.w3.org/2000/svg';
export const svg = (tag, attrs = {}) => { const e = document.createElementNS(SVG, tag); for (const [k, v] of Object.entries(attrs)) e.setAttribute(k, v); return e; };

export const MON = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];
export const fmtDate = (s, year = true) => (s ? `${+s.slice(8, 10)} ${MON[+s.slice(5, 7) - 1]}${year ? ' ' + s.slice(0, 4) : ''}` : '');
export const ms = (s) => Date.UTC(+s.slice(0, 4), +s.slice(5, 7) - 1, +s.slice(8, 10));
export const num = (x, d = 0) => (x == null ? '—' : Number(x).toLocaleString('en-US', { minimumFractionDigits: d, maximumFractionDigits: d }));

export function ago(days) {
  if (days <= 0) return 'today';
  if (days === 1) return '1 day ago';
  if (days < 60) return `${days} days ago`;
  const m = Math.round(days / 30.4);
  return m < 24 ? `${m} months ago` : `${(days / 365.25).toFixed(1)} years ago`;
}

const PV = { best_guess: ['best guess', 'Invented for this demonstration. No doctor has reviewed it.'], persona: ['persona', 'Stated in the persona document.'], mixed: ['persona + best guess', 'The year or fact is stated in the persona; the day or detail is a best guess.'] };
export function pv() { return null; } // provenance badges are not shown in this view

// a small trend line for a tile: no axes, a dashed goal line, a dot for every dated value on lab-type series 
export function spark(points, { goal = null, dots = true } = {}) {
  const W = 100, H = 30, pad = 3;
  const el = svg('svg', { class: 'spark', viewBox: `0 0 ${W} ${H}`, preserveAspectRatio: 'none', 'aria-hidden': 'true' });
  if (!points || points.length < 2) return el;
  const ts = points.map((p) => ms(p[0])), vs = points.map((p) => p[1]);
  const t0 = Math.min(...ts), t1 = Math.max(...ts);
  let lo = Math.min(...vs), hi = Math.max(...vs);
  if (goal != null) { lo = Math.min(lo, goal); hi = Math.max(hi, goal); }
  if (hi === lo) { hi += 1; lo -= 1; }
  const x = (t) => pad + ((t - t0) / (t1 - t0 || 1)) * (W - 2 * pad), y = (v) => H - pad - ((v - lo) / (hi - lo)) * (H - 2 * pad);
  if (goal != null) el.append(svg('line', { class: 'goal', x1: 0, x2: W, y1: y(goal), y2: y(goal), 'vector-effect': 'non-scaling-stroke' }));
  const d = points.map((p, i) => `${i ? 'L' : 'M'}${x(ts[i]).toFixed(2)} ${y(vs[i]).toFixed(2)}`).join('');
  el.append(svg('path', { class: 'ln', d, 'vector-effect': 'non-scaling-stroke' }));
  if (dots && points.length <= 80) {
    points.forEach((p, i) => {
      const last = i === points.length - 1;
      el.append(svg('path', { class: `dpt ${p[2] === 'data' ? 'solid' : 'hollow'}`, d: `M${x(ts[i]).toFixed(2)} ${y(vs[i]).toFixed(2)}h0`, 'vector-effect': 'non-scaling-stroke' }));
      if (p[2] !== 'data') el.append(svg('path', { class: 'dpt2', d: `M${x(ts[i]).toFixed(2)} ${y(vs[i]).toFixed(2)}h0`, 'vector-effect': 'non-scaling-stroke' }));
      if (last) el.append(svg('path', { class: 'lastdot', d: `M${x(ts[i]).toFixed(2)} ${y(vs[i]).toFixed(2)}h0`, 'vector-effect': 'non-scaling-stroke' }));
    });
  } else {
    const i = points.length - 1;
    el.append(svg('path', { class: 'lastdot', d: `M${x(ts[i]).toFixed(2)} ${y(vs[i]).toFixed(2)}h0`, 'vector-effect': 'non-scaling-stroke' }));
  }
  return el;
}

export const CHEV = () => { const s = svg('svg', { class: 'chev', viewBox: '0 0 24 24', fill: 'none', stroke: 'currentColor', 'stroke-width': '2', 'stroke-linecap': 'round', 'stroke-linejoin': 'round' }); s.append(svg('path', { d: 'M6 9l6 6 6-6' })); return s; };
