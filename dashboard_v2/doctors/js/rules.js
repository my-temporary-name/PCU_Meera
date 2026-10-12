// The NMG Lite rules, one function per domain, every result tagged with its rule ID (doctors_bands_encoded.md).
// Pure: no DOM, no network. It runs in the browser and in node (tests/run_rules.mjs). It never combines the domain signals into one colour.
//
// Kinds: G guideline threshold, B NMG Lite operational band (not a diagnostic criterion), F formula, D definition or state, S suggestion.

export const RULES = {
  A1: ['anthropometry', 'green', 'B', 'BMI under 23, and WHtR under 0.50, and WHR at or under 0.90 (men) or 0.80 (women). All three must hold.'],
  A2: ['anthropometry', 'amber', 'B', 'BMI 23 to 24.9, and/or WHtR 0.50 to 0.54, and/or WHR above 0.90 (men) or 0.80 (women).'],
  A3: ['anthropometry', 'red', 'G', 'BMI 25 or more, and/or waist 90 cm or more (men) or 80 cm or more (women), and/or WHtR 0.55 or more.'],
  A4: ['anthropometry', 'rule', 'B', 'When criteria disagree, the worst signal wins (Red over Amber over Green). This is an assumption, not stated in the document.'],
  A5: ['anthropometry', 'how', 'F', 'Waist at the midpoint between the last palpable rib and the iliac crest; hip at the widest point; BMI = kg/m²; WHR = waist/hip; WHtR = waist/height.'],
  G1: ['glycemia', 'green', 'G', 'FPG under 100 mg/dL and HbA1c under 5.7%.'],
  G2: ['glycemia', 'amber', 'G', 'ADA prediabetes range: FPG 100 to 125, and/or HbA1c 5.7 to 6.4, and/or 2-hour OGTT glucose 140 to 199.'],
  G3: ['glycemia', 'amber', 'B', 'Higher attention within prediabetes: FPG 110 or more and/or HbA1c 6.0 or more. Attention values, not ADA thresholds.'],
  G4: ['glycemia', 'red', 'G', 'Known diabetes, or an ADA diabetes-range result needing confirmation: FPG 126 or more, HbA1c 6.5 or more, or OGTT 2-hour 200 or more.'],
  G5: ['glycemia', 'rule', 'G', 'A diagnosis without unequivocal hyperglycemia needs two abnormal results. Not needed here: the diagnosis is established.'],
  G6: ['glycemia', 'rule', 'D', 'An ordinary postprandial glucose is not the OGTT 2-hour value. Every derived 2-hour value is labelled "from CGM, not OGTT".'],
  L1: ['lipids', 'green', 'B', 'TG under 150; HDL-C not low (under 40 men, under 50 women); TG/HDL-C under 2.0; LDL-C at the individual goal.'],
  L2: ['lipids', 'amber', 'B', 'TG 150 or more and/or low HDL-C; TG/HDL-C 2.0 to under 3.0; LDL-C above the individual goal and/or raised non-HDL-C or apoB.'],
  L3: ['lipids', 'red', 'B', 'Marked or worsening dyslipidemia; TG/HDL-C 3.0 or more; LDL-C persistently above goal despite management; other significant atherogenic burden.'],
  L4: ['lipids', 'ref', 'G', 'ADA 2026 LDL-C goal: under 70 mg/dL for diabetes aged 40 to 75 at higher cardiovascular risk; under 55 with established ASCVD.'],
  L5: ['lipids', 'ref', 'G', 'Lp(a) 125 nmol/L or 50 mg/dL or more is risk-enhancing; measure at least once in adulthood; not serially monitored.'],
  L6: ['lipids', 'formula', 'F', 'non-HDL-C = total cholesterol minus HDL-C; TG/HDL-C = TG / HDL-C in mg/dL.'],
  K1: ['kidney', 'green', 'G', 'UACR under 30 mg/g; eGFR 90 or more, or 60 to 89 without another kidney-damage marker.'],
  K2: ['kidney', 'amber', 'B', 'Persistent UACR 30 to 299 and/or meaningful eGFR decline.'],
  K3: ['kidney', 'red', 'G', 'eGFR under 60 and/or UACR 300 or more, especially persistent or progressive.'],
  K4: ['kidney', 'rule', 'G', 'CKD needs abnormal structure or function for at least 3 months. eGFR 60 to 89 alone does not establish CKD.'],
  P1: ['activity', 'green', 'G', 'IPAQ moderate or high category (official criteria).'],
  P2: ['activity', 'amber', 'B', 'IPAQ low category and/or increasing sedentary time.'],
  P3: ['activity', 'red', 'B', 'Persistently low activity with high sedentary exposure plus metabolic deterioration.'],
  M1: ['lifestyle', 'green', 'B', 'No tobacco; sleep of at least 7 hours; no major modifier identified.'],
  M2: ['lifestyle', 'amber', 'B', 'Tobacco or substance exposure, sleep under 7 hours, strong family history, PCOS, prior gestational diabetes, adverse occupational pattern, or another relevant modifier.'],
  M3: ['lifestyle', 'red', 'B', 'Multiple major modifiers occurring with significant metabolic or organ abnormalities.'],
  N1: ['bp', 'none', 'D', 'Blood pressure: the document lists it in section 1 but gives no Green, Amber or Red row. Values, trend and treatment are shown without a colour.'],
  N2: ['liver', 'none', 'D', 'Liver: the document asks to keep the ALT and AST trend and any documented imaging or diagnosis, but gives no band. MASLD needs documented steatosis plus a cardiometabolic risk factor.'],
  S1: ['state', 'state', 'D', 'Lower metabolic risk: no major risk factor and glycemia below the prediabetes range.'],
  S2: ['state', 'state', 'D', 'Increased metabolic risk: normal glycemia with central adiposity or overweight, family history, hypertension, dyslipidemia, inactivity, PCOS, MASLD or CVD. Not prediabetes.'],
  S3: ['state', 'state', 'G', 'Prediabetes: HbA1c 5.7 to 6.4, FPG 100 to 125, or 2-hour OGTT 140 to 199.'],
  S4: ['state', 'state', 'G', 'Type 2 diabetes: established or new by ADA criteria, then described by treatment, glycemic trajectory, complications and organ involvement.'],
  X1: ['extra', 'formula', 'F', 'Estimated HbA1c (%) = 0.017 × fructosamine (µmol/L) + 1.61. An HbA1c equivalent, not an ADA conversion; does not replace a reliable HbA1c.'],
  X2: ['extra', 'ref', 'G', 'Fructosamine reference interval depends on the assay (Mayo 200 to 285 µmol/L; ARIC community sample 194.8 to 258.0). Use the reporting laboratory\'s interval.'],
  X3: ['extra', 'formula', 'F', 'HOMA1-IR = fasting insulin × fasting glucose (mg/dL) / 405. No universal cutoff: the value is kept with its inputs and no threshold is applied.'],
  X4: ['extra', 'definition', 'D', 'PCOS (adults): at least two of hyperandrogenism, ovulatory dysfunction, polycystic ovarian morphology (or AMH), after excluding other causes.'],
  X5: ['extra', 'principle', 'D', 'TG/HDL-C describes an insulin-resistant phenotype; LDL-C, non-HDL-C, apoB and Lp(a) describe atherogenic particle burden. Complementary, not interchangeable.'],
  F1: ['followup', 'row', 'S', 'Lower metabolic risk, normal screening: routine preventive care; repeat diabetes screening at least every 3 years.'],
  F2: ['followup', 'row', 'S', 'Increased metabolic risk without prediabetes: about every 6 to 12 months; sooner if worsening.'],
  F3: ['followup', 'row', 'S', 'Prediabetes: about every 6 to 12 months (3 to 6 months if very high risk); test for progression at least yearly.'],
  F4: ['followup', 'row', 'S', 'Stable type 2 diabetes at individual goals: about every 3 to 6 months; glycemic status at least twice a year.'],
  F5: ['followup', 'row', 'S', 'Type 2 diabetes not at goal or recent treatment change: about every 1 to 3 months; glycemic status about every 3 months.'],
  F6: ['followup', 'row', 'S', 'Medication start or titration, insulin adjustment, symptomatic hyperglycemia, recurrent hypoglycemia, acute illness: days to 4 weeks by urgency.'],
  F7: ['followup', 'row', 'S', 'Lipid-lowering therapy started or changed: recheck lipids 4 to 12 weeks after a change, then yearly when stable; Lp(a) once in adulthood.'],
  F8: ['followup', 'row', 'S', 'Diabetes without established CKD: eGFR and UACR at least yearly.'],
  F9: ['followup', 'row', 'S', 'Established CKD: eGFR and UACR 1 to 4 times a year by stage.'],
};

