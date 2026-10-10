// The doctor's view. Inputs (data/nmg.json, built from CSV files only) -> fixed rules (rules.js) -> display. No model, no pipeline.
import { h, fmtDate, ms, num, ago, pv, spark, CHEV } from './ui.js';
import { evaluate, RULES, SENTENCE, goalOf, addMonths, daysBetween, iso } from './rules.js';
import { trendChart, palette } from './charts.js';

const data = await (await fetch('data/nmg.json')).json();
const R = evaluate(data);
const AS_OF = data.meta.as_of;
const SIGWORD = { green: 'Green', amber: 'Amber', red: 'Red', none: 'No band', notcomputed: 'Not computed' };
const DIRWORD = { up: ['▲', 'up'], down: ['▼', 'down'], steady: ['●', 'steady'] };
const KIND = { G: 'Guideline threshold', B: 'NMG Lite operational band (not a diagnostic criterion)', F: 'Formula', D: 'Definition or state', S: 'Suggestion (follow-up)' };
const open = new Set(), sel = {}, lanesOn = { meds: true, visits: true, dx: true, diary: false }, redraws = new Map(), charts = new Map();

// ---- small builders ------------------------------------------------------------------------------------------------------------------------------------------
const fv = (k, x) => { const v = data.vars[k]; const d = v ? v.dec : 1; return (x == null ? '—' : Number(x).toLocaleString('en-US', { minimumFractionDigits: d, maximumFractionDigits: d })); };
const sigPill = (s) => h('span', { class: `sig ${s}` }, h('i'), SIGWORD[s] || s);
const rid = (id) => { const r = RULES[id]; return h('span', { class: `rid ${r ? r[2] : ''}`, title: r ? `${id} · ${KIND[r[2]]}\n${r[3]}` : id }, id); };
const dirChip = (dir, change, dec = 1, unit = '') => {
  const ch = dir && dir.change != null ? dir.change : change;
  if (!dir || !dir.dir) return h('span', { class: 'muted' }, `change ${ch > 0 ? '+' : ''}${Number(ch).toFixed(dec)}${unit ? ' ' + unit : ''} (no tolerance defined)`);
  const [a, w] = DIRWORD[dir.dir];
  return h('span', { class: dir.dir === 'steady' ? 'dir-steady' : '' }, h('span', { class: 'arrow' }, a), w, ` (${ch > 0 ? '+' : ''}${Number(ch).toFixed(dec)}${unit ? ' ' + unit : ''})`);
};

function varTile(key, o = {}) {
  const v = data.vars[key]; if (!v) return null;
  const pts = data.series[key], L = v.latest, dec = v.dec;
  const g = o.goal ?? null;
  const main = o.main ?? L.v, mainTxt = o.mainTxt ?? Number(main).toLocaleString('en-US', { minimumFractionDigits: dec, maximumFractionDigits: dec });
  const t = h('div', { class: 'tile', 'data-key': key },
    h('div', { class: 'tk' }, h('span', {}, o.label ?? v.label), pv(L.b)),
    h('div', { class: 'tv num' }, mainTxt, ' ', h('small', {}, o.unit ?? v.unit)),
    h('div', { class: 'td' }, o.caption ?? `${fmtDate(L.d)} · ${ago(L.age)}`),
    spark(pts.length > 400 ? pts.slice(-180) : pts, { goal: g, dots: v.kind === 'lab' }));
  if (v.kind === 'lab') {
    if (v.baseline) t.append(h('div', { class: 'cmp', title: 'Her baseline = the median of the earlier values in the previous 24 months. Direction = latest minus baseline; "steady" when the change is within the tolerance (a display convention, not a signal).' }, 'Her baseline ', h('b', {}, fv(key, v.baseline.v)), ' · ', dirChip(v.direction, v.direction ? v.direction.change : 0, dec)));
    else t.append(h('div', { class: 'cmp muted' }, 'No baseline: fewer than 2 earlier values in 24 months'));
    if (v.since_dx) t.append(h('div', { class: 'cmp', title: `Against the value at the diagnosis visit, ${fmtDate(v.since_dx.d)}` }, 'Since diagnosis ', h('b', {}, fv(key, v.since_dx.v)), ' → ', v.since_dx.delta === 0 ? 'unchanged' : (v.since_dx.delta > 0 ? '▲ up ' : '▼ down ') + Math.abs(v.since_dx.delta).toFixed(dec), v.since_dx.b !== 'data' ? [' ', pv(v.since_dx.b)] : null));
  } else if (v.baseline) {
    t.append(h('div', { class: 'cmp', title: 'Last 28 days (median) against her baseline: the median of the 90 days that end 28 days before the latest date.' }, 'Last 28 days ', h('b', {}, fv(key, v.last28.median)), ' vs baseline ', h('b', {}, fv(key, v.baseline.v)), ' · ', dirChip(v.direction, v.direction ? v.direction.change : 0, dec)));
  }
  return t;
}
const factTile = (label, big, caption, extra = [], badge = null) => h('div', { class: 'tile' }, h('div', { class: 'tk' }, h('span', {}, label), pv(badge)), h('div', { class: 'tv num' }, ...[].concat(big)), caption ? h('div', { class: 'td' }, caption) : null, ...extra);

