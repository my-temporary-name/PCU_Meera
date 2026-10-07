// Quality view: how the texts were made, what failed, what was kept, and the known limit.
import { S, n1 } from '../store.js';
import { h, card, table, stat } from '../ui.js';
import { mount, palette, base, valueAxis } from '../charts.js';
import { countBar } from './trace_ui.js';

export function render(root) {
  const q = S.quality;
  const n = q.versions;
  const src = q.text_sources;
  root.append(h('div', { class: 'page-head' }, h('div', {}, h('h1', {}, 'Quality'), h('p', {}, 'How the texts were made, which checks caught problems, and what is still imperfect. Nothing here is hidden: a fallback is shown as a fallback everywhere.'))));
  root.append(h('div', { class: 'grid g4' },
    stat('Versions written', n), stat('Model text (this run)', src['model text'] || 0), stat('Kept from earlier prompts', src['kept from an earlier prompt'] || 0, 're-checked under the final checks'), stat('Code-line fallbacks', src.fallback || 0, `${(100 * (src.fallback || 0) / n).toFixed(1)}%`)));

  root.append(card('Where each text came from', 'A model text must pass 16 checks (numbers, causal words, claim strength, copied diary text, ...). Two failures → the code line is used.',
    countBar([{ label: 'model text', n: src['model text'] || 0, color: 'var(--primary)' }, { label: 'kept from an earlier prompt', n: src['kept from an earlier prompt'] || 0, color: 'var(--low)' }, { label: 'code-line fallback', n: src.fallback || 0, color: 'var(--warn)' }])));

  const el = h('div', { class: 'chart', style: { height: '260px' } });
  const checks = Object.entries(q.first_attempt_failures_by_check).sort((a, b) => b[1] - a[1]);
  root.append(h('div', { class: 'grid g2' },
    card('Which checks caught a first attempt', 'Versions whose first model answer failed that check (across every run kept in the database)', checks.length ? el : h('div', { class: 'muted' }, 'No failures recorded.')),
    card('Model calls and tokens', null, h('div', { class: 'tile-grid' }, stat('Tokens in', n1(q.tokens.in, 0)), stat('Tokens out', n1(q.tokens.out, 0)), stat('PI situations lines', q.pi_lines_with_text, `of ${Object.values(q.pi_lines).reduce((a, b) => a + b, 0)} note versions`),
      ...Object.entries(q.pi_lines).map(([k, v]) => stat('PI line: ' + k.replace(/_/g, ' '), v))))));
  setTimeout(() => {
    if (!checks.length) return;
    const p = palette();
    mount(el, base({ grid: { left: 8, right: 36, top: 8, bottom: 8, containLabel: true }, tooltip: { ...base().tooltip, trigger: 'item' }, xAxis: valueAxis(),
      yAxis: { type: 'category', inverse: true, data: checks.map((c) => c[0].replace(/_/g, ' ')), axisLabel: { color: p.ink2 }, axisLine: { show: false }, axisTick: { show: false } },
      series: [{ type: 'bar', data: checks.map((c) => c[1]), itemStyle: { color: p.ep, borderRadius: [0, 6, 6, 0] }, barMaxWidth: 16, label: { show: true, position: 'right', color: p.ink2 } }] }));
  }, 0);

  root.append(card(`Code-line fallbacks (${q.fallbacks.length})`, 'The model text failed its checks twice; the text built by code from the structured layer is shown instead. Click a row to see it.',
    table([{ label: 'Version', render: (f) => h('span', { class: 'mono' }, f.id.replace('fnd_case_', '').replace('+05:30', '')) },
      { label: 'Why the last attempt failed', render: (f) => (f.failed.length ? [...new Set(f.failed[f.failed.length - 1].map((x) => x.check.replace(/_/g, ' ')))].join(', ') : '—') },
      { label: 'Detail', render: (f) => h('span', { class: 'muted' }, f.failed.length ? f.failed[f.failed.length - 1].map((x) => x.detail).join('; ').slice(0, 130) : '') }], q.fallbacks,
    { onRow: (f) => { const m = f.id.match(/^fnd_(case_.+)_v(\d+)$/); location.hash = `#/case/${encodeURIComponent(m[1])}/${m[2]}`; } })));

  root.append(card('Known limit: repeated wording', `${q.repeated.length} versions repeat their headline as a sentence, or write a sentence twice. The checks do not catch it yet.`,
    table([{ label: 'Version', render: (f) => h('span', { class: 'mono' }, f.id.replace('fnd_case_', '').replace('+05:30', '')) }, { label: 'What', render: (f) => f.kind }], q.repeated,
      { onRow: (f) => { const m = f.id.match(/^fnd_(case_.+)_v(\d+)$/); location.hash = `#/case/${encodeURIComponent(m[1])}/${m[2]}`; } })));
  root.append(card('Methods in this run', null, h('div', { class: 'tile-grid' }, Object.entries(q.meta).map(([k, v]) => stat(k.replace(/_/g, ' '), h('span', { class: 'mono', style: { fontSize: '12px' } }, v))))));
  return [['Pipeline', '#/pipeline'], ['Quality']];
}