export const DOMAINS = [
  ['anthropometry', 'Anthropometry'], ['glycemia', 'Glycemia'], ['bp', 'Blood pressure'], ['lipids', 'Lipids'],
  ['kidney', 'Kidney'], ['liver', 'Liver'], ['activity', 'Physical activity'], ['lifestyle', 'Lifestyle and modifiers'],
];
const ORDER = { red: 3, amber: 2, green: 1 };

// ---- small helpers ---------------------------------------------------------------------------------------------------------------------------------------------
export const utc = (s) => Date.UTC(+s.slice(0, 4), +s.slice(5, 7) - 1, +s.slice(8, 10));
export const iso = (t) => new Date(t).toISOString().slice(0, 10);
export const daysBetween = (a, b) => Math.round((utc(b) - utc(a)) / 864e5);
export function addMonths(s, n) {
  const y = +s.slice(0, 4), m = +s.slice(5, 7) - 1 + n, day = +s.slice(8, 10);
  const last = new Date(Date.UTC(y, m + 1, 0)).getUTCDate();
  return iso(Date.UTC(y, m, Math.min(day, last)));
}
const num = (x) => (typeof x === 'number' && !Number.isNaN(x) ? x : null);
const L = (data, k) => (data.vars[k] ? num(data.vars[k].latest.v) : null);
const D = (data, k) => (data.vars[k] ? data.vars[k].latest.d : null);
const fmt = (x, d = 2) => (x == null ? 'not recorded' : Number(x).toFixed(d));
const f = (data, k) => { const v = data.vars[k]; return v ? Number(v.latest.v).toFixed(v.dec) : 'not recorded'; };