// ---- the domain tiles --------------------------------------------------------------------------------------------------------------------------------------
function tilesFor(id) {
  const c = data.cgm, bp = data.bp, dv = data.derived, S = data.standing;
  const a1c = data.vars.hba1c, gHb = goalOf(data, 'HbA1c'), gLdl = goalOf(data, 'LDL-C');
  if (id === 'anthropometry') return [varTile('bmi'), varTile('waist'), varTile('whr'), varTile('whtr'), varTile('weight', { goal: 68 })];
  if (id === 'glycemia') {
    const gap = data.gmi_gap.filter((x) => x.b === 'data').slice(-1)[0];
    return [
      varTile('hba1c', { goal: gHb ? gHb.value : null }), varTile('fpg'),
      factTile('Glucose monitoring (CGM), last 90 days', [num(c.w90.mean, 1), ' ', h('small', {}, 'mg/dL mean')], `GMI ${c.w90.gmi} · time in range 70 to 180 ${c.w90.tir}% · below 70 ${c.w90.below70}% · ${num(c.w90.n)} readings`, [
        h('div', { class: 'cmp' }, 'Whole year: mean ', h('b', {}, c.year.mean), ' · GMI ', h('b', {}, c.year.gmi), ' · time in range ', h('b', {}, c.year.tir + '%')),
        data.vars.cgm_mean?.baseline ? h('div', { class: 'cmp' }, 'Last 28 days ', h('b', {}, fv('cgm_mean', data.vars.cgm_mean.last28.median)), ' vs baseline ', h('b', {}, fv('cgm_mean', data.vars.cgm_mean.baseline.v)), ' · ', dirChip(null, data.vars.cgm_mean.direction.change, 1)) : null,
        gap ? h('div', { class: 'cmp', title: 'HbA1c minus the glucose-monitoring estimate (GMI) over the 90 days before the lab date.' }, 'Lab HbA1c ', h('b', {}, gap.hba1c), ' vs GMI ', h('b', {}, gap.gmi), ' · gap ', h('b', {}, (gap.gap > 0 ? '+' : '') + gap.gap)) : null]),
      factTile('2-hour glucose after meals', '', 'from CGM, not OGTT (G6)', ['breakfast', 'lunch', 'dinner'].filter((k) => c.post_meal_2h[k]).map((k) => h('div', { class: 'cmp' }, `${k[0].toUpperCase() + k.slice(1)} median `, h('b', {}, c.post_meal_2h[k].median), ` · 90th percentile ${c.post_meal_2h[k].p90} · ${c.post_meal_2h[k].n} meals`)).concat([h('div', { class: 'cmp muted' }, `Last dinner ${c.post_meal_2h.dinner.last.v} mg/dL`)])),
      varTile('fructosamine'),
    ];
  }
  if (id === 'bp') {
    const g = goalOf(data, 'Blood pressure'), cs = data.vars.bp_clinic_sys, cd = data.vars.bp_clinic_dia;
    return [
      factTile('Home reading, latest', [`${bp.last.sys}/${bp.last.dia}`, ' ', h('small', {}, 'mmHg')], `${fmtDate(bp.last.d)} · ${ago(daysBetween(bp.last.d, AS_OF))}`, [spark(data.series.bp_sys.slice(-90), { goal: g ? g.value : null, dots: false }), h('div', { class: 'cmp' }, 'Median of the year ', h('b', {}, `${bp.median[0]}/${bp.median[1]}`), ` · range ${bp.range_sys[0]}–${bp.range_sys[1]} / ${bp.range_dia[0]}–${bp.range_dia[1]}`)]),
      factTile('Home mean, last 28 days', [`${bp.mean_last28[0]}/${bp.mean_last28[1]}`, ' ', h('small', {}, 'mmHg')], `${bp.n_last28} readings`, [data.vars.bp_sys?.direction ? h('div', { class: 'cmp', title: 'Last 28 days (median) against the median of the 90 days that end 28 days before the latest date.' }, 'Systolic vs her baseline ', h('b', {}, fv('bp_sys', data.vars.bp_sys.baseline.v)), ' · ', dirChip(data.vars.bp_sys.direction, data.vars.bp_sys.direction.change, 1)) : null, h('div', { class: 'cmp muted' }, `${bp.share_130_80}% of home readings at or above 130 or 80 · ${bp.share_140_90}% at or above 140 or 90 (descriptive shares, not signals)`)]),
      varTile('bp_clinic_sys', { label: 'Clinic reading, latest', mainTxt: `${cs.latest.v}/${cd.latest.v}`, unit: 'mmHg' }),
      factTile('Goal and treatment', g ? [`under ${g.value}/${g.value2}`, ' ', h('small', {}, 'mmHg')] : 'no goal', g ? 'set by the clinic' : '', [h('div', { class: 'cmp' }, 'Amlodipine 5 mg daily since ', h('b', {}, fmtDate(S.meds.find((m) => /amlodipine/i.test(m.name)).start)), ' · hypertension diagnosed ', fmtDate(S.conds.find((x) => /hypertension/i.test(x.name)).date)), h('div', { class: 'cmp muted' }, R.domains[2].aboveGoalLatest ? 'The latest home and clinic readings are above the goal (a description, not a signal).' : 'The latest readings are within the goal.')], g ? g.b : null),
    ];
  }
  if (id === 'lipids') {
    const rx = R.domains.find((d) => d.id === 'lipids').treatment;
    return [varTile('ldl', { goal: gLdl ? gLdl.value : null }), varTile('tg', { goal: 150 }), varTile('hdl', { goal: 50 }), varTile('tg_hdl', { goal: 2 }), varTile('nonhdl'), varTile('tc'), varTile('apob'),
      factTile('Lp(a)', [num(data.vars.lpa.latest.v), ' ', h('small', {}, 'nmol/L')], `${fmtDate(data.vars.lpa.latest.d)} · measured once in adulthood (L5)`, [h('div', { class: 'cmp muted' }, 'Risk-enhancing at 125 nmol/L or more; not serially monitored.')], data.vars.lpa.latest.b),
      factTile('Lipid-lowering treatment', rx.replace('No lipid-lowering therapy', 'None'), gLdl ? `LDL-C goal under ${gLdl.value} mg/dL ` : '', [])];
  }
  if (id === 'kidney') return [varTile('egfr'), varTile('creat'), varTile('uacr')];
  if (id === 'liver') {
    const us = S.imaging.find((i) => /ultrasound/i.test(i.modality)), m = S.conds.find((x) => /MASLD/i.test(x.name));
    return [varTile('alt'), varTile('ast'), varTile('ggt'), varTile('hsi'), factTile('Liver imaging', us ? 'Grade 1 steatosis' : 'none', us ? `Abdominal ultrasound ${fmtDate(us.d)}` : '', us ? [h('div', { class: 'cmp' }, us.impression)] : [], us ? us.b : null),
      factTile('MASLD', m ? 'Documented' : 'Not documented', m ? `since ${fmtDate(m.date)} · steatosis on imaging plus a cardiometabolic risk factor` : '', [h('div', { class: 'cmp muted' }, 'Abnormal ALT or AST alone does not establish MASLD.')], m ? m.b : null)];
  }
  if (id === 'activity') {
    const ip = data.ipaq[data.ipaq.length - 1];
    return [
      factTile('IPAQ-Short, latest', [ip.category.toUpperCase(), ' ', h('small', {}, `${num(ip.met)} MET-min/week`)], `${fmtDate(ip.d)} · official category`, [h('div', { class: 'cmp' }, data.ipaq.map((x) => `${fmtDate(x.d, false)}: ${x.category}`).join(' · ')), spark(data.series.ipaq, { goal: 600 })], ip.b),
      factTile('Daily steps (wearable)', [num(dv.steps.median), ' ', h('small', {}, 'median')], `year median · last 30 days mean ${num(dv.steps.last30_mean)}`, [spark(data.series.steps.slice(-180), { dots: false }), h('div', { class: 'cmp' }, `${dv.steps.share_lt_4000}% of days under 4,000 steps · ${dv.steps.share_ge_7000}% at or above 7,000`), data.vars.steps.baseline ? h('div', { class: 'cmp' }, 'Last 28 days ', h('b', {}, fv('steps', data.vars.steps.last28.median)), ' vs baseline ', h('b', {}, fv('steps', data.vars.steps.baseline.v)), ' · ', dirChip(data.vars.steps.direction, data.vars.steps.direction.change, 0)) : null]),
      factTile('Sedentary time', [(dv.sedentary.median / 60).toFixed(1), ' ', h('small', {}, 'h a day, median')], `last 30 days median ${(dv.sedentary.last30_median / 60).toFixed(1)} h`, [spark(data.series.sedentary.slice(-180), { dots: false }), data.vars.sedentary.baseline ? h('div', { class: 'cmp' }, 'Last 28 days ', h('b', {}, fv('sedentary', data.vars.sedentary.last28.median)), ' vs baseline ', h('b', {}, fv('sedentary', data.vars.sedentary.baseline.v)), ' · ', dirChip(data.vars.sedentary.direction, data.vars.sedentary.direction.change, 0, 'min')) : null]),
    ];
  }
  // lifestyle
  const L = R.domains.find((d) => d.id === 'lifestyle'), sl = dv.sleep, fam = S.fam, occ = S.life.find((x) => x.domain === 'Occupation'), hh = S.life.find((x) => x.domain === 'Household'), tob = S.life.find((x) => x.domain === 'Tobacco'), alc = S.life.find((x) => x.domain === 'Alcohol'), caf = S.life.find((x) => x.domain === 'Caffeine'), diet = S.life.find((x) => x.domain === 'Diet pattern');
  return [
    factTile('Sleep, 7-night average', [sl.last7.toFixed(2), ' ', h('small', {}, 'h')], `source: ${sl.source}`, [spark(data.series.sleep.slice(-90), { goal: 7, dots: false }), h('div', { class: 'cmp' }, `Last night ${sl.last_night} h · last 30 nights ${sl.last30} h · year median ${sl.median_year} h`), h('div', { class: 'cmp muted' }, `${sl.share_under_7}% of ${sl.nights} nights under 7 h`), data.vars.sleep.baseline ? h('div', { class: 'cmp' }, 'Last 28 days ', h('b', {}, fv('sleep', data.vars.sleep.last28.median)), ' vs baseline ', h('b', {}, fv('sleep', data.vars.sleep.baseline.v)), ' · ', dirChip(data.vars.sleep.direction, data.vars.sleep.direction.change, 2)) : null]),
    factTile('Modifiers recorded', [String(L.modifiers.length)], 'counted for rule M2; only recorded ones', L.modifiers.map((m) => h('div', { class: 'cmp', title: m.detail }, h('b', {}, m.name), ' ', pv(m.b)))),
    factTile('Tobacco, alcohol, caffeine', tob ? tob.value : 'not recorded', '', [alc ? h('div', { class: 'cmp' }, 'Alcohol: ', alc.value, ` (${dv.alcohol_dates.length} diary entries in the data year)`) : null, caf ? h('div', { class: 'cmp' }, 'Caffeine: ', caf.value) : null], tob ? tob.b : null),
    factTile('Family history', 'First degree', '', fam.filter((f) => f.premature !== 'not documented').map((f) => h('div', { class: 'cmp' }, h('b', {}, f.relative), ': ', f.condition, f.onset ? `, age ${f.onset}` : '', f.premature && !/not applicable/i.test(f.premature) ? ` (premature: ${f.premature.split(' (')[0]})` : '', ' ', pv(f.b))).concat([h('div', { class: 'cmp muted' }, 'PCOS, gestational diabetes and inherited conditions: not documented.')])),
    factTile('Occupation and diet', occ ? occ.value.split(',')[0] : '', occ ? occ.detail : '', [diet ? h('div', { class: 'cmp' }, h('b', {}, 'Diet: '), diet.value, ' · ', diet.detail) : null, hh ? h('div', { class: 'cmp muted' }, hh.value, '. ', hh.detail) : null], occ ? occ.b : null),
    factTile('PCOS and gestational history', 'None documented', 'the persona is silent; this is not a clinical finding', [h('div', { class: 'cmp muted' }, 'X4: PCOS needs at least two of hyperandrogenism, ovulatory dysfunction and polycystic ovarian morphology after excluding other causes.')], 'best_guess'),
  ];
}

