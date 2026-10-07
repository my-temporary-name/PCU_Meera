// The case trace: one case followed from the alert on the chart, through the packet and the evidence, to the structured layer, the text, and what the text drew on.
import { S, DAY, ds, ms, fmtDate, fmtTime, n1, loadCase, measureName } from '../store.js';
import { h, card, icon, table, legend } from '../ui.js';
import { mount, palette, base, timeAxis, valueAxis } from '../charts.js';
import { labelChip, wordingChip, flagChips, refChip, wireRefs, countBar, kvlist, STATUS_COLOR } from './trace_ui.js';
import { sizeChip, alertValue, sourceBadge } from './shared.js';
import { glucoseSlice, hrSlice } from '../store.js';

export async function render(root, [id, vArg]) {
  const idx = S.cases.findIndex((c) => c.id === id);
  if (idx < 0) { root.append(card('Case not found', null, h('a', { href: '#/cases' }, 'Browse all cases'))); return [['Cases', '#/cases'], [id || '—']]; }
  const meta = S.cases[idx];
  const D = await loadCase(id);
  const prev = S.cases[idx - 1], next = S.cases[idx + 1];
  let vi = Math.min(Math.max(Number(vArg) ? Number(vArg) - 1 : D.versions.length - 1, 0), D.versions.length - 1);
  let ai = 0;

  const head = h('div', {});
  const strip = h('div', { class: 'vstrip' });
  const chartCard = chartBlock(D);
  const trace = h('div', { class: 'trace' });
  const alertBody = h('div', {}), packetBody = h('div', {}), evidenceBody = h('div', {}), structBody = h('div', {}), textBody = h('div', {}), ctxBody = h('div', {});

  const drawHead = () => {
    const v = D.versions[vi];
    head.replaceChildren(h('div', { class: 'page-head' },
      h('div', {}, h('div', { class: 'row', style: { gap: '8px', marginBottom: '6px' } }, h('span', { class: 'chip ep' }, 'Case'), h('span', { class: 'muted num' }, `${fmtDate(D.case.local_date, { dow: true, year: true })} · opened ${fmtTime(D.case.t0)}`), sourceBadge(v.text.source, v.text.from_prompt)),
        h('h1', { style: { maxWidth: '960px' } }, v.text.headline), h('p', { class: 'mono muted' }, D.case.case_id)),
      h('div', { class: 'row' }, prev && h('a', { class: 'btn icon', href: `#/case/${encodeURIComponent(prev.id)}`, title: 'Previous case' }, icon('left')), h('a', { class: 'btn', href: '#/cases' }, 'All cases'),
        next && h('a', { class: 'btn icon', href: `#/case/${encodeURIComponent(next.id)}`, title: 'Next case' }, icon('right')))));
    h2strip();
  };
  const h2strip = () => {
    strip.replaceChildren();
    D.versions.forEach((v, i) => {
      if (i) strip.append(h('div', { class: 'vline' }));
      strip.append(h('button', { class: `vdot ${i === vi ? 'on' : ''}`, type: 'button', onclick: () => { vi = i; drawVersion(); } }, h('i'), `v${v.version}`, h('span', {}, fmtTime(v.t)), h('span', {}, v.completions.length ? 'late result' : `${v.handoffs.length} alert${v.handoffs.length === 1 ? '' : 's'}`)));
    });
  };

  const drawAlertParts = () => {
    packetBody.replaceChildren(packetView(D, D.alerts[ai].id));
    evidenceBody.replaceChildren(evidenceView(D, D.alerts[ai].id));
  };
  const drawVersion = () => {
    drawHead();
    structBody.replaceChildren(structView(D, D.versions[vi]));
    textBody.replaceChildren(textView(D.versions[vi]));
    ctxBody.replaceChildren(contextView(D.versions[vi]));
    history.replaceState(null, '', `#/case/${encodeURIComponent(id)}/${D.versions[vi].version}`);
  };

  alertBody.append(alertsView(D));
  const alertTabs = D.alerts.length > 1 ? h('div', { class: 'tabs2' }, D.alerts.map((a, i) => h('button', { class: `tab2 ${i === ai ? 'on' : ''}`, type: 'button', onclick: (e) => { ai = i; e.currentTarget.parentNode.querySelectorAll('.tab2').forEach((x, j) => x.classList.toggle('on', j === i)); drawAlertParts(); } }, `Alert ${i + 1} · ${measureName(a.measure)}`))) : null;

  const step = (n, k, title, db, ...kids) => h('div', { class: 'step' }, h('div', { class: 'rail' }, h('div', { class: 'dot2' }, n)),
    h('div', { class: 'body' }, h('section', { class: 'card' }, h('div', { class: 'step-title' }, h('span', { class: 'step-k' }, k), h('h2', {}, title), h('span', { class: 'db' }, db)), h('div', { style: { height: '10px' } }), ...kids)));
  trace.append(
    step(1, 'State Engine', 'The alert', 'state_engine.db → state_handoffs', alertBody),
    step(2, 'Rulebook Lookup', 'The checklist it was given', 'rulebook_lookup.db → rulebook_packets', alertTabs, packetBody),
    step(3, 'Evidence Engine', 'What her own history says about each factor', 'evidence_engine.db → event_evidence', evidenceBody),
    step(4, 'Findings Engine', 'The structured layer (decided by code)', 'findings_loop_polish.db → findings', structBody),
    step(5, 'Findings Engine', 'The text (written from it)', 'findings_loop_polish.db → finding_text', textBody),
    step(6, 'Context and PI', 'What the text drew on', 'diary · earlier summaries · pi_loop_polish.db', ctxBody));

  root.append(head, h('section', { class: 'card' }, h('div', { class: 'card-head' }, h('div', {}, h('h2', {}, 'Versions of this case'), h('div', { class: 'sub' }, 'A new version is written every time a new alert or a late result arrives. Pick one: steps 4 to 6 follow it.'))), strip), chartCard, trace);
  wireRefs(trace);
  drawVersion();
  drawAlertParts();
  return [['Pipeline', '#/pipeline'], ['Cases', '#/cases'], [fmtDate(D.case.local_date) + ' · ' + fmtTime(D.case.t0)]];
}