function goal(data, domain) {
  const g = data.standing.goals.find((x) => x.domain.toLowerCase() === domain.toLowerCase());
  if (!g) return null;
  const m = /(\d+(?:\.\d+)?)(?:\/(\d+))?/.exec(g.target);
  return m ? { value: +m[1], value2: m[2] ? +m[2] : null, text: g.target, b: g.b, rule: g.rationale } : null;
}
export const goalOf = goal;

function worst(trace) {
  const hit = trace.filter((t) => t.met && ORDER[t.signal]);
  if (!hit.length) return null;
  const top = Math.max(...hit.map((t) => ORDER[t.signal]));
  return hit.filter((t) => ORDER[t.signal] === top);
}

function result(data, id, name, trace, extra = {}) {
  const w = worst(trace);
  const signal = extra.signal ?? (w ? w[0].signal : 'none');
  const rules = extra.rules ?? (w ? [...new Set(w.map((t) => t.rule))] : []);
  const also = [...new Set(trace.filter((t) => t.met && ORDER[t.signal] && (!w || ORDER[t.signal] < ORDER[w[0].signal])).map((t) => t.rule))];
  return { id, name, signal, rules, also, trace, notes: [], ...extra, headline: extra.headline ?? '' };
}

// ---- domains --------------------------------------------------------------------------------------------------------------------------------------------------
function anthropometry(data, sex) {
  const bmi = L(data, 'bmi'), waist = L(data, 'waist'), whr = L(data, 'whr'), whtr = L(data, 'whtr');
  const male = sex === 'male', waistCut = male ? 90 : 80, whrCut = male ? 0.9 : 0.8;
  const t = [];
  const add = (rule, signal, label, value, met) => t.push({ rule, signal, label, value, met });
  add('A3', 'red', 'BMI 25 or more', bmi == null ? 'not recorded' : `BMI ${fmt(bmi)}`, bmi != null && bmi >= 25);
  add('A3', 'red', `Waist ${waistCut} cm or more`, waist == null ? 'not recorded' : `waist ${fmt(waist, 1)} cm`, waist != null && waist >= waistCut);
  add('A3', 'red', 'WHtR 0.55 or more', whtr == null ? 'not recorded' : `WHtR ${fmt(whtr, 3)}`, whtr != null && whtr >= 0.55);
  add('A2', 'amber', 'BMI 23 to 24.9', bmi == null ? 'not recorded' : `BMI ${fmt(bmi)}`, bmi != null && bmi >= 23 && bmi < 25);
  add('A2', 'amber', 'WHtR 0.50 to 0.54', whtr == null ? 'not recorded' : `WHtR ${fmt(whtr, 3)}`, whtr != null && whtr >= 0.5 && whtr < 0.55);
  add('A2', 'amber', `WHR above ${whrCut.toFixed(2)}`, whr == null ? 'not recorded' : `WHR ${fmt(whr, 3)}`, whr != null && whr > whrCut);
  add('A1', 'green', 'BMI under 23, WHtR under 0.50 and WHR at or under ' + whrCut.toFixed(2), 'all three', bmi != null && whtr != null && whr != null && bmi < 23 && whtr < 0.5 && whr <= whrCut);
  const missing = [bmi, whtr, whr].some((x) => x == null);
  const r = result(data, 'anthropometry', 'Anthropometry', t, { headline: `BMI ${fmt(bmi)} · waist ${fmt(waist, 1)} cm · WHtR ${fmt(whtr, 3)} · WHR ${fmt(whr, 3)}` });
  if (r.signal === 'green' && missing) { r.signal = 'none'; r.notes.push('Some measures are not recorded, so no Green is given.'); }
  r.notes.push('A4: when criteria disagree the worst signal wins. This is an assumption in the pack, not stated in the document.');
  return r;
}