// ---- charts: which series, which reference lines ------------------------------------------------------------------------------------------------------
const TABS = {
  anthropometry: [['bmi', 'BMI'], ['waist', 'Waist'], ['whr', 'WHR'], ['whtr', 'WHtR'], ['weight', 'Weight']],
  glycemia: [['hba1c', 'HbA1c'], ['fpg', 'Fasting glucose'], ['cgm_mean', 'CGM daily mean'], ['fructosamine', 'Fructosamine'], ['homa', 'HOMA1-IR']],
  bp: [['bp', 'Home and clinic']],
  lipids: [['ldl', 'LDL-C'], ['tg', 'Triglycerides'], ['hdl', 'HDL-C'], ['tg_hdl', 'TG/HDL-C'], ['nonhdl', 'Non-HDL-C'], ['tc', 'Total cholesterol'], ['apob', 'ApoB']],
  kidney: [['egfr', 'eGFR'], ['uacr', 'UACR'], ['creat', 'Creatinine']],
  liver: [['liver', 'ALT · AST · GGT'], ['hsi', 'Steatosis index']],
  activity: [['ipaq', 'IPAQ'], ['steps', 'Daily steps'], ['sedentary', 'Sedentary time']],
  lifestyle: [['sleep', 'Sleep']],
};
const EVKEY = { bp: 'bp_clinic_sys', liver: 'alt' };

function refsFor(key) {
  const sex = R.sex, gHb = goalOf(data, 'HbA1c'), gLdl = goalOf(data, 'LDL-C'), gBp = goalOf(data, 'Blood pressure');
  const goal = (y, t) => ({ y, label: `${t}`, tone: 'goal' });
  const m = {
    bmi: [{ y: 23, label: 'A2: 23' }, { y: 25, label: 'A3: 25' }], waist: [{ y: sex === 'male' ? 90 : 80, label: `A3: ${sex === 'male' ? 90 : 80} cm` }], whr: [{ y: sex === 'male' ? 0.9 : 0.8, label: `A2: ${sex === 'male' ? 0.9 : 0.8}` }],
    whtr: [{ y: 0.5, label: 'A2: 0.50' }, { y: 0.55, label: 'A3: 0.55' }], weight: [goal(68, 'goal 68 kg')],
    hba1c: [{ y: 5.7, label: 'G2: 5.7' }, { y: 6.5, label: 'G4: 6.5' }].concat(gHb ? [goal(gHb.value, `goal ${gHb.value.toFixed(1)}`)] : []), fpg: [{ y: 100, label: 'G2: 100' }, { y: 126, label: 'G4: 126' }],
    fructosamine: [{ y: 200, label: 'X2: 200 (Mayo)' }, { y: 285, label: 'X2: 285 (Mayo)' }], cgm_mean: [{ y: 70, label: '70' }, { y: 180, label: '180' }],
    bp: gBp ? [goal(gBp.value, `goal ${gBp.value}`), goal(gBp.value2, `goal ${gBp.value2}`)] : [],
    ldl: (gLdl ? [goal(gLdl.value, `goal ${gLdl.value}`)] : []).concat([{ y: 130, label: 'ICMR high: 130' }]), tg: [{ y: 150, label: 'L2: 150' }], hdl: [{ y: sex === 'male' ? 40 : 50, label: `L2 low: ${sex === 'male' ? 40 : 50}` }],
    tg_hdl: [{ y: 2, label: 'L2: 2.0' }, { y: 3, label: 'L3: 3.0' }], lpa: [{ y: 125, label: 'L5: 125' }], egfr: [{ y: 90, label: 'K1: 90' }, { y: 60, label: 'K3: 60' }], uacr: [{ y: 30, label: 'K2: 30' }, { y: 300, label: 'K3: 300' }],
    ipaq: [{ y: 600, label: '600 MET-min' }], sleep: [{ y: 7, label: 'M1/M2: 7 h' }],
  };
  return m[key] || [];
}
// shaded zones for the full trend, straight from the rules: signal, from, to (null = open end). Only where the document defines a band.
function zonesFor(key) {
  const f = R.sex !== 'male', gLdl = goalOf(data, 'LDL-C'), z = (signal, from, to) => ({ signal, from, to });
  const m = {
    bmi: [z('green', null, 23), z('amber', 23, 25), z('red', 25, null)], waist: [z('red', f ? 80 : 90, null)], whr: [z('green', null, f ? 0.8 : 0.9), z('amber', f ? 0.8 : 0.9, null)],
    whtr: [z('green', null, 0.5), z('amber', 0.5, 0.55), z('red', 0.55, null)], hba1c: [z('green', null, 5.7), z('amber', 5.7, 6.5), z('red', 6.5, null)], fpg: [z('green', null, 100), z('amber', 100, 126), z('red', 126, null)],
    tg: [z('green', null, 150), z('amber', 150, null)], hdl: [z('amber', null, f ? 50 : 40), z('green', f ? 50 : 40, null)], tg_hdl: [z('green', null, 2), z('amber', 2, 3), z('red', 3, null)],
    ldl: gLdl ? [z('green', null, gLdl.value), z('amber', gLdl.value, null)] : [], egfr: [z('red', null, 60), z('green', 90, null)], uacr: [z('green', null, 30), z('amber', 30, 300), z('red', 300, null)],
    sleep: [z('amber', null, 7), z('green', 7, null)], ipaq: [z('amber', null, 600), z('green', 600, null)],
  };
  return m[key] || [];
}
const RANGE = (k) => (data.vars[k] && data.vars[k].kind === 'daily');

