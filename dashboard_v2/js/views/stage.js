// One page per component: what goes in, what comes out, real counts, real examples, and the hand-over to the next stage.
import { S, n1, measureName, loadCase, fmtDate, mondayOf } from '../store.js';
import { h, card, table, chip } from '../ui.js';
import { mount, palette, base, valueAxis, cssVar } from '../charts.js';
import { kvlist, show, labelChip, wordingChip, countBar, STATUS_COLOR } from './trace_ui.js';

const ACCENT = ['#7cc8bb', '#8fd1a8', '#f2cf8a', '#f0a3b2', '#b6acec', '#9db9ee', '#7cc8bb', '#b6acec'];
// counts already drawn in the stage's chart are not repeated as tiles; a tile may carry a one-line explanation
let START_STEP = 0;
const HIDE = { pi: (k) => k.startsWith('final status'), findings: () => true, state: () => true, rulebook: () => true, evidence: () => true, linker: () => true, baseline: (k) => / windows \(/.test(k) };
const NOTE = { threshold: {
  'readings checked': 'Every raw reading from her files for the year (24 measures). The plausibility filter asks of each one: could this be real?',
  'rejected': 'Readings that could not be real and were removed before anything else: all five were glucose above 600 mg/dL while she was active.',
  'status rows': 'Passed readings that were given a status (normal, borderline, high or low) against a reference range. Fewer than the readings that passed, because heart rate is judged only at rest, hourly steps are summed to days, and weight has no range.' },
  pi: {
  'weekly jobs': 'PI runs once per calendar week (Monday to Sunday) and looks at everything Findings wrote that week.',
  'relationships': 'Different relationships (for example short sleep → higher glucose) PI kept a long-term note for.',
  'memory versions': 'Times those notes were rewritten; a note gets a new version only when its status, counts or text changes.' },
  linker: {
  'store rows': 'Every row of the Personal Data Store: the 44,469 evaluated readings plus the pairings in the chart.',
  'context events': 'The other streams kept for the later components: meals, sleep, mood, diary, location, heart rate and hourly steps.' } };
const WHERE = { threshold: 'Reads final/*.csv; writes output/threshold_evaluation_results.csv and plausibility_filter_results.csv', linker: 'Reads the threshold results and the context streams; writes output/short_range_pairings.csv and the Personal Data Store' };

export function render(root, [id, stepArg]) {
  START_STEP = Math.max(0, (+stepArg || 1) - 1);
  const stages = S.pipeline.stages;
  const i = stages.findIndex((s) => s.id === id);
  if (i < 0) { root.append(card('Component not found', null, h('a', { href: '#/pipeline' }, 'Back to the pipeline'))); return [['Pipeline', '#/pipeline'], [id || '—']]; }
  const s = stages[i], prev = stages[i - 1], next = stages[i + 1];
  const featured = S.cases.find((c) => c.date === '2025-11-18') || S.cases[0];

  const accent = ACCENT[i % ACCENT.length];
  root.style.setProperty('--accent', accent);
  root.append(h('section', { class: 'stage-hero', style: `--accent: ${accent}` },
    h('div', { class: 'stage-hero-main' },
      h('div', { class: 'stage-num' }, s.n),
      h('div', {}, h('div', { class: 'stage-kicker' }, `Component ${s.n} of ${stages.length}`), h('h1', {}, s.name), h('div', { class: 'stage-db' }, s.db))),
    h('div', { class: 'tracker' }, stages.map((x, j) => h('a', { class: `tk ${j === i ? 'on' : j < i ? 'done' : ''}`, href: `#/stage/${x.id}`, title: x.name }, h('i', {}, x.n), h('span', {}, x.name.split(' ')[0])))),
    h('div', { class: 'row', style: { marginTop: '4px' } }, prev && h('a', { class: 'btn', href: `#/stage/${prev.id}` }, '← ' + prev.name.split(' ')[0]), next && h('a', { class: 'btn primary', style: `background:${accent};border-color:${accent}`, href: `#/stage/${next.id}` }, next.name.split(' ')[0] + ' →'))));

  root.append(h('section', { class: 'io-grid', style: `--accent: ${accent}` },
    h('div', { class: 'io-box in' }, h('div', { class: 'io-k' }, h('span', { class: 'tag in' }, 'IN'), 'What goes in'), h('p', {}, s.in)), h('div', { class: 'arrow' }, h('span', {}, '→')),
    h('div', { class: 'io-box out' }, h('div', { class: 'io-k' }, h('span', { class: 'tag out' }, 'OUT'), 'What comes out'), h('p', {}, s.out))));

  const kpiRows = Object.entries(s.counts).filter(([k]) => !(HIDE[s.id] && HIDE[s.id](k)));
  if (kpiRows.length) root.append(h('div', { class: 'kpis', style: `--accent: ${accent}` }, kpiRows.map(([k, v]) => h('div', { class: 'kpi2' }, h('span', { class: 'kpi2-v num' }, n1(v, 0)), h('span', { class: 'kpi2-k' }, k), NOTE[s.id] && NOTE[s.id][k] ? h('span', { class: 'kpi2-n' }, NOTE[s.id][k]) : null))));

  const extra = SPECIFIC[s.id] && SPECIFIC[s.id](s);
  if (extra) root.append(extra);

  if (s.id !== 'baseline' && s.id !== 'rulebook') root.append(s.id === 'state' ? stateExamples(s) : s.id === 'linker' ? linkerExample(s) : s.id === 'threshold' ? thresholdExamples(s) : s.id === 'findings' ? findingsExample() : s.id === 'pi' ? piExample(stages) : card('A real example', 'First rows of what this component wrote', sample(s)));
  root.append(card('How it hands over', null, h('div', { class: 'stack', style: { gap: '10px' } },
    h('div', {}, h('span', { class: 'key-link' }, s.next)),
    h('div', { class: 'row' },
      next && h('a', { class: 'btn primary', href: `#/stage/${next.id}` }, `Next: ${next.name} →`),
      h('a', { class: 'btn', href: `#/case/${encodeURIComponent(featured.id)}` }, 'See this stage inside a real case')))));
  return [['Pipeline', '#/pipeline'], [s.name]];
}

function findingsExample() {
  const box = h('div', { class: 'stack', style: { gap: '14px' } }, h('div', { class: 'muted' }, 'Loading…'));
  const id = 'case_2026-03-16T01:15:00+05:30';
  loadCase(id).then((D) => {
    const last = D.versions[D.versions.length - 1], c = S.cases.find((x) => x.id === id) || {};
    const seen = new Set(), used = last.factors.filter((f) => !['not_mentioned', 'not_known_yet'].includes(f.wording) && f.phrase && !seen.has(f.phrase + f.outcome) && seen.add(f.phrase + f.outcome));
    box.replaceChildren(
      h('div', { class: 'ex-head' }, h('div', { class: 'ex-title' }, last.text.headline),
        h('div', { class: 'row', style: { gap: '8px', flexWrap: 'wrap' } }, chip(null, `${D.alerts.length} alerts`), chip(null, `${D.versions.length} versions`), chip(null, last.mode + ' mode'), chip(null, last.text.source === 'llm' ? 'written by the model' : 'written by code'), h('a', { class: 'btn', href: `#/case/${encodeURIComponent(id)}` }, 'Open the full trace'))),
      h('div', { class: 'ex-cols' },
        h('div', { class: 'ex-box' }, h('div', { class: 'ex-k' }, 'The context written for the last version'), h('ul', { class: 'points' }, last.text.sentences.map((x) => h('li', {}, x.text)))),
        h('div', { class: 'ex-box' }, h('div', { class: 'ex-k' }, 'What it is built from'), h('div', { class: 'ex-built' }, used.map((f) => h('div', { class: 'ex-f' }, h('span', { class: 'ex-fp' }, f.phrase, f.outcome ? h('em', {}, ` → ${f.outcome}`) : null), h('span', { class: 'row', style: { gap: '6px' } }, labelChip(f.label), wordingChip(f.wording))))))),
      h('div', { class: 'ex-box' }, h('div', { class: 'ex-k' }, 'How the case grew, version by version'), h('ol', { class: 'ex-vers' }, D.versions.map((v) => h('li', {}, h('span', { class: 'ex-vn' }, `v${v.version}`), h('span', {}, v.text.headline), h('span', { class: 'muted' }, v.mode))))));
  });
  return card('A real example', 'One case from start to finish: a night of high glucose and heart rate in March', box);
}

function linkerExample(s) {
  const e = s.example, date = e.when.slice(0, 10), time = e.when.slice(11, 16);
  const clock = (iso) => (iso ? iso.slice(11, 16) : '');
  const dur = (m) => { const a = Math.abs(Math.round(m)), hh = Math.floor(a / 60), mm = a % 60; return hh ? `${hh} h${mm ? ` ${mm} min` : ''}` : `${mm} min`; };
  const lagText = (x) => (x.lag == null ? null : x.lag === 0 ? 'around the reading' : x.lag > 0 ? `${dur(x.lag)} before` : `${dur(x.lag)} later that day`);
  const of = (t) => e.pairings.filter((x) => x.type === t);
  const KIND = [
    ['meal', 'Meal', 'up to 150 min before', '#f2b78f'], ['activity', 'Activity', 'a step hour up to 90 min before', '#b6acec'], ['heart_rate', 'Heart rate', 'within 2 hours either side', '#f0a3b2'],
    ['medication', 'Medication', 'logged that day', '#7cc8bb'], ['sleep', 'Sleep', 'the night before', '#8fd1a8'], ['mood', 'Mood', 'that part of the day', '#9db9ee'],
    ['diary', 'Diary', 'that day', '#f2cf8a'], ['context_event', 'Context event', 'same calendar day', '#a9bdb7']];
  const body = (t, xs) => {
    const x = xs[0];
    if (t === 'meal') { const [lab, ...rest] = x.summary.split(': '); return [h('div', { class: 'lk-big' }, lab.charAt(0).toUpperCase() + lab.slice(1)), h('div', { class: 'lk-sub' }, rest.join(': ')), h('div', { class: 'lk-meta' }, `started ${clock(x.when)} · ${lagText(x)}`)]; }
    if (t === 'medication') return [h('div', { class: 'lk-meds' }, xs.map((m) => { const [id, st] = [m.summary.replace(/^med_\d+_/, '').replace(/ (taken|missed)$/, ''), m.summary.endsWith('missed') ? 'missed' : 'taken']; return h('span', { class: `lk-med ${st}` }, st === 'taken' ? '✓ ' : '✕ ', id, h('em', {}, ` ${st}`)); }))];
    if (t === 'activity') return [h('div', { class: 'lk-big' }, x.summary.replace(' that hour', ''), h('small', {}, ' in that hour')), h('div', { class: 'lk-meta' }, `hour started ${clock(x.when)} · ${lagText(x)}`)];
    if (t === 'heart_rate') { const m = x.summary.match(/avg ([\d.]+) bpm \(([\d.]+)-([\d.]+), n=(\d+)\)/); return m ? [h('div', { class: 'lk-big' }, n1(+m[1], 0), h('small', {}, ' bpm average')), h('div', { class: 'lk-meta' }, `range ${m[2]} to ${m[3]} · ${m[4]} readings`)] : [h('div', { class: 'lk-big' }, x.summary)]; }
    if (t === 'sleep') { const m = x.summary.match(/([\d.]+)h \((\w+)\)/); return m ? [h('div', { class: 'lk-big' }, m[1], h('small', {}, ' h of sleep · ' + m[2])), h('div', { class: 'lk-meta' }, `recorded at ${clock(x.when)} · ${lagText(x)}`)] : [h('div', { class: 'lk-big' }, x.summary)]; }
    if (t === 'mood') { const m = x.summary.match(/^(.*) \((.*)\)$/); return [h('div', { class: 'lk-big' }, m ? m[1].replace(/_/g, ' ') : x.summary), m ? h('div', { class: 'lk-meta' }, `category: ${m[2].replace(/_/g, ' ')}`) : null]; }
    if (t === 'context_event') { const [cat, ...rest] = x.summary.split(': '); return [h('div', { class: 'lk-big' }, rest.join(': ')), h('div', { class: 'lk-meta' }, `${cat.replace(/_/g, ' ')} · at ${clock(x.when)}, ${lagText(x)}`)]; }
    return [h('div', { class: 'lk-big' }, x.summary)];
  };
  const tiles = KIND.map(([t, name, rule, col]) => { const xs = of(t); return h('div', { class: 'lk-tile', style: `--c: ${col}` }, h('div', { class: 'lk-top' }, h('b', {}, name), h('span', { class: 'muted' }, rule)), ...(xs.length ? body(t, xs) : [h('div', { class: 'lk-meta' }, 'nothing found')])); });
  return card('One glucose reading and everything linked to it', 'A real reading, with the eight kinds of nearby events the linker checked for it. Each tile is one kind and what was found.', h('div', { class: 'stack', style: { gap: '16px' } },
    h('div', { class: 'lk-head' }, h('div', {}, h('div', { class: 'lk-ghead' }, 'CGM glucose · ', fmtDate(date, { dow: true, year: true }), ` · ${time}`), h('div', { class: 'lk-gval num' }, n1(e.value, 1), h('small', {}, ' mg/dL'), h('span', { class: 'tx-chip', style: '--c: var(--bad)' }, e.status))),
      h('div', { class: 'row', style: { gap: '8px', flexWrap: 'wrap' } }, h('span', { class: 'chip' }, `${e.pairings.length} pairings from this one reading`), h('a', { class: 'btn', href: `#/week/${mondayOf(date)}` }, 'Open that week →'))),
    h('div', { class: 'lk-grid' }, tiles),
    h('p', { class: 'muted', style: { margin: 0, fontSize: '12.5px' } }, 'Meals, activity and heart rate are matched by time. Medication, diary, mood, sleep and context events are matched by the day or the part of the day, so a context event can be later that day, as here. Pairings only say "this was nearby", never that it caused the reading.')));
}

function kv(rows) { return kvlist(Object.fromEntries(rows)); }

function rangeText(b, unit) {
  const f = (x) => n1(x, x % 1 ? 1 : 0), u = unit === '%' ? '%' : ` ${unit}`;
  return b[0] == null ? `under ${f(b[1])}${u}` : b[1] == null ? `${f(b[0])}${u} or more` : `${f(b[0])} to ${f(b[1])}${u}`;
}
function ruler(e) {
  const finite = [...new Set(e.bands.flatMap((b) => [b[0], b[1]]).filter((x) => x != null))].sort((a, b) => a - b);
  const span = (finite[finite.length - 1] - finite[0]) || finite[0] * 0.3, pad = span * 0.55;
  let lo = finite[0] - pad, hi = finite[finite.length - 1] + pad;
  lo = Math.min(lo, e.value - span * 0.12); hi = Math.max(hi, e.value + span * 0.12);
  if (finite[0] >= 0 && lo < 0) lo = 0;
  const pos = (x) => (100 * (Math.min(hi, Math.max(lo, x)) - lo)) / (hi - lo);
  const col = { normal: '--ok', borderline: '--warn', abnormal: '--bad' };
  const segs = e.bands.map((b) => { const a = pos(b[0] == null ? lo : b[0]), z = pos(b[1] == null ? hi : b[1]); return h('i', { class: 'rk-seg', style: `left:${a}%;width:${z - a}%;--c:var(${col[b[2]]})`, title: `${b[2]}: ${rangeText(b, e.unit)}` }); });
  const ticks = finite.map((x) => h('span', { class: 'rk-tick num', style: `left:${pos(x)}%` }, n1(x, x % 1 ? 1 : 0)));
  return h('div', { class: 'rk' }, h('div', { class: 'rk-track' }, ...segs, h('i', { class: 'rk-mark', style: `left:${pos(e.value)}%` })), h('div', { class: 'rk-ticks' }, ...ticks));
}
function thresholdExamples(s) {
  const STAT = { normal: ['Normal', '--ok'], borderline_high: ['Borderline high', '--warn'], high: ['High', '--bad'], low: ['Low', '--low'], borderline_low: ['Borderline low', null] };
  const cards = s.examples.map((e) => {
    const [name, color] = STAT[e.status], c = color ? `var(${color})` : '#f2b78f';
    const b = e.bands.find((x) => (x[0] == null || e.value >= x[0]) && (x[1] == null || e.value < x[1])) || e.bands[0];
    const where = b[2] === 'normal' ? 'inside the normal range' : b[2] === 'borderline' ? `in the borderline band, ${e.status.endsWith('high') ? 'above' : 'below'} normal` : 'in the abnormal band';
    const date = e.when.slice(0, 10), isLab = e.biomarker === 'hba1c';
    const href = isLab ? '#/labs' : `#/week/${mondayOf(date)}`;
    const when = e.when.length > 10 ? `${fmtDate(date, { year: true })} · ${e.when.slice(11, 16)}` : fmtDate(date, { year: true });
    return h('div', { class: 'tx-card', style: `--c: ${c}` },
      h('div', { class: 'tx-top' }, h('span', { class: 'tx-chip' }, name), h('span', { class: 'muted tx-when' }, when)),
      h('div', { class: 'tx-name' }, e.label), h('div', { class: 'tx-val num' }, n1(e.value, e.value % 1 ? 1 : 0), h('small', {}, ' ' + e.unit)),
      ruler(e),
      h('div', { class: 'tx-why' }, h('b', {}, `${n1(e.value, e.value % 1 ? 1 : 0)}${e.unit === '%' ? '%' : ' ' + e.unit}`), ` is ${where} (${rangeText(b, e.unit)}).`),
      h('div', { class: 'muted tx-foot' }, `Reference group: ${String(e.age_group).replace(/_/g, ' ')} · ${n1(e.of_status, 0)} of her ${n1(e.of_measure, 0)} ${/^[A-Z]{2}/.test(e.label) ? e.label : e.label.charAt(0).toLowerCase() + e.label.slice(1)} readings have this status.`),
      h('a', { class: 'btn', href }, isLab ? 'See all her lab results →' : `Open that week →`));
  });
  return card('One real reading for each status', 'Each card is a real reading from her year. The coloured bar is the reference range used: green normal, amber borderline, rose abnormal; the dark marker is where this reading falls.', h('div', { class: 'tx-grid' }, cards));
}


const POS = (label) => { const l = label || ''; return l.startsWith('far') ? 'far' : l.startsWith('clearly') ? 'clearly' : l.startsWith('slightly') ? 'slightly' : l ? 'within' : 'none'; };
const MNAME = { glucose: 'Glucose', heart_rate: 'Heart rate', step_count: 'Steps', sleep_duration: 'Sleep', resting_heart_rate: 'Resting heart rate', blood_pressure: 'Blood pressure', medication_adherence: 'Medicines taken', mood_state: 'Mood', hydration: 'Hydration', screen_time: 'Screen time', sedentary_time: 'Sedentary time', hba1c: 'HbA1c (lab)' };
function stateExamples(s) {
  const st = s.story, A = st.adverse, V = st.favourable, hhmm = (t) => t.slice(11, 16), day = (t) => fmtDate(t.slice(0, 10), { dow: true, year: true });
  const dur = (a, b) => { const m = Math.round((Date.parse(b) - Date.parse(a)) / 60000), hh = Math.floor(m / 60), mm = m % 60; return hh ? `${hh} h${mm ? ` ${mm} min` : ''}` : `${mm} min`; };
  const posChip = (label) => (label ? h('span', { class: `se-pos ${POS(label)}` }, label) : h('span', { class: 'muted' }, '—'));
  const tag = (txt, cls) => h('span', { class: `se-tag ${cls}` }, txt);
  const mname = (k) => MNAME[k] || k.replace(/_/g, ' ');

  // one tick
  const trs = st.tick.rows.map((r) => h('tr', { class: r.open_item ? 'se-open' : '' }, h('td', {}, h('b', {}, mname(r.measure))), h('td', { class: 'r num' }, r.value == null ? '—' : `${typeof r.value === 'number' ? n1(r.value, r.value % 1 ? 1 : 0) : r.value}${r.unit ? ' ' + r.unit : ''}`),
    h('td', { class: 'r num' }, r.median != null ? `${n1(r.median, r.median % 1 ? 1 : 0)} ± ${n1(r.sd, 1)}` : '—'), h('td', {}, posChip(r.label)), h('td', {}, r.clinical ? h('span', { class: 'muted' }, r.clinical.replace(/_/g, ' ')) : '—'),
    h('td', {}, r.open_item ? tag(r.item_class, r.item_class) : '')));
  const tickBox = h('div', { class: 'se-box' }, h('div', { class: 'se-k' }, h('span', { class: 'se-n' }, '1'), 'A tick'),
    h('p', { class: 'se-p' }, `One moment, ${hhmm(st.tick.as_of)} on ${day(st.tick.as_of)} (one of the ${n1(st.ticks_total, 0)} ticks in the year). The engine looks at the newest value of every watched measure and asks how far each is from her usual, in units of her own spread. ${st.tick.n_open} items were open at this tick.`),
    h('div', { class: 'table-wrap' }, h('table', { class: 'tbl se-tbl' }, h('thead', {}, h('tr', {}, ['Measure', 'Newest value', 'Her usual ± spread', 'Position', 'Clinical status', 'Item open'].map((x, i) => h('th', { class: i === 1 || i === 2 ? 'r' : '' }, x)))), h('tbody', {}, trs))));

  // the episode chart
  const chartFor = (item, el) => {
    const pts = item.points, cats = pts.map((q) => hhmm(q.t)), iO = pts.findIndex((q) => q.t === item.opened_at), iC = pts.findIndex((q) => q.t === item.closed_at);
    setTimeout(() => {
      const p = palette(), col = { within: p.muted, slightly: cssVar('--warn'), clearly: cssVar('--bad'), far: cssVar('--bad'), none: p.muted };
      mount(el, base({
        grid: { left: 8, right: 16, top: 34, bottom: 8, containLabel: true },
        tooltip: { ...base().tooltip, trigger: 'axis', formatter: (ps) => { const q = pts[ps[0].dataIndex]; return `<b>${hhmm(q.t)}</b><br>${item.measure.replace(/_/g, ' ')}: <b>${q.v} ${item.unit || ''}</b><br>her usual ${q.med} ± ${q.sd}<br>${q.label} (${q.z} spreads)`; } },
        xAxis: { type: 'category', data: cats, axisTick: { show: false }, axisLabel: { color: p.ink2, interval: 1 } }, yAxis: { ...valueAxis({ scale: true }), name: item.unit, nameTextStyle: { color: p.muted, align: 'left' } },
        series: [
          { type: 'line', id: 'lo', stack: 'b', symbol: 'none', lineStyle: { opacity: 0 }, silent: true, data: pts.map((q) => (q.med != null ? q.med - q.sd : null)) },
          { type: 'line', id: 'rng', stack: 'b', symbol: 'none', lineStyle: { opacity: 0 }, areaStyle: { color: cssVar('--primary'), opacity: 0.2 }, silent: true, data: pts.map((q) => (q.med != null ? 2 * q.sd : null)) },
          { type: 'line', id: 'med', symbol: 'none', lineStyle: { color: cssVar('--primary'), type: 'dashed', width: 1.6 }, silent: true, data: pts.map((q) => q.med) },
          { type: 'line', id: 'val', z: 4, symbol: 'circle', symbolSize: 10, lineStyle: { color: p.ink, width: 2 }, data: pts.map((q) => ({ value: q.v, itemStyle: { color: col[POS(q.label)], borderColor: p.surface, borderWidth: 2 } })),
            markArea: iO >= 0 && iC >= 0 ? { silent: true, data: [[{ xAxis: iO, itemStyle: { color: item.item_class === 'adverse' ? 'rgba(238,148,165,.18)' : 'rgba(124,200,187,.2)' } }, { xAxis: iC }]] } : undefined,
            markLine: { silent: true, symbol: 'none', animation: false, lineStyle: { color: p.ink, type: 'solid', width: 1.2 }, label: { color: p.ink, fontSize: 11.5, fontWeight: 650, position: 'end' }, data: [...(iO >= 0 ? [{ xAxis: iO, label: { formatter: 'item opens' } }] : []), ...(iC >= 0 ? [{ xAxis: iC, label: { formatter: 'item closes' } }] : [])] } }],
      }));
    }, 0);
  };
  const advEl = h('div', { class: 'chart', style: { height: '300px' } }); chartFor(A, advEl);
  const favEl = h('div', { class: 'chart', style: { height: '260px' } }); chartFor(V, favEl);
  const nOpen = A.points.filter((q) => q.open).length;
  const itemBox = h('div', { class: 'se-box' }, h('div', { class: 'se-k' }, h('span', { class: 'se-n' }, '2'), 'An item'),
    h('p', { class: 'se-p' }, `One episode of a measure staying off her usual. Here glucose: the dashed line is her usual for that time of day, the shaded band is one spread either side, and the dots are the ticks. A dot turns rose when the position is "clearly" or "far" off. The first such tick (${hhmm(A.points[A.points.findIndex((q) => q.run === 1)].t)}) only starts a run; the second in a row at ${hhmm(A.opened_at)} opens the item. It closes after two ticks back to "slightly" or better.`), advEl);
  const advBox = h('div', { class: 'se-box se-adv' }, h('div', { class: 'se-k' }, h('span', { class: 'se-n' }, '3'), 'An adverse item'),
    h('p', { class: 'se-p' }, `This item is adverse because glucose above her usual is the bad direction for glucose. Direction decides adverse or favourable; recovery is just how an item closes.`),
    kv([['Item', A.item_id], ['Direction', `${A.direction} her usual`], ['Opened by', `${A.trigger} (two ticks in a row, "${A.size_at_open}" off)`], ['Peak', `${A.size_peak}, ${A.peak_value} ${A.unit} at ${hhmm(A.peak_at)}`], ['Open for', `${dur(A.opened_at, A.closed_at)} (${nOpen} ticks)`], ['Closed because', `${A.close_reason}: back to slightly or better for two ticks`]]));
  const H = A.handoff, alert = S.alerts.find((a) => a.id === H.handoff_id), meal = H.context.last_meal;
  const alertBox = h('div', { class: 'se-box se-alert' }, h('div', { class: 'se-k' }, h('span', { class: 'se-n' }, '4'), 'An alert'),
    h('p', { class: 'se-p' }, 'Every adverse item becomes one alert (a hand-off) the moment it opens: a small record of what was happening, which the Rulebook Lookup receives next.'),
    kv([['Alert id', H.handoff_id], ['Written', `${hhmm(H.written_at)} on ${day(H.written_at)}`], ['What', `${A.measure} ${H.direction} her usual, ${H.size}`], ['Value', `${H.value} ${A.unit}, ${H.position_z} spreads off (usual based on ${H.usual_basis.replace(/_/g, ' ')})`], ['Clinical status', H.clinical_status],
      ['Last meal', meal ? `${meal.label.replace(/_/g, ' ')}, ${dur(meal.time, H.written_at)} earlier` : '—'], ['Sleep last night', `${H.context.sleep_last_night.value} h (${H.context.sleep_last_night.position})`], ['Other open items', H.context.other_open_items.map((x) => mname(x)).join(', ') || 'none'], ['Diary entries today', String(H.context.diary_today_count)]]),
    alert && alert.case ? h('a', { class: 'btn', href: `#/case/${encodeURIComponent(alert.case)}`, style: { alignSelf: 'flex-start' } }, 'Open the case this alert is in →') : null);
  const favBox = h('div', { class: 'se-box se-fav' }, h('div', { class: 'se-k' }, h('span', { class: 'se-n' }, '5'), 'A favourable item'),
    h('p', { class: 'se-p' }, `On ${day(V.opened_at)} glucose ran well below her usual for ${dur(V.opened_at, V.closed_at)}. That is the welcome direction for glucose, so the item is recorded, with no alert written. (${V.item_id})`), favEl,
    kv([['Direction', `${V.direction} her usual`], ['Class', 'favourable: recorded, no hand-off'], ['Furthest from her usual', `${V.peak_value} ${V.unit} at ${hhmm(V.peak_at)}`], ['Closed because', V.close_reason]]));

  return card('One real episode, from a tick to an alert', `A real afternoon, ${fmtDate(A.opened_at.slice(0, 10), { year: true })}, and one favourable episode for contrast. Each box is one of the five terms.`, h('div', { class: 'stack', style: { gap: '16px' } }, tickBox, itemBox, h('div', { class: 'se-row' }, advBox, alertBox), favBox));
}


const RULE_NAME = (id) => id.replace('_above_post_meal', ' above, within 180 min of a meal').replace('_above_no_recent_meal', ' above, no recent meal').replace(/_/g, ' ').replace(/^./, (c) => c.toUpperCase());
const TIER_COLOR = { primary: '#7cc8bb', secondary: '#b6acec', tertiary: '#f2cf8a' };
function rulebookExplorer(s) {
  const rules = s.rulebook_table, nCand = rules.reduce((a, r) => a + r.candidates.length, 0);
  let cur = 0;
  const list = h('div', { class: 'rb-list' }), panel = h('div', { class: 'rb-panel' });
  const human = (c) => c.replace(/_/g, ' ').replace(/^./, (x) => x.toUpperCase());
  const skipText = (k, n, c) => { const [reason, detail] = k.split('|'); return reason === 'no_stream' ? `Skipped in ${n} alert${n > 1 ? 's' : ''}: no data stream (${(detail || '').replace(/_/g, ' ')})` : `Skipped in ${n} alert${n > 1 ? 's' : ''}: it applies only if ${c.applies_if || detail}, and that did not hold`; };
  const draw = () => {
    list.replaceChildren(...rules.map((r, i) => h('button', { type: 'button', class: `rb-rule ${i === cur ? 'on' : ''} ${r.status !== 'active' ? 'off' : ''}`, onclick: () => { cur = i; draw(); } },
      h('b', {}, RULE_NAME(r.rule_id)), h('span', { class: 'muted' }, `${r.alerts} alerts · ${r.candidates.length} candidates${r.status !== 'active' ? ' · deferred' : ''}`))));
    const r = rules[cur];
    const budget = r.status === 'active'
      ? [`primary: all ${r.primary}`, `secondary: up to ${r.secondary}`, `tertiary: up to ${r.tertiary}`, `at most ${r.max_total} in a packet`] : ['rule not switched on: its candidates are listed but not tested'];
    panel.replaceChildren(
      h('div', { class: 'rb-head' }, h('h3', {}, RULE_NAME(r.rule_id)), h('span', { class: `chip ${r.status === 'active' ? 'ok' : 'warn'}` }, r.status)),
      h('p', { class: 'rb-when' }, h('b', {}, 'Used when: '), r.when, `. It matched ${r.alerts} alerts this year.`),
      h('div', { class: 'rb-budget' }, budget.map((b) => h('span', { class: 'chip' }, b))),
      h('p', { class: 'muted rb-why' }, r.why_budget),
      h('div', { class: 'rb-cands' }, r.candidates.map((c) => {
        const pct = r.alerts ? (100 * c.selected / r.alerts) : 0, sk = Object.entries(c.skipped), ns = Object.entries(c.not_selected);
        return h('div', { class: 'rb-cand', style: `--c: ${TIER_COLOR[c.tier]}` },
          h('div', { class: 'rb-rank' }, c.rank),
          h('div', { class: 'rb-body' },
            h('div', { class: 'rb-top' }, h('b', {}, human(c.candidate)), h('span', { class: 'rb-tier' }, c.tier), h('span', { class: 'chip', title: 'Strength of the published evidence behind this candidate' }, `evidence ${c.level}`)),
            h('div', { class: 'rb-check' }, c.check, c.outcome ? h('span', { class: 'muted' }, ` → compared on: ${c.outcome}`) : null),
            h('div', { class: 'rb-chips' }, h('span', { class: 'chip' }, `looks back: ${c.lookback}`), c.data_kinds ? h('span', { class: 'chip' }, `needs: ${c.data_kinds}`) : null, h('span', { class: `chip ${c.applies_if ? 'warn' : ''}` }, c.applies_if ? `only if: ${c.applies_if}` : 'always applies')),
            h('div', { class: 'rb-use' }, h('span', { class: 'rb-bar' }, h('i', { style: `width:${pct}%` })), h('span', { class: 'num' }, `selected in ${c.selected} of ${r.alerts}`),
              ...sk.map(([k, n]) => h('span', { class: 'rb-skip' }, skipText(k, n, c))), ...ns.map(([k, n]) => h('span', { class: 'rb-skip cut' }, k === 'rule_deferred' ? `Not tested in ${n} alerts: rule deferred` : `Cut by the budget in ${n} alert${n > 1 ? 's' : ''}`)))));
      })));
  };
  draw();
  return card(`The rulebook: ${rules.length} rules, ${nCand} candidates`, 'Pick a rule to see when it is used, how many candidates a packet may hold, and every candidate with the check it runs and what happened to it across the year\'s alerts. The rulebook is fixed: nothing here is learned from her.', h('div', { class: 'rb-wrap' }, list, panel));
}

function piExample(stages) {
  const m = S.memByKey.get('sleep_hours@prev_night->hr_day_mean') || S.pi.memories[0];
  const v = m.versions[m.versions.length - 1], c = m.counters;
  const rel = ((stages.find((x) => x.id === 'evidence') || {}).relationships || []).find((r) => r.key === m.key);
  const cases = S.cases.filter((x) => x.keys.includes(m.key));
  const tile = (n, l, d) => h('div', { class: 'ex-tile' }, h('span', { class: 'ex-tn num' }, n), h('b', {}, l), h('span', { class: 'muted' }, d));
  const el = h('div', { class: 'chart clickable', style: { height: '190px' } });
  const wl = m.weekly_labels.map((x) => x[0]);
  setTimeout(() => {
    const p = palette();
    const col = { supported: cssVar('--ok'), suggestive: cssVar('--warn'), not_supported: cssVar('--low'), insufficient: p.line };
    const chart = mount(el, base({
      grid: { left: 8, right: 14, top: 24, bottom: 8, containLabel: true },
      tooltip: { ...base().tooltip, trigger: 'item', formatter: (q) => `<b>${q.data.w}</b><br>${q.data.l.replace(/_/g, ' ')} · her history backed it on ${q.value} of ${q.data.n} days<br><span style="opacity:.7">Click to see that week</span>` },
      xAxis: { type: 'category', data: wl, axisTick: { show: false }, axisLine: { lineStyle: { color: p.line } }, axisLabel: { color: p.muted, interval: 4, formatter: (w) => w.slice(2).replace('-W', ' w') } },
      yAxis: { ...valueAxis({ max: 7 }), minInterval: 1, splitLine: { lineStyle: { color: p.line, type: [4, 6], opacity: 0.6 } } },
      series: [{ type: 'bar', barWidth: '62%', data: m.weekly_labels.map((x) => ({ value: x[2], w: x[0], l: x[1], n: x[3], itemStyle: { color: col[x[1]], borderRadius: [4, 4, 0, 0] } })),
        markLine: { silent: true, symbol: 'none', z: 10, lineStyle: { color: p.ink, width: 1.5, type: 'dashed', opacity: 0.8 }, label: { show: false },
          data: m.status_history.map((t) => ({ xAxis: t.week, name: `${t.from} → ${t.to}` })) } }],
    }));
    chart.on('click', (q) => { if (q.data && q.data.w) location.hash = `#/pi/week/${q.data.w}`; });
  }, 0);
  const days = rel ? rel.days : null, total = days ? Object.values(days).reduce((a, b) => a + b, 0) : 0;
  const LABS = [['supported', '--ok'], ['suggestive', '--warn'], ['not_supported', '--low'], ['insufficient', '--muted']];
  return card('A real example', 'One long-term note, followed from its first sighting to the end of the year', h('div', { class: 'stack', style: { gap: '16px' } },
    h('div', { class: 'ex-head' },
      h('div', { class: 'ex-title' }, `${m.phrase} → ${m.outcome}`),
      h('div', { class: 'row', style: { gap: '8px', flexWrap: 'wrap' } }, labelChip(m.status), m.same_day_only ? h('span', { class: 'chip' }, 'same day only') : null, h('span', { class: 'chip' }, `created in ${m.created_week}`), h('span', { class: 'chip' }, `${m.versions.length} versions`), h('a', { class: 'btn', href: `#/pi/${encodeURIComponent(m.key)}` }, 'Open its full history'))),
    h('div', { class: 'ex-note' }, h('div', { class: 'ex-k' }, `What PI wrote · version ${v.version}, ${fmtDate(v.written_at.slice(0, 10), { year: true })}`),
      h('p', { class: 'ex-quote' }, v.association), v.situations ? h('p', { class: 'ex-sit' }, v.situations) : null),
    h('div', { class: 'ex-tiles' },
      tile(fmtDate(c.first_seen, { year: true }), 'first seen', 'the first day it appeared in a case'), tile(fmtDate(c.last_seen, { year: true }), 'last seen', 'the most recent day'),
      tile(n1(c.case_days, 0), 'days it appeared', `${c.exposed_case_days} of them with the factor itself present`), tile(n1(c.weeks_seen, 0), 'weeks seen', `across ${cases.length} cases`)),
    h('div', { class: 'ex-box' }, h('div', { class: 'ex-k' }, 'How well her history backed it, week by week'), h('p', { class: 'muted', style: { margin: '0 0 6px', fontSize: '12.5px' } }, 'Bar height = days that week (of 7) her own history supported it; colour = the label that week; the dashed line marks the week the note changed status (' + m.status_history.map((t) => `${t.from} → ${t.to}, ${t.week}`).join('; ') + '). Click a bar to open that week.'), el),
    days ? h('div', { class: 'ex-box' }, h('div', { class: 'ex-k' }, 'Same relationship in the Evidence Engine'), h('p', { class: 'muted', style: { margin: '0 0 8px', fontSize: '12.5px' } }, `The Evidence Engine tested this every day of the year (${n1(total, 0)} daily records). PI turns those daily labels into the weekly ones above.`),
      h('span', { class: 'rel-strip', style: 'height:14px' }, LABS.map(([k, cv]) => (days[k] ? h('i', { style: `width:${100 * days[k] / total}%; background: var(${cv})`, title: `${k.replace(/_/g, ' ')}: ${days[k]}` }) : null))),
      h('div', { class: 'row', style: { gap: '14px', flexWrap: 'wrap', marginTop: '8px' } }, LABS.map(([k, cv]) => h('span', { class: 'rel-key', style: `--c: var(${cv})` }, h('i', {}), `${k.replace(/_/g, ' ')} ${days[k] || 0}`)), h('a', { href: '#/stage/evidence', style: { marginLeft: 'auto' } }, 'See all 63 relationships →'))) : null,
    h('div', { class: 'ex-box' }, h('div', { class: 'ex-k' }, `Cases where it came up (${cases.length})`), h('div', { class: 'row', style: { gap: '6px', flexWrap: 'wrap' } },
      cases.slice(0, 12).map((x) => h('a', { class: 'chip ep', href: `#/case/${encodeURIComponent(x.id)}`, title: x.headline }, fmtDate(x.date, {}))), cases.length > 12 ? h('span', { class: 'muted' }, `and ${cases.length - 12} more`) : null))));
}

function sample(s) {
  const sm = s.sample;
  const out = h('div', { class: 'stack', style: { gap: '12px' } });
  Object.entries(sm).forEach(([k, v]) => {
    if (v == null) return;
    out.append(h('h3', {}, k.replace(/_/g, ' ')));
    if (k === 'packet') out.append(packetBox(v));
    else if (k === 'evidence') out.append(evidenceBox(v));
    else if (Array.isArray(v)) v.forEach((r) => out.append(h('div', { class: 'sample' }, kvlist(r))));
    else out.append(h('div', { class: 'sample' }, kvlist(flat(v))));
  });
  return out;
}
const flat = (o) => Object.fromEntries(Object.entries(o).filter(([k]) => !['sentences', 'facts', 'weekly_labels'].includes(k)).map(([k, v]) => [k, Array.isArray(v) && v.length > 6 ? `${v.length} items` : v]));

function packetBox(p) {
  return h('div', { class: 'sample' }, kvlist({ rule: p.rule, status: p.status, 'candidates selected': p.selected.length, skipped: p.n_skipped, 'not selected': p.n_not_selected }),
    table([{ label: '#', render: (r) => r.rank }, { label: 'Tier', render: (r) => h('span', { class: 'chip' }, r.tier) }, { label: 'Candidate', render: (r) => r.candidate.replace(/_/g, ' ') }, { label: 'What is checked', render: (r) => r.text || r.check }], p.selected));
}
function evidenceBox(e) {
  return h('div', { class: 'sample' }, kvlist({ 'method': e.method, factors: e.factors.length }),
    table([{ label: '#', render: (r) => r.rank }, { label: 'Factor', render: (r) => r.phrase || r.candidate }, { label: 'Compared with', render: (r) => r.outcome || '—' }, { label: 'Label', render: (r) => labelChip(r.support) }], e.factors));
}

// ---- stage specific charts -------------------------------------------------------------------------------------------------------------
function bar(title, sub, data, { horizontal = true, color, height = 260 } = {}) {
  const el = h('div', { class: 'chart', style: { height: `${height}px` } });
  setTimeout(() => {
    const p = palette();
    mount(el, base({
      grid: { left: 8, right: 40, top: 10, bottom: 8, containLabel: true },
      tooltip: { ...base().tooltip, trigger: 'item' },
      xAxis: horizontal ? valueAxis() : { type: 'category', data: data.map((d) => d[0]), axisLabel: { color: p.muted } },
      yAxis: horizontal ? { type: 'category', inverse: true, data: data.map((d) => d[0]), axisLabel: { color: p.ink2 }, axisLine: { show: false }, axisTick: { show: false } } : valueAxis(),
      series: [{ type: 'bar', data: data.map((d) => ({ value: d[1], itemStyle: { color: d[2] || color || p.primary, borderRadius: horizontal ? [0, 6, 6, 0] : [6, 6, 0, 0] } })), barMaxWidth: 20, label: { show: horizontal, position: 'right', color: p.ink2 } }],
    }));
  }, 0);
  return card(title, sub, el);
}

const SPECIFIC = {
  threshold: () => {
    const pl = S.meta.pipeline, counts = pl.status_counts;
    const ST = [
      { k: 'borderline_high', name: 'Borderline high', color: '--warn', def: 'Above the normal range, but not yet past the abnormal cut-point (glucose 99 to 126 mg/dL). Mostly glucose.' },
      { k: 'high', name: 'High', color: '--bad', def: 'Past the abnormal cut-point on the high side (glucose 126 or more, HbA1c 6.5% or more).' },
      { k: 'normal', name: 'Normal', color: '--ok', def: 'Inside the reference range for that measure (resting heart rate 60 to 100, glucose 70 to 99).' },
      { k: 'low', name: 'Low', color: '--low', def: 'Past the abnormal cut-point on the low side (sleep under 6 hours, steps under 4,000 a day).' },
      { k: 'borderline_low', name: 'Borderline low', color: null, def: 'Below the normal range but not yet abnormal (sleep 6 to 7 hours, hydration 1,500 to 2,000 mL).' }];
    const colorOf = (x) => (x.color ? cssVar(x.color) : '#f2b78f');
    const total = ST.reduce((a, x) => a + (counts[x.k] || 0), 0);
    const el = h('div', { class: 'chart', style: { height: '260px' } });
    setTimeout(() => {
      const p = palette();
      mount(el, base({
        tooltip: { ...base().tooltip, trigger: 'item', formatter: (q) => `<b>${q.name}</b><br>${n1(q.value, 0)} readings · ${q.percent}%` },
        title: { text: n1(total, 0), subtext: 'readings with a status', left: 'center', top: '38%', textStyle: { color: p.ink, fontSize: 24, fontWeight: 700 }, subtextStyle: { color: p.muted, fontSize: 12 } },
        series: [{ type: 'pie', radius: ['62%', '86%'], center: ['50%', '50%'], padAngle: 2, itemStyle: { borderRadius: 7, borderColor: p.surface, borderWidth: 2 }, label: { show: false }, emphasis: { scale: true, scaleSize: 5 },
          data: ST.map((x) => ({ name: x.name, value: counts[x.k] || 0, itemStyle: { color: colorOf(x) } })) }],
      }));
    }, 0);
    const legend = h('div', { class: 'stack', style: { gap: '9px', justifyContent: 'center' } }, ST.map((x) => h('div', { class: 'gist-def', style: `--c: ${colorOf(x)}` }, h('i', {}),
      h('div', {}, h('div', { class: 'row', style: { gap: '8px', alignItems: 'baseline' } }, h('b', {}, x.name), h('span', { class: 'num muted' }, `${n1(counts[x.k] || 0, 0)} · ${(100 * (counts[x.k] || 0) / total).toFixed(1)}%`)), h('div', { class: 'muted', style: { fontSize: '13px' } }, x.def)))));
    return card('Status given to each evaluated reading', 'Compared with fixed reference ranges only, never with her own baseline', h('div', { class: 'grid g2', style: { alignItems: 'center' } }, el, legend));
  },
  linker: (s) => {
    const f = s.flow, c = s.counts;
    const notLinked = f.status_rows - f.linked;
    const fn = (cls, n, label, cap, tip) => h('div', { class: `fnode ${cls}`, tabindex: 0 }, h('span', { class: 'fn-n num' }, n1(n, 0)), h('span', { class: 'fn-l' }, label), h('span', { class: 'fn-c' }, cap), h('div', { class: 'ftip' }, tip));
    const fa = (text, cls = '') => h('div', { class: `farrow ${cls}` }, h('span', {}, text), h('i', {}));
    const at = (col, row, span, el) => { el.style.gridColumn = col; el.style.gridRow = span ? `${row} / span ${span}` : row; return el; };
    const op = (sym) => h('div', { class: 'f-op' }, sym);
    const flowA = h('div', { class: 'gflow' },
      at(1, 1, 2, fn('f-grey', f.status_rows, 'status rows', 'from component 1', 'Every reading that received a status (normal, borderline, high or low) in the Plausibility filter and Threshold evaluator: 77,792 passed readings, of which 44,469 could be judged.')),
      at(2, 1, 0, fa('only high or low glucose')), at(2, 2, 0, fa('everything else', 'soft')),
      at(3, 1, 0, fn('f-purple', f.linked, 'glucose readings linked', `${n1(f.glucose_status.high, 0)} high · ${f.glucose_status.low} low`, 'Only CGM glucose readings with status high or low are linked. Borderline readings, normal readings and the fasting-glucose lab results are deliberately left out.')),
      at(3, 2, 0, fn('f-blue soft', notLinked, 'not linked', 'borderline or normal glucose, every other measure', 'Readings that stay in the store as they are but are not paired with anything: 18,120 borderline-high glucose, 759 normal glucose, and all heart rate, sleep, lab, blood pressure and other statuses.')),
      at(4, 1, 0, fa('checked against 8 kinds of nearby events')),
      at(5, 1, 0, fn('f-green solid', f.pairings, 'pairings', `${(f.pairings / f.linked).toFixed(1)} per linked reading`, 'A pairing is one row: a glucose reading plus something that happened near it in time (a meal, a medicine, an active hour, sleep, mood, diary, an event, a heart-rate summary). It says "this happened nearby", never that it caused anything.')));
    const flowB = h('div', { class: 'gflow gflow-b' },
      at(1, 1, 0, fn('f-grey', f.store_readings, 'status rows', 'kept as they are', 'All 44,469 status rows are written to the store, linked or not.')), at(2, 1, 0, op('+')),
      at(3, 1, 0, fn('f-green', f.store_pairings, 'pairings', 'written as well', 'The pairings from the linker are written to the same table.')), at(4, 1, 0, op('=')),
      at(5, 1, 0, fn('f-warn solid', f.store_readings + f.store_pairings, 'store rows', 'table raw_events', 'The Personal Data Store\'s main table, raw_events: the status rows and the pairings, nothing else. The store only stores; it computes nothing.')),
      at(1, 2, 0, fn('f-blue', c['context events'], 'context events', 'a separate table', 'Things from her life that are recorded but never given a status, kept in their own table (context_events) so the linker and later components can look them up. Nothing is paired or computed here.')),
      at(2, 2, 3, h('div', { class: 'gnote', style: 'grid-column: 2 / 6 !important; margin-left: 10px' }, h('b', {}, 'Context events: '), Object.entries(f.context_streams).map(([k, v]) => `${k.replace(/_/g, ' ')} ${n1(v, 0)}`).join(' · '))));

    // pairing kinds: donut + the fixed rule for each
    const KIND = [
      ['medication', 'Medication', 'Each medicine logged that calendar day (the adherence record has no time).', 'always 3 per reading', '#7cc8bb'],
      ['activity', 'Activity', 'An hour of steps that started up to 90 minutes before, with steps above zero.', 'zero or more', '#b6acec'],
      ['diary', 'Diary', 'The diary entry of that day.', 'always 1', '#f2cf8a'], ['heart_rate', 'Heart rate', 'A summary (average, lowest, highest, count) of the heart rate within 2 hours either side.', 'always 1', '#f0a3b2'],
      ['mood', 'Mood', 'The mood record for that part of the day: morning, afternoon or evening.', 'always 1', '#9db9ee'], ['sleep', 'Sleep', 'The sleep record of the night before.', 'always 1', '#8fd1a8'],
      ['meal', 'Meal', 'A meal that started up to 150 minutes before the reading.', 'zero or more', '#f2b78f'], ['context_event', 'Context event', 'Any event logged on the same calendar day, before or after the reading.', 'zero or more', '#a9bdb7']];
    const total = c.pairings, n = (k) => c[`pairings: ${k}`] || 0;
    const el = h('div', { class: 'chart', style: { height: '300px' } });
    setTimeout(() => {
      const p = palette();
      mount(el, base({
        tooltip: { ...base().tooltip, trigger: 'item', formatter: (q) => `<b>${q.name}</b><br>${n1(q.value, 0)} pairings · ${q.percent}%` },
        title: { text: n1(total, 0), subtext: 'pairings', left: 'center', top: '39%', textStyle: { color: p.ink, fontSize: 26, fontWeight: 700 }, subtextStyle: { color: p.muted, fontSize: 12 } },
        series: [{ type: 'pie', radius: ['60%', '86%'], center: ['50%', '50%'], padAngle: 2, itemStyle: { borderRadius: 7, borderColor: p.surface, borderWidth: 2 }, label: { show: false }, emphasis: { scale: true, scaleSize: 5 },
          data: KIND.map(([k, name, , , col]) => ({ name, value: n(k), itemStyle: { color: col } })) }],
      }));
    }, 0);
    const rules = h('div', { class: 'stack', style: { gap: '8px' } }, KIND.map(([k, name, rule, many, col]) => h('div', { class: 'gist-def', style: `--c: ${col}` }, h('i', {}),
      h('div', {}, h('div', { class: 'row', style: { gap: '8px', alignItems: 'baseline', flexWrap: 'wrap' } }, h('b', {}, name), h('span', { class: 'num muted' }, `${n1(n(k), 0)} · ${(100 * n(k) / total).toFixed(1)}%`), h('span', { class: 'chip', style: { fontSize: '11px' } }, many)),
        h('div', { class: 'muted', style: { fontSize: '13px' } }, rule)))));
    return h('div', { class: 'stack' },
      card('From status rows to the store', 'Hover any box for its definition', h('div', { class: 'stack', style: { gap: '18px' } }, flowA, h('div', { class: 'gflow-sep' }, h('span', {}, 'What the Personal Data Store then holds')), flowB)),
      card('Pairings by kind, and the fixed rule for each', 'The same eight kinds are checked for every linked reading; the time windows are fixed numbers, with no learning and no model. Whether a row is written depends on what actually happened nearby.',
        h('div', { class: 'grid g2', style: { alignItems: 'start' } }, el, rules)));
  },
  baseline: (s) => {
    const f = s.flow, T = f.tiers, e = s.example_week;
    const fn = (cls, n, label, cap, tip, step) => h('div', { class: `fnode ${cls}`, tabindex: 0 }, step ? h('span', { class: 'bs-num' }, step) : null, h('span', { class: 'fn-n num' }, n), h('span', { class: 'fn-l' }, label), h('span', { class: 'fn-c' }, cap), h('div', { class: 'ftip' }, tip));
    const fa = (text, cls = '') => h('div', { class: `farrow ${cls}` }, h('span', {}, text), h('i', {}));
    const at = (col, row, span, el) => { el.style.gridColumn = col; el.style.gridRow = span ? `${row} / span ${span}` : row; return el; };
    const days = T.day.windows, weeks = T.week.windows, months = T.month.windows;

    // ---- what comes in
    const inFlow = h('div', { class: 'gflow' },
      at(1, 1, 0, fn('f-grey', n1(f.in_status_rows, 0), 'status rows', 'from the store', 'The readings that received a status in component 1. The engine takes the time, the measure, the value and the status of each.')),
      at(1, 2, 0, fn('f-blue', n1(f.in_context, 0), 'context events', 'from the store', 'Heart rate, medication taken or missed, mood, meals, location, sleep quality and diary entries, copied from her files without any status.')),
      at(2, 1, 2, fa('grouped by local day')),
      at(3, 1, 2, fn('f-green solid', days, 'days', '1 Oct 2025 to 17 Sep 2026', 'Every row is assigned to a calendar day in her time zone. From here on the engine works day by day.')),
      at(4, 1, 2, h('div', { class: 'gnote', style: 'grid-column: 4 / 6 !important' }, h('b', {}, 'Not used: '), `${n1(f.not_used_pairings, 0)} pairings (the linker's "this was nearby" rows) and ${n1(f.not_used_hourly_steps, 0)} hourly steps (kept for the Rulebook; the engine uses the daily step totals from the status rows). It never reads an alert.`)));

    // ---- the nine steps
    const STEPS = [
      ['Load by day', n1(days, 0), 'days of data', 'Group the 44,469 status rows and the 45,952 context events by local day.', 'f-grey'],
      ['Clean the glucose', n1(f.removed, 0), `readings removed (${f.removed_days} days)`, 'A glucose reading is removed before any metric is computed if it is outside the device range (40 to 400 mg/dL) or jumps more than 75 mg/dL per 15 minutes. The raw values are kept on record.', 'f-warn'],
      ['Turn each day into numbers', '13', 'measures per day', 'Average glucose, time in range, variability, post-meal peak, heart rate, resting heart rate, sleep, steps, sedentary time, medicines taken, strained mood periods, hydration and screen time.', 'f-blue'],
      ['Work out her usual', '14', 'days to learn it', 'For each measure: the median, the spread and a flat band (half a spread), from only the days before the window. Until 14 days of history exist, nothing is judged.', 'f-purple'],
      ['Build the windows', `${n1(weeks, 0)} + ${months}`, 'weeks and months', `Every day from the 7th gets a week window (the 7 days ending then); every 30 days a month checkpoint. Each is compared with the one before. Plus the ${days} day windows.`, 'f-green'],
      ['Label the changes', '3', 'directions · 3 sizes', 'Each change is compared with her own flat band: flat, up or down, and small, moderate or large.', 'f-blue'],
      ['Decide what is notable', `${T.day.notable} · ${T.week.notable} · ${T.month.notable}`, 'days · weeks · months', 'Configured thresholds are checked on cleaned values. A window that crosses one is notable, and the reason is recorded. A crossing caused only by a bad reading is set aside.', 'f-red'],
      ['List the material changes', `${T.day.quiet}`, 'quiet days (no weeks or months)', 'A typed list: thresholds crossed, every missed dose, diary entries, statuses worse than her usual, large changes and data gaps. An empty list means a quiet window.', 'f-warn'],
      ['Write the gist', '590', '120 written by code', 'The model words the facts the code decided: 528 passed the checks first time, 62 after a retry. The 120 windows that are too early or quiet get a plain line written by code.', 'f-green solid']];
    const stepGrid = h('div', { class: 'bs-grid' }, STEPS.map(([name, n, cap, tip, cls], i) => fn(cls, n, name, cap, tip, i + 1)));

    // ---- one real window, step by step
    const M = (k) => S.baseline_meta.measures.find((m) => m.key === k);
    const dec = (k, v) => n1(v, M(k) ? M(k).decimals : 1);
    const KEYS = ['cgm_glucose_reading', 'sleep_duration', 'step_count', 'resting_heart_rate', 'continuous_heart_rate', 'medication_adherence'];
    const tbl = (head, rows, text = false) => h('div', { class: 'table-wrap' }, h('table', { class: `tbl bs-tbl ${text ? 'bs-text' : ''}` }, h('thead', {}, h('tr', {}, head.map((x, i) => h('th', { class: i && !text ? 'r' : '' }, x)))), h('tbody', {}, rows.map((r) => h('tr', {}, r.map((c, i) => h('td', { class: i && !text ? 'r num' : '' }, c)))))));
    const med = (id) => id.replace(/^med_\d+_/, '');
    const g = e.glucose, tagOf = (k) => e.tags.find((t) => t.measure === k);
    const dayLabel = (d) => fmtDate(d, { dow: true });
    const matLine = (x) => {
      if (x.kind === 'missed_dose') return `Missed ${med(x.medicine)}: ${x.days} of ${x.of} days`;
      if (x.kind === 'diary_event') return `${fmtDate(x.date)}: ${x.text}`;
      if (x.kind === 'status_worse_than_usual') return `${measureName(x.measure)} ${String(x.status).replace(/_/g, ' ')} on ${x.days} of ${x.of} ${x.unit || 'days'} (her usual: ${String(x.usual).replace(/_/g, ' ')})`;
      if (x.kind === 'large_change') return `${x.label} went ${x.direction_word}, a ${x.size} change`;
      if (x.kind === 'anchor_crossed') return `Threshold crossed: ${x.anchor.replace(/_/g, ' ')}`;
      return x.kind.replace(/_/g, ' ');
    };
    const panels = [
      () => [h('p', { class: 'bs-lead' }, `Week window ${fmtDate(e.start)} → ${fmtDate(e.end, { year: true })}: ${e.n_days} days of the store's rows.`),
        kv([['Glucose readings', `${n1(g.n_readings, 0)} of ${e.n_days * 96} expected (${n1(g.completeness_pct, 0)}% complete)`], ['Medicine records', `${e.n_days * 3} expected (3 medicines × ${e.n_days} days)`], ['Mood records', `${e.n_days * 3} expected (3 time blocks × ${e.n_days} days)`], ['Diary entries in the window', String(e.material_kinds.diary_event || 0)]])],
      () => [h('div', { class: 'bs-big num' }, n1(e.removed, 0), h('small', {}, ' glucose readings removed this week')),
        h('p', { class: 'muted' }, `The rule: a reading is removed if it is outside 40 to 400 mg/dL, or jumps more than 75 mg/dL per 15 minutes from the last kept reading. This week nothing was removed. Across the whole year ${f.removed} readings were removed, on ${f.removed_days} days${f.removed_examples[0] ? `, for example ${f.removed_examples[0].value} mg/dL on ${fmtDate(f.removed_examples[0].time.slice(0, 10), { year: true })}` : ''}.`)],
      () => [tbl(['Day', 'Avg glucose', 'Time in range', 'Sleep (h)', 'Steps', 'Medicines taken', 'Missed'], e.daily.map((d) => [dayLabel(d.date), n1(d.glucose_mean, 0), `${n1(d.tir_pct, 0)}%`, n1(d.sleep_hours, 1), n1(d.steps, 0), `${n1(d.adherence_pct, 0)}%`, (d.missed_medicines || []).map(med).join(', ') || '—'])),
        h('p', { class: 'muted' }, `The week's value is the mean of these daily values (glucose pooled over the cleaned readings): glucose ${dec('cgm_glucose_reading', e.vals.cgm_glucose_reading)} mg/dL, sleep ${dec('sleep_duration', e.vals.sleep_duration)} h, steps ${dec('step_count', e.vals.step_count)}, medicines taken ${dec('medication_adherence', e.vals.medication_adherence)}%.`)],
      () => [tbl(['Measure', 'Her usual (median)', 'Normal spread (±)', 'Flat band', 'Days it rests on'], KEYS.map((k) => [`${M(k).label} (${M(k).unit})`, dec(k, e.prof[k][1]), dec(k, e.prof[k][2]), dec(k, e.prof[k][3]), n1(e.prof[k][0], 0)])),
        h('p', { class: 'muted' }, `Computed only from the ${e.prof.cgm_glucose_reading[0]} days before ${fmtDate(e.start)}. The flat band is half a spread: a change smaller than that counts as no change.`)],
      () => [tbl(['Measure', 'This week', 'Previous week', 'Change'], KEYS.map((k) => { const d = e.vals[k] - e.prev[k]; return [`${M(k).label} (${M(k).unit})`, dec(k, e.vals[k]), dec(k, e.prev[k]), `${d > 0 ? '+' : d < 0 ? '−' : ''}${dec(k, Math.abs(d))}`]; })),
        h('p', { class: 'muted' }, 'A week window is compared with the 7 days before it; a month checkpoint with the previous checkpoint.')],
      () => [h('div', { class: 'bs-tags' }, [...e.tags].sort((a, b) => ['none', 'small', 'moderate', 'large'].indexOf(b.size) - ['none', 'small', 'moderate', 'large'].indexOf(a.size)).filter((t) => t.direction !== 'not_enough_data').map((t) => h('div', { class: `bs-tag ${t.direction === 'flat' ? 'flat' : t.size}` }, h('b', {}, t.label), h('span', {}, t.direction === 'flat' ? 'about the same' : `${t.direction_word || t.direction} · ${t.size}`)))),
        h('p', { class: 'muted' }, 'Each change is measured against her own flat band for that measure, so "large" for heart rate and "large" for steps mean the same thing: far outside her normal wobble.')],
      () => [h('div', { class: 'row', style: { gap: '8px', flexWrap: 'wrap' } }, e.anchors.map((a) => h('span', { class: 'chip bad' }, a.replace(/_/g, ' ')))),
        h('div', { class: 'bl-why' }, h('b', {}, 'Why this week is notable: '), e.reason),
        h('p', { class: 'muted' }, `The thresholds are checked on the cleaned values. Across the year ${T.day.notable} of ${days} days, ${T.week.notable} of ${weeks} weeks and ${T.month.notable} of ${months} months were notable.`)],
      () => [h('ul', { class: 'points' }, e.material.map((x) => h('li', {}, matLine(x)))), h('p', { class: 'muted' }, 'This list is what the gist is written from. A window with an empty list is "quiet": 91 days were, and no week or month.')],
      () => [h('div', { class: 'bl-head' }, e.headline), h('ul', { class: 'points' }, e.sentences.map((x) => h('li', {}, x))),
        h('div', { class: 'row', style: { gap: '8px' } }, h('span', { class: 'chip ok' }, e.gist_status === 'gist_ok' ? 'worded by the model, passed the checks first time' : e.gist_status.replace(/_/g, ' '))),
        h('p', { class: 'muted' }, 'The model never received her numbers: its view has no digits, only what moved, with sizes and frequencies as words. Code checks every sentence for direction, causal words and numbers.')]];
    let cur = Math.min(START_STEP, STEPS.length - 1);
    const panel = h('div', { class: 'bs-panel' }), tabs = h('div', { class: 'bs-tabs' });
    const draw = () => {
      tabs.replaceChildren(...STEPS.map(([name], i) => h('button', { type: 'button', class: `bs-tab ${i === cur ? 'on' : ''}`, onclick: () => { cur = i; draw(); } }, h('i', {}, i + 1), name)));
      panel.replaceChildren(h('div', { class: 'bs-ptitle' }, h('span', { class: 'bs-num' }, cur + 1), STEPS[cur][0]), ...panels[cur](),
        h('div', { class: 'row', style: { gap: '8px', marginTop: '6px' } }, cur > 0 ? h('button', { type: 'button', class: 'bl-btn', onclick: () => { cur--; draw(); } }, '◀ previous step') : null, cur < STEPS.length - 1 ? h('button', { type: 'button', class: 'bl-btn', onclick: () => { cur++; draw(); } }, 'next step ▶') : null,
          h('a', { class: 'btn', href: `#/baselines/week/${e.end}/cgm_glucose_reading`, style: { marginLeft: 'auto' } }, 'Open this week on Her baseline →')));
    };
    draw();

    // ---- what a record holds
    const ex = (k) => `${dec(k, e.vals[k])} ${M(k).unit}`;
    const anatomy = tbl(['Part of the record', 'What it is', `Example (week of ${fmtDate(e.start)} to ${fmtDate(e.end)})`], [
      ['Numbers', 'The window\'s value for each of 13 measures, plus the previous window\'s values', `resting heart rate ${ex('resting_heart_rate')}, previous week ${dec('resting_heart_rate', e.prev.resting_heart_rate)}`],
      ['Glucose detail', 'Average, estimated HbA1c, time in range, time above and below, variability, lowest, highest, completeness', `average ${dec('cgm_glucose_reading', g.mean)}, time in range ${n1(g.tir_pct, 1)}%, ${n1(g.n_readings, 0)} readings`],
      ['Her usual', 'Median, spread, flat band and number of days, from earlier days only', `resting heart rate usual ${dec('resting_heart_rate', e.prof.resting_heart_rate[1])} ± ${dec('resting_heart_rate', e.prof.resting_heart_rate[2])} from ${e.prof.resting_heart_rate[0]} days`],
      ['Directions', 'Each change against the previous window: flat, up or down, with a size', `heart rate ${tagOf('continuous_heart_rate').direction} (${tagOf('continuous_heart_rate').size}); sleep ${tagOf('sleep_duration').direction} (${tagOf('sleep_duration').size})`],
      ['Notable flag and reason', 'Which thresholds were crossed, decided by code', e.reason],
      ['Material changes', 'A typed list: missed doses, diary entries, statuses worse than usual, large changes, data gaps', `${e.material_kinds.missed_dose || 0} missed medicines, ${e.material_kinds.diary_event || 0} diary entries, ${e.material_kinds.status_worse_than_usual || 0} statuses worse than usual`],
      ['Data quality', 'Questionable readings removed and a reliable flag', `${e.removed} removed · reliable`],
      ['Moved together', 'The other measures that moved with glucose, only when glucose moved', 'listed only when glucose moved'],
      ['Gist (text)', 'A headline and a few sentences worded from the facts', e.headline]], true);

    return h('div', { class: 'stack' },
      card('What comes in', 'Only the store: no pairings, no alerts', inFlow),
      card('What happens inside', 'Nine steps, from rows to written windows. Hover a box for its definition.', stepGrid),
      card('Follow one real week through it', `The week of ${fmtDate(e.start)} to ${fmtDate(e.end, { year: true })}: click a step to see that step's actual numbers.`, h('div', { class: 'bs-stepper' }, tabs, panel)),
      SPECIFIC.baselineProduced(s),
      card('What each window holds', 'One record per window, 710 in all (352 days, 346 weeks, 12 months). It outputs numbers, directions, flags and a short text; it does not output relationships or causes, and it is not the PI memory.', anatomy));
  },
  baselineProduced: (s) => {
    const GIST = {
      code_line_early: { name: 'Too early', color: '#a9bdb7', def: 'Less than 14 days of history, or nothing earlier to compare with, so the code writes a short line from the top facts.' },
      code_line_quiet: { name: 'Quiet', color: 'var(--low)', def: 'Nothing material changed (no missed dose, no large move), so the code writes a plain "quiet" line.' },
      gist_ok: { name: 'Model gist', color: 'var(--primary)', def: 'Something material changed; the model worded the code-computed facts and passed every check on the first try.' },
      gist_retry_ok: { name: 'Model gist after a retry', color: 'var(--warn)', def: 'As above, but the first attempt failed a check and the retry passed.' },
    };
    const TIERS = [['day', 'Days', 'One calendar day, compared with her usual on earlier days.'], ['week', 'Weeks', 'A rolling 7 days (one for every day from the 7th), compared with the 7 days before.'],
      ['month', 'Months', 'A checkpoint every 30 days plus a final partial one, compared with the previous checkpoint.']];
    const n = (t, g) => s.counts[`${t} windows (${g})`] || 0;
    const key = h('div', { class: 'gist-key' }, Object.values(GIST).map((g) => h('div', { class: 'gist-def', style: `--c: ${g.color}` }, h('i', {}), h('div', {}, h('b', {}, g.name), h('span', {}, g.def)))));
    const charts = TIERS.map(([t, label, def]) => {
      const total = Object.keys(GIST).reduce((a, g) => a + n(t, g), 0);
      const el = h('div', { class: 'chart', style: { height: '230px' } });
      setTimeout(() => {
        const p = palette();
        mount(el, base({
          tooltip: { ...base().tooltip, trigger: 'item', formatter: (q) => `<b>${q.name}</b><br>${n1(q.value, 0)} ${label.toLowerCase()} · ${q.percent}%` },
          title: { text: n1(total, 0), subtext: label.toLowerCase(), left: 'center', top: '39%', textStyle: { color: p.ink, fontSize: 26, fontWeight: 700 }, subtextStyle: { color: p.muted, fontSize: 12 } },
          series: [{ type: 'pie', radius: ['56%', '82%'], center: ['50%', '50%'], padAngle: 2, itemStyle: { borderRadius: 7, borderColor: p.surface, borderWidth: 2 }, label: { show: false }, emphasis: { scale: true, scaleSize: 5 },
            data: Object.entries(GIST).filter(([g]) => n(t, g)).map(([g, d]) => ({ name: d.name, value: n(t, g), itemStyle: { color: cssVar(d.color.replace('var(', '').replace(')', '')) || d.color } })) }],
        }));
      }, 0);
      return h('div', { class: 'donut-col' }, h('h3', {}, label), h('div', { class: 'muted donut-def' }, def), el,
        h('div', { class: 'donut-list' }, Object.entries(GIST).map(([g, d]) => h('div', { class: n(t, g) ? '' : 'zero', style: `--c: ${d.color}` }, h('i', {}), h('span', {}, d.name), h('b', { class: 'num' }, n1(n(t, g), 0))))));
    });
    return card('The 710 windows, by length and by how their gist was produced', 'Colour = how the gist was produced. Every window gets a short gist; the code computes every number and the model only words them.',
      h('div', { class: 'stack' }, h('div', {}, h('h3', { style: { marginBottom: '8px' } }, 'How the gist was produced'), key), h('div', { class: 'grid g3' }, charts), h('a', { class: 'btn', href: '#/baselines' }, 'Browse the windows')));
  },
  state: (s) => {
    const c = s.counts, ticks = c['ticks (15 minutes)'], items = c.items, adv = c['items adverse'], fav = c['items favourable'], al = c.alerts;
    const node = (cls, n, label, cap, tip) => h('div', { class: `fnode ${cls}`, tabindex: 0 }, h('span', { class: 'fn-n num' }, n1(n, 0)), h('span', { class: 'fn-l' }, label), h('span', { class: 'fn-c' }, cap), h('div', { class: 'ftip' }, tip));
    const arrow = (text, cls = '') => h('div', { class: `farrow ${cls}` }, h('span', {}, text), h('i', {}));
    const pct = (a, b) => `${(100 * a / b).toFixed(1)}%`;
    const flow = h('div', { class: 'sflow' },
      h('div', { class: 'f-ticks' }, node('f-grey', ticks, 'ticks', 'every 15 minutes of the year', 'A tick is one look at her: every 15 minutes the engine takes the latest reading of each measure and compares it with her own usual from the Baseline Engine.')),
      h('div', { class: 'f-a1' }, arrow('stayed off her usual')),
      h('div', { class: 'f-items' }, node('f-warn', items, 'items', `${pct(items, ticks)} of ticks led to one`, 'An item is a measure that moved away from her usual and stayed there. It opens when that starts and closes when she is back to usual, or when the data goes stale.')),
      h('div', { class: 'f-a2 top' }, arrow('unwelcome direction')), h('div', { class: 'f-a2 bot' }, arrow('welcome direction', 'soft')),
      h('div', { class: 'f-adv' }, node('f-red', adv, 'adverse', 'moved the unwelcome way', 'Adverse: the measure moved in the direction that is unwelcome for it, for example heart rate above her usual or glucose high.')),
      h('div', { class: 'f-fav' }, node('f-green', fav, 'favourable', 'moved the welcome way', 'Favourable: the measure moved in the welcome direction, for example glucose lower than her usual. It is recorded, but only handed on if it is far from her usual or abnormal on that side.')),
      h('div', { class: 'f-a3 top' }, arrow('handed on')), h('div', { class: 'f-a3 bot' }, arrow('kept on record', 'soft')),
      h('div', { class: 'f-alert' }, node('f-red solid', al, 'alerts', 'escalated to the Rulebook', 'An alert (hand-off) is one item sent on to the Rulebook Lookup, which picks the factors worth checking for it. Every adverse item became an alert.')),
      h('div', { class: 'f-rec' }, node('f-green soft', items - al, 'recorded only', 'not escalated', 'Recorded only: the item stays in the State Engine log but nothing is sent on, because it moved the welcome way and was not far or abnormal.')));
    const measures = [...new Set(S.alerts.map((a) => a.measure))];
    const palettes = ['#7cc8bb', '#f0a3b2', '#b6acec', '#f2cf8a', '#9db9ee', '#8fd1a8', '#f2b78f', '#a9bdb7', '#d6a8d0'];
    const el = h('div', { class: 'chart', style: { height: '400px' } });
    const MN = ['January', 'February', 'March', 'April', 'May', 'June', 'July', 'August', 'September', 'October', 'November', 'December'];
    const months = S.pipeline.months, name = (m) => MN[+m.slice(5) - 1];
    const totals = months.map((mo) => S.alerts.filter((a) => a.month === mo).length);
    const years = [...new Set(months.map((m) => m.slice(0, 4)))];
    setTimeout(() => {
      const p = palette();
      const grad = (c) => c;
      const bands = years.map((y, i) => { const ms = months.filter((m) => m.startsWith(y)); return [{ xAxis: ms[0], name: y, itemStyle: { color: i % 2 ? 'rgba(120,140,135,.10)' : 'rgba(120,140,135,.03)' }, label: { show: true, position: 'insideTop', color: p.muted, fontSize: 13, fontWeight: 700, distance: 6 } }, { xAxis: ms[ms.length - 1] }]; });
      mount(el, base({
        legend: { top: 0, data: measures.map((m) => measureName(m)),
          tooltip: { show: true, backgroundColor: base().tooltip && base().tooltip.backgroundColor, formatter: (q) => {
            const m = measures.find((x) => measureName(x) === q.name); const per = months.map((mo) => [mo, S.alerts.filter((a) => a.month === mo && a.measure === m).length]).filter(([, n]) => n);
            const tot = per.reduce((a, [, n]) => a + n, 0);
            return `<b>${q.name}</b>: ${tot} alerts in total<br>` + per.map(([mo, n]) => `${name(mo).slice(0, 3)} ${mo.slice(2, 4)}: <b>${n}</b>`).join(' · '); } }, icon: 'roundRect', itemWidth: 12, itemHeight: 12, itemGap: 16, textStyle: { color: p.ink2 } }, grid: { left: 8, right: 14, top: 48, bottom: 8, containLabel: true },
        tooltip: { ...base().tooltip, trigger: 'axis', axisPointer: { type: 'shadow', shadowStyle: { color: 'rgba(120,140,135,.12)' } },
          formatter: (ps) => { const rows = ps.filter((q) => q.seriesType === 'bar' && q.value).sort((x, y) => y.value - x.value); const i = ps[0].dataIndex;
            return `<b>${name(months[i])} ${months[i].slice(0, 4)}</b> · ${totals[i]} alerts<br>` + rows.map((q) => `${q.marker} ${q.seriesName}: <b>${q.value}</b>`).join('<br>'); } },
        xAxis: { type: 'category', data: months, axisTick: { show: false }, axisLine: { lineStyle: { color: p.line } }, axisLabel: { color: p.ink2, fontSize: 12, margin: 12, formatter: (v) => name(v) } },
        yAxis: { ...valueAxis(), name: 'alerts', nameTextStyle: { color: p.muted, align: 'left' }, splitLine: { lineStyle: { color: p.line, type: [4, 6], opacity: 0.6 } } },
        series: [...measures.map((m, k) => ({ name: measureName(m), type: 'bar', stack: 'a', barWidth: '46%', itemStyle: { color: grad(palettes[k % palettes.length]), borderRadius: 4, borderColor: p.surface, borderWidth: 1.5 }, emphasis: { focus: 'series' },
          data: months.map((mo) => S.alerts.filter((a) => a.month === mo && a.measure === m).length || null),
          ...(k === 0 ? { markArea: { silent: true, data: bands } } : {}) })),
          { name: 'total', type: 'line', symbol: 'circle', symbolSize: 0, lineStyle: { opacity: 0 }, silent: true, tooltip: { show: false }, data: totals, z: 5, label: { show: true, position: 'top', color: p.ink, fontWeight: 700, fontSize: 13 }, legendHoverLink: false }],
      }));
    }, 0);
    return h('div', { class: 'stack' }, card('From every look at her to an alert', 'Hover a box for its definition', flow), card('Alerts by month and measure', 'Every alert handed on by the State Engine', el));
  },
  rulebook: (s) => {
    const c = s.counts, ok = c['packets ok'], def = c['packets deferred'], total = c.packets;
    const KINDS = [
      { name: 'Packet written', n: ok, color: '--ok', def: 'A rule matched the alert, so the packet holds an ordered checklist of the factors worth testing, with the window to look in for each.' },
      { name: 'Deferred', n: def, color: '--warn', def: 'The matching rule is not switched on yet, so the packet only lists every candidate as "not selected, rule deferred" and nothing is tested.' }];
    const el = h('div', { class: 'chart', style: { height: '230px' } });
    setTimeout(() => {
      const p = palette();
      mount(el, base({
        tooltip: { ...base().tooltip, trigger: 'item', formatter: (q) => `<b>${q.name}</b><br>${n1(q.value, 0)} packets · ${q.percent}%` },
        title: { text: n1(total, 0), subtext: 'packets', left: 'center', top: '39%', textStyle: { color: p.ink, fontSize: 28, fontWeight: 700 }, subtextStyle: { color: p.muted, fontSize: 12 } },
        series: [{ type: 'pie', radius: ['56%', '82%'], padAngle: 3, itemStyle: { borderRadius: 7, borderColor: p.surface, borderWidth: 2 }, label: { show: false }, emphasis: { scale: true, scaleSize: 5 },
          data: KINDS.map((k) => ({ name: k.name, value: k.n, itemStyle: { color: cssVar(k.color) } })) }],
      }));
    }, 0);
    const legend = h('div', { class: 'stack', style: { gap: '12px', justifyContent: 'center' } }, KINDS.map((k) => h('div', { class: 'gist-def', style: `--c: var(${k.color})` }, h('i', {}), h('div', {}, h('div', { class: 'row', style: { gap: '8px', alignItems: 'baseline' } }, h('b', {}, k.name), h('span', { class: 'num muted' }, `${n1(k.n, 0)} · ${(100 * k.n / total).toFixed(1)}%`)), h('div', { class: 'muted', style: { fontSize: '13px' } }, k.def)))));
    const MEAS = (r) => r.replace(/_(above|below).*$/, '');
    const rules = {}; S.alerts.forEach((a) => { const r = a.rule || 'none'; rules[r] = (rules[r] || 0) + 1; });
    const tint = ['#7cc8bb', '#f0a3b2', '#b6acec', '#f2cf8a', '#9db9ee', '#8fd1a8', '#f2b78f', '#a9bdb7', '#d6a8d0', '#c8d98a'];
    const order = [...new Set(Object.entries(rules).sort((x, y) => y[1] - x[1]).map(([r]) => MEAS(r)))];
    const max = Math.max(...Object.values(rules)), all = Object.values(rules).reduce((x, y) => x + y, 0);
    const tre = h('div', { class: 'rule-grid' }, Object.entries(rules).sort((x, y) => y[1] - x[1]).map(([r, n]) => {
      const m = MEAS(r), rest = r.slice(m.length + 1).replace(/_/g, ' ');
      return h('div', { class: 'rule-tile', style: `--c: ${tint[order.indexOf(m) % tint.length]}` },
        h('span', { class: 'rule-m' }, m.replace(/_/g, ' ')), h('span', { class: 'rule-r' }, rest),
        h('span', { class: 'rule-n num' }, n1(n, 0)), h('span', { class: 'rule-bar' }, h('i', { style: `width:${Math.max(4, 100 * n / max)}%` })), h('span', { class: 'rule-p' }, `${(100 * n / all).toFixed(1)}% of alerts`));
    }));
    return h('div', { class: 'stack' },
      card('How many alerts got a checklist', 'Every alert becomes a packet; colour shows whether the checklist could be written', h('div', { class: 'grid g2', style: { alignItems: 'center' } }, el, legend)),
      card('Which rule matched each alert', 'Each tile is a rule that decides which factors to look at; colour = the measure it is about', tre),
      rulebookExplorer(s));
  },
  evidence: (s) => {
    const c = s.counts, total = c['daily relationship records'];
    const LAB = [
      { k: 'supported', name: 'Supported', color: '--ok', def: 'Her own history backs it: the pattern is clear and larger than chance would give.' },
      { k: 'suggestive', name: 'Suggestive', color: '--warn', def: 'A weak or borderline pattern: worth noting, not strong enough to claim.' },
      { k: 'not_supported', name: 'Not supported', color: '--low', def: 'Enough history to test it, and the pattern does not show up in her data.' },
      { k: 'insufficient', name: 'Insufficient', color: '--muted', def: 'Not enough of her history yet (a test needs 60 usable days and 60 distinct dates), or the data is missing.' }];
    const n = (k) => c[`daily labels ${k}`] || 0;
    const el = h('div', { class: 'chart', style: { height: '260px' } });
    setTimeout(() => {
      const p = palette();
      mount(el, base({
        tooltip: { ...base().tooltip, trigger: 'item', formatter: (q) => `<b>${q.name}</b><br>${n1(q.value, 0)} daily records · ${q.percent}%` },
        title: { text: n1(total, 0), subtext: 'records', left: 'center', top: '40%', textStyle: { color: p.ink, fontSize: 22, fontWeight: 700 }, subtextStyle: { color: p.muted, fontSize: 12 } },
        series: [{ type: 'pie', radius: ['62%', '86%'], center: ['50%', '50%'], padAngle: 2, itemStyle: { borderRadius: 7, borderColor: p.surface, borderWidth: 2 }, label: { show: false }, emphasis: { scale: true, scaleSize: 5 },
          data: LAB.map((l) => ({ name: l.name, value: n(l.k), itemStyle: { color: cssVar(l.color) } })) }],
      }));
    }, 0);
    const legend = h('div', { class: 'stack', style: { gap: '10px', justifyContent: 'center' } }, LAB.map((l) => h('div', { class: 'gist-def', style: `--c: var(${l.color})` }, h('i', {}), h('div', {}, h('div', { class: 'row', style: { gap: '8px', alignItems: 'baseline' } }, h('b', {}, l.name), h('span', { class: 'num muted' }, `${n1(n(l.k), 0)} · ${(100 * n(l.k) / total).toFixed(1)}%`)), h('div', { class: 'muted', style: { fontSize: '13px' } }, l.def)))));

    const GROUP = { post_meal_peak: 'Glucose peak after a meal', non_meal_mean: 'Glucose between meals', day_min_glucose: 'Lowest glucose of the day', hr_day_mean: 'Heart rate over the day', hr_hour_mean: 'Heart rate within an hour', resting_hr_day: 'Resting heart rate',
      sleep_hours_night: 'Sleep length', fluid_intake_day: 'Fluid intake', missed_doses_day: 'Missed doses', systolic_reading: 'Blood pressure' };
    const rels = s.relationships, groups = {};
    rels.forEach((r) => { (groups[r.group] = groups[r.group] || []).push(r); });
    const strip = (days) => { const t = Object.values(days).reduce((a, b) => a + b, 0); return h('span', { class: 'rel-strip', title: LAB.map((l) => `${l.name}: ${days[l.k] || 0}`).join(' · ') }, LAB.map((l) => (days[l.k] ? h('i', { style: `width:${100 * days[l.k] / t}%; background: var(${l.color})` }) : null))); };
    const variantOf = (r) => { const m = r.outcome.match(/ after (\w+)$/); return m ? m[1] : null; };
    const gsorted = Object.entries(groups).sort((x, y) => y[1].length - x[1].length);
    const dayTxt = (r) => { const d = r.days, parts = []; if (d.supported) parts.push(`supported ${d.supported}`); if (d.suggestive) parts.push(`suggestive ${d.suggestive}`); if (d.not_supported) parts.push(`not supported ${d.not_supported}`); if (d.insufficient) parts.push(`insufficient ${d.insufficient}`); return parts.join(' · ') + ' days'; };
    const sizeOf = (list) => list.length;
    let curG = 0;
    const gList = h('div', { class: 'rb-list' }), gPanel = h('div', { class: 'rb-panel' });
    const drawG = () => {
      gList.replaceChildren(...gsorted.map(([g, list], i) => {
        const tested = list.filter((r) => (r.days.supported || 0) + (r.days.suggestive || 0) + (r.days.not_supported || 0) > 0).length, sup = list.filter((r) => r.latest === 'supported').length;
        return h('button', { type: 'button', class: `rb-rule ${i === curG ? 'on' : ''}`, onclick: () => { curG = i; drawG(); } }, h('b', {}, GROUP[g] || g.replace(/_/g, ' ')), h('span', { class: 'muted' }, `${sizeOf(list)} relationships · ${tested} tested · ${sup} supported now`));
      }));
      const [g, list] = gsorted[curG];
      const rows = {}; list.forEach((r) => { (rows[r.phrase] = rows[r.phrase] || []).push(r); });
      const outc = list[0].outcome.replace(/ after \w+$/, ' after a meal');
      gPanel.replaceChildren(
        h('div', { class: 'rb-head' }, h('h3', {}, GROUP[g] || g.replace(/_/g, ' '))),
        h('p', { class: 'rb-when' }, h('b', {}, 'Compared with: '), outc, `. ${list.length} relationship${list.length > 1 ? 's' : ''}; each row is a factor, and the bar shows how many days of the year it got each label.`),
        ...Object.entries(rows).map(([ph, vs]) => h('div', { class: 'rel-row2' }, h('div', { class: 'rel-ph' }, ph),
          h('div', { class: 'rel-vars2' }, [...vs].sort((x, y) => ['breakfast', 'lunch', 'dinner'].indexOf(variantOf(x)) - ['breakfast', 'lunch', 'dinner'].indexOf(variantOf(y))).map((r) => h('div', { class: 'rel-var2' },
            h('div', { class: 'rel-var2-top' }, variantOf(r) ? h('em', {}, variantOf(r)) : null, h('span', { class: 'muted' }, 'last day:'), labelChip(r.latest)), strip(r.days), h('div', { class: 'muted rel-days' }, dayTxt(r))))))));
    };
    drawG();
    // how to read a bar
    const mini = (parts) => h('span', { class: 'rel-strip rel-mini' }, parts.map(([k, w]) => h('i', { style: `width:${w}%; background: var(${LAB.find((l) => l.k === k).color})` })));
    const READ = [
      [[['supported', 100]], 'All green', 'Supported on almost every day of the year: the link showed up in her history and kept showing up.'],
      [[['supported', 70], ['suggestive', 6], ['insufficient', 24]], 'Mostly green with a grey end', 'Supported on most days. The grey is the days with too little history to test, mainly the first two months, because a relationship needs 60 days of data. This is the typical shape.'],
      [[['supported', 30], ['suggestive', 15], ['not_supported', 35], ['insufficient', 20]], 'A mix of green, amber and blue', 'Shows up on some days and not on others: not steady. Read it as weak, not as a pattern.'],
      [[['not_supported', 80], ['insufficient', 20]], 'Mostly blue', 'Tested on enough days, and the link did not show up in her data.'],
      [[['insufficient', 100]], 'All grey', 'Never testable in the year: too few days with the factor present, or not enough data to compare.']];
    const readBox = h('div', { class: 'rel-read' }, READ.map(([parts, title, text]) => h('div', { class: 'rel-read-item' }, mini(parts), h('div', {}, h('b', {}, title), h('div', { class: 'muted' }, text)))));
    const key = h('div', { class: 'row', style: { gap: '14px', flexWrap: 'wrap' } }, LAB.map((l) => h('span', { class: 'rel-key', style: `--c: var(${l.color})` }, h('i', {}), l.name)));
    const perAlert = h('div', { class: 'grid g2' },
      h('div', { class: 'big-note', style: '--c: var(--ep)' }, h('span', { class: 'bn-n num' }, n1(c['alert records'], 0)), h('b', {}, 'alert evidence records'),
        h('p', { class: 'muted' }, 'One for each alert. For every factor on that alert\'s Rulebook checklist it says whether her own history backs it (supported, suggestive, not supported, insufficient), with the numbers behind the label. These go on to the Findings Engine.')),
      h('div', { class: 'big-note', style: '--c: var(--warn)' }, h('span', { class: 'bn-n num' }, n1(c.completions, 0)), h('b', {}, 'completions'),
        h('p', { class: 'muted' }, 'Some checks cannot be finished at the moment of the alert, for example what happened in the hours after it. For these alerts the engine came back later and filled in that missing result; the original record is never changed.')));
    return h('div', { class: 'stack' },
      card('What the engine wrote for each alert', 'Separate from the daily refresh below', perAlert),
      card('The daily refresh: every relationship, every day', 'Using only her own history up to that day, so a label can change as more data arrives', h('div', { class: 'grid g2', style: { alignItems: 'center' } }, el, legend)),
      card(`The ${rels.length} relationships it tests`, 'A fixed list of candidate relationships, each tested every day on her own history. Pick a group to see them, and use the guide to read the bars.', h('div', { class: 'stack', style: { gap: '16px' } }, h('div', { class: 'ex-box' }, h('div', { class: 'ex-k' }, 'How to read a bar'), h('p', { class: 'muted', style: { margin: 0, fontSize: '12.5px' } }, 'A bar is the share of the year\'s days that got each label, always in this order: green, amber, blue, grey. It is not a timeline.'), key, readBox), h('div', { class: 'rb-wrap' }, gList, gPanel))));
  },
  findings: (s) => {
    const c = s.counts, cases = c.cases, vers = c.versions, desc = c['cases (descriptive mode)'], rel = c['cases (relationship mode)'];
    const kept = c['text: kept from an earlier prompt'], model = c['text: model text'], fb = c['text: fallback'], alerts = S.alerts.length;
    const node = (cls, n, label, cap, tip) => h('div', { class: `fnode ${cls}`, tabindex: 0 }, h('span', { class: 'fn-n num' }, n1(n, 0)), h('span', { class: 'fn-l' }, label), h('span', { class: 'fn-c' }, cap), h('div', { class: 'ftip' }, tip));
    const arrow = (text, cls = '') => h('div', { class: `farrow ${cls}` }, h('span', {}, text), h('i', {}));
    const at = (col, row, span, el) => { el.style.gridColumn = col; el.style.gridRow = span ? `${row} / span ${span}` : row; return el; };
    const wrap = (...kids) => h('div', { class: 'gflow' }, kids);
    const flowA = wrap(
      at(1, 1, 2, node('f-red', alerts, 'alerts', 'from the State Engine', 'An alert is one deviation (a measure off her usual, for example heart rate above it) handed on by the State Engine.')),
      at(2, 1, 2, arrow('grouped when close in time')),
      at(3, 1, 2, node('f-purple', cases, 'cases', `${(alerts / cases).toFixed(1)} alerts per case`, 'A case groups alerts that happened close together (each within 6 hours of the previous one, at most 36 hours in all), so one episode is written about once instead of alert by alert.')),
      at(4, 1, 0, arrow('no link found yet')), at(4, 2, 0, arrow('a link has support', 'soft')),
      at(5, 1, 0, node('f-blue', desc, 'descriptive mode', 'describes what happened', 'Descriptive: the text only describes what happened, for example "afternoon heart rate was far above her usual after a meal". No factor had enough support in her history to be named as a link. Counted by each case\'s last version.')),
      at(5, 2, 0, node('f-green', rel, 'relationship mode', 'may name a link', 'Relationship: at least one factor was supported by her own history, so the text may say it "may be linked to" what happened, never that it caused it. Counted by each case\'s last version.')));
    const flowB = wrap(
      at(1, 1, 3, node('f-purple solid', vers, 'versions', `${(vers / cases).toFixed(1)} per case`, 'A version is the case as written at one moment. Each time a new alert or a late result arrives, the case gets a new version with its own structured layer (decided by code) and text. Earlier versions are never changed.')),
      at(2, 1, 3, arrow('each version gets a text')),
      at(3, 1, 0, node('f-blue', kept, 'kept from an earlier prompt', `${(100 * kept / vers).toFixed(0)}% of versions`, 'The text was written under an earlier prompt, its facts did not change, and it still passes today\'s checks, so it was not rewritten.')),
      at(3, 2, 0, node('f-green', model, 'model text', `${(100 * model / vers).toFixed(0)}% of versions`, 'The model worded the code\'s structured layer and the text passed every check, on the first try or after one retry.')),
      at(3, 3, 0, node('f-warn', fb, 'code-line fallback', `${(100 * fb / vers).toFixed(1)}% of versions`, 'The model\'s text failed the checks twice, so the plain sentence built by code from the structured layer is used instead.')),
      at(4, 1, 3, h('div', { class: 'gnote' }, 'Every sentence is checked by code: no numbers, no causal words, nothing stronger than the evidence allows. The model only words what the code decided.')));
    const MN = ['January', 'February', 'March', 'April', 'May', 'June', 'July', 'August', 'September', 'October', 'November', 'December'];
    const months = S.pipeline.months, name = (m) => MN[+m.slice(5) - 1];
    const cs = months.map((m) => (S.casesByMonth.get(m) || []).length), vs = months.map((m) => (S.casesByMonth.get(m) || []).reduce((a, x) => a + x.versions, 0));
    const el = h('div', { class: 'chart', style: { height: '340px' } });
    setTimeout(() => {
      const p = palette();
      const bands = [...new Set(months.map((m) => m.slice(0, 4)))].map((y, i) => { const ms = months.filter((m) => m.startsWith(y)); return [{ xAxis: ms[0], name: y, itemStyle: { color: i % 2 ? 'rgba(120,140,135,.10)' : 'rgba(120,140,135,.03)' }, label: { show: true, position: 'insideTop', color: p.muted, fontSize: 13, fontWeight: 700, distance: 6 } }, { xAxis: ms[ms.length - 1] }]; });
      mount(el, base({
        grid: { left: 8, right: 14, top: 36, bottom: 8, containLabel: true },
        tooltip: { ...base().tooltip, trigger: 'axis', axisPointer: { type: 'shadow', shadowStyle: { color: 'rgba(120,140,135,.12)' } }, formatter: (ps) => { const i = ps[0].dataIndex; return `<b>${name(months[i])} ${months[i].slice(0, 4)}</b><br>${cs[i]} cases · ${vs[i]} versions`; } },
        xAxis: { type: 'category', data: months, axisTick: { show: false }, axisLine: { lineStyle: { color: p.line } }, axisLabel: { color: p.ink2, fontSize: 12, margin: 12, formatter: (v) => name(v) } },
        yAxis: { ...valueAxis(), splitLine: { lineStyle: { color: p.line, type: [4, 6], opacity: 0.6 } } },
        series: [{ name: 'Cases', type: 'bar', barWidth: '26%', barGap: '12%', itemStyle: { color: '#b6acec', borderRadius: [6, 6, 0, 0] }, data: cs, label: { show: true, position: 'top', color: p.ink2, fontSize: 11 }, markArea: { silent: true, data: bands } },
          { name: 'Versions', type: 'bar', barWidth: '26%', itemStyle: { color: '#7cc8bb', borderRadius: [6, 6, 0, 0] }, data: vs, label: { show: true, position: 'top', color: p.ink2, fontSize: 11 } }],
      }));
    }, 0);
    const def = (color, title, text) => h('div', { class: 'gist-def', style: `--c: ${color}` }, h('i', {}), h('div', {}, h('b', {}, title), h('div', { class: 'muted', style: { fontSize: '13px' } }, text)));
    return h('div', { class: 'stack' },
      card('From alerts to written context', 'Hover any box for its definition', h('div', { class: 'stack', style: { gap: '18px' } }, flowA, h('div', { class: 'gflow-sep' }, h('span', {}, 'Every case keeps growing: a new version each time something new arrives')), flowB)),
      card('Cases and versions by month', 'How many episodes there were each month, and how many times each was rewritten', h('div', { class: 'stack' },
        h('div', { class: 'grid g2' }, def('#b6acec', 'Case', 'One episode: alerts that happened close together (within 6 hours of each other, at most 36 hours in all), written about as a whole.'),
          def('#7cc8bb', 'Version', 'The case as written at one moment. A case gets a new version each time a new alert or a late result arrives, so a case has one or more versions.')), el)));
  },
  pi: () => {
    const fin = {};
    S.pi.memories.forEach((m) => { fin[m.status] = (fin[m.status] || 0) + 1; });
    const ST = [
      { k: 'supported', name: 'Supported', color: '--ok', def: 'Seen again and again over several weeks, and her own history keeps backing it.' },
      { k: 'candidate', name: 'Candidate', color: '--ep', def: 'Seen, but not repeated enough yet to rely on.' },
      { k: 'weakened', name: 'Weakened', color: '--warn', def: 'Was supported, but the latest weeks no longer back it.' },
      { k: 'retracted', name: 'Retracted', color: '--bad', def: 'Stopped holding up and was withdrawn.' }];
    const total = S.pi.memories.length;
    const don = h('div', { class: 'chart', style: { height: '240px' } });
    setTimeout(() => {
      const p = palette();
      mount(don, base({
        tooltip: { ...base().tooltip, trigger: 'item', formatter: (q) => `<b>${q.name}</b><br>${n1(q.value, 0)} notes · ${q.percent}%` },
        title: { text: n1(total, 0), subtext: 'long-term notes', left: 'center', top: '38%', textStyle: { color: p.ink, fontSize: 26, fontWeight: 700 }, subtextStyle: { color: p.muted, fontSize: 12 } },
        series: [{ type: 'pie', radius: ['62%', '86%'], center: ['50%', '50%'], padAngle: 3, itemStyle: { borderRadius: 7, borderColor: p.surface, borderWidth: 2 }, label: { show: false }, emphasis: { scale: true, scaleSize: 5 },
          data: ST.filter((x) => fin[x.k]).map((x) => ({ name: x.name, value: fin[x.k], itemStyle: { color: cssVar(x.color) } })) }],
      }));
    }, 0);
    const legend = h('div', { class: 'stack', style: { gap: '10px', justifyContent: 'center' } }, ST.map((x) => h('div', { class: fin[x.k] ? 'gist-def' : 'gist-def zero', style: `--c: var(${x.color})` }, h('i', {}), h('div', {}, h('div', { class: 'row', style: { gap: '8px', alignItems: 'baseline' } }, h('b', {}, x.name), h('span', { class: 'num muted' }, `${fin[x.k] || 0} of ${total}`)), h('div', { class: 'muted', style: { fontSize: '13px' } }, x.def)))));

    // weeks: Monday of an ISO week, label "6 Oct"
    const isoMon = (w) => { const [y, n] = w.split('-W').map(Number); const j4 = Date.UTC(y, 0, 4); const dow = (new Date(j4).getUTCDay() + 6) % 7; return j4 - dow * 864e5 + (n - 1) * 7 * 864e5; };
    const MS = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];
    const lab = (w) => { const d = new Date(isoMon(w)); return `${d.getUTCDate()} ${MS[d.getUTCMonth()]}`; };
    const weeks = S.pi.weeks, wl = weeks.map((w) => w.week);
    const el = h('div', { class: 'chart clickable', style: { height: '340px' } });
    setTimeout(() => {
      const p = palette();
      const years = [...new Set(weeks.map((w) => new Date(isoMon(w.week)).getUTCFullYear()))];
      const bands = years.map((y, i) => { const ws = weeks.filter((w) => new Date(isoMon(w.week)).getUTCFullYear() === y); return [{ xAxis: ws[0].week, name: String(y), itemStyle: { color: i % 2 ? 'rgba(120,140,135,.10)' : 'rgba(120,140,135,.03)' }, label: { show: true, position: 'insideTop', color: p.muted, fontSize: 13, fontWeight: 700, distance: 6 } }, { xAxis: ws[ws.length - 1].week }]; });
      const chart = mount(el, base({
        grid: { left: 8, right: 14, top: 36, bottom: 8, containLabel: true },
        tooltip: { ...base().tooltip, trigger: 'axis', axisPointer: { type: 'shadow', shadowStyle: { color: 'rgba(120,140,135,.14)' } },
          formatter: (ps) => { const w = weeks[ps[0].dataIndex]; return `<b>Week of ${lab(w.week)}</b> · ${w.week}<br>${w.entries} case${w.entries === 1 ? '' : 's'} received · ${w.written} note${w.written === 1 ? '' : 's'} written${w.changes.length ? `<br>${w.changes.length} status change${w.changes.length > 1 ? 's' : ''}` : ''}<br><span style="opacity:.7">Click to see them</span>`; } },
        xAxis: { type: 'category', data: wl, axisTick: { show: false }, axisLine: { lineStyle: { color: p.line } }, axisLabel: { color: p.ink2, fontSize: 11.5, margin: 10, interval: 3, formatter: (v) => lab(v) } },
        yAxis: { ...valueAxis(), minInterval: 1, splitLine: { lineStyle: { color: p.line, type: [4, 6], opacity: 0.6 } } },
        series: [{ type: 'bar', barWidth: '58%', data: weeks.map((w) => ({ value: w.entries, itemStyle: { color: w.changes.length ? '#f2cf8a' : '#b6acec', borderRadius: [5, 5, 0, 0] } })), emphasis: { itemStyle: { color: '#7cc8bb' } }, markArea: { silent: true, data: bands } }],
      }));
      chart.getZr().on('click', (e) => { const pt = [e.offsetX, e.offsetY]; if (!chart.containPixel('grid', pt)) return; const i = chart.convertFromPixel({ seriesIndex: 0 }, pt)[0]; if (wl[i]) location.hash = `#/pi/week/${wl[i]}`; });
      chart.getZr().on('mousemove', (e) => { el.style.cursor = chart.containPixel('grid', [e.offsetX, e.offsetY]) ? 'pointer' : 'default'; });
    }, 0);
    return h('div', { class: 'stack' },
      card('Where the long-term notes ended up', 'Each relationship PI kept a note for finishes the year in one of these states', h('div', { class: 'stack' }, h('div', { class: 'grid g2', style: { alignItems: 'center' } }, don, legend), h('a', { class: 'btn', href: '#/pi' }, 'Open the PI view'))),
      card('Cases PI received each week', 'Each bar is one calendar week: how many cases Findings wrote that week (the latest version of each). Amber bars are weeks in which a note changed status. Click a bar to open that week in the PI view and its cases.', el));
  },
};