// ---- the context chart: glucose, heart rate, steps around the case, alerts as numbered pins ------------------------------------------------------
function chartBlock(D) {
  const el = h('div', { class: 'chart', style: { height: '600px' } });
  const alerts = D.alerts;
  const t0 = Math.min(D.case.t0, ...alerts.map((a) => a.t)), t1 = Math.max(D.case.t1 ?? D.case.t0, ...alerts.map((a) => a.t));
  const pad = Math.max(10 * 3600000, (30 * 3600000 - (t1 - t0)) / 2);
  const from = t0 - pad, to = t1 + pad;
  setTimeout(() => {
    const P = palette();
    const g = glucoseSlice(from, to), hr = hrSlice(from, to);
    const steps = [];
    for (let d = ds(from); ms(d) < to; d = ds(ms(d) + DAY)) (S.hourly_steps[d] || []).forEach((v, hh) => steps.push([ms(d) + hh * 3600000 + 1800000, v]));
    const meals = S.meals.filter((m) => m.t >= from && m.t < to);
    const lines = alerts.map((a, i) => ({ xAxis: a.t, label: { show: true, formatter: String(i + 1), color: '#fff', backgroundColor: P.bad, borderRadius: 9, padding: [2, 6], fontWeight: 700, position: 'start' }, lineStyle: { color: P.bad, type: 'solid', width: 1.4, opacity: 0.7 } }));
    const mealLines = meals.map((m) => ({ xAxis: m.t, label: { show: true, formatter: m.label[0].toUpperCase(), color: P.muted, fontSize: 10, position: 'insideEndTop' }, lineStyle: { color: P.muted, type: 'dashed', opacity: 0.5, width: 1 } }));
    const caseArea = [[{ xAxis: D.case.t0 - 450000, itemStyle: { color: P.ep, opacity: 0.1 } }, { xAxis: (D.case.t1 ?? D.case.t0) + 450000 }]];
    const chart = mount(el, base({
      axisPointer: { link: [{ xAxisIndex: 'all' }] },
      grid: [{ left: 8, right: 14, top: 30, height: '36%', containLabel: true }, { left: 8, right: 14, top: '52%', height: '19%', containLabel: true }, { left: 8, right: 14, top: '78%', height: '12%', containLabel: true }],
      tooltip: { ...base().tooltip, trigger: 'axis', axisPointer: { type: 'line', lineStyle: { color: P.muted } }, formatter: (ps) => {
        const t = ps[0].axisValue; const out = [`<b>${fmtDate(ds(t), { dow: true })} · ${fmtTime(t)}</b>`];
        ps.forEach((p) => { if (['Glucose', 'Heart rate', 'Steps this hour'].includes(p.seriesName)) out.push(`${p.seriesName} <b>${n1(p.value[1], p.seriesName === 'Glucose' ? 1 : 0)}</b>`); });
        const m = meals.filter((x) => x.t <= t && t - x.t <= 150 * 60000).pop(); if (m) out.push(`<span style="color:${P.muted}">${Math.round((t - m.t) / 60000)} min after ${m.label}: ${m.food}</span>`);
        return out.join('<br>');
      } },
      xAxis: [0, 1, 2].map((i) => timeAxis({ gridIndex: i, min: from, max: to, axisLabel: { show: i === 2, color: P.muted }, splitLine: { show: true, lineStyle: { color: P.line, opacity: 0.6 } } })),
      yAxis: [valueAxis({ gridIndex: 0, name: 'glucose mg/dL', min: (v) => Math.floor(v.min / 20) * 20 - 10, nameTextStyle: { color: P.muted, align: 'left' } }), valueAxis({ gridIndex: 1, name: 'heart rate bpm', scale: true, nameTextStyle: { color: P.muted, align: 'left' } }), valueAxis({ gridIndex: 2, name: 'steps / h', splitNumber: 2, nameTextStyle: { color: P.muted, align: 'left' } })],
      dataZoom: [{ type: 'inside', xAxisIndex: [0, 1, 2] }],
      series: [
        { name: 'Glucose', type: 'line', xAxisIndex: 0, yAxisIndex: 0, data: g, showSymbol: false, lineWidth: 1.6, lineStyle: { width: 1.7, color: P.primary }, z: 3, markLine: { silent: true, symbol: 'none', data: [...mealLines, ...lines] }, markArea: { silent: true, data: caseArea } },
        { name: 'Heart rate', type: 'line', xAxisIndex: 1, yAxisIndex: 1, data: hr, showSymbol: false, lineStyle: { width: 1.5, color: P.bad }, markLine: { silent: true, symbol: 'none', data: lines.map((l) => ({ ...l, label: { show: false } })) }, markArea: { silent: true, data: caseArea } },
        { name: 'Steps this hour', type: 'bar', xAxisIndex: 2, yAxisIndex: 2, data: steps, barWidth: 14, itemStyle: { color: P.low, opacity: 0.75, borderRadius: [3, 3, 0, 0] } },
      ],
    }));
    void chart;
  }, 0);
  return card('Around the case', 'Numbered pins are the alerts (step 1); dashed lines are meals (B, L, D, S); violet is the span of the case. Scroll to zoom.',
    h('div', {}, el, h('div', { class: 'row', style: { marginTop: '8px' } }, legend([[palette().primary, 'Glucose (15 min)'], [palette().bad, 'Heart rate (15 min)'], [palette().low, 'Steps per hour'], [palette().ep, 'Case']]))));
}

