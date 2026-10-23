// The doctor's view. Inputs (data/nmg.json, built from CSV files only) -> fixed rules (rules.js) -> display. No model, no pipeline.
import { h, fmtDate, ms, num, ago, pv, spark, CHEV, MON } from './ui.js';
import { evaluate, RULES, SENTENCE, goalOf, addMonths, daysBetween, iso } from './rules.js';
import { trendChart, palette } from './charts.js';
import { predictions, recommendations, PRED, PRED_DOMAIN } from './outlook.js';
import { initScribe } from './scribe.js';
import { scheduleBar, schedulePage } from './schedule.js';

const tokRgb = (n) => getComputedStyle(document.documentElement).getPropertyValue(n).trim();
const data = await (await fetch('data/nmg.json')).json();
const R = evaluate(data);
const AS_OF = data.meta.as_of;
const SIGWORD = { green: 'Green', amber: 'Amber', red: 'Red', none: 'Grey', notcomputed: 'Not computed' };
const DIRWORD = { up: ['▲', 'up'], down: ['▼', 'down'], steady: ['●', 'steady'] };
const KIND = { G: 'Guideline threshold', B: 'NMG Lite operational band (not a diagnostic criterion)', F: 'Formula', D: 'Definition or state', S: 'Suggestion (follow-up)' };
const open = new Set(), sel = {}, lanesOn = { meds: true, visits: true, dx: true, diary: false }, redraws = new Map(), charts = new Map();

// ---- small builders ------------------------------------------------------------------------------------------------------------------------------------------
const fv = (k, x) => { const v = data.vars[k]; const d = v ? v.dec : 1; return (x == null ? '—' : Number(x).toLocaleString('en-US', { minimumFractionDigits: d, maximumFractionDigits: d })); };
const sigPill = (s) => h('span', { class: `sig ${s}` }, h('i'), SIGWORD[s] || s);
const rid = (id) => { const r = RULES[id]; return h('span', { class: `rid ${r ? r[2] : ''}`, tabindex: '0', title: r ? `${id} · ${KIND[r[2]]}\n${r[3]}` : id }, id); };
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
      factTile('2-hour glucose after meals', '', 'from CGM, not OGTT', ['breakfast', 'lunch', 'dinner'].filter((k) => c.post_meal_2h[k]).map((k) => h('div', { class: 'cmp' }, `${k[0].toUpperCase() + k.slice(1)} median `, h('b', {}, c.post_meal_2h[k].median), ` · 90th percentile ${c.post_meal_2h[k].p90} · ${c.post_meal_2h[k].n} meals`)).concat([h('div', { class: 'cmp muted' }, `Last dinner ${c.post_meal_2h.dinner.last.v} mg/dL`)])),
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
      factTile('Lp(a)', [num(data.vars.lpa.latest.v), ' ', h('small', {}, 'nmol/L')], `${fmtDate(data.vars.lpa.latest.d)} · measured once in adulthood`, [h('div', { class: 'cmp muted' }, 'Risk-enhancing at 125 nmol/L or more; not serially monitored.')], data.vars.lpa.latest.b),
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
    factTile('Sleep, 7-night average', [sl.last7.toFixed(2), ' ', h('small', {}, 'h')], '', [spark(data.series.sleep.slice(-90), { goal: 7, dots: false }), h('div', { class: 'cmp' }, `Last night ${sl.last_night} h · last 30 nights ${sl.last30} h · year median ${sl.median_year} h`), h('div', { class: 'cmp muted' }, `${sl.share_under_7}% of ${sl.nights} nights under 7 h`), data.vars.sleep.baseline ? h('div', { class: 'cmp' }, 'Last 28 days ', h('b', {}, fv('sleep', data.vars.sleep.last28.median)), ' vs baseline ', h('b', {}, fv('sleep', data.vars.sleep.baseline.v)), ' · ', dirChip(data.vars.sleep.direction, data.vars.sleep.direction.change, 2)) : null]),
    factTile('Modifiers recorded', [String(L.modifiers.length)], 'counted for rule M2; only recorded ones', L.modifiers.map((m) => h('div', { class: 'cmp', title: m.detail }, h('b', {}, m.name), ' ', pv(m.b)))),
    factTile('Tobacco, alcohol, caffeine', tob ? tob.value : 'not recorded', '', [alc ? h('div', { class: 'cmp' }, 'Alcohol: ', alc.value, ` (${dv.alcohol_dates.length} diary entries in the data year)`) : null, caf ? h('div', { class: 'cmp' }, 'Caffeine: ', caf.value) : null], tob ? tob.b : null),
    factTile('Family history', 'First degree', '', fam.filter((f) => f.premature !== 'not documented').map((f) => h('div', { class: 'cmp' }, h('b', {}, f.relative), ': ', f.condition, f.onset ? `, age ${f.onset}` : '', f.premature && !/not applicable/i.test(f.premature) ? ` (premature: ${f.premature.split(' (')[0]})` : '', ' ', pv(f.b))).concat([h('div', { class: 'cmp muted' }, 'PCOS, gestational diabetes and inherited conditions: not documented.')])),
    factTile('Occupation and diet', occ ? occ.value.split(',')[0] : '', occ ? occ.detail : '', [diet ? h('div', { class: 'cmp' }, h('b', {}, 'Diet: '), diet.value, ' · ', diet.detail) : null, hh ? h('div', { class: 'cmp muted' }, hh.value, '. ', hh.detail) : null], occ ? occ.b : null),
    factTile('PCOS and gestational history', 'None documented', 'not documented', [], 'best_guess'),
  ];
}