function glycemia(data) {
  const known = data.standing.conds.find((c) => /type 2 diabetes/i.test(c.name) && /active/i.test(c.status));
  const a1c = L(data, 'hba1c'), fpg = L(data, 'fpg');
  const t = [];
  t.push({ rule: 'G4', signal: 'red', label: 'Known diabetes', value: known ? `type 2 diabetes since ${known.date}` : 'no diagnosis recorded', met: !!known });
  t.push({ rule: 'G4', signal: 'red', label: 'HbA1c 6.5% or more', value: a1c == null ? 'not recorded' : `HbA1c ${fmt(a1c, 1)}%`, met: a1c != null && a1c >= 6.5 });
  t.push({ rule: 'G4', signal: 'red', label: 'FPG 126 mg/dL or more', value: fpg == null ? 'not recorded' : `FPG ${fmt(fpg, 0)}`, met: fpg != null && fpg >= 126 });
  t.push({ rule: 'G4', signal: 'red', label: '2-hour OGTT glucose 200 or more', value: 'not recorded (no OGTT)', met: false });
  t.push({ rule: 'G3', signal: 'amber', label: 'Higher attention within prediabetes: FPG 110 or more, or HbA1c 6.0 or more', value: a1c == null && fpg == null ? 'not recorded' : `HbA1c ${fmt(a1c, 1)}, FPG ${fmt(fpg, 0)}`, met: !known && ((fpg != null && fpg >= 110 && fpg < 126) || (a1c != null && a1c >= 6 && a1c < 6.5)) });
  t.push({ rule: 'G2', signal: 'amber', label: 'Prediabetes range: FPG 100 to 125 or HbA1c 5.7 to 6.4', value: a1c == null && fpg == null ? 'not recorded' : `HbA1c ${fmt(a1c, 1)}, FPG ${fmt(fpg, 0)}`, met: !known && ((fpg != null && fpg >= 100 && fpg < 126) || (a1c != null && a1c >= 5.7 && a1c < 6.5)) });
  t.push({ rule: 'G1', signal: 'green', label: 'FPG under 100 and HbA1c under 5.7', value: `HbA1c ${fmt(a1c, 1)}, FPG ${fmt(fpg, 0)}`, met: !known && fpg != null && a1c != null && fpg < 100 && a1c < 5.7 });
  const g = goal(data, 'HbA1c');
  const r = result(data, 'glycemia', 'Glycemia', t, { headline: `HbA1c ${fmt(a1c, 1)}% · fasting glucose ${fmt(fpg, 0)} mg/dL` });
  r.goal = g ? { text: g.text, value: g.value, b: g.b } : null;
  r.aboveGoal = g && a1c != null ? a1c > g.value : null;
  if (known) r.notes.push('G4 is Red for every person with known diabetes, so on its own it carries no information about control. HbA1c is shown against her goal, and the CGM figures beside it. CGM never gives a colour (G6).');
  if (r.signal === 'none') r.notes.push('No diagnosis and no lab result: no colour is given from CGM alone.');
  return r;
}

function bp(data) {
  const g = goal(data, 'Blood pressure');
  const home = data.bp, clinic = data.vars.bp_clinic_sys && data.vars.bp_clinic_dia ? { sys: L(data, 'bp_clinic_sys'), dia: L(data, 'bp_clinic_dia'), d: D(data, 'bp_clinic_sys') } : null;
  const r = result(data, 'bp', 'Blood pressure', [], {
    signal: 'none', rules: ['N1'],
    headline: `Home ${home.last.sys}/${home.last.dia} · clinic ${clinic ? clinic.sys + '/' + clinic.dia : 'not recorded'} · 28-day home mean ${home.mean_last28[0]}/${home.mean_last28[1]}`,
  });
  r.goal = g ? { text: g.text, sys: g.value, dia: g.value2, b: g.b } : null;
  if (g) {
    r.aboveGoalLatest = home.last.sys >= g.value || home.last.dia >= g.value2;
    r.aboveGoalMean = home.mean_last28[0] >= g.value || home.mean_last28[1] >= g.value2;
  }
  r.notes.push('N1: the document has no Green, Amber or Red row for blood pressure. Values, trend, goal and treatment are shown without a colour.');
  return r;
}