// ---- steps 1 to 3: per alert ---------------------------------------------------------------------------------------------------------------------
function alertsView(D) {
  return table([
    { label: '#', render: (a) => h('span', { class: 'chip bad' }, D.alerts.indexOf(a) + 1) },
    { label: 'When (IST)', render: (a) => `${fmtDate(ds(a.t))} · ${fmtTime(a.t)}` },
    { label: 'What', render: (a) => h('span', {}, h('b', {}, measureName(a.measure)), ' ', h('span', { class: 'muted' }, a.direction === 'above' ? '▲ above usual' : '▼ below usual')) },
    { label: 'How far', render: (a) => sizeChip(a.size) }, { label: 'Trigger', render: (a) => a.trigger }, { label: 'Value', right: true, render: alertValue },
    { label: 'Usual taken from', render: (a) => (a.usual_basis || '').replace(/_/g, ' ') },
    { label: 'Around it', render: (a) => ctxText(a.context) },
  ], D.alerts);
}
function ctxText(c) {
  if (!c) return '—';
  const bits = [];
  if (c.last_meal) bits.push(`${c.last_meal.label.replace(/_/g, ' ')} ${c.last_meal.minutes_ago} min earlier`);
  if (c.medication) bits.push(`doses ${c.medication.taken}/${c.medication.expected}` + (c.medication.missed && c.medication.missed.length ? ` (missed ${c.medication.missed.join(', ')})` : ''));
  if (c.sleep_last_night) bits.push(`slept ${n1(c.sleep_last_night.value)} h`);
  if (c.other_open_items && c.other_open_items.length) bits.push(`${c.other_open_items.length} other open item${c.other_open_items.length === 1 ? '' : 's'}`);
  if (c.diary_today_count) bits.push(`${c.diary_today_count} diary entr${c.diary_today_count === 1 ? 'y' : 'ies'} today`);
  return h('span', { class: 'muted' }, bits.join(' · ') || '—');
}