// ---- charts: which series, which reference lines ------------------------------------------------------------------------------------------------------
const TABS = {
  anthropometry: [['bmi', 'BMI'], ['waist', 'Waist'], ['whr', 'WHR'], ['whtr', 'WHtR'], ['weight', 'Weight']],
  glycemia: [['hba1c', 'HbA1c'], ['fpg', 'Fasting glucose'], ['cgm_mean', 'CGM daily mean'], ['fructosamine', 'Fructosamine'], ['homa', 'HOMA1-IR']],
  bp: [['bp', 'Home and clinic']],
  lipids: [['ldl', 'LDL-C'], ['tg', 'Triglycerides'], ['hdl', 'HDL-C'], ['tg_hdl', 'TG/HDL-C'], ['nonhdl', 'Non-HDL-C'], ['tc', 'Total cholesterol'], ['apob', 'ApoB'], ['lpa', 'Lp(a)']],
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
  if (tab === 'liver') { Object.assign(spec, { unit: 'U/L', dec: 0, title: 'ALT, AST and GGT' }); spec.lines = [mk('alt', 'ALT', P.primaryInk, 'lab'), mk('ast', 'AST', P.ep, 'lab'), mk('ggt', 'GGT', P.low, 'lab')]; return spec; }
  const v = data.vars[tab];
  Object.assign(spec, { unit: v.unit, dec: v.dec, title: v.label });
  spec.lines = [mk(tab, v.label, P.primaryInk)];
  if (v.kind === 'daily') {
    const end = ms(lastD(tab)), d0 = ms(data.series[tab][0][0]);
    spec.xmin = d0 - 3 * 864e5; spec.xmax = end + 2 * 864e5; spec.dx = null;
    if (v.baseline) { spec.windows.push({ from: end - 117 * 864e5, to: end - 28 * 864e5, label: 'baseline (90 days)', color: `rgba(${tokRgb('--win-rgb')},.16)` }, { from: end - 27 * 864e5, to: end, label: '', color: 'rgba(162,48,95,.14)' }); spec.baseline = { from: end - 117 * 864e5, to: end - 28 * 864e5, value: v.baseline.v }; }
    if (tab === 'cgm_mean') spec.band = { lo: 70, hi: 180, label: 'time-in-range band 70 to 180' };
  } else {
    if (v.baseline) { const from = ms(addMonths(lastD(tab), -24)), to = ms(lastD(tab)); spec.windows.push({ from, to, label: 'baseline window (previous 24 months)', color: `rgba(${tokRgb('--win-rgb')},.16)` }); spec.baseline = { from, to, value: v.baseline.v }; }
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
// Status dots and pills stay in colour even while a card is quiet. Set to false to grey the Domains status dots until hover.
const STATUS_COLOURS_ALWAYS_ON = true;
if (!STATUS_COLOURS_ALWAYS_ON) document.documentElement.classList.add('status-quiet');
const EMBED = new URLSearchParams(location.search).get('embed') === '1';
const DOMTABS = [['values', 'Status and trends'], ['episodes', 'Events and episodes']];
const labVar = (dom, k) => (k === 'bp' ? 'bp_clinic_sys' : k === 'liver' ? 'alt' : k);

// a plain-words summary of a chart for assistive technology (the chart itself is a canvas)
function chartSummary(spec) {
  const ln = spec.lines.filter((l) => l.pts && l.pts.length).map((l) => { const q = l.pts[l.pts.length - 1]; return `${l.name}: latest ${Number(q[1]).toLocaleString('en-US', { maximumFractionDigits: spec.dec == null ? 1 : spec.dec })} ${spec.unit || ''} on ${fmtDate(q[0])}, ${l.pts.length} readings from ${fmtDate(l.pts[0][0])}`; });
  return `${spec.title || 'Trend'}, a line chart over time. ${ln.join('; ')}.`;
}
function trendPanel(dom, opts = {}) {
  const tabs = TABS[dom.id];
  if (!tabs.some(([k]) => k === sel[dom.id])) sel[dom.id] = tabs[0][0];
  const chartEl = h('div', { class: 'chartbox' }), legend = h('div', { class: 'legend' }), tabsEl = h('div', { class: 'vtabs' });
  const lanesEl = h('div', { class: 'lanes' }, [['meds', 'Medicines'], ['visits', 'Clinic visits'], ['dx', 'Diagnoses and imaging'], ['diary', 'Diary: symptoms and care']].map(([k, t]) => h('label', {}, h('input', { type: 'checkbox', checked: lanesOn[k] ? true : null, onchange: (e) => { lanesOn[k] = e.target.checked; draw(); } }), t)));
  const draw = () => {
    tabsEl.replaceChildren(...(tabs.length > 1 ? tabs.map(([k, t]) => h('button', { type: 'button', class: `vt ${sel[dom.id] === k ? 'on' : ''}`, onclick: () => { sel[dom.id] = k; draw(); } }, t)) : []));
    const k = sel[dom.id];
    if (charts.get(dom.id)) { charts.get(dom.id).dispose(); charts.delete(dom.id); }
    const spec = specFor(k); spec.draw = true;
    const hMax = lanesOn.meds ? 470 : 420;
    chartEl.style.height = (opts.chips === false ? Math.max(380, Math.min(hMax, innerHeight - 56 - 350)) : hMax) + 'px';
    chartEl.setAttribute('role', 'img'); chartEl.setAttribute('aria-label', chartSummary(spec));
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
  return h('div', { class: 'panel' }, opts.chips === false ? null : tabsEl, lanesEl, chartEl, legend);
}

// Events and episodes: an episode is the stretch between two clinic visits. For each one: how the domain's main value moved, what was recorded in between, and how the visit that closed it concluded.
const EPKEY = { anthropometry: 'weight', glycemia: 'hba1c', bp: 'bp_clinic_sys', lipids: 'ldl', kidney: 'egfr', liver: 'alt', activity: 'ipaq', lifestyle: 'sleep' };
const EPKIND = ['symptom', 'healthcare_interaction', 'life_event', 'substance_use', 'environment', 'travel', 'social_interaction', 'habits', 'allergy'];
const EPLABEL = { symptom: 'Symptom', healthcare_interaction: 'Care', life_event: 'Life event', substance_use: 'Substance use', environment: 'Environment', travel: 'Travel', social_interaction: 'Family and social', habits: 'Habit', allergy: 'Allergy', medicine: 'Medicine', diagnosis: 'Diagnosis', imaging: 'Imaging' };
function span(a, b) { const d = daysBetween(a, b); return d < 60 ? `${d} days` : d < 700 ? `${Math.round(d / 30.4)} months` : `${(d / 365.25).toFixed(1)} years`; }
function episodes(dom) {
  const key = EPKEY[dom.id], v = data.vars[key], S = data.standing;
  const pts = data.series[key] || [];
  const at = (d) => { // the value at a visit: the nearest lab within 45 days, or the average of the 30 days before for a daily series
    if (v.kind === 'lab') { const x = pts.map((p) => [Math.abs(daysBetween(p[0], d)), p]).sort((m, n) => m[0] - n[0])[0]; return x && x[0] <= 45 ? x[1][1] : null; }
    const w = pts.filter((p) => p[0] <= d && daysBetween(p[0], d) < 30); return w.length >= 5 ? w.reduce((t, p) => t + p[1], 0) / w.length : null;
  };
  const visits = S.visits.filter((x) => x.d <= AS_OF), out = [];
  for (let i = visits.length - 1; i > 0; i--) {
    const a = visits[i - 1], b = visits[i], v0 = at(a.d), v1 = at(b.d);
    if (v0 == null || v1 == null) continue;
    const tol = v.direction && v.direction.tol != null ? v.direction.tol : Math.abs(v0) * 0.03, ch = v1 - v0;
    const word = Math.abs(ch) < tol ? 'held steady' : ch > 0 ? 'rose' : 'fell', open = b.d >= AS_OF;
    const items = [];
    S.diary.filter((e) => e.d > a.d && e.d <= b.d).forEach((e) => items.push({ d: e.d, k: e.category, t: e.text, pr: EPKIND.indexOf(e.category) < 0 ? 99 : EPKIND.indexOf(e.category) }));
    S.meds.forEach((m) => { if (m.start && m.start > a.d && m.start <= b.d) items.push({ d: m.start, k: 'medicine', t: `Started ${m.name} ${m.dose}, ${m.freq} (${m.indication})`, pr: -1 }); if (m.end && m.end > a.d && m.end <= b.d) items.push({ d: m.end, k: 'medicine', t: `Stopped ${m.name} ${m.dose} (${m.status})`, pr: -1 }); });
    S.conds.forEach((c) => { if (c.date && c.date > a.d && c.date <= b.d && !/none/i.test(c.status)) items.push({ d: c.date, k: 'diagnosis', t: `${c.name.replace(/ \(.*\)$/, '')} diagnosed`, pr: -1 }); });
    S.imaging.forEach((m) => { if (m.d > a.d && m.d <= b.d) items.push({ d: m.d, k: 'imaging', t: `${m.modality}: ${m.impression || m.finding}`, pr: -1 }); });
    const shown = items.sort((x, y) => x.pr - y.pr || (x.d < y.d ? -1 : 1)).slice(0, 6).sort((x, y) => (x.d < y.d ? -1 : 1));
    const next = visits[i + 1] ? at(visits[i + 1].d) : null;
    out.push({ a, b, v0, v1, ch, word, open, shown, more: items.length - shown.length, next, nextVisit: visits[i + 1] });
  }
  return out.slice(0, 6);
}
function episodesPanel(dom) {
  const key = EPKEY[dom.id], v = data.vars[key], fv = (x) => Number(x).toLocaleString('en-US', { minimumFractionDigits: v.dec, maximumFractionDigits: v.dec });
  const eps = episodes(dom);
  const card = (e) => h('article', { class: `ep${e.open ? ' open' : ''}` },
    h('header', { class: 'ep-h' },
      h('div', { class: 'ep-t' }, e.word === 'held steady' ? `${v.label} held steady near ${fv(e.v1)} ${v.unit}` : `${v.label} ${e.word} from ${fv(e.v0)} to ${fv(e.v1)} ${v.unit}`),
      h('div', { class: 'ep-s' }, `${fmtDate(e.a.d)} to ${fmtDate(e.b.d)} · ${span(e.a.d, e.b.d)}${e.open ? ' · still open' : ''}`)),
    h('div', { class: 'ep-body' },
      h('section', {}, h('div', { class: 'sh' }, 'What was recorded in between'),
        e.shown.length ? h('ul', { class: 'ep-list' }, e.shown.map((x) => h('li', {}, h('span', { class: 'ep-d' }, fmtDate(x.d, false)), h('span', { class: 'ep-k' }, EPLABEL[x.k] || x.k), h('span', { class: 'ep-x' }, x.t))), e.more > 0 ? h('li', { class: 'ep-more' }, `and ${e.more} more recorded entries`) : null) : h('p', { class: 'muted', style: { margin: 0 } }, 'No events were recorded in this period.')),
      h('section', {}, h('div', { class: 'sh' }, e.open ? 'How it ends' : 'How it concluded'),
        e.open ? h('p', { class: 'ep-c' }, `This episode closes at today's review (${fmtDate(e.b.d)}). The values above are as of that date.`)
          : h('div', { class: 'ep-c' }, h('p', {}, h('b', {}, `${fmtDate(e.b.d)}, ${e.b.type}. `), e.b.reason), h('p', {}, h('b', {}, 'Decision: '), e.b.decision),
            e.next != null ? h('p', { class: 'muted' }, `Next value: ${fv(e.next)} ${v.unit} on ${fmtDate(e.nextVisit.d)}.`) : null))));
  return h('div', { class: 'pscroll' }, h('div', { class: 'panel narrow' },
    h('p', { class: 'ep-lead' }, `An episode is the stretch between two clinic visits. Each one shows how ${v.label} moved, what was recorded in between, and how the visit that closed it concluded.`),
    eps.length ? eps.map(card) : h('p', { class: 'muted' }, 'No clinic visits with a recorded value to build episodes from.')));
}

// ---- header and route -----------------------------------------------------------------------------------------------------------------------------------
const NAVL = [['schedule', "Today's schedule"], ['', 'Overview'], ['graphs', 'All graphs']];
// motion tokens live in the CSS (one rhythm); the JS reads them from there
const tok = (name, d) => parseFloat(getComputedStyle(document.documentElement).getPropertyValue(name)) || d;
const CALM = matchMedia('(prefers-reduced-motion: reduce)');
// the tab switchers share one highlight. It stretches over both tabs and settles on the new one; the page is redrawn on every route change, so the previous place is remembered.
const IND = {};
function indicate(box, key, vertical) {
  const ind = h('span', { class: 'ind', 'aria-hidden': 'true' });
  box.classList.add('has-ind'); box.prepend(ind);
  const vert = () => !!vertical && !matchMedia('(max-width: 900px)').matches; // the page tabs are a vertical rail on wide screens and a row on narrow ones
  const pos = (on) => (vert() ? [on.offsetTop, on.offsetHeight] : [on.offsetLeft, on.offsetWidth]);
  const css = (p) => (vert() ? { transform: `translateY(${p[0]}px)`, height: p[1] + 'px' } : { transform: `translateX(${p[0]}px)`, width: p[1] + 'px' });
  const set = (p) => { ind.style.width = ''; ind.style.height = ''; Object.assign(ind.style, css(p)); };
  box._place = () => { const on = box.querySelector('a.on'); if (on) set(pos(on)); };
  requestAnimationFrame(() => {
    const on = box.querySelector('a.on'); if (!on) return;
    const p = pos(on), prev = IND[key];
    set(p); IND[key] = p;
    if (prev && (prev[0] !== p[0] || prev[1] !== p[1]) && !CALM.matches && ind.animate) {
      const lo = Math.min(prev[0], p[0]), hi = Math.max(prev[0] + prev[1], p[0] + p[1]);
      ind.animate([css(prev), css([lo, hi - lo]), css(p)].map((f, i) => (i === 1 ? { ...f, offset: 0.45 } : f)), { duration: tok('--dur-pill', 380), easing: 'cubic-bezier(.22, 1, .36, 1)' });
    }
  });
  return box;
}
window.addEventListener('resize', () => document.querySelectorAll('.has-ind').forEach((b) => b._place && b._place()));

// theme: a circular reveal from the button where the View Transitions API exists, a 300 ms cross-fade elsewhere
function switchTheme(ev, want) {
  const root = document.documentElement, n = want || (root.dataset.theme === 'dark' ? 'light' : 'dark');
  if (n === root.dataset.theme) return;
  const apply = () => { root.dataset.theme = n; try { localStorage.setItem('theme', n); } catch (e) { /* ignore */ } try { if (EMBED && parent !== window) parent.postMessage({ type: 'dv-theme', theme: n }, location.origin); } catch (e) { /* ignore */ } syncFab(); go(); };
  if (CALM.matches) { apply(); return; }
  if (document.startViewTransition) {
    const r = ev.currentTarget.getBoundingClientRect(), x = r.left + r.width / 2, y = r.top + r.height / 2, R = Math.hypot(Math.max(x, innerWidth - x), Math.max(y, innerHeight - y));
    document.startViewTransition(apply).ready.then(() => root.animate({ clipPath: [`circle(0px at ${x}px ${y}px)`, `circle(${R}px at ${x}px ${y}px)`] }, { duration: tok('--dur-theme', 600), easing: 'cubic-bezier(.22, 1, .36, 1)', pseudoElement: '::view-transition-new(root)' })).catch(() => {});
  } else {
    root.classList.add('theme-fade'); apply(); setTimeout(() => root.classList.remove('theme-fade'), 340);
  }
}

function topbar(route) {
  const S = data.standing, sx = S.sex.sex[0].toUpperCase() + S.sex.sex.slice(1);
  const patientBlock = h('div', { class: 'tb-pt' }, h('div', { class: 'tb-av', title: data.meta.patient }, h('img', { src: 'img/meera.jpg', alt: data.meta.patient })),
    h('div', { class: 'tb-id' }, h('h1', { class: 'tb-name' }, data.meta.patient),
      h('div', { class: 'tb-facts' }, h('span', {}, `${S.age.age_years} years · ${sx}`), h('span', {}, `Born ${fmtDate(S.age.date_of_birth)}`), h('span', {}, S.life.find((x) => x.domain === 'Occupation').value))));
  const more = h('button', { type: 'button', class: 'tb-more', 'aria-expanded': 'false', 'aria-controls': 'tb-prof' }, h('span', {}, 'Profile'), h('span', { class: 'tb-chev', 'aria-hidden': 'true', html: '<svg viewBox="0 0 24 24" width="14" height="14" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"><path d="M6 9l6 6 6-6"/></svg>' }));
  const prof = h('section', { class: 'tb-prof', id: 'tb-prof', 'aria-label': 'Profile', inert: '' }, h('div', { class: 'tb-prof-in' }, profilePanel()));
  const bar = h('header', { class: 'topbar pt' }, h('div', { class: 'tb-row' }, EMBED ? null : h('div', { class: 'brand' }, h('span', { class: 'brand-mark', html: '<svg viewBox="0 0 24 24"><path d="M3 13h4l2.5-6 4 12 2.5-6h5"/></svg>' }), "Doctor's view"),
    patientBlock, h('span', { class: 'top-sp' }), h('span', { class: 'chip' }, `As of ${fmtDate(AS_OF)}`), more), prof);
  bindProfile(bar, more, prof);
  return bar;
}
// the profile opens under the banner on hover (or a tap / Enter on the Profile button) and pushes the page down; it never overlaps anything
function bindProfile(bar, btn, prof) {
  const HOVER = matchMedia('(hover: hover) and (pointer: fine)'); let tIn = 0, tOut = 0, pinned = false;
  const set = (v) => { bar.classList.toggle('open', v); btn.setAttribute('aria-expanded', String(v)); if (v) prof.removeAttribute('inert'); else prof.setAttribute('inert', ''); };
  bar.addEventListener('mouseenter', () => { if (!HOVER.matches) return; clearTimeout(tOut); clearTimeout(tIn); tIn = setTimeout(() => set(true), 140); });
  bar.addEventListener('mouseleave', () => { if (!HOVER.matches) return; clearTimeout(tIn); if (!pinned) { clearTimeout(tOut); tOut = setTimeout(() => set(false), 260); } });
  btn.addEventListener('click', () => { if (bar.classList.contains('open') && pinned) { pinned = false; set(false); } else { pinned = true; set(true); } });
  document.addEventListener('keydown', (e) => { if (e.key === 'Escape' && bar.classList.contains('open') && bar.isConnected) { pinned = false; set(false); } });
  document.addEventListener('pointerdown', (e) => { if (pinned && bar.isConnected && !bar.contains(e.target)) { pinned = false; set(false); } }, true);
  if (typeof ResizeObserver === 'function') new ResizeObserver(() => { if (window.__syncEdge) window.__syncEdge(); window.dispatchEvent(new Event('dv-bar')); }).observe(bar);
}
// the detailed profile: who she is, everything on her problem list, family, habits and work, and the scans on file
function profilePanel() {
  const S = data.standing, grp = (title, ...kids) => h('div', { class: 'tbp-g' }, h('div', { class: 'tbp-h' }, title), ...kids);
  const row = (k, t, tip, cls) => h('div', { class: `tbp-r${cls ? ' ' + cls : ''}`, title: tip || null }, k ? h('b', {}, k) : null, h('span', {}, t));
  const life = (d) => S.life.find((x) => x.domain === d);
  const conds = S.conds.filter((c) => /active|self-reported/i.test(c.status) && !/none/i.test(c.status));
  const fam = S.fam.filter((f) => f.onset || f.year);
  const scans = (S.imaging || []).map((m) => row(`${m.modality}, ${monYr(m.d)}`, m.impression.split(';')[0], `${m.indication}\n${m.finding}`));
  return [
    grp('About her',
      row('Work pattern', life('Occupation').detail),
      row('Home', life('Household').value),
      row('Weight and build', `${data.vars.weight.latest.v} kg, BMI ${data.vars.bmi.latest.v.toFixed(1)}, waist ${Math.round(data.vars.waist.latest.v)} cm`)),
    grp('Problem list',
      conds.map((c) => row(c.name.replace(/ \(.*\)$/, '').replace(/ \/ .*$/, ''), `${c.date ? c.date.slice(0, 4) + ', ' : ''}${c.status.replace(/^active, /, '').replace('self-reported, intermittent', 'self-reported')}`, c.note, 'in'))),
    grp('Family history', fam.map((f) => row(f.relative, `${f.condition.replace(/^Coronary artery disease with bypass surgery$/, 'Heart bypass surgery').replace(/^Type/, 'type').replace(/^Hypertension/, 'hypertension')}${f.onset ? `, age ${f.onset}` : ''}`, null, 'in')),
      scans.length ? h('div', { class: 'tbp-h sub' }, 'Scans on file') : null, ...scans),
    grp('Habits',
      row('Smoking', life('Tobacco').value, null, 'in'), row('Alcohol', life('Alcohol').value, null, 'in'), row('Caffeine', life('Caffeine').value, null, 'in'),
      row('Meals', life('Diet pattern').value, life('Diet pattern').detail, 'in'),
      row('Activity', life('Physical activity').value, null, 'in'))
  ];
}
// the page tabs: a vertical rail on the left (a row on narrow screens)
function sideNav(route) {
  return h('aside', { class: 'dv-side', 'aria-label': 'Pages and visit brief' },
    indicate(h('nav', { class: 'tnav vert', 'aria-label': 'Pages' }, NAVL.map(([k, t2]) => h('a', { href: `#/${k}`, 'aria-current': (route.page === k || (k === '' && ['d', 'p', 'r'].includes(route.page))) ? 'page' : null, class: (route.page === k || (k === '' && ['d', 'p', 'r'].includes(route.page))) ? 'on' : '' }, t2))), 'nav', true),
    h('section', { class: 'dv-brief', 'aria-label': 'Visit brief' }, h('div', { class: 'dv-brief-h' }, 'Visit brief'), briefs()));
}

// the fixed sentence is on every page; the provenance notes sit behind "About this view"
function sentence() {
  return h('section', { class: 'stmtbar' }, h('div', { class: 'stmt' }, SENTENCE),
    h('details', { class: 'about' }, h('summary', {}, 'About this view'),
      h('div', { class: 'small' }, 'Direction words (up, down, steady), her baseline and "since diagnosis" are display conventions with invented tolerances, not signals and not diagnoses.'),
      h('div', { class: 'sigkey' }, [['green', 'Green', 'lower concern'], ['amber', 'Amber', 'increased attention'], ['red', 'Red', 'high attention'], ['none', 'Grey', 'no priority defined']].map(([c, t, d]) => h('div', {}, sigPill(c), h('span', {}, h('b', {}, t), ' ', d)))),
      h('div', { class: 'small' }, 'Signals are per domain and never combined into one colour. Hover a rule ID (A3, G4, L3…) for its text.')));
}

function patient() {
  const S = data.standing, st = R.state, age = S.age.age_years;
  const dxAge = st.since ? daysBetween(st.since, AS_OF) : null;
  const yrs = dxAge != null ? `${Math.floor(dxAge / 365.25)} y ${Math.round((dxAge % 365.25) / 30.4)} m` : '';
  const active = S.conds.filter((c) => /active|self-reported/i.test(c.status) && !/none/i.test(c.status)).filter((c) => /diabetes|hypertension|hypothyroid/i.test(c.name)); // the three on treatment; the rest are in the Profile card
  const sx = S.sex.sex[0].toUpperCase() + S.sex.sex.slice(1);
  const initials = data.meta.patient.split(/[\s_]+/).filter((w) => !/^v\d+$/i.test(w)).map((w) => w[0].toUpperCase()).join('').slice(0, 2);
  const sec = (cls, title, sub, ...kids) => h('div', { class: `pb-sec ${cls}` }, h('div', { class: 'pb-h' }, h('i', {}), title, sub ? h('small', {}, sub) : null), ...kids);
  const allergies = S.alg.filter((al) => /active/i.test(al.status));
  return h('section', { class: 'pband' },
    h('div', { class: 'pb-secs' },
      sec('cond', 'Conditions', null,
        h('div', { class: 'pb-tags' }, active.map((c) => h('span', { class: 'chip wrap', title: `${c.note}${c.date ? '\nDate: ' + c.date : ''}` }, c.name.replace(/ \(.*\)$/, ''), c.date ? ` ${c.date.slice(0, 4)}` : '')))),
      sec('meds', 'Medicines', 'taken, last 90 days',
        h('div', { class: 'pb-meds' }, S.meds.filter((m) => m.status === 'active').map((m) => { const a = data.adherence[m.adherence_id]; return h('div', { class: 'pb-med', title: `Since ${fmtDate(m.start)} · ${m.indication}${a ? '\nWhole year ' + a.year + '%' : ''}` }, h('span', {}, h('b', {}, m.name), ` ${m.dose}, ${m.freq}`), a ? h('span', { class: 'num' }, h('span', { class: 'adh' }, h('i', { style: `width:${a.last90}%` })), `${a.last90}%`) : null); }))),
      sec('goal', 'Goals', 'set by the clinic',
        h('div', { class: 'pb-meds' }, [['HbA1c', 'hba1c'], ['LDL-C', 'ldl']].map(([dom, key]) => { const g = S.goals.find((x) => x.domain === dom), v = data.vars[key]; return g ? h('div', { class: 'pb-med', title: `${g.rationale}\nSet ${fmtDate(g.date)}` }, h('span', {}, h('b', {}, dom), ` ${g.target}`), v ? h('span', { class: 'num' }, 'now ', h('b', {}, `\u00a0${Number(v.latest.v).toLocaleString('en-US', { minimumFractionDigits: v.dec, maximumFractionDigits: v.dec })}`), h('small', {}, `\u00a0${v.unit}`)) : null) : null; }))),
      sec('alg', 'Allergy', null,
        allergies.length ? allergies.map((al) => h('div', { class: 'pb-allergy', title: `${al.reaction}; confirmed ${al.date}` }, h('b', {}, al.name), h('span', {}, al.reaction))) : h('div', { class: 'pb-note' }, 'None active.'))));
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

// The first REST_ROWS rows of each box show at rest; the other rows (the same DOM nodes, moved, never copied) live in a details blob that splits off below the box on hover.
const REST_ROWS = 1;      // rows kept in the box when the boxes sit below the content (narrow screens)
const RAIL_REST_ROWS = 0; // rows kept in the box in the left rail, where it is only a title and a date line
const WIDE = () => matchMedia('(min-width: 901px)').matches;
// goo filter for the amoeba split, applied to the shapes layer only and only while it moves
if (!document.getElementById('dv-goo-defs')) {
  const ns = 'http://www.w3.org/2000/svg', svg = document.createElementNS(ns, 'svg'); svg.id = 'dv-goo-defs'; svg.setAttribute('width', '0'); svg.setAttribute('height', '0'); svg.setAttribute('aria-hidden', 'true'); svg.style.cssText = 'position:absolute;width:0;height:0';
  svg.innerHTML = '<defs><filter id="dv-goo" x="-30%" y="-20%" width="160%" height="470%" color-interpolation-filters="sRGB"><feGaussianBlur in="SourceGraphic" stdDeviation="8" result="b"/><feColorMatrix in="b" mode="matrix" values="1 0 0 0 0 0 1 0 0 0 0 0 1 0 0 0 0 0 24 -11" result="g"/><feComposite in="SourceGraphic" in2="g" operator="atop"/></filter></defs>';
  document.body.append(svg);
  if (!('SVGFEColorMatrixElement' in window) || !('SVGFEGaussianBlurElement' in window)) document.documentElement.classList.add('no-goo');
}
const BOX = { open: null }; // only one blob is open at a time
const SIMPLE = () => CALM.matches || document.documentElement.classList.contains('no-goo'); // no ripple, goo or morph: the details just fade in inside the one big box
const BOX_CLASSES = ['blob-on', 'morphing', 'is-open', 'is-merged', 'settled', 'content-on'];
const clearBox = (st) => ['tIn', 'tOut', 'tEnd', 'tContent', 'tMerge', 'tSettle', 'tShrink'].forEach((k) => clearTimeout(st[k]));
function closeBox(box) {
  const st = box._st; if (!st || !st.open) return;
  clearTimeout(st.tEnd); clearTimeout(st.tContent); clearTimeout(st.tMerge); clearTimeout(st.tSettle); clearTimeout(st.tShrink);
  st.open = false; st.pinned = false;
  box.classList.remove('content-on'); box.setAttribute('aria-expanded', 'false'); box.querySelector('.bc').tabIndex = -1;
  if (BOX.open === box) BOX.open = null;
  if (SIMPLE()) { box.classList.remove(...BOX_CLASSES); return; }
  // reverse of the open: the one big box splits, the lower part shrinks back into the box and merges (about 650 ms)
  box.classList.add('morphing'); box.classList.remove('settled', 'is-merged');
  st.tShrink = setTimeout(() => { if (!st.open) box.classList.remove('is-open'); }, 240);
  st.tEnd = setTimeout(() => { if (!st.open) box.classList.remove('blob-on', 'morphing'); }, 240 + 520);
}
function sizeBox(box) {
  const bc = box.querySelector('.bc'), rail = box.parentElement.classList.contains('rail'), bw = 360, boxh = box.offsetHeight;
  box.style.setProperty('--boxh', boxh + 'px'); box.style.setProperty('--boxw', box.offsetWidth + 'px'); box.style.setProperty('--bw', bw + 'px');
  // the details open to the right in the rail (height capped to the room below the box's top, scrolling inside); below the box on narrow screens
  const room = rail ? Math.max(220, innerHeight - box.getBoundingClientRect().top - 18) : innerHeight * 0.6;
  const bh = Math.min(bc.scrollHeight, rail ? room : innerHeight * 0.6);
  box.style.setProperty('--bh', bh + 'px'); box.style.setProperty('--mh', Math.max(boxh, bh) + 'px');
}
function openBox(box) {
  const st = box._st; if (!st || st.open) return;
  if (BOX.open && BOX.open !== box) closeBox(BOX.open);
  clearTimeout(st.tEnd); clearTimeout(st.tContent); clearTimeout(st.tMerge); clearTimeout(st.tSettle); clearTimeout(st.tShrink);
  st.open = true; BOX.open = box;
  const bc = box.querySelector('.bc');
  sizeBox(box);
  box.setAttribute('aria-expanded', 'true'); box.classList.add('blob-on');
  if (SIMPLE()) { box.classList.add('is-open', 'is-merged', 'settled', 'content-on'); box.querySelector('.bc').tabIndex = 0; return; }
  // 1) a droplet buds downward and pinches off, 2) it expands into a second box, 3) after a short hold the two join back into ONE big box, then the goo filter is removed
  box.classList.add('morphing'); void box.offsetWidth; box.classList.add('is-open');
  st.tContent = setTimeout(() => { if (st.open) { box.classList.add('content-on'); box.querySelector('.bc').tabIndex = 0; } }, 560);
  st.tMerge = setTimeout(() => { if (st.open) box.classList.add('is-merged'); }, 1050);
  st.tSettle = setTimeout(() => { if (st.open) { box.classList.add('settled'); box.classList.remove('morphing'); } }, 1050 + 450 + 100);
}
function ripple(box, e) {
  if (CALM.matches) return;
  const rp = box.querySelector('.rp'), b = box.getBoundingClientRect();
  const x = e ? e.clientX - b.left : b.width / 2, y = e ? e.clientY - b.top : b.height / 2, R = Math.hypot(Math.max(x, b.width - x), Math.max(y, b.height - y));
  [0, 1, 2].forEach((i) => {
    const r = document.createElement('i'); r.style.cssText = `left:${x}px;top:${y}px;width:${2 * R}px;height:${2 * R}px;margin:${-R}px 0 0 ${-R}px;`; rp.appendChild(r);
    r.animate([{ transform: 'scale(0)', opacity: 0.9 }, { transform: 'scale(1)', opacity: 0 }], { duration: 1100, delay: i * 170, easing: 'cubic-bezier(.22, 1, .36, 1)', fill: 'both' }).onfinish = () => r.remove();
  });
}
function enhanceBoxes(wrap, restRows) {
  const HOVER = matchMedia('(hover: hover) and (pointer: fine)');
  [...wrap.children].forEach((box, i) => {
    const bh = box.querySelector('.bh'), ul = box.querySelector('ul'), rows = [...ul.children], more = rows.slice(restRows), title = bh.querySelector('span');
    title.id = `box-t${i}`;
    const moreUl = h('ul', {}); more.forEach((li) => moreUl.append(li)); // the same nodes, moved
    const shapes = h('div', { class: 'shapes', 'aria-hidden': 'true' }, h('div', { class: 'sh-box' }), h('div', { class: 'sh-blob' }));
    const rp = h('div', { class: 'rp', 'aria-hidden': 'true' });
    const chev = h('span', { class: 'chev', 'aria-hidden': 'true', html: '<svg viewBox="0 0 24 24" width="14" height="14" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"><path d="M6 9l6 6 6-6"/></svg>' });
    if (!ul.children.length) ul.hidden = true;
    const bx = h('div', { class: 'bx' }, bh, ul);
    const bc = h('div', { class: 'bc', id: `box-d${i}`, role: 'region', tabindex: '-1', 'aria-labelledby': title.id }, moreUl);
    box.replaceChildren(shapes, h('div', { class: 'hair', 'aria-hidden': 'true' }), rp, bx, chev, bc, h('div', { class: 'bridge', 'aria-hidden': 'true' }));
    box.tabIndex = 0; box.setAttribute('role', 'group'); box.setAttribute('aria-expanded', 'false'); box.setAttribute('aria-controls', bc.id); box.setAttribute('aria-labelledby', title.id);
    const st = box._st = { open: false, pinned: false, tIn: 0, tOut: 0, tEnd: 0, tContent: 0, tMerge: 0, tSettle: 0, tShrink: 0 };
    const leave = () => { clearTimeout(st.tIn); if (!st.pinned) { clearTimeout(st.tOut); st.tOut = setTimeout(() => { if (!st.pinned) closeBox(box); }, 220); } };
    box.addEventListener('mouseenter', (e) => { if (!HOVER.matches) return; clearTimeout(st.tOut); ripple(box, e); clearTimeout(st.tIn); st.tIn = setTimeout(() => openBox(box), 120); });
    box.addEventListener('mouseleave', () => { if (HOVER.matches) leave(); });
    box.addEventListener('pointerdown', (e) => { if (e.pointerType === 'mouse' && !HOVER.matches) return; ripple(box, e); });
    const toggle = () => { if (st.open && st.pinned) { closeBox(box); } else { openBox(box); st.pinned = true; } };
    box.addEventListener('click', (e) => { if (e.target.closest('a')) return; toggle(); });
    box.addEventListener('keydown', (e) => { if (e.target === box && (e.key === 'Enter' || e.key === ' ')) { e.preventDefault(); toggle(); } });
    box.addEventListener('focusin', () => { if (box.matches(':focus-visible')) { clearTimeout(st.tOut); openBox(box); } });
    box.addEventListener('focusout', (e) => { if (!box.contains(e.relatedTarget)) { clearTimeout(st.tIn); if (!st.pinned) { clearTimeout(st.tOut); st.tOut = setTimeout(() => closeBox(box), 220); } } });
  });
  return wrap;
}
document.addEventListener('pointerdown', (e) => { if (BOX.open && !BOX.open.contains(e.target)) closeBox(BOX.open); }, true);
document.addEventListener('keydown', (e) => { if (e.key === 'Escape' && BOX.open) closeBox(BOX.open); });
window.addEventListener('resize', () => { if (BOX.open) sizeBox(BOX.open); });

// the patient summary: how long she has been in follow-up, what she is going through, her medicines, and which way her results are heading (all from her own record)
function summary() {
  const S = data.standing, dx = data.meta.dx_date, g14 = data.cgm.w14, g90 = data.cgm.w90, sl = data.derived.sleep;
  const mo = (+AS_OF.slice(0, 4) - +dx.slice(0, 4)) * 12 + (+AS_OF.slice(5, 7) - +dx.slice(5, 7)) - (+AS_OF.slice(8, 10) < +dx.slice(8, 10) ? 1 : 0), yr = Math.floor(mo / 12), mr = mo % 12;
  const span = `${yr} year${yr === 1 ? '' : 's'}${mr ? ` ${mr} month${mr === 1 ? '' : 's'}` : ''}`;
  const meds = S.meds.filter((m) => m.status === 'active'), ad = meds.map((m) => data.adherence[m.adherence_id]).filter(Boolean).map((a) => a.last90);
  const worse = [], better = [], same = [], nm = (v) => v.label.replace(/, clinic$/, ' (clinic)');
  PRED.forEach((c) => { const v = data.vars[c.key]; if (!v || !v.prev) return; const a = v.prev.v, b = v.latest.v, rel = Math.abs(b - a) / Math.max(Math.abs(a), 1e-9);
    if (rel < 0.02) same.push(nm(v)); else (((b > a) === (c.worse === 'up')) ? worse : better).push(`${nm(v)} ${fv(c.key, a)} \u2192 ${fv(c.key, b)}`); });
  if (g14.mean > g90.mean + 3) worse.push(`Average glucose ${Math.round(g90.mean)} \u2192 ${Math.round(g14.mean)} (90 days against 14)`);
  const li = (k, t) => h('li', {}, h('b', {}, k), t);
  const rows = [
    li('In follow-up', `${span}, since ${fmtDate(dx)} \u00b7 ${S.visits.length} visits`),
    li('Treated for', 'Type 2 diabetes, hypertension, underactive thyroid; also high triglycerides, extra weight, fatty liver'),
    li('Going through', `A hard month: quarter-close at work, then festival hosting. Tired and foggy, walks slipped, sleep about ${sl.last7.toFixed(1)} h`),
    li('Medicines', `${meds.map((m) => `${m.name} ${m.dose}`).join(', ')}; taken ${Math.min(...ad)} to ${Math.max(...ad)} % of days. No cholesterol medicine; a second diabetes medicine put off`),
    worse.length ? li('Going the wrong way', worse.join(', ')) : null,
    better.length ? li('Improving', better.join(', ')) : null,
    same.length ? li('Holding steady', same.join(', ')) : null,
  ].filter(Boolean);
  return { sub: `${span} in follow-up`, rows };
}

// four short cards under the banner: who she is, what happened at the last visit, what her PCU shows since, and what she brings today
function briefs() {
  const S = data.standing, prev = S.visits.filter((v) => v.d < AS_OF).slice(-1)[0];
  const weeks = Math.round(daysBetween(prev.d, AS_OF) / 7);
  const g14 = data.cgm.w14, g90 = data.cgm.w90, sl = data.derived.sleep, adh = Object.values(data.adherence).map((a) => a.last90), tsh = data.series.tsh.slice(-2);
  const brief = (cls, title, sub, ...pts) => h('section', { class: `brief ${cls}` },
    h('div', { class: 'bh' }, h('span', {}, title), sub ? h('small', {}, sub) : null), h('ul', {}, pts));
  const li = (k, t) => h('li', {}, k ? h('b', {}, k.replace(/:$/, '')) : null, t); // a label sits on its own line above its value, so the colon is dropped
  const wide = WIDE(), summ = summary();
  return enhanceBoxes(h('div', { class: `briefs${wide ? ' rail' : ''}` },
    brief('b-sum', 'Patient summary', summ.sub, ...summ.rows),
    brief('b-last', 'Last visit', `${fmtDate(prev.d)} · ${weeks} weeks ago`,
      li('Type:', prev.type),
      li('Came with:', prev.reason),
      li('Numbers:', `HbA1c ${prev.hba1c} %, weight ${prev.weight} kg, BP ${prev.bp}`),
      li('Went with:', prev.decision)),
    brief('b-since', 'Since then', `${fmtDate(prev.d, false)} to ${fmtDate(AS_OF)}`,
      li('Glucose:', `last 14 days averaged ${Math.round(g14.mean)} mg/dL, up from ${Math.round(g90.mean)} over 90 days (GMI ${g14.gmi.toFixed(1)} against ${g90.gmi.toFixed(1)})`),
      li('HbA1c:', `now ${data.vars.hba1c.latest.v} %`),
      li('Walks:', 'slipped from 7 Sep, three missed in a row by 10 Sep'),
      li('Sleep:', `${sl.last7.toFixed(1)} h over the last 7 nights (${sl.last30.toFixed(1)} h over 30)`),
      li('Medicines:', `taken ${Math.min(...adh)}–${Math.max(...adh)} % over 90 days`),
      li('Life:', 'school worry about her daughter in July, a calm August, then quarter-close and Ganesh Chaturthi hosting from early September'),
      li('TSH:', `repeated, ${tsh[1][1].toFixed(1)} (was ${tsh[0][1].toFixed(1)})`)),
    brief('b-now', 'Concern today', null,
      li(null, 'Tired and foggy after a hard month'),
      li(null, 'Knows her walks and medicine timing slipped'),
      li(null, 'Knows HbA1c is back up'),
      li(null, 'Wants to reset once the quarter-close and festival pressure ease'))), wide ? RAIL_REST_ROWS : REST_ROWS);
}

// ---- Predictions and Interventions / recommendations (decision support for the clinician; logic in outlook.js) --------------------------------------------
const CTX = { data, R, asOf: AS_OF, refsFor, zonesFor }, PREDS = predictions(CTX), RECS = recommendations(CTX, PREDS);
const PRED_TONE = { bad: 'Heading the wrong way', good: 'Heading the right way', okay: 'Steady, in range', watch: 'Not improving', steady: 'Holding steady' };
const monYr = (d) => `${MON[+d.slice(5, 7) - 1]} ${d.slice(0, 4)}`;
const REC_STATE = { negative: ['red', 'Needs action'], watch: ['amber', 'Keep an eye'], positive: ['green', 'On track'] };
const domName = (id) => (R.domains.find((d) => d.id === id) || { name: id }).name;

function predCard(p) {
  const tone = p.ok ? p.tone : 'none', f = (x) => `${fv(p.key, x)} ${p.unit}`.trim();
  const tip = p.ok ? `${p.label}: ${f(p.now.v)} now. ${p.lines.join(' ')} ${p.why}\nClick for the graph and the reasons.` : `${p.label}: ${p.reason}`;
  const row = (l, v) => h('div', {}, h('span', { class: 'fl' }, l), h('span', { class: 'fv num' }, v));
  return h('a', { class: `dcard pcard ${tone}`, href: `#/p/${p.key}`, title: tip },
    h('div', { class: 'dc-top' }, h('span', { class: 'dc-name' }, p.label)),
    p.ok ? h('div', { class: 'dc-facts' }, row(p.nowLabel || 'Now', f(p.now.v)), row(`By ${monYr(p.endDate)}`, f(p.end.c)), row('80 % range', `${p.range}`))
      : h('div', { class: 'dc-facts' }, h('div', {}, h('span', { class: 'fl' }, p.reason))),
    p.ok ? h('div', { class: 'pc-say' }, PRED_TONE[p.verdict]) : null,
    h('span', { class: 'dc-go' }, 'Open ', h('span', { class: 'chev-r' }, '›')));
}
function recCard(r) {
  const [tone, word] = REC_STATE[r.state];
  return h('a', { class: `dcard rcard ${tone}`, href: `#/r/${r.id}`, title: `${r.title}\n${r.facts[0] || ''}\nClick for what could be done and where it comes from.` },
    h('div', { class: 'dc-top' }, h('span', { class: 'dc-name' }, r.title)),
    h('div', { class: 'rc-chips' }, h('span', { class: 'rc-verb' }, r.verb), h('span', { class: 'rc-state' }, word), h('span', { class: 'rc-dom' }, domName(r.domain))),
    h('p', { class: 'rc-sum' }, r.facts[0] || ''),
    h('span', { class: 'dc-go' }, 'Open ', h('span', { class: 'chev-r' }, '›')));
}
function outlookSections() {
  const intro = (title, sub) => h('div', { class: 'dom-intro' }, h('h2', {}, title), h('p', { class: 'sec-sub' }, sub));
  return h('div', { class: 'outlook' },
    h('section', { class: 'domains', id: 'predictions' }, intro('Predictions', 'If things carry on as they are now, what could happen and when.'), h('div', { class: 'dgrid8' }, PREDS.map(predCard))),
    h('section', { class: 'domains', id: 'recommendations' }, intro('Interventions and recommendations', 'What could be done to stop, reduce, improve or continue each situation.'), h('div', { class: 'dgrid8' }, RECS.map(recCard))));
}

// the projection graph: her readings, the projection with its 80 % range, and two what-if lines
function outlookChart(el, p) {
  const E = window.echarts, P = palette(), c = E.init(el, null, { renderer: 'canvas' }), T = (d) => ms(d), fmt = (x) => fv(p.key, x);
  const hist = p.hist.map((q) => [T(q[0]), q[1]]), proj = (k) => p.proj.map((q) => [T(q.d), q[k]]);
  const ys = [...p.hist.map((q) => q[1]), ...p.proj.flatMap((q) => [q.lo, q.hi, q.imp, q.slp])], lo0 = Math.min(...ys), hi0 = Math.max(...ys), pad = (hi0 - lo0) * 0.12 || 1;
  const yMin = lo0 - pad, yMax = hi0 + pad, near = (y) => y >= yMin - (hi0 - lo0) * 0.5 && y <= yMax + (hi0 - lo0) * 0.5;
  const ZC = { green: `rgba(${P.zg},.13)`, amber: `rgba(${P.za},.17)`, red: `rgba(${P.zr},.13)` };
  const zones = (p.zones || []).map((z) => [{ yAxis: z.from == null ? yMin : Math.max(z.from, yMin), itemStyle: { color: ZC[z.signal] } }, { yAxis: z.to == null ? yMax : Math.min(z.to, yMax) }]).filter((z) => z[0].yAxis < z[1].yAxis);
  const refs = (p.refs || []).filter((r) => near(r.y)).map((r) => ({ yAxis: r.y, lineStyle: { color: r.tone === 'goal' ? P.primaryInk : P.ink2, type: 'dashed', width: 1.2, opacity: 0.8 }, label: { formatter: r.label, position: 'insideStartTop', color: r.tone === 'goal' ? P.primaryInk : P.ink2, fontSize: 11, fontWeight: 600 } }));
  const line = (name, data, color, extra = {}) => ({ name, type: 'line', data, smooth: 0.5, showSymbol: false, silent: false, ...(extra.end ? { endLabel: { show: true, formatter: extra.end, color, fontSize: 11, fontWeight: 600 } } : {}), lineStyle: { color, width: 2, ...(extra.ls || {}) }, itemStyle: { color }, z: 3, ...extra.s });
  const series = [
    { ...line('Recorded', hist, P.primary, { s: { showSymbol: true, symbol: 'circle', symbolSize: 7, smooth: false } }), markArea: { silent: true, data: zones }, markLine: { silent: true, symbol: 'none', animation: false, data: [...refs, { xAxis: T(p.now.d), lineStyle: { color: P.muted, type: 'solid', width: 1, opacity: 0.6 }, label: { formatter: 'latest reading', position: 'insideEndTop', color: P.ink2, fontSize: 11 } }] } },
    { name: '', type: 'line', data: proj('lo'), stack: 'band', smooth: 0.5, symbol: 'none', lineStyle: { opacity: 0 }, silent: true, tooltip: { show: false }, z: 1 },
    { name: '', type: 'line', data: p.proj.map((q) => [T(q.d), q.hi - q.lo]), stack: 'band', smooth: 0.5, symbol: 'none', lineStyle: { opacity: 0 }, areaStyle: { color: P.primary, opacity: 0.14 }, silent: true, tooltip: { show: false }, z: 1 },
    line('Continues as now', proj('c'), P.primary, { ls: { type: 'dashed', width: 2.4 }, end: 'continues' }),
    line('Returns to her best', proj('imp'), P.ep, { ls: { type: 'dotted', width: 2.4 }, end: 'her best' }),
    line('Keeps slipping', proj('slp'), P.ink2, { ls: { type: 'dotted', width: 2.4 }, end: 'slipping' }),
  ];
  c.setOption({
    useUTC: true, animation: true, animationDuration: 1000, animationEasing: 'cubicOut', textStyle: { fontFamily: P.font, color: P.ink2 },
    grid: { left: 62, right: 130, top: 26, bottom: 44 },
    xAxis: { type: 'time', min: T(p.hist[0][0]), max: T(p.endDate) + 6 * 864e5, axisLine: { lineStyle: { color: P.line } }, axisLabel: { color: P.ink2, fontSize: 12 }, splitLine: { show: false },
      axisPointer: { label: { show: true, backgroundColor: P.ink, color: P.surface, borderColor: P.ink, formatter: (q) => fmtDate(new Date(q.value).toISOString().slice(0, 10)) } } },
    yAxis: { type: 'value', min: yMin, max: yMax, name: p.unit, nameTextStyle: { color: P.muted, fontSize: 12, align: 'right' }, axisLabel: { color: P.ink2, fontSize: 12, formatter: (v) => fmt(v) }, splitLine: { lineStyle: { color: P.line, opacity: 0.6 } } },
    tooltip: { trigger: 'axis', backgroundColor: P.surface, borderColor: P.line, textStyle: { color: P.ink, fontSize: 12.5 }, extraCssText: 'box-shadow:0 6px 20px rgba(0,0,0,.18);border-radius:10px;',
      formatter: (ps) => { const rows = ps.filter((q) => q.seriesName && q.value && q.value[1] != null); if (!rows.length) return ''; return `<b>${fmtDate(new Date(rows[0].value[0]).toISOString().slice(0, 10))}</b>` + rows.map((q) => `<div>${q.marker} ${q.seriesName}: <b>${fmt(q.value[1])}</b> ${p.unit}</div>`).join(''); } },
    series,
  });
  return c;
}

function predPopup(key) {
  const p = PREDS.find((x) => x.key === key); if (!p) return [h('p', {}, 'Unknown prediction.')];
  lastFit = true;
  const f = (x) => `${fv(p.key, x)} ${p.unit}`.trim(), dom = R.domains.find((d) => d.id === p.domain), rel = RECS.filter((r) => r.domain === p.domain);
  const head = h('section', { class: 'dhead' }, h('div', { class: 'dh-main' }, p.ok ? h('span', { class: `sig ${p.tone}` }, h('i'), PRED_TONE[p.verdict]) : h('span', { class: 'sig none' }, h('i'), 'Not enough readings'), h('h2', { id: 'modal-title' }, p.label), h('span', { class: 'dom-line' }, p.ok ? p.short : p.reason)),
    h('div', { class: 'dom-rules' }, h('span', { class: 'muted', style: { fontSize: '12px' } }, dom ? dom.name : '')));
  const blk = (t, ...kids) => h('div', { class: 'tile otext' }, h('div', { class: 'tk' }, h('span', {}, t)), ...kids);
  const tiles = h('div', { class: 'tiles' });
  if (p.ok) {
    tiles.append(
      blk('What could happen', h('ul', { class: 'o-list' }, p.lines.map((l) => h('li', {}, l)))),
      blk('Three ways it could go', h('div', { class: 'o-scen' }, p.scen.map((q) => h('div', { class: 'o-sc' }, h('div', { class: 'o-sn' }, q.name), h('div', { class: 'o-sv num' }, f(q.end), q.band ? h('span', { class: `dot ${q.band}`, title: `${SIGWORD[q.band]} band` }) : null), h('div', { class: 'o-sd' }, q.text))))),
      blk('Why this is good or bad', h('p', { class: 'o-p' }, p.why)),
      blk('How this was made', h('p', { class: 'o-p muted' }, p.basis)),
      rel.length ? blk('What could be done', h('ul', { class: 'o-list' }, rel.slice(0, 3).map((r) => h('li', {}, h('a', { href: `#/r/${r.id}` }, r.title))))) : null);
  } else tiles.append(blk('Why there is no projection', h('p', { class: 'o-p' }, p.reason), h('p', { class: 'o-p muted' }, 'A projection needs at least four readings spread over four months, or six weeks of daily data.')));
  const chartEl = h('div', { class: 'chartbox' }), legend = h('div', { class: 'legend' });
  chartEl.style.height = Math.max(380, Math.min(470, innerHeight - 56 - 350)) + 'px';
  legend.append(h('span', {}, h('i', { class: 'dot fill' }), 'recorded'), h('span', {}, h('i', { class: 'dash' }), 'continues as now'), h('span', {}, h('i', { class: 'band' }), '80 % range'), h('span', {}, h('i', { class: 'dotted' }), 'returns to her best / keeps slipping'), p.zones && p.zones.length ? h('span', {}, h('i', { class: 'zone' }), 'Green, Amber, Red bands') : null);
  chartEl.setAttribute('role', 'img'); chartEl.setAttribute('aria-label', p.ok ? `${p.label} projection chart. Now ${f(p.now.v)}; ${p.short}; 80 % range ${p.range} ${p.unit}.` : `${p.label}: no projection, ${p.reason}`);
  requestAnimationFrame(() => { if (p.ok) charts.set('pred', outlookChart(chartEl, p)); });
  return [head, h('div', { class: 'split' }, tiles, h('div', { class: 'split-r' }, h('div', { class: 'panel' }, chartEl, legend)))];
}

function recPopup(id) {
  const r = RECS.find((x) => x.id === id); if (!r) return [h('p', {}, 'Unknown suggestion.')];
  lastFit = true;
  const [tone, word] = REC_STATE[r.state], preds = PREDS.filter((p) => p.domain === r.domain && p.ok);
  const head = h('section', { class: 'dhead' }, h('div', { class: 'dh-main' }, h('span', { class: `sig ${tone}` }, h('i'), word), h('h2', { id: 'modal-title' }, r.title)), h('div', { class: 'dom-rules' }, h('span', { class: 'rc-verb' }, r.verb), ' ', h('span', { class: 'muted', style: { fontSize: '12px' } }, domName(r.domain))));
  const card = (t, ...kids) => h('article', { class: 'ep' }, h('header', { class: 'ep-h' }, h('div', { class: 'ep-t' }, t)), h('div', { class: 'ep-body one' }, ...kids));
  return [head, h('div', { class: 'pscroll' }, h('div', { class: 'panel narrow' },
    card('What is happening', h('ul', { class: 'o-list' }, r.facts.map((l) => h('li', {}, l))), preds.length ? h('div', { class: 'o-links' }, preds.map((p) => h('a', { class: 'chip', href: `#/p/${p.key}` }, `Projection: ${p.label} ›`))) : null),
    card('What could be done', h('ul', { class: 'o-list' }, r.consider.map((l) => h('li', {}, l))))))];
}

function overviewPage() {
  const card = (dom) => h('a', { class: `dcard ${dom.signal}`, href: `#/d/${dom.id}` },
    h('div', { class: 'dc-top' }, h('span', { class: 'dc-name' }, dom.name)),
    dom.signal === 'none' ? h('div', { class: 'dom-rules' }, h('span', { class: 'muted', style: { fontSize: '11.5px' } }, 'no priority defined')) : null,
    h('div', { class: 'dc-facts' }, keyFacts(dom.id).map(([l, v, u]) => h('div', {}, h('span', { class: 'fl' }, l), h('span', { class: 'fv num' }, v, ' ', h('small', {}, u))))),
    h('span', { class: 'dc-go' }, 'Open ', h('span', { class: 'chev-r' }, '›')));
  const KEY = [['red', 'Red', 'high attention'], ['amber', 'Amber', 'increased attention'], ['green', 'Green', 'lower concern'], ['none', 'Grey', 'no priority defined']];
  const ordered = KEY.flatMap(([sig]) => R.domains.filter((d) => d.signal === sig));
  return [patient(), h('section', { class: 'domains' },
    h('div', { class: 'dom-intro' }, h('h2', {}, 'Domains'),
      h('details', { class: 'about' }, h('summary', {}, 'About the data'),
        h('div', { class: 'sigkey' }, KEY.map(([c, t, d]) => h('div', {}, sigPill(c), h('span', {}, d)))))),
    h('div', { class: 'dgrid8' }, ordered.map(card))), outlookSections()];
}

function domainPage(id, tab, key) {
  const dom = R.domains.find((d) => d.id === id);
  if (!dom) return [h('p', {}, 'Unknown domain.')];
  if (key && TABS[id].some(([k]) => k === key)) sel[id] = key;
  if (!DOMTABS.some(([k]) => k === tab)) tab = tab === 'events' ? 'episodes' : 'values';
  const evVar = data.vars[({ anthropometry: 'weight', glycemia: 'hba1c', bp: 'bp_clinic_sys', lipids: 'ldl', kidney: 'egfr', liver: 'alt', activity: 'ipaq', lifestyle: 'sleep' })[id]];
  const fuRow = id === 'glycemia' ? R.followup.find((x) => /^F[45]$/.test(x.rule || '')) : id === 'kidney' ? R.followup.find((x) => x.rule === 'F8') : id === 'lipids' ? R.followup.find((x) => x.rule === 'F7') : null;
  const head = h('section', { class: `dhead ${dom.signal}` },
    h('div', { class: 'dh-main' }, sigPill(dom.signal), h('h2', { id: 'modal-title' }, dom.name), h('span', { class: 'dom-line' }, dom.headline)),
    h('div', { class: 'dom-rules' }, fuRow ? h('span', { class: 'muted', style: { fontSize: '12.5px' } }, 'Suggested review: ', fuRow.next ? `${fuRow.label} by ${fmtDate(fuRow.next)} (${fuRow.text})` : fuRow.label) : null));
  const seg = indicate(h('div', { class: 'seg' }, DOMTABS.map(([k, t]) => h('a', { href: `#/d/${id}/${k}${key ? '/' + key : ''}`, 'aria-current': k === tab ? 'page' : null, class: k === tab ? 'on' : '' }, t))), 'seg');
  let body;
  lastFit = true; // every tab keeps the same popup size, so the tab bar never moves
  if (tab === 'values') {
    // values on the left, the trend of the selected one on the right
    if (!TABS[id].some(([k]) => k === sel[id])) sel[id] = TABS[id][0][0];
    const tiles = h('div', { class: 'tiles' }, tilesFor(id).filter(Boolean)), trend = trendPanel(dom, { chips: false });
    const mark = () => tiles.querySelectorAll('.tile').forEach((t) => { t.classList.toggle('on', t.dataset.key === sel[id]); if (t.getAttribute('role') === 'button') t.setAttribute('aria-pressed', String(t.dataset.key === sel[id])); });
    const OWN = { 'Glucose monitoring (CGM), last 90 days': 'cgm_mean', 'Home reading, latest': 'bp', 'Home mean, last 28 days': 'bp', 'Clinic reading, latest': 'bp', 'Goal and treatment': 'bp', 'Lp(a)': 'lpa', 'IPAQ-Short, latest': 'ipaq', 'Daily steps (wearable)': 'steps', 'Sedentary time': 'sedentary', 'Sleep, 7-night average': 'sleep' };
    const SHARED = { alt: 'liver', ast: 'liver', ggt: 'liver', bp_clinic_sys: 'bp' };
    tiles.querySelectorAll('.tile').forEach((t) => { const lab = t.querySelector('.tk span'), k = OWN[lab && lab.textContent] || SHARED[t.dataset.key]; if (k) t.dataset.key = k; });
    tiles.querySelectorAll('.tile').forEach((t) => { t.dataset.dom = id; if (t.dataset.key && TABS[id].some(([k]) => k === t.dataset.key)) { t.style.cursor = 'pointer'; t.title = 'Show its trend'; t.tabIndex = 0; t.setAttribute('role', 'button'); const pick = () => { sel[id] = t.dataset.key; mark(); redraws.get(id)(); }; t.addEventListener('click', pick); t.addEventListener('keydown', (e) => { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); pick(); } }); } });
    mark();
    body = h('div', { class: 'split' }, tiles, h('div', { class: 'split-r' }, trend));
  } else body = episodesPanel(dom);
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
      const el = h('div', { class: 'gchart', role: 'img', 'aria-label': chartSummary(spec) });
      const vk = labVar({ id: d }, k), v = data.vars[vk], sig = R.domains.find((x) => x.id === d).signal;
      const latest = k === 'bp' ? `${data.bp.last.sys}/${data.bp.last.dia} mmHg` : k === 'liver' ? `ALT ${data.vars.alt.latest.v} · AST ${data.vars.ast.latest.v} · GGT ${data.vars.ggt.latest.v}` : `${fv(vk, v.latest.v)} ${v.unit}`;
      grid.append(h('div', { class: 'gtile' }, h('div', { class: 'gd' }, R.domains.find((x) => x.id === d).name), h('div', { class: 'gh' }, h('a', { href: `#/d/${d}/trend/${k}`, title: 'Open the full trend' }, spec.title || v.label), h('span', { class: 'gv' }, h('b', {}, latest))), el, h('div', { class: 'grefs' }, (spec.refs || []).map((r) => { const m = /^([A-Z]\d)\b/.exec(r.label); return h('span', { class: 'gref' }, m ? rid(m[1]) : null, ` ${r.label.replace(/^[A-Z]\d:?\s*/, '')}`); }))));
      return [el, spec];
    });
    requestAnimationFrame(() => {
      const QUIET = matchMedia('screen and (hover: hover) and (pointer: fine) and (prefers-contrast: no-preference)');
      const css = (n) => getComputedStyle(document.documentElement).getPropertyValue(n).trim();
      made.forEach(([el, spec], i) => {
        const base = spec.lines.map((l) => l.color), tile = el.closest('.gtile');
        // quiet at rest: the lines are grey until the card is hovered or focused; then the chart is drawn again in its own colours
        const make = (quiet, still) => { if (charts.get(`g${i}`)) charts.get(`g${i}`).dispose(); const gs = [css('--quiet-g1'), css('--quiet-g2'), css('--quiet-g3')]; spec.lines.forEach((l, j) => { l.color = quiet ? gs[j % 3] : base[j]; }); spec.still = still; const c = trendChart(el, spec, { meds: [], visits: false, dx: false, diary: false }, data.events); charts.set(`g${i}`, c); c.group = 'g'; if (gState.link && window.echarts.connect) window.echarts.connect('g'); };
        make(QUIET.matches, false);
        if (QUIET.matches && tile) { tile.addEventListener('mouseenter', () => make(false, true)); tile.addEventListener('focusin', () => make(false, true)); tile.addEventListener('mouseleave', () => make(true, true)); }
      });
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
  box.append(h('div', { class: 'card-head' }, h('div', {}, h('h2', {}, 'All graphs'), h('div', { class: 'sub' }, 'Every trend in one view on the same date axis, so one can be read against another. Hover for a value; click a title to open it.'))), filters, grid);
  return box;
}

function parseRoute() {
  const p = location.hash.replace(/^#\/?/, '').split('/').map(decodeURIComponent);
  if (p[0] === 'd') return { page: 'd', id: p[1], tab: p[2], key: p[3] };
  if (p[0] === 'p' || p[0] === 'r') return { page: p[0], id: p[1] };
  if (p[0] === 'schedule') return { page: 'schedule' };
  return { page: ['review', 'notices', 'graphs', 'rules'].includes(p[0]) ? p[0] : '' };
}

// one hover card for every title: the full rule text, readable in both themes. It opens on hover, on keyboard focus and on a tap. The text also goes to assistive technology (aria-description).
const TIP = h('div', { class: 'gtip', role: 'tooltip' }); document.body.append(TIP);
const tipText = (t) => { const [first, ...rest] = t.dataset.tip.split('\n'); TIP.replaceChildren(rest.length ? h('b', {}, first) : first, rest.join('\n')); TIP.style.display = 'block'; };
const putTip = (x, y) => { const w = TIP.offsetWidth, hh = TIP.offsetHeight; TIP.style.left = Math.max(8, Math.min(x, innerWidth - w - 8)) + 'px'; TIP.style.top = (y + hh > innerHeight - 8 ? Math.max(8, y - hh - 30) : y) + 'px'; };
const tipTarget = (e) => e.target.closest && e.target.closest('[data-tip]');
function bindTips() { document.querySelectorAll('[title]').forEach((t) => { const v = t.getAttribute('title'); if (!v) return; t.dataset.tip = v; t.removeAttribute('title'); if (!t.getAttribute('aria-description')) t.setAttribute('aria-description', v.replace(/\n/g, ' ')); }); }
{
  document.addEventListener('mouseover', (e) => { const t = tipTarget(e); if (!t) { TIP.style.display = 'none'; return; } tipText(t); putTip(e.clientX + 14, e.clientY + 18); });
  document.addEventListener('mousemove', (e) => { if (TIP.style.display === 'block' && tipTarget(e)) putTip(e.clientX + 14, e.clientY + 18); });
  document.addEventListener('mouseleave', () => { TIP.style.display = 'none'; });
  document.addEventListener('focusin', (e) => { const t = tipTarget(e); if (!t || !e.target.matches(':focus-visible')) return; tipText(t); const b = t.getBoundingClientRect(); putTip(b.left, b.bottom + 8); });
  document.addEventListener('focusout', () => { TIP.style.display = 'none'; });
  document.addEventListener('keydown', (e) => { if (e.key === 'Escape') TIP.style.display = 'none'; });
  let tapT = 0;
  document.addEventListener('click', (e) => { if (!matchMedia('(hover: none)').matches) return; const t = tipTarget(e); clearTimeout(tapT); if (!t || t.closest('a')) { TIP.style.display = 'none'; return; } tipText(t); const b = t.getBoundingClientRect(); putTip(b.left, b.bottom + 8); tapT = setTimeout(() => { TIP.style.display = 'none'; }, 5000); });
}

let lastPage = null, lastFit = false;
// a big popup over the overview, with a close icon; the page behind is blurred. Closing plays a short reverse animation first.
const MODAL_PAGES = ['d', 'p', 'r'];
let closing = false, lastCard = null;
document.addEventListener('pointerdown', (e) => { const c = e.target.closest && e.target.closest('.dcard'); if (c) { const b = c.getBoundingClientRect(); lastCard = { x: b.left + b.width / 2, y: b.top + b.height / 2 }; } }, true);
function closeModal() {
  const back = document.querySelector('.modal-back');
  if (!back) { location.hash = '#/'; return; }
  if (closing) return;
  closing = true; back.classList.add('closing');
  setTimeout(() => { closing = false; location.hash = '#/'; }, CALM.matches ? 100 : tok('--dur-popup-out', 240));
}
function modal(kids, fit) {
  const box = h('div', { class: `modal${fit ? ' fit' : ''}`, role: 'dialog', 'aria-modal': 'true', 'aria-labelledby': 'modal-title', tabindex: '-1' },
    h('button', { class: 'mclose', type: 'button', 'aria-label': 'Close', title: 'Close', onclick: closeModal, html: '<svg viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" stroke-width="2.4" stroke-linecap="round"><path d="M6 6l12 12M18 6L6 18"/></svg>' }),
    h('div', { class: 'mbody' }, ...kids));
  // a tab switch inside an open popup redraws it: no open animation again, only a short cross-fade of the content
  return h('div', { class: `modal-back${MODAL_PAGES.includes(lastPage) ? ' swap' : ''}`, onclick: (e) => { if (e.target === e.currentTarget) closeModal(); } }, box);
}
document.addEventListener('keydown', (e) => { if (e.key === 'Escape' && MODAL_PAGES.includes(parseRoute().page)) closeModal(); });

// pointer effects (all off for touch and reduced motion): domain cards tilt up to 4 degrees with a specular light and a border glow that follow the cursor,
// the other cards get the glow only, the Print and theme buttons are pulled up to 4 px toward the cursor, and a faint blush light follows the pointer.
{
  const fine = matchMedia('(hover: hover) and (pointer: fine)');
  let cur = null, cur2 = null, raf = 0, last = null;
  const reset = (c) => { c.classList.remove('tilting'); ['--rx', '--ry', '--mx', '--my'].forEach((k) => c.style.removeProperty(k)); };
  const frame = () => {
    raf = 0; const e = last; if (!e) return;
    const root = document.documentElement; root.style.setProperty('--px', e.clientX + 'px'); root.style.setProperty('--py', e.clientY + 'px'); root.classList.add('has-light');
    const t = e.target.closest ? e.target : null;
    const c = t && t.closest('.dcard'), g = !c && t && t.closest('.brief, .gtile');
    if (cur && cur !== c) { reset(cur); cur = null; } if (cur2 && cur2 !== g) { reset(cur2); cur2 = null; }
    if (c) { const b = c.getBoundingClientRect(), x = (e.clientX - b.left) / b.width, y = (e.clientY - b.top) / b.height; cur = c; c.classList.add('tilting'); c.style.setProperty('--ry', ((x - .5) * 8).toFixed(2) + 'deg'); c.style.setProperty('--rx', ((.5 - y) * 8).toFixed(2) + 'deg'); c.style.setProperty('--mx', (x * 100).toFixed(1) + '%'); c.style.setProperty('--my', (y * 100).toFixed(1) + '%'); }
    if (g) { const b = g.getBoundingClientRect(); cur2 = g; g.style.setProperty('--mx', (((e.clientX - b.left) / b.width) * 100).toFixed(1) + '%'); g.style.setProperty('--my', (((e.clientY - b.top) / b.height) * 100).toFixed(1) + '%'); }
    document.querySelectorAll('.topbar .btn').forEach((bt) => { const b = bt.getBoundingClientRect(), dx = e.clientX - (b.left + b.width / 2), dy = e.clientY - (b.top + b.height / 2), d = Math.hypot(dx, dy);
      if (d < 90) { bt.style.setProperty('--bx', Math.max(-4, Math.min(4, dx * .14)).toFixed(2) + 'px'); bt.style.setProperty('--by', Math.max(-4, Math.min(4, dy * .14)).toFixed(2) + 'px'); } else { bt.style.removeProperty('--bx'); bt.style.removeProperty('--by'); } });
  };
  document.addEventListener('pointermove', (e) => { if (!fine.matches || CALM.matches || e.pointerType === 'touch') return; last = e; if (!raf) raf = requestAnimationFrame(frame); });
  document.addEventListener('mouseout', (e) => { if (e.relatedTarget) return; last = null; document.documentElement.classList.remove('has-light'); [cur, cur2].forEach((c) => c && reset(c)); cur = cur2 = null; document.querySelectorAll('.topbar .btn').forEach((bt) => { bt.style.removeProperty('--bx'); bt.style.removeProperty('--by'); }); });
}

// domain cards reveal once as they scroll into view, 60 ms apart within a row. Only the first draw hides them (never with reduced motion or without IntersectionObserver); printing releases them all.
function revealCards() {
  const cards = [...document.querySelectorAll('.dcard')];
  if (!cards.length || !('IntersectionObserver' in window) || CALM.matches) return;
  const first = [...cards].slice(0, 4).map((c) => c.getBoundingClientRect().left).sort((a, b) => a - b);
  cards.forEach((c) => c.classList.add('rv-wait'));
  const release = (c) => { const intro = document.documentElement.classList.contains('dv-enter') ? 1000 : 0, col = Math.max(0, first.findIndex((l) => Math.abs(l - c.getBoundingClientRect().left) < 40)); c.style.transitionDelay = `${intro + col * 60}ms`; c.classList.add('rv-go'); c.classList.remove('rv-wait'); setTimeout(() => { c.classList.remove('rv-go'); c.style.transitionDelay = ''; }, intro + 900 + col * 60); };
  const io = new IntersectionObserver((es) => es.forEach((en) => { if (en.isIntersecting) { io.unobserve(en.target); release(en.target); } }), { threshold: 0.12 });
  cards.forEach((c) => io.observe(c));
  window.addEventListener('beforeprint', () => { io.disconnect(); document.querySelectorAll('.dcard.rv-wait').forEach((c) => c.classList.remove('rv-wait')); });
}

// press illumination: one delegated listener records where a control was pressed; the CSS draws and scales a soft glow from that point while :active
document.addEventListener('pointerdown', (e) => { const t = e.target.closest && e.target.closest('.btn, .tnav a, .seg a, .vt, .mclose'); if (!t) return; const b = t.getBoundingClientRect(); t.style.setProperty('--press-x', (e.clientX - b.left).toFixed(0) + 'px'); t.style.setProperty('--press-y', (e.clientY - b.top).toFixed(0) + 'px'); }, true);

// light / dark switch: a small colourful button at the bottom right. It shows the current mode; on hover or focus it opens to show the sun and the moon side by side.
const SUN = '<svg viewBox="0 0 24 24" width="20" height="20" aria-hidden="true"><circle cx="12" cy="12" r="4.6" fill="#F6B13B"/><g stroke="#F08A24" stroke-width="2" stroke-linecap="round"><path d="M12 2.5v2.4M12 19.1v2.4M2.5 12h2.4M19.1 12h2.4M5.3 5.3l1.7 1.7M17 17l1.7 1.7M5.3 18.7L7 17M17 7l1.7-1.7"/></g></svg>';
const MOON = '<svg viewBox="0 0 24 24" width="20" height="20" aria-hidden="true"><path d="M20 14.2A8.4 8.4 0 0 1 9.8 4 8.6 8.6 0 1 0 20 14.2z" fill="#7F8CF0"/><circle cx="16.6" cy="6.2" r="1.1" fill="#C9CFFF"/><circle cx="19.2" cy="9.4" r=".7" fill="#C9CFFF"/></svg>';
function syncFab() { const d = document.documentElement.dataset.theme === 'dark', f = document.querySelector('.themefab'); if (!f) return; f.dataset.mode = d ? 'dark' : 'light'; f.querySelectorAll('button').forEach((b) => b.setAttribute('aria-pressed', String((b.dataset.t === 'dark') === d))); }
{
  const mk = (t, svg, label) => h('button', { type: 'button', 'data-t': t, 'aria-label': label, title: label, html: svg, onclick: (e) => switchTheme(e, t) });
  const fab = h('div', { class: 'themefab', role: 'group', 'aria-label': 'Colour theme' }, mk('light', SUN, 'Light mode'), mk('dark', MOON, 'Dark mode'));
  document.body.append(fab); syncFab();
}

// scroll edge: a short strip under the bar that fades the content into the page colour once content has scrolled under the bar
{
  const edge = h('div', { class: 'edge-fade', 'aria-hidden': 'true' }, h('i', {})); document.body.append(edge);
  window.__syncEdge = () => { const bar = document.querySelector('.topbar'); if (bar) document.documentElement.style.setProperty('--bar-b', bar.getBoundingClientRect().bottom + 'px'); document.documentElement.classList.toggle('scrolled', scrollY > 6); };
  addEventListener('scroll', window.__syncEdge, { passive: true }); addEventListener('resize', window.__syncEdge);
}

let wasWide = WIDE();
window.addEventListener('resize', () => { if (WIDE() !== wasWide) { wasWide = WIDE(); go(); } });
let firstDraw = true;
function go() {
  charts.forEach((c) => c.dispose()); charts.clear(); redraws.clear();
  const r = parseRoute(), root = document.getElementById('root');
  const content = MODAL_PAGES.includes(r.page) ? (() => { const dp = r.page === 'd' ? domainPage(r.id, r.tab, r.key) : r.page === 'p' ? predPopup(r.id) : recPopup(r.id); return [...overviewPage(), modal(dp, lastFit)]; })() : r.page === 'review' ? [followup()] : r.page === 'notices' ? [notices()] : r.page === 'graphs' ? [graphsPage()] : r.page === 'rules' ? [rulesPage()] : overviewPage();
  const cat = (p) => (p === '' || MODAL_PAGES.includes(p) ? 'overview' : p), swapPage = !firstDraw && lastPage !== null && cat(lastPage) !== cat(r.page) && !CALM.matches;
  if (firstDraw) { document.documentElement.classList.add('dv-enter'); setTimeout(() => { document.documentElement.classList.remove('dv-enter'); if (window.__syncEdge) window.__syncEdge(); }, 2200); }
  document.body.classList.toggle('on-schedule', r.page === 'schedule');
  if (r.page === 'schedule') {
    root.replaceChildren(scheduleBar(AS_OF), schedulePage(AS_OF, () => { location.hash = '#/'; }));
    document.body.classList.remove('noscroll'); window.scrollTo(0, 0); lastPage = 'schedule'; firstDraw = false; window.__syncEdge(); bindTips(); return;
  }
  root.replaceChildren(topbar(r), h('div', { class: 'dv-body' }, sideNav(r), h('main', { class: `page${swapPage ? ' dv-swap' : ''}` }, ...content,
    )));
  document.body.classList.toggle('noscroll', MODAL_PAGES.includes(r.page));
  if (!MODAL_PAGES.includes(r.page) && !MODAL_PAGES.includes(lastPage)) window.scrollTo(0, 0);
  const opening = MODAL_PAGES.includes(r.page) && !MODAL_PAGES.includes(lastPage), pop = document.querySelector('.modal');
  if (opening && pop && lastCard) { const b = pop.getBoundingClientRect(); pop.style.transformOrigin = `${lastCard.x - b.left}px ${lastCard.y - b.top}px`; }
  if (firstDraw) revealCards();
  bindTips(); modalFocus(r); lastPage = r.page; lastHash = location.hash; firstDraw = false; window.__syncEdge();
}
// while a popup is open the page behind it (bar, rail, content, notes orb) is inert; focus moves into the popup and returns to the card that opened it
let lastHash = '';
function modalFocus(r) {
  const open = MODAL_PAGES.includes(r.page), back = document.querySelector('.modal-back'), main = document.querySelector('main.page');
  const behind = [document.querySelector('.topbar'), document.querySelector('.dv-side'), document.querySelector('.scribe-root'), ...(main ? [...main.children].filter((el) => el !== back) : [])];
  behind.forEach((el) => { if (el) { if (open) el.setAttribute('inert', ''); else el.removeAttribute('inert'); } });
  if (open && back) {
    const dlg = back.querySelector('.modal');
    if (!MODAL_PAGES.includes(lastPage)) dlg.focus({ preventScroll: true });
    else { const on = dlg.querySelector('.seg a.on'); if (on && (document.activeElement === document.body || !dlg.contains(document.activeElement))) on.focus({ preventScroll: true }); }
  } else if (!open && MODAL_PAGES.includes(lastPage)) {
    const back2 = document.querySelector(`a.dcard[href="${lastHash.split('/').slice(0, 3).join('/')}"]`); if (back2) back2.focus({ preventScroll: true });
  }
}
{ const q = new URLSearchParams(location.search); if (q.get('lanes')) q.get('lanes').split(',').forEach((k) => { if (k in lanesOn) lanesOn[k] = true; }); }
window.addEventListener('hashchange', go);
window.addEventListener('resize', () => charts.forEach((c) => c.resize()));
if (!location.hash) history.replaceState(null, '', location.pathname + location.search + '#/schedule'); // the first screen is today's schedule
go();
initScribe();
window.__nmg = { data, R };