function lipids(data, sex) {
  const tg = L(data, 'tg'), hdl = L(data, 'hdl'), ldl = L(data, 'ldl'), r = L(data, 'tg_hdl'), apob = L(data, 'apob');
  const lowHdl = sex === 'male' ? 40 : 50, gl = goal(data, 'LDL-C');
  const lipidRx = data.standing.meds.find((m) => /lipid/i.test(m.name));
  const treated = !!(lipidRx && /active/i.test(lipidRx.status));
  const t = [];
  const add = (rule, signal, label, value, met) => t.push({ rule, signal, label, value, met });
  add('L3', 'red', 'TG/HDL-C 3.0 or more', r == null ? 'not recorded' : `TG/HDL-C ${fmt(r)}`, r != null && r >= 3);
  add('L3', 'red', 'Marked or worsening dyslipidemia', 'not defined in the document', false);
  add('L3', 'red', 'LDL-C persistently above goal despite management', gl && ldl != null ? `LDL-C ${fmt(ldl, 0)} against goal ${gl.value}; ${treated ? 'treated' : 'no lipid-lowering therapy'}` : 'no goal', false);
  add('L2', 'amber', 'TG 150 mg/dL or more', tg == null ? 'not recorded' : `TG ${fmt(tg, 0)}`, tg != null && tg >= 150);
  add('L2', 'amber', `Low HDL-C (under ${lowHdl})`, hdl == null ? 'not recorded' : `HDL-C ${fmt(hdl, 0)}`, hdl != null && hdl < lowHdl);
  add('L2', 'amber', 'TG/HDL-C 2.0 to under 3.0', r == null ? 'not recorded' : `TG/HDL-C ${fmt(r)}`, r != null && r >= 2 && r < 3);
  add('L2', 'amber', 'LDL-C above the individual goal', gl && ldl != null ? `LDL-C ${fmt(ldl, 0)} against goal ${gl.value}` : 'no goal set', gl && ldl != null && ldl > gl.value);
  add('L2', 'amber', 'Raised non-HDL-C or apoB', apob == null ? 'apoB not recorded; no cutoff defined' : `apoB ${fmt(apob, 0)}; no cutoff defined`, false);
  add('L1', 'green', 'TG under 150, HDL-C not low, TG/HDL-C under 2.0 and LDL-C at goal', 'all four', tg != null && hdl != null && r != null && tg < 150 && hdl >= lowHdl && r < 2 && (!gl || ldl == null || ldl <= gl.value));
  const out = result(data, 'lipids', 'Lipids', t, { headline: `LDL-C ${fmt(ldl, 0)} · TG ${fmt(tg, 0)} · HDL-C ${fmt(hdl, 0)} · TG/HDL-C ${fmt(r)}` });
  out.treatment = treated ? `${lipidRx.name} active` : 'No lipid-lowering therapy';
  out.goal = gl ? { text: gl.text, value: gl.value, b: gl.b } : null;
  out.notes.push('L3 also names "marked or worsening" and "persistently above goal despite management". The document defines none of these, so they are not scored; only the TG/HDL-C ≥ 3.0 clause is.');
  out.notes.push('X5: TG/HDL-C describes an insulin-resistant phenotype; LDL-C, non-HDL-C, apoB and Lp(a) describe atherogenic burden. They are complementary, not interchangeable.');
  return out;
}

function kidney(data) {
  const egfr = L(data, 'egfr'), uacr = L(data, 'uacr');
  const t = [];
  const add = (rule, signal, label, value, met) => t.push({ rule, signal, label, value, met });
  add('K3', 'red', 'eGFR under 60', egfr == null ? 'not recorded' : `eGFR ${fmt(egfr, 1)}`, egfr != null && egfr < 60);
  add('K3', 'red', 'UACR 300 mg/g or more', uacr == null ? 'not recorded' : `UACR ${fmt(uacr, 0)}`, uacr != null && uacr >= 300);
  add('K2', 'amber', 'UACR 30 to 299 mg/g', uacr == null ? 'not recorded' : `UACR ${fmt(uacr, 0)}`, uacr != null && uacr >= 30 && uacr < 300);
  add('K2', 'amber', 'Meaningful eGFR decline', 'not defined in the document', false);
  add('K1', 'green', 'UACR under 30 mg/g and eGFR 60 or more', egfr == null || uacr == null ? 'a value is not recorded' : `eGFR ${fmt(egfr, 1)}, UACR ${fmt(uacr, 0)}`, egfr != null && uacr != null && uacr < 30 && egfr >= 60);
  const out = result(data, 'kidney', 'Kidney', t, { headline: `eGFR ${fmt(egfr, 1)} · creatinine ${f(data, 'creat')} mg/dL · UACR ${uacr == null ? 'not recorded' : fmt(uacr, 0) + ' mg/g'}` });
  if (uacr == null && egfr != null) { out.signal = 'none'; out.rules = []; out.notes.push('UACR not recorded, so no Green is given.'); }
  if (out.signal === 'amber') out.notes.push('K4: CKD needs abnormal results for at least 3 months, so a single abnormal UACR should be repeated.');
  out.notes.push('K2 names a "meaningful eGFR decline" and a "persistent" UACR; the document defines neither, so the decline is not scored.');
  return out;
}