function specFor(tab) {
  const P = palette(), lastD = (k) => data.vars[k].latest.d;
  const spec = { key: tab, refs: refsFor(tab), dec: 1, unit: '', lines: [], extra: [], windows: [], dx: ms(data.meta.dx_date), xmin: ms('2021-09-20'), xmax: ms(AS_OF) + 24 * 864e5 };
  const mk = (k, name, color, kind) => ({ key: k, name: name || data.vars[k].label, color, kind: kind || data.vars[k].kind, pts: data.series[k] });
  if (tab === 'bp') {
    Object.assign(spec, { unit: 'mmHg', dec: 0, title: 'Home and clinic blood pressure' });
    spec.lines = [mk('bp_sys', 'Home systolic (daily mean)', P.primaryInk, 'daily'), mk('bp_dia', 'Home diastolic (daily mean)', P.ep, 'daily'), mk('bp_clinic_sys', 'Clinic systolic', P.ink, 'lab'), mk('bp_clinic_dia', 'Clinic diastolic', P.muted, 'lab')];
    return spec;
  }
  if (tab === 'liver') { Object.assign(spec, { unit: 'U/L', dec: 0, title: 'ALT, AST and GGT' }); spec.lines = [mk('alt', 'ALT', P.primaryInk, 'lab'), mk('ast', 'AST', P.ep, 'lab'), mk('ggt', 'GGT', P.warn, 'lab')]; return spec; }
  const v = data.vars[tab];
  Object.assign(spec, { unit: v.unit, dec: v.dec, title: v.label });
  spec.lines = [mk(tab, v.label, P.primaryInk)];
  if (v.kind === 'daily') {
    const end = ms(lastD(tab)), d0 = ms(data.series[tab][0][0]);
    spec.xmin = d0 - 3 * 864e5; spec.xmax = end + 2 * 864e5; spec.dx = null;
    if (v.baseline) { spec.windows.push({ from: end - 117 * 864e5, to: end - 28 * 864e5, label: 'baseline (90 days)', color: 'rgba(120,140,135,.14)' }, { from: end - 27 * 864e5, to: end, label: '', color: 'rgba(107,184,171,.2)' }); spec.baseline = { from: end - 117 * 864e5, to: end - 28 * 864e5, value: v.baseline.v }; }
    if (tab === 'cgm_mean') spec.band = { lo: 70, hi: 180, label: 'time-in-range band 70 to 180' };
  } else {
    if (v.baseline) { const from = ms(addMonths(lastD(tab), -24)), to = ms(lastD(tab)); spec.windows.push({ from, to, label: 'baseline window (previous 24 months)', color: 'rgba(120,140,135,.13)' }); spec.baseline = { from, to, value: v.baseline.v }; }
  }
  if (tab === 'hba1c') {
    spec.extra = [{ name: 'Estimated HbA1c from CGM (GMI, 90 days before)', color: P.ep, dashed: true, note: 'GMI = 3.31 + 0.02392 × mean glucose over the 90 days before the lab date', pts: data.gmi_gap.map((x) => [x.d, x.gmi, x.b === 'data' ? 'data' : x.b]) }];
  }
  if (tab === 'homa') spec.refs = [];
  spec.zones = zonesFor(tab);
  return spec;
}

function lanesData() {
  const meds = data.standing.meds.filter((m) => m.start).map((m) => ({ label: `${m.name} ${m.dose}`.trim(), start: m.start, end: m.end, status: m.status, b: m.b }));
  return { meds: lanesOn.meds ? meds : [], visits: lanesOn.visits, dx: lanesOn.dx, diary: lanesOn.diary };
}

// ---- the pages -------------------------------------------------------------------------------------------------------------------------------------------------
// Overview (patient + one card per domain) -> a domain page (Values | Trend | Rules | Events | All values, one at a time) -> Suggested review, Notices, All rules.
const EMBED = new URLSearchParams(location.search).get('embed') === '1';
const DOMTABS = [['values', 'Values now'], ['trend', 'Trend'], ['rules', 'Rules'], ['events', 'Events'], ['all', 'All values']];
const labVar = (dom, k) => (k === 'bp' ? 'bp_clinic_sys' : k === 'liver' ? 'alt' : k);