function packetView(D, hid) {
  const p = D.packets[hid];
  if (!p) return h('div', { class: 'muted' }, 'This alert has no packet.');
  return h('div', { class: 'stack', style: { gap: '10px' } },
    h('div', { class: 'row' }, h('span', { class: 'chip primary' }, 'Rule: ', p.rule.replace(/_/g, ' ')), h('span', { class: `chip ${p.status === 'ok' ? 'ok' : 'warn'}` }, p.status === 'ok' ? 'Packet ready' : 'Rule deferred'),
      p.budget && h('span', { class: 'muted' }, `Budget: ${p.budget.primary_count ?? '—'} primary · up to ${p.budget.secondary_max} secondary · ${p.budget.tertiary_max} tertiary`), h('span', { class: 'muted' }, `${p.selected.length} selected · ${p.n_not_selected} left out by the budget`)),
    table([{ label: '#', render: (r) => r.rank }, { label: 'Tier', render: (r) => h('span', { class: 'chip' }, r.tier) }, { label: 'Candidate', render: (r) => h('b', {}, r.candidate.replace(/_/g, ' ')) },
      { label: 'The check', render: (r) => h('span', { class: 'ink2' }, r.text || r.check) }, { label: 'Compared with', render: (r) => h('span', { class: 'muted' }, r.outcome || '—') }], p.selected));
}

function evidenceView(D, hid) {
  const e = D.evidence[hid];
  if (!e) return h('div', { class: 'muted' }, 'No evidence record (the rule was deferred).');
  const c = e.counts;
  const comp = (D.completions[e.evidence_id] || []);
  return h('div', { class: 'stack', style: { gap: '10px' } },
    countBar([['supported', c.supported], ['suggestive', c.suggestive], ['not_supported', c.not_supported], ['insufficient', c.insufficient], ['not_applicable', c.not_applicable], ['not_yet_available', c.not_yet_available]].map(([k, n]) => ({ label: k.replace(/_/g, ' '), n, color: STATUS_COLOR[k] || 'var(--line)' }))),
    table([
      { label: '#', render: (r) => r.rank }, { label: 'Factor', render: (r) => h('div', {}, h('b', {}, r.phrase || r.candidate), r.outcome && h('div', { class: 'muted' }, '→ ', r.outcome)) },
      { label: 'Label', render: (r) => labelChip(r.support, r.reason ? `reason: ${r.reason}` : '') }, { label: 'Why not tested / flags', render: (r) => h('span', { class: 'row', style: { gap: '4px' } }, r.reason ? h('span', { class: 'muted' }, r.reason) : null, flagChips(r.flags)) },
      { label: 'Present now?', render: (r) => (r.exposure ? h('span', { class: `chip ${r.exposure === 'exposed' ? 'primary' : ''}` }, r.exposure.replace(/_/g, ' ')) : '—') },
      { label: 'This event', render: (r) => (r.event ? h('span', { class: 'muted num' }, [r.event.observed != null ? `observed ${n1(r.event.observed)}` : '', r.event.history_median != null ? `usual ${n1(r.event.history_median)}` : '', r.event.percentile != null ? `percentile ${n1(r.event.percentile, 0)}` : ''].filter(Boolean).join(' · ')) : '—') },
    ], e.factors),
    e.overlap.length ? h('div', { class: 'callout info' }, `${e.overlap.length} pair${e.overlap.length === 1 ? '' : 's'} of factors often occur together, so their separate roles cannot be told apart.`) : null,
    comp.length ? h('div', { class: 'callout info' }, `Late result: ${comp.map((x) => `${x.candidate.replace(/_/g, ' ')} → ${x.support}`).join(', ')} (evaluated after the event).`) : null);
}