function liver(data) {
  const masld = data.standing.conds.find((c) => /MASLD|steatosis/i.test(c.name));
  const us = data.standing.imaging.find((i) => /ultrasound/i.test(i.modality));
  const r = result(data, 'liver', 'Liver', [], { signal: 'none', rules: ['N2'], headline: `ALT ${f(data, 'alt')} · AST ${f(data, 'ast')} · GGT ${f(data, 'ggt')} U/L${us ? ' · grade 1 steatosis on ultrasound ' + us.d : ''}` });
  r.masld = masld ? { date: masld.date, b: masld.b } : null;
  r.notes.push('N2: the document has no band for the liver. The ALT and AST trend and the documented imaging and diagnosis are shown without a colour. MASLD needs documented steatosis plus a cardiometabolic risk factor; abnormal ALT or AST alone does not establish it. The steatosis index is an index, not a diagnosis.');
  return r;
}

function activity(data) {
  const ip = data.ipaq.length ? data.ipaq[data.ipaq.length - 1] : null;
  const low = data.ipaq.filter((x) => x.category === 'low').length;
  const t = [];
  t.push({ rule: 'P2', signal: 'amber', label: 'IPAQ low category', value: ip ? `IPAQ ${ip.category}, ${ip.met} MET-min/week on ${ip.d}` : 'no IPAQ entry', met: !!ip && ip.category === 'low' });
  t.push({ rule: 'P2', signal: 'amber', label: 'Increasing sedentary time', value: data.vars.sedentary?.direction ? `sedentary ${data.vars.sedentary.direction.dir} against her baseline` : 'not available', met: data.vars.sedentary?.direction?.dir === 'up' });
  t.push({ rule: 'P3', signal: 'red', label: 'Persistently low activity with high sedentary exposure plus metabolic deterioration', value: ip ? `${low} of ${data.ipaq.length} IPAQ entries low; sedentary ${(data.derived.sedentary.median / 60).toFixed(1)} h/day` : 'no IPAQ entry', met: false });
  t.push({ rule: 'P1', signal: 'green', label: 'IPAQ moderate or high', value: ip ? `IPAQ ${ip.category}` : 'no IPAQ entry', met: !!ip && (ip.category === 'moderate' || ip.category === 'high') });
  const out = result(data, 'activity', 'Physical activity', t, { headline: ip ? `IPAQ ${ip.category} (${ip.met} MET-min/week) · median ${data.derived.steps.median.toLocaleString('en-US')} steps/day · ${(data.derived.sedentary.median / 60).toFixed(1)} h sedentary` : `Median ${data.derived.steps.median} steps/day` });
  if (!ip) { out.signal = 'notcomputed'; out.rules = []; out.notes.push('Not computed: there is no IPAQ entry. Steps and sedentary time are shown as plain values.'); }
  out.notes.push('P3 needs the doctors\' definitions of "persistently", "high" and "deterioration". Without them it is not scored and the signal stays Amber (default Q6, Q10).');
  out.notes.push('Wearable steps are low and the IPAQ is low; they agree.');
  return out;
}