function trendPanel(dom) {
  const tabs = TABS[dom.id];
  if (!tabs.some(([k]) => k === sel[dom.id])) sel[dom.id] = tabs[0][0];
  const chartEl = h('div', { class: 'chartbox' }), legend = h('div', { class: 'legend' }), tabsEl = h('div', { class: 'vtabs' });
  const lanesEl = h('div', { class: 'lanes' }, [['meds', 'Medicines'], ['visits', 'Clinic visits'], ['dx', 'Diagnoses and imaging'], ['diary', 'Diary: symptoms and care']].map(([k, t]) => h('label', {}, h('input', { type: 'checkbox', checked: lanesOn[k] ? true : null, onchange: (e) => { lanesOn[k] = e.target.checked; draw(); } }), t)));
  const draw = () => {
    tabsEl.replaceChildren(...(tabs.length > 1 ? tabs.map(([k, t]) => h('button', { type: 'button', class: `vt ${sel[dom.id] === k ? 'on' : ''}`, onclick: () => { sel[dom.id] = k; draw(); } }, t)) : []));
    const k = sel[dom.id];
    if (charts.get(dom.id)) { charts.get(dom.id).dispose(); charts.delete(dom.id); }
    const spec = specFor(k);
    chartEl.style.height = (lanesOn.meds ? 470 : 420) + 'px';
    charts.set(dom.id, trendChart(chartEl, spec, lanesData(), data.events));
    legend.replaceChildren(...[
      h('span', {}, h('i', {}), 'value (solid line)'), h('span', {}, h('i', { class: 'dot fill' }), 'recorded value'),
      h('span', {}, h('i', { class: 'band' }), 'baseline window and last 28 days'), h('span', {}, h('i', { class: 'dash' }), 'reference line with its rule ID'),
      spec.zones && spec.zones.length ? h('span', {}, h('i', { class: 'zone' }), 'shaded zones: green, amber, red as the rules define them (a zone is not a diagnosis)') : null,
      spec.offscale && spec.offscale.length ? h('span', {}, 'Off the chart: ', spec.offscale.map((r) => [rid(r.label.split(':')[0]), ` ${r.label.split(': ')[1] || r.label} `])) : null,
      spec.extra && spec.extra.length ? h('span', {}, h('i', { class: 'dot' }), 'estimated HbA1c from CGM (GMI)') : null, h('span', { class: 'muted' }, 'Hold Shift and scroll to zoom; drag to move.')].filter(Boolean));
  };
  redraws.set(dom.id, draw);
  requestAnimationFrame(draw);
  return h('div', { class: 'panel' }, tabsEl, lanesEl, chartEl, legend);
}

function rulesPanel(dom) {
  const order = { red: 0, amber: 1, green: 2 };
  const rows = [...dom.trace].sort((a, b) => (b.met - a.met) || (order[a.signal] - order[b.signal]));
  return h('div', { class: 'panel narrow' },
    rows.length ? h('table', { class: 'trace' }, h('tbody', {}, rows.map((t) => h('tr', { class: t.met ? 'met' : 'no', style: `--accent: var(--sg-${t.signal === 'none' ? 'none' : t.signal})` }, h('td', { class: 'mk' }, t.met ? '✓' : '–'), h('td', {}, rid(t.rule)), h('td', {}, h('span', { class: `dot ${t.signal}` }), t.label, h('div', { class: 'val muted' }, t.value))))))
      : h('p', { style: { margin: 0 } }, rid(dom.rules[0]), ' ', RULES[dom.rules[0]][3]),
    h('p', { class: 'muted', style: { fontSize: '11.5px' } }, 'A guideline threshold (G) comes from a cited guideline. An NMG Lite band (B) is an operational attention band, not a diagnostic criterion.'),
    dom.notes.length ? h('div', {}, h('div', { class: 'sh' }, 'Notes'), h('ul', { class: 'notes' }, dom.notes.map((n) => h('li', {}, n)))) : null);
}

function eventsPanel(dom) {
  const tabs = TABS[dom.id];
  const list = [...new Set(tabs.map(([k]) => labVar(dom, k)))].filter((k) => data.vars[k] && data.vars[k].events);
  const cur = labVar(dom, sel[dom.id]);
  const box = h('div', {});
  const draw = (k) => {
    const v = data.vars[k];
    box.replaceChildren(h('div', { class: 'sh' }, v.kind === 'lab' ? `Events around the last change of ${v.label} (${v.prev ? fmtDate(v.prev.d) : 'start'} to ${fmtDate(v.latest.d)})` : `Events in the last 28 days of ${v.label}`),
      v.events.length ? h('div', { class: 'events' }, [...v.events].reverse().map((e) => h('div', { class: 'ev' }, h('span', { class: 'd' }, fmtDate(e.d)), h('span', {}, h('span', { class: 'k' }, e.kind.replace('_', ' ')), e.text, ' ', pv(e.b))))) : h('div', { class: 'muted', style: { fontSize: '12.5px' } }, 'No medicine change, visit, imaging, diagnosis or diary event in this period.'),
      h('div', { class: 'muted', style: { fontSize: '11.5px', marginTop: '4px' } }, 'Shown as markers around the change, never as causes.'));
  };
  const pick = h('div', { class: 'vtabs' });
  const render = (k) => { pick.replaceChildren(...(list.length > 1 ? list.map((x) => h('button', { type: 'button', class: `vt ${x === k ? 'on' : ''}`, onclick: () => render(x) }, data.vars[x].label)) : [])); draw(k); };
  render(list.includes(cur) ? cur : list[0]);
  return h('div', { class: 'panel narrow' }, pick, box);
}

function allValuesPanel(dom) {
  const list = [...new Set(TABS[dom.id].map(([k]) => labVar(dom, k)))].filter((k) => data.vars[k] && data.vars[k].kind === 'lab');
  if (!list.length) return h('div', { class: 'panel muted' }, 'This domain has daily or wearable series only; open the Trend tab to see them.');
  const box = h('div', {}), pick = h('div', { class: 'vtabs' });
  const render = (k) => {
    const v = data.vars[k], pts = data.series[k];
    pick.replaceChildren(...(list.length > 1 ? list.map((x) => h('button', { type: 'button', class: `vt ${x === k ? 'on' : ''}`, onclick: () => render(x) }, data.vars[x].label)) : []));
    box.replaceChildren(h('div', { class: 'valbox open' }, h('table', { class: 'tbl' }, h('thead', {}, h('tr', {}, h('th', {}, 'Date'), h('th', { class: 'r' }, `${v.label} (${v.unit})`), h('th', {}, 'Source'))), h('tbody', {}, [...pts].reverse().map((p) => h('tr', {}, h('td', {}, fmtDate(p[0])), h('td', { class: 'r num' }, Number(p[1]).toFixed(v.dec)), h('td', {}, pv(p[2]) || h('span', { class: 'muted' }, 'data file'))))))));
  };
  render(list.includes(labVar(dom, sel[dom.id])) ? labVar(dom, sel[dom.id]) : list[0]);
  return h('div', { class: 'panel narrow' }, pick, box);
}

// ---- header and route -----------------------------------------------------------------------------------------------------------------------------------
const NAVL = [['', 'Overview'], ['review', 'Suggested review'], ['notices', 'Read with the values'], ['graphs', 'All graphs']];
function topbar(route) {
  const t = document.documentElement.dataset.theme;
  return h('header', { class: 'topbar' }, EMBED ? null : h('div', { class: 'brand' }, h('span', { class: 'brand-mark', html: '<svg viewBox="0 0 24 24"><path d="M3 13h4l2.5-6 4 12 2.5-6h5"/></svg>' }), "Doctor's view"),
    h('nav', { class: 'tnav' }, NAVL.map(([k, t2]) => h('a', { href: `#/${k}`, class: (route.page === k || (k === '' && route.page === 'd')) ? 'on' : '' }, t2))),
    h('span', { class: 'top-sp' }), route.page === '' ? null : h('span', { class: 'chip primary' }, `${data.meta.patient} · ${data.standing.age.age_years} · ${data.standing.sex.sex}`), h('span', { class: 'chip' }, `As of ${fmtDate(AS_OF)}`), h('span', { class: 'chip ep' }, 'synthetic'),
    EMBED ? null : h('button', { class: 'btn', type: 'button', onclick: () => window.print() }, 'Print'),
    EMBED ? null : h('button', { class: 'btn', type: 'button', title: 'Light or dark theme', onclick: () => { const n = document.documentElement.dataset.theme === 'dark' ? 'light' : 'dark'; document.documentElement.dataset.theme = n; try { localStorage.setItem('theme', n); } catch (e) { /* ignore */ } go(); } }, t === 'dark' ? 'Light' : 'Dark'));
}