// ---- steps 4 to 6: per version ----------------------------------------------------------------------------------------------------------------------
function structView(D, v) {
  const sig = (f) => JSON.stringify([f.phrase, f.wording, f.position, f.outcome, f.group]);
  const alias = {};
  v.factors.forEach((f) => { (alias[sig(f)] ||= []).push(f.id); });
  const shown = v.factors.filter((f) => !['not_mentioned', 'not_known_yet'].includes(f.wording));
  const hidden = v.factors.length - shown.length;
  return h('div', { class: 'stack', style: { gap: '12px' } },
    h('div', { class: 'row' }, h('span', { class: `chip ${v.mode === 'relationship' ? 'ep' : ''}` }, v.mode === 'relationship' ? 'Mode: may discuss links' : 'Mode: describe only'), h('span', { class: 'chip' }, `History: ${v.history_note.replace(/_/g, ' ')}`), h('span', { class: 'muted' }, `as of ${fmtDate(ds(v.t))} · ${fmtTime(v.t)}`)),
    h('div', {}, h('h3', {}, 'What was off her usual'), h('div', { class: 'itemlist', style: { marginTop: '6px' } }, v.measures.map((m) => h('div', { class: 'itemrow', 'data-refs': m.id }, refChip(m.id), h('div', { class: 'ph' }, h('b', {}, measureName(m.measure)), ' was ', h('b', {}, m.strength), ' ', m.direction === 'above' ? 'above' : 'below', ' her usual'), h('div', { class: 'tags' }, h('span', { class: 'muted num' }, fmtTime(m.t))))))),
    h('div', {}, h('h3', {}, 'What was looked at, and what the text may say about it'),
      h('div', { class: 'itemlist', style: { marginTop: '6px' } }, shown.map((f) => h('div', { class: 'itemrow', 'data-refs': [...alias[sig(f)], f.group].filter(Boolean).join(' ') }, refChip(f.id),
        h('div', {}, h('div', { class: 'ph' }, h('b', {}, f.phrase || f.candidate), f.outcome && h('span', { class: 'muted' }, ' → ', f.outcome)), f.position && h('div', { class: 'sub' }, f.position)),
        h('div', { class: 'tags' }, labelChip(f.label), wordingChip(f.wording), f.exposure && f.exposure !== 'exposed' ? h('span', { class: 'chip' }, f.exposure.replace(/_/g, ' ')) : null, flagChips(f.flags), f.group ? h('span', { class: 'ref g' }, f.group) : null)))),
      hidden ? h('div', { class: 'muted', style: { marginTop: '6px' } }, `${hidden} more factors were tested but are not mentioned (not present, or not known yet).`) : null),
    v.groups.length ? h('div', {}, h('h3', {}, 'Described together'), v.groups.map((g) => h('div', { class: 'row', 'data-refs': g.group_id, style: { gap: '6px', marginTop: '4px' } }, refChip(g.group_id), h('span', { class: 'ink2' }, g.reason === 'entangled' ? 'often occur together; roles cannot be told apart' : 'present together'), g.members.map(refChip)))) : null,
    v.not_known_yet.length ? h('div', { 'data-refs': 'n1' }, h('h3', {}, 'Not known yet'), h('div', { class: 'ink2' }, v.not_known_yet.join(' · '))) : null,
    h('div', { 'data-refs': 'h1', class: 'item' }, h('h3', {}, 'Repeat information from PI'), v.repeat.length ? v.repeat.map((r) => h('div', { class: 'row', style: { gap: '8px', marginTop: '4px' } }, h('span', { class: 'ink2' }, phraseOf(r.relationship_key)), r.pi_status ? labelChip(r.pi_status) : h('span', { class: 'chip' }, 'no note yet'), h('span', { class: 'chip' }, `seen before: ${r.seen_before.replace(/_/g, ' ')}`))) : h('div', { class: 'muted' }, 'No relationship is claimed in this version.')));
}
const phraseOf = (key) => { const m = S.memByKey.get(key); return m ? `${m.phrase} → ${m.outcome}` : key; };