function lifestyle(data) {
  const sleep = data.derived.sleep;
  const fam = data.standing.fam.find((x) => /type 2 diabetes/i.test(x.condition));
  const occ = data.standing.life.find((x) => /occupational pattern/i.test(x.domain));
  const masld = data.standing.conds.find((c) => /MASLD/i.test(c.name) && /active/i.test(c.status));
  const peri = data.standing.conds.find((c) => /perimenopause/i.test(c.name) && /active/i.test(c.status));
  const pcos = data.standing.conds.find((c) => /polycystic/i.test(c.name));
  const gdm = data.standing.conds.find((c) => /gestational/i.test(c.name));
  const tobacco = data.standing.life.find((x) => x.domain === 'Tobacco');
  const alcohol = data.standing.life.find((x) => x.domain === 'Alcohol');
  const mods = [];
  if (sleep.last7 < 7) mods.push({ name: 'Sleep under 7 hours', detail: `7-night average ${sleep.last7} h; year median ${sleep.median_year} h`, b: 'data' });
  if (fam) mods.push({ name: 'First-degree family history of type 2 diabetes', detail: `${fam.relative}, onset ${fam.onset}`, b: fam.b });
  if (occ && /adverse/i.test(occ.value)) mods.push({ name: 'Adverse occupational pattern', detail: occ.detail, b: occ.b });
  if (masld) mods.push({ name: 'MASLD', detail: `documented ${masld.date}`, b: masld.b });
  if (peri) mods.push({ name: 'Perimenopause', detail: `since ${peri.date}`, b: peri.b });
  if (pcos && /active/i.test(pcos.status)) mods.push({ name: 'PCOS', detail: '', b: pcos.b });
  if (gdm && /history|yes|active/i.test(gdm.status) && !/none/i.test(gdm.status)) mods.push({ name: 'Prior gestational diabetes', detail: '', b: gdm.b });
  if (tobacco && !/never/i.test(tobacco.value)) mods.push({ name: 'Tobacco exposure', detail: tobacco.value, b: tobacco.b });
  const t = [];
  t.push({ rule: 'M3', signal: 'red', label: 'Multiple major modifiers with significant metabolic or organ abnormalities', value: `${mods.length} modifiers recorded; "multiple" and "major" are not defined`, met: false });
  t.push({ rule: 'M2', signal: 'amber', label: 'Any relevant modifier recorded', value: mods.length ? mods.map((m) => m.name).join('; ') : 'none recorded', met: mods.length > 0 });
  t.push({ rule: 'M1', signal: 'green', label: 'No tobacco, sleep of at least 7 hours and no major modifier', value: mods.length ? 'not met' : 'met', met: mods.length === 0 && sleep.last7 >= 7 });
  const out = result(data, 'lifestyle', 'Lifestyle and modifiers', t, { headline: `${mods.length} modifiers recorded · sleep ${sleep.last7} h (7-night average) · ${tobacco ? tobacco.value : 'tobacco not recorded'}` });
  out.modifiers = mods;
  out.context = [alcohol && { name: 'Alcohol', detail: `${alcohol.value}; ${data.derived.alcohol_dates.length} diary entries in the data year` }, { name: 'PCOS', detail: pcos ? pcos.status : 'not recorded' }, { name: 'Gestational diabetes history', detail: gdm ? gdm.status : 'not recorded' }].filter(Boolean);
  out.notes.push('Only recorded modifiers are counted. Occasional social alcohol is shown as context and not counted.');
  out.notes.push('If M3 were read literally ("multiple major modifiers" with MASLD and obesity present) this domain would read Red. The document does not define "multiple" or "major", so it stays Amber (default Q10).');
  return out;
}

// ---- state, follow-up, notices ---------------------------------------------------------------------------------------------------------------------
function state(data, doms) {
  const known = data.standing.conds.find((c) => /type 2 diabetes/i.test(c.name) && /active/i.test(c.status));
  if (known) return { rule: 'S4', name: 'Type 2 diabetes', since: known.date, text: RULES.S4[3] };
  const a1c = L(data, 'hba1c'), fpg = L(data, 'fpg');
  if ((a1c != null && a1c >= 5.7) || (fpg != null && fpg >= 100)) return { rule: 'S3', name: 'Prediabetes', since: null, text: RULES.S3[3] };
  const risk = doms.some((d) => (d.id === 'anthropometry' || d.id === 'lipids') && (d.signal === 'amber' || d.signal === 'red'));
  return risk ? { rule: 'S2', name: 'Increased metabolic risk', since: null, text: RULES.S2[3] } : { rule: 'S1', name: 'Lower metabolic risk', since: null, text: RULES.S1[3] };
}