// the fixed sentence is on every page; the provenance notes sit behind "About this view"
function sentence() {
  return h('section', { class: 'stmtbar' }, h('div', { class: 'stmt' }, SENTENCE),
    h('details', { class: 'about' }, h('summary', {}, 'About this view'),
      h('div', { class: 'small' }, 'Direction words (up, down, steady), her baseline and "since diagnosis" are display conventions with invented tolerances, not signals and not diagnoses.'),
      h('div', { class: 'sigkey' }, [['green', 'Green', 'lower concern'], ['amber', 'Amber', 'increased attention'], ['red', 'Red', 'high attention'], ['none', 'No band', 'the document gives no band, or data is missing: values and trend only']].map(([c, t, d]) => h('div', {}, sigPill(c), h('span', {}, h('b', {}, t), ' ', d)))),
      h('div', { class: 'small' }, 'Signals are per domain and never combined into one colour. Hover a rule ID (A3, G4, L3…) for its text.')));
}

function patient() {
  const S = data.standing, st = R.state, age = S.age.age_years;
  const dxAge = st.since ? daysBetween(st.since, AS_OF) : null;
  const yrs = dxAge != null ? `${Math.floor(dxAge / 365.25)} y ${Math.round((dxAge % 365.25) / 30.4)} m` : '';
  const active = S.conds.filter((c) => /active|self-reported/i.test(c.status) && !/none/i.test(c.status));
  const sx = S.sex.sex[0].toUpperCase() + S.sex.sex.slice(1);
  const col = (title, sub, ...kids) => h('div', { class: 'pb-col' }, h('div', { class: 'pb-k' }, title, sub ? h('small', {}, sub) : null), ...kids);
  return h('section', { class: 'pband' },
    col('Patient', null,
      h('div', { class: 'pb-name' }, data.meta.patient),
      h('div', { class: 'pb-line' }, `${sx} · ${age} years`), h('div', { class: 'pb-line muted' }, `Born ${fmtDate(S.age.date_of_birth)}`),
      h('div', { class: 'pb-line' }, S.life.find((x) => x.domain === 'Occupation').value),
      h('div', { class: 'pb-state', title: 'Diagnosed 2022-02-04. Prediabetes (S3) does not apply: diabetes is established.' }, h('b', {}, st.name), h('span', {}, st.since ? `since ${fmtDate(st.since)} (${yrs})` : ''), rid(st.rule))),
    col('Conditions', null,
      h('div', { class: 'pb-chips' }, active.map((c) => h('span', { class: 'chip wrap', title: `${c.note}${c.date ? '\nDate: ' + c.date + ' (' + c.date_basis + ')' : ''}` }, c.name.replace(/ \(.*\)$/, ''), c.date ? ` ${c.date.slice(0, 4)}` : ''))),
      h('div', { class: 'pb-note' }, 'Not documented: ASCVD, heart failure, CKD, PCOS, gestational diabetes.')),
    col('Medicines', 'taken, last 90 days',
      h('div', { class: 'pb-meds' }, S.meds.filter((m) => m.status === 'active').map((m) => { const a = data.adherence[m.adherence_id]; return h('div', { class: 'pb-med', title: `Since ${fmtDate(m.start)} · ${m.indication}${a ? '\nWhole year ' + a.year + '%' : ''}` }, h('span', {}, h('b', {}, m.name), ` ${m.dose}, ${m.freq}`), a ? h('span', { class: 'num' }, h('span', { class: 'adh' }, h('i', { style: `width:${a.last90}%` })), `${a.last90}%`) : null); })),
      h('div', { class: 'pb-note' }, 'No lipid-lowering therapy, no glucocorticoids.'),
      S.alg.filter((al) => /active/i.test(al.status)).map((al) => h('div', { class: 'pb-allergy', title: `${al.reaction}; confirmed ${al.date}` }, 'Allergy', h('b', {}, `${al.name} (${al.reaction})`)))));
}

// three headline numbers per domain for its overview card
function keyFacts(id) {
  const f = (k, label) => { const v = data.vars[k]; return v ? [label || v.label, Number(v.latest.v).toLocaleString('en-US', { minimumFractionDigits: v.dec, maximumFractionDigits: v.dec }), v.unit] : null; };
  const dv = data.derived, bp = data.bp, ip = data.ipaq[data.ipaq.length - 1];
  const m = {
    anthropometry: [f('bmi'), f('waist'), f('whtr')], glycemia: [f('hba1c'), f('fpg', 'Fasting glucose'), ['CGM mean, 90 days', num(data.cgm.w90.mean, 1), 'mg/dL']],
    bp: [['Home, latest', `${bp.last.sys}/${bp.last.dia}`, 'mmHg'], ['Home, 28-day mean', `${bp.mean_last28[0]}/${bp.mean_last28[1]}`, 'mmHg'], ['Clinic, latest', `${data.vars.bp_clinic_sys.latest.v}/${data.vars.bp_clinic_dia.latest.v}`, 'mmHg']],
    lipids: [f('ldl'), f('tg', 'Triglycerides'), f('hdl')], kidney: [f('egfr'), f('uacr'), f('creat')], liver: [f('alt'), f('ast'), f('ggt')],
    activity: [['IPAQ-Short', ip.category, `${num(ip.met)} MET-min/wk`], ['Daily steps, median', num(dv.steps.median), 'steps'], ['Sedentary, median', (dv.sedentary.median / 60).toFixed(1), 'h a day']],
    lifestyle: [['Sleep, 7 nights', dv.sleep.last7.toFixed(2), 'h'], ['Modifiers recorded', String(R.domains.find((d) => d.id === 'lifestyle').modifiers.length), '']],
  };
  return (m[id] || []).filter(Boolean);
}