function textView(v) {
  const t = v.text;
  const li = t.sentences.map((s, i) => h('li', {}, h('span', { class: 'n' }, i + 1), h('span', {}, s.text, h('span', { class: 'refs' }, s.refs.map(refChip)))));
  return h('div', { class: 'stack', style: { gap: '8px' } },
    h('div', { class: 'row' }, sourceBadge(t.source, t.from_prompt), h('span', { class: 'muted' }, `prompt ${t.prompt} · checks ${t.checks}`)),
    h('div', { class: 'headline' }, t.headline), h('ol', { class: 'sentences' }, li),
    t.failed ? h('div', { class: 'callout' }, h('b', {}, 'Why the model text was not used: '), t.failed.map((att, i) => h('div', {}, `attempt ${i + 1}: `, att.map((f) => `${f.check.replace(/_/g, ' ')} (${f.detail})`).join('; ') || 'no failure recorded'))) : null,
    h('div', { class: 'muted' }, 'The chips after each sentence are the items it cites. Hover one to highlight it above and below.'));
}

function contextView(v) {
  const diary = v.diary, sm = v.state_memory, notes = v.pi_notes;
  return h('div', { class: 'stack', style: { gap: '14px' } },
    h('div', {}, h('h3', {}, 'Diary entries it could see'), diary.length ? h('div', { class: 'itemlist', style: { marginTop: '6px' } }, diary.map((d) => h('div', { class: 'itemrow', 'data-refs': d.id }, refChip(d.id), h('div', {}, h('div', { class: 'ph' }, d.text), d.note && h('div', { class: 'sub' }, d.note)), h('div', { class: 'tags' }, h('span', { class: 'chip warn' }, (d.category || '').replace(/_/g, ' ')), d.t ? h('span', { class: 'muted num' }, `${fmtDate(ds(d.t))} · ${fmtTime(d.t)}`) : null)))) : h('div', { class: 'muted' }, 'None in the window.')),
    h('div', {}, h('h3', {}, 'Earlier summaries'), sm.length ? h('div', { class: 'itemlist', style: { marginTop: '6px' } }, sm.map((s) => h('div', { class: 'itemrow', 'data-refs': s.id }, refChip(s.id), h('div', { class: 'ph' }, s.headline || '—'), h('div', { class: 'tags' }, h('span', { class: 'mono muted' }, s.window))))) : h('div', { class: 'muted' }, 'None used.')),
    h('div', {}, h('h3', {}, 'PI notes it drew on'), notes.length ? h('div', { class: 'itemlist', style: { marginTop: '6px' } }, notes.map((n) => h('div', { class: 'pnote', 'data-refs': n.view_id },
      h('div', { class: 'row', style: { gap: '8px' } }, refChip(n.view_id), labelChip(n.status), h('span', { class: 'muted' }, `version ${n.version} written ${fmtDate(n.written_at.slice(0, 10))}`), h('a', { href: `#/pi/${encodeURIComponent(n.key)}` }, 'open this relationship →')),
      h('div', { class: 'assoc' }, n.association), n.situations ? h('div', { class: 'sit' }, h('b', {}, 'Situations noted: '), n.situations) : null))) : h('div', { class: 'muted' }, 'No long-term note existed yet for what this version mentions.')));
}
