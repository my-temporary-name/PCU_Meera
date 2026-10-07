import { S, fmtDate, n1, NAMES } from '../store.js';
import { h, card, chip, table, STATUS } from '../ui.js';

export function render(root) {
  const pipe = S.meta.pipeline;
  root.append(h('div', { class: 'page-head' }, h('div', {}, h('h1', {}, 'Data sources'), h('p', {}, 'What was collected from the patient, what was derived from it, and where each piece appears in this dashboard.'))));

  root.append(card('How to read this record', 'The words the pipeline pages use', h('div', { class: 'grid g3' },
    explain('Alert', 'A deviation from her usual that the State Engine decided to hand on (a heart rate above usual, a glucose reading above usual, a missed dose...).'),
    explain('Case', 'Alerts that arrive close in time are written up together. A case gets a new version every time a new alert or a late result arrives.'),
    explain('Version', 'One written account of a case at one moment: a structured layer decided by code, and a text written from it. Versions are never changed.'),
    explain('Evidence', 'For each possible factor (a late meal, short sleep, a missed dose...) a label of how well her own history supports it: supported, suggestive, not supported or insufficient.'),
    explain('PI note', 'A long-term note about one relationship (for example short sleep and a higher heart rate), kept week by week with a status: candidate, supported, weakened or retracted.'),
    explain('Fallback', 'When the model text failed its checks twice, the text built by code from the structured layer is shown instead and marked.'))));

  root.append(card('Reference status', 'Every reading is compared with fixed reference ranges; no readings are interpreted beyond that.',
    h('div', { class: 'row' }, Object.keys(STATUS).map((s) => chip(s)), h('span', { class: 'muted' }, 'Glucose from the CGM stream is compared with the fasting-glucose reference, so post-meal readings often show as high.'))));

  const kinds = ['Patient data'];
  kinds.forEach((k) => {
    const rows = S.meta.sources.filter((s) => s.kind === k);
    root.append(card(k, null, table([
      { label: 'Source', render: (s) => h('div', {}, h('b', {}, s.label), h('div', { class: 'mono muted' }, s.file)) },
      { label: 'Records', right: true, render: (s) => s.rows.toLocaleString() },
      { label: 'Coverage', render: (s) => `${fmtDate(s.start, { year: true })} → ${fmtDate(s.end, { year: true })}` },
      { label: 'Shown in', render: (s) => s.shown },
    ], rows)));
  });

  const fc = pipe.filter_counts;
  root.append(card('Signal quality check', `${Object.values(fc).reduce((a, b) => a + b, 0).toLocaleString()} readings were screened for physiological plausibility before any status was assigned.`,
    h('div', { class: 'stack' },
      h('div', { class: 'grid g4' },
        ...Object.entries(fc).map(([k, v]) => h('div', { class: 'stat' }, h('span', { class: 'k' }, k.replace('_', ' ').toLowerCase()), h('span', { class: 'v num' }, v.toLocaleString()))),
        h('div', { class: 'stat' }, h('span', { class: 'k' }, 'readings given a status'), h('span', { class: 'v num' }, pipe.evaluated.toLocaleString()))),
      h('h3', {}, 'Rejected readings (excluded from every chart and statistic)'),
      table([
        { label: 'When', render: (r) => r.timestamp.replace('T', ' ').slice(0, 16) },
        { label: 'Measure', render: (r) => NAMES[r.biomarker] || r.biomarker },
        { label: 'Value', right: true, render: (r) => n1(r.value) },
        { label: 'Result', render: (r) => h('span', { class: 'chip bad' }, r.result.replace('_', ' ').toLowerCase()) },
        { label: 'Reason', render: (r) => h('span', { class: 'muted' }, r.reason) },
      ], pipe.rejected, { empty: 'No readings were rejected.' }),
      h('h3', {}, 'Status counts across all evaluated readings'),
      h('div', { class: 'row' }, Object.entries(pipe.status_counts).map(([k, v]) => h('span', { class: 'row', style: { gap: '6px' } }, chip(k), h('b', { class: 'num' }, v.toLocaleString())))))));

  root.append(card('Known limits', null, h('ul', { class: 'notes' },
    h('li', {}, 'Labs are shown as individual draws; the pipeline does not build baselines for them.'),
    h('li', {}, 'The confidence/source of each reference range is not yet recorded.'),
    h('li', {}, 'The text of a case is a wording of its structured layer: the labels and classes in the trace are what the code decided.'),
    h('li', {}, 'Medication adherence, mood and cycle data are shown as recorded; they are not scored.'))));
  return [['Data sources']];
}

function explain(title, text) {
  return h('div', { class: 'stat' }, h('b', {}, title), h('span', { class: 'ink2' }, text));
}