function overviewPage() {
  const card = (dom) => h('a', { class: `dcard ${dom.signal}`, href: `#/d/${dom.id}` },
    h('div', { class: 'dc-top' }, h('span', { class: 'dc-name' }, dom.name)),
    h('div', { class: 'dom-rules' }, dom.rules.map(rid), dom.also.length ? [h('span', { class: 'muted', style: { fontSize: '11.5px' } }, 'also met:'), dom.also.map(rid)] : null, dom.signal === 'none' ? h('span', { class: 'muted', style: { fontSize: '11.5px' } }, 'no priority defined') : null),
    h('div', { class: 'dc-facts' }, keyFacts(dom.id).map(([l, v, u]) => h('div', {}, h('span', { class: 'fl' }, l), h('span', { class: 'fv num' }, v, ' ', h('small', {}, u))))),
    h('span', { class: 'dc-go' }, 'Open ›'));
  const GROUPS = [['red', 'high attention'], ['amber', 'increased attention'], ['green', 'lower concern'], ['none', 'no priority defined']];
  const groups = GROUPS.map(([sig, desc]) => [sig, desc, R.domains.filter((d) => d.signal === sig)]).filter((g) => g[2].length);
  return [patient(), h('section', { class: 'domains' },
    h('div', { class: 'dom-intro' }, h('h2', {}, 'Domains'),
      h('details', { class: 'about' }, h('summary', {}, 'About the data'),
        h('div', { class: 'small' }, 'Direction words (up, down, steady), her baseline and "since diagnosis" are display conventions with invented tolerances, not signals and not diagnoses. Hover a rule ID (A3, G4, L3…) for its text.'))),
    groups.map(([sig, desc, list]) => h('div', { class: 'sgroup' }, h('div', { class: 'sg-head' }, sigPill(sig), h('span', { class: 'muted' }, `${list.length} ${list.length === 1 ? 'domain' : 'domains'} · ${desc}`)), h('div', { class: 'dgrid8' }, list.map(card))))) ];
}

function domainPage(id, tab, key) {
  const dom = R.domains.find((d) => d.id === id);
  if (!dom) return [h('p', {}, 'Unknown domain.')];
  if (key && TABS[id].some(([k]) => k === key)) sel[id] = key;
  if (!DOMTABS.some(([k]) => k === tab)) tab = 'values';
  const evVar = data.vars[({ anthropometry: 'weight', glycemia: 'hba1c', bp: 'bp_clinic_sys', lipids: 'ldl', kidney: 'egfr', liver: 'alt', activity: 'ipaq', lifestyle: 'sleep' })[id]];
  const fuRow = id === 'glycemia' ? R.followup.find((x) => /^F[45]$/.test(x.rule || '')) : id === 'kidney' ? R.followup.find((x) => x.rule === 'F8') : id === 'lipids' ? R.followup.find((x) => x.rule === 'F7') : null;
  const head = h('section', { class: `dhead ${dom.signal}` }, h('a', { class: 'back', href: '#/' }, '‹ All domains'),
    h('div', { class: 'dh-main' }, sigPill(dom.signal), h('h1', {}, dom.name), h('span', { class: 'dom-line' }, dom.headline)),
    h('div', { class: 'dom-rules' }, dom.rules.map(rid), dom.also.length ? [h('span', { class: 'muted', style: { fontSize: '11.5px' } }, 'also met:'), dom.also.map(rid)] : null,
      fuRow ? h('span', { class: 'muted', style: { fontSize: '12.5px', marginLeft: '10px' } }, 'Suggested review: ', fuRow.next ? `${fuRow.label} by ${fmtDate(fuRow.next)} (${fuRow.text})` : fuRow.label, ' ') : null, fuRow ? rid(fuRow.rule) : null));
  const seg = h('div', { class: 'seg' }, DOMTABS.map(([k, t]) => h('a', { href: `#/d/${id}/${k}${key ? '/' + key : ''}`, class: k === tab ? 'on' : '' }, t)));
  let body;
  if (tab === 'values') {
    const tiles = h('div', { class: 'tiles' }, tilesFor(id).filter(Boolean));
    tiles.querySelectorAll('.tile').forEach((t) => { t.dataset.dom = id; if (t.dataset.key && TABS[id].some(([k]) => k === t.dataset.key)) { t.style.cursor = 'pointer'; t.title = 'Open its trend'; t.addEventListener('click', () => { sel[id] = t.dataset.key; location.hash = `#/d/${id}/trend/${t.dataset.key}`; }); } });
    body = h('div', { class: 'panel' }, tiles);
  } else if (tab === 'trend') body = trendPanel(dom);
  else if (tab === 'rules') body = rulesPanel(dom);
  else if (tab === 'events') body = eventsPanel(dom);
  else body = allValuesPanel(dom);
  return [head, seg, body];
}

function followup() {
  return h('section', { class: 'card' }, h('div', { class: 'card-head' }, h('div', {}, h('h2', {}, 'Suggested review'), h('div', { class: 'sub' }, `Section 5 of the document, as suggestions only, never as an action. Follow-up is driven by clinical stability, treatment change, symptoms and organ risk, not by colour alone. Due dates are counted from ${fmtDate(AS_OF)}.`))),
    h('div', { class: 'fu' }, R.followup.map((r, i) => h('div', { class: `fu-row ${i === 0 ? 'main' : ''}` }, h('div', { class: 'dom-rules' }, r.rule ? rid(r.rule) : null, h('b', {}, r.label)), r.next ? [h('div', { class: 'fu-big num' }, fmtDate(r.next)), h('div', { class: 'fu-due' }, r.text)] : null, h('div', { class: 'cmp', style: { fontSize: '12.5px' } }, r.note || '')))));
}

function notices() {
  return h('section', { class: 'card' }, h('div', { class: 'card-head' }, h('div', {}, h('h2', {}, 'Read these with the values'), h('div', { class: 'sub' }, 'A few things about this data that a reader needs to know. They state what is in the data and do not explain it.'))),
    h('div', { class: 'notices' }, R.notices.map((n) => h('div', { class: 'notice' }, h('b', {}, h('span', { class: 'n' }, n.id), n.title), h('span', {}, n.text)))));
}

function rulesPage() {
  const used = new Set(R.domains.flatMap((d) => d.trace.map((t) => t.rule).concat(d.rules)));
  R.followup.forEach((f) => f.rule && used.add(f.rule)); used.add(R.state.rule);
  return h('section', { class: 'card' }, h('div', { class: 'card-head' }, h('div', {}, h('h2', {}, `All ${Object.keys(RULES).length} rules`), h('div', { class: 'sub' }, 'The 38 rules in doctors_bands_encoded.md plus the 9 follow-up rows, and which ones were evaluated for her. Where the document is ambiguous or silent, the spec default was followed and is written in the domain\'s notes.'))),
    h('div', { class: 'table-wrap' }, h('table', { class: 'tbl' }, h('thead', {}, h('tr', {}, h('th', {}, 'ID'), h('th', {}, 'Domain'), h('th', {}, 'Signal'), h('th', {}, 'Kind'), h('th', {}, 'Rule'), h('th', {}, 'Used here'))),
      h('tbody', {}, Object.entries(RULES).map(([id, r]) => h('tr', {}, h('td', {}, rid(id)), h('td', {}, r[0]), h('td', {}, r[1]), h('td', { title: KIND[r[2]] }, r[2]), h('td', {}, r[3]), h('td', {}, used.has(id) ? 'yes' : '')))))));
}