function followup(data, st) {
  const asOf = data.meta.as_of, rows = [];
  const due = (last, months, label, rule, note) => {
    const next = addMonths(last, months), n = daysBetween(asOf, next);
    return { rule, label, last, next, days: n, text: n >= 0 ? `due in ${n} days` : `overdue by ${-n} days`, note };
  };
  const a1c = data.vars.hba1c, g = goal(data, 'HbA1c');
  let main = null;
  if (st.rule === 'S4') {
    if (g && a1c) {
      const atGoal = a1c.latest.v <= g.value;
      main = { ...due(a1c.latest.d, atGoal ? 6 : 3, 'HbA1c review', atGoal ? 'F4' : 'F5', `HbA1c ${a1c.latest.v} against goal ${g.text}${atGoal ? '' : '; no treatment change in the data year'}`), goal: g };
    } else main = { rule: null, label: 'HbA1c review', note: 'No HbA1c goal is recorded, so no follow-up row is chosen.' };
  } else if (st.rule === 'S3') main = { rule: 'F3', label: 'Test for progression to diabetes', note: 'at least yearly' };
  else if (st.rule === 'S2') main = { rule: 'F2', label: 'Reassess weight, waist, blood pressure and lifestyle', note: 'about every 6 to 12 months' };
  else main = { rule: 'F1', label: 'Routine preventive care', note: 'repeat diabetes screening at least every 3 years' };
  rows.push(main);
  if (st.rule === 'S4') {
    const eg = data.vars.egfr?.latest.d, ua = data.vars.uacr?.latest.d;
    if (eg && ua) rows.push(due([eg, ua].sort()[0], 12, 'eGFR and UACR', 'F8', `last eGFR ${eg}, last UACR ${ua}`));
    else rows.push({ rule: 'F8', label: 'eGFR and UACR', note: ua ? 'eGFR not recorded' : 'UACR not recorded: a yearly check cannot be dated' });
  }
  const lp = data.vars.lpa;
  rows.push({ rule: 'L5', label: 'Lp(a)', note: lp ? `measured once in adulthood (${lp.latest.d}); not serially monitored` : 'not recorded: the document asks for one measurement in adulthood' });
  const lipDate = data.vars.ldl?.latest.d;
  rows.push({ rule: 'F7', label: 'Lipid panel', note: `last panel ${lipDate}. The document gives a recheck interval only after a lipid-lowering therapy is started or changed (4 to 12 weeks), and none has been.` });
  return rows;
}

function notices(data) {
  const gap = data.gmi_gap.filter((x) => x.b === 'data');
  const a1cs = gap.map((x) => x.hba1c), gmis = gap.map((x) => x.gmi);
  const min = (a) => Math.min(...a), max = (a) => Math.max(...a);
  const frs = data.series.fructosamine || [];
  const below = data.cgm.readings_below_70;
  const labDates = new Set();
  for (const k of ['hba1c', 'fpg', 'ldl', 'tg', 'egfr', 'alt']) (data.series[k] || []).forEach(([d]) => { if (d >= '2025-09-15') labDates.add(d); });
  const labBG = [...labDates].filter((d) => (data.series.hba1c || []).some(([x, , b]) => x === d && b !== 'data'));
  return [
    { id: 1, title: 'HbA1c and CGM differ', text: `Lab HbA1c ${min(a1cs)} to ${max(a1cs)}% against a CGM-based estimate (GMI) of ${min(gmis)} to ${max(gmis)}% and ${data.cgm.year.tir}% time in range. Fructosamine (${frs.length ? min(frs.map((x) => x[1])) + ' to ' + max(frs.map((x) => x[1])) : 'not recorded'} µmol/L) follows the CGM. Possible glycation gap: HbA1c reads higher than glucose monitoring (document reference 22).` },
    { id: 2, title: `${below.length} readings of 65.0 mg/dL are isolated sensor artifacts`, text: `They are not hypoglycemia and are not counted as events (${below.map((x) => x[0].slice(0, 10)).join(', ')}). The cleaned glucose series has no real reading under 70 or under 54.` },
    { id: 3, title: 'Activity data conflict', text: `Wearable steps are low (median ${data.derived.steps.median.toLocaleString('en-US')} a day) and the IPAQ is low.` },
    { id: 4, title: 'Only a few lab dates exist in the data year', text: `${labDates.size} lab dates from 15 Sep 2025 to 17 Sep 2026. Always read each value with its date.` },
  ];
}

export function evaluate(data) {
  const sex = (data.standing.sex.sex || 'female').toLowerCase();
  const doms = [anthropometry(data, sex), glycemia(data), bp(data), lipids(data, sex), kidney(data), liver(data), activity(data), lifestyle(data)];
  const st = state(data, doms);
  return { sex, domains: doms, state: st, followup: followup(data, st), notices: notices(data) };
}

export const SENTENCE = 'Green, Amber and Red are domain-specific clinical-attention signals from NMG Lite. They are not diagnostic criteria and not a validated composite risk score.';