// every graph in one view, small, on a shared date axis so one can be read against another
const GRAPHS = [
  ['anthropometry', ['bmi', 'waist', 'whr', 'whtr', 'weight']], ['glycemia', ['hba1c', 'fpg', 'cgm_mean', 'fructosamine', 'homa']], ['bp', ['bp']],
  ['lipids', ['ldl', 'tg', 'hdl', 'tg_hdl', 'nonhdl', 'tc', 'apob']], ['kidney', ['egfr', 'uacr', 'creat']], ['liver', ['liver', 'hsi']],
  ['activity', ['ipaq', 'steps', 'sedentary', 'rhr']], ['lifestyle', ['sleep']],
];
const gState = { dom: 'all', range: 'all', link: true };
function graphsPage() {
  const grid = h('div', { class: 'ggrid' }), box = h('section', { class: 'panel' });
  const draw = () => {
    charts.forEach((c) => c.dispose()); charts.clear(); grid.replaceChildren();
    const items = GRAPHS.filter(([d]) => gState.dom === 'all' || gState.dom === d).flatMap(([d, ks]) => ks.map((k) => [d, k]));
    const a = gState.range === 'year' ? ms(AS_OF) - 365 * 864e5 : ms('2021-09-20'), b = ms(AS_OF) + 10 * 864e5;
    const made = items.map(([d, k]) => {
      const spec = specFor(k); spec.compact = true; spec.xmin = a; spec.xmax = b; spec.dx = (ms(data.meta.dx_date) >= a) ? ms(data.meta.dx_date) : null; spec.windows = []; spec.zones = [];
      const el = h('div', { class: 'gchart' });
      const vk = labVar({ id: d }, k), v = data.vars[vk], sig = R.domains.find((x) => x.id === d).signal;
      const latest = k === 'bp' ? `${data.bp.last.sys}/${data.bp.last.dia} mmHg` : k === 'liver' ? `ALT ${data.vars.alt.latest.v} · AST ${data.vars.ast.latest.v} · GGT ${data.vars.ggt.latest.v}` : `${fv(vk, v.latest.v)} ${v.unit}`;
      grid.append(h('div', { class: 'gtile' }, h('div', { class: 'gd' }, R.domains.find((x) => x.id === d).name), h('div', { class: 'gh' }, h('a', { href: `#/d/${d}/trend/${k}`, title: 'Open the full trend' }, spec.title || v.label), h('span', { class: 'gv' }, h('b', {}, latest))), el, h('div', { class: 'grefs' }, (spec.refs || []).map((r) => { const m = /^([A-Z]\d)\b/.exec(r.label); return h('span', { class: 'gref' }, m ? rid(m[1]) : null, ` ${r.label.replace(/^[A-Z]\d:?\s*/, '')}`); }))));
      return [el, spec];
    });
    requestAnimationFrame(() => {
      made.forEach(([el, spec], i) => { const c = trendChart(el, spec, { meds: [], visits: false, dx: false, diary: false }, data.events); charts.set(`g${i}`, c); c.group = 'g'; });
      if (gState.link && window.echarts.connect) window.echarts.connect('g');
    });
  };
  const chip = (label, on, fn) => h('button', { type: 'button', class: `vt ${on ? 'on' : ''}`, onclick: fn }, label);
  const filters = h('div', { class: 'gfilters' });
  const paint = () => {
    filters.replaceChildren(h('div', { class: 'vtabs' }, chip('All domains', gState.dom === 'all', () => { gState.dom = 'all'; paint(); draw(); }), R.domains.map((d) => chip(d.name, gState.dom === d.id, () => { gState.dom = d.id; paint(); draw(); }))),
      h('div', { class: 'vtabs' }, chip('Whole record', gState.range === 'all', () => { gState.range = 'all'; paint(); draw(); }), chip('Last 12 months', gState.range === 'year', () => { gState.range = 'year'; paint(); draw(); })),
      h('label', {}, h('input', { type: 'checkbox', checked: gState.link ? true : null, onchange: (e) => { gState.link = e.target.checked; draw(); } }), 'Link the cursor across graphs'));
  };
  paint(); draw();
  box.append(h('div', { class: 'card-head' }, h('div', {}, h('h2', {}, 'All graphs'), h('div', { class: 'sub' }, 'Every trend in one view on the same date axis, so one can be read against another. Hover for a value; click a title for the full trend with rules and events.'))), filters, grid);
  return box;
}

function parseRoute() {
  const p = location.hash.replace(/^#\/?/, '').split('/').map(decodeURIComponent);
  if (p[0] === 'd') return { page: 'd', id: p[1], tab: p[2], key: p[3] };
  return { page: ['review', 'notices', 'graphs', 'rules'].includes(p[0]) ? p[0] : '' };
}

// one hover card for every title: shows the full rule text next to the cursor, readable in both themes
{
  const tip = h('div', { class: 'gtip' }); document.body.append(tip);
  const put = (e) => { const w = tip.offsetWidth, hh = tip.offsetHeight; tip.style.left = Math.max(8, Math.min(e.clientX + 14, innerWidth - w - 8)) + 'px'; tip.style.top = (e.clientY + 18 + hh > innerHeight ? e.clientY - hh - 12 : e.clientY + 18) + 'px'; };
  document.addEventListener('mouseover', (e) => {
    const t = e.target.closest && e.target.closest('[title],[data-tip]');
    if (!t) { tip.style.display = 'none'; return; }
    if (t.hasAttribute('title')) { t.dataset.tip = t.getAttribute('title'); t.removeAttribute('title'); }
    const [first, ...rest] = t.dataset.tip.split('\n');
    tip.replaceChildren(rest.length ? h('b', {}, first) : first, rest.join('\n')); tip.style.display = 'block'; put(e);
  });
  document.addEventListener('mousemove', (e) => { if (tip.style.display === 'block') put(e); });
  document.addEventListener('mouseleave', () => { tip.style.display = 'none'; });
}

function go() {
  charts.forEach((c) => c.dispose()); charts.clear(); redraws.clear();
  const r = parseRoute(), root = document.getElementById('root');
  const content = r.page === 'd' ? domainPage(r.id, r.tab, r.key) : r.page === 'review' ? [followup()] : r.page === 'notices' ? [notices()] : r.page === 'graphs' ? [graphsPage()] : r.page === 'rules' ? [rulesPage()] : overviewPage();
  root.replaceChildren(topbar(r), h('main', { class: 'page' }, ...content,
    r.page === 'rules' ? null : h('a', { href: '#/rules', class: 'rules-cta' }, h('span', { class: 'rc-ic', html: '<svg viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M4 5h12a3 3 0 0 1 3 3v11H7a3 3 0 0 1-3-3z"/><path d="M8 9h7M8 13h7"/></svg>' }), h('span', {}, h('b', {}, 'All rules'), h('small', {}, 'every rule the view applies, and which ones were used for her')), h('span', { class: 'rc-go' }, '›')),
    h('div', { class: 'footer' }, `Built from ${data.meta.inputs.final.length} files in final/ and ${data.meta.inputs.doctors_data.length} in doctors_data/ (CSV only). Glucose file md5 ${data.meta.glucose_md5.slice(0, 8)} ${data.meta.glucose_md5_ok ? '(the correct copy)' : '(NOT the expected copy)'}. No risk score, no overall colour, no diagnosis, no advice.`)));
  window.scrollTo(0, 0);
}
{ const q = new URLSearchParams(location.search); if (q.get('lanes')) q.get('lanes').split(',').forEach((k) => { if (k in lanesOn) lanesOn[k] = true; }); }
window.addEventListener('hashchange', go);
window.addEventListener('resize', () => charts.forEach((c) => c.resize()));
go();
window.__nmg = { data, R };
