// Predictions and recommendations. Pure logic over the loaded data; no model, no network.
// A prediction extends HER OWN readings with a straight line (ordinary least squares) and shows an 80 percent range; two more lines show what happens if she
// returns to her best level, or keeps worsening at the fastest pace seen between two of her own readings. A recommendation is a suggestion built from the
// NMG Lite rules, the clinic's goals and her record. Both are decision support for the clinician, never a diagnosis or a risk score.
import { goalOf, daysBetween, iso, utc } from './rules.js';

// key, what is worse, how far ahead, how far back to fit, daily series are averaged by week first
export const PRED = [
  { key: 'hba1c', worse: 'up', ahead: 180, back: 730, label: 'HbA1c' },
  { key: 'fpg', worse: 'up', ahead: 180, back: 730, label: 'Fasting glucose' },
  { key: 'cgm_mean', worse: 'up', ahead: 90, back: 120, daily: true, label: 'Average glucose (CGM)' },
  { key: 'ldl', worse: 'up', ahead: 180, back: 730, label: 'LDL-C' },
  { key: 'tg', worse: 'up', ahead: 180, back: 730, label: 'Triglycerides' },
  { key: 'hdl', worse: 'down', ahead: 180, back: 730, label: 'HDL-C' },
  { key: 'bp_clinic_sys', worse: 'up', ahead: 180, back: 730, label: 'Blood pressure (clinic, systolic)' },
  { key: 'weight', worse: 'up', ahead: 180, back: 548, label: 'Weight' },
  { key: 'egfr', worse: 'down', ahead: 365, back: 1095, label: 'eGFR' },
  { key: 'alt', worse: 'up', ahead: 180, back: 730, label: 'ALT' },
  { key: 'sleep', worse: 'down', ahead: 60, back: 90, daily: true, label: 'Sleep' },
];
export const PRED_DOMAIN = { hba1c: 'glycemia', fpg: 'glycemia', cgm_mean: 'glycemia', ldl: 'lipids', tg: 'lipids', hdl: 'lipids', bp_clinic_sys: 'bp', weight: 'anthropometry', egfr: 'kidney', alt: 'liver', sleep: 'lifestyle' };

const T80 = [0, 0, 1.89, 1.64, 1.53, 1.48, 1.44, 1.41, 1.4];
const RANK = { green: 0, amber: 1, red: 2 };
const SIGNAL_WORD = { green: 'Green', amber: 'Amber', red: 'Red' };
const asOfDate = (ctx) => ctx.asOf;
const addDays = (s, n) => iso(utc(s) + n * 864e5);
const fix = (x, d) => Number(x).toLocaleString('en-US', { minimumFractionDigits: d, maximumFractionDigits: d });
const MON = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];
const dfmt = (s) => `${+s.slice(8, 10)} ${MON[+s.slice(5, 7) - 1]} ${s.slice(0, 4)}`;
const mfmt = (s) => `${MON[+s.slice(5, 7) - 1]} ${s.slice(0, 4)}`;

function bandAt(zones, v) { for (const z of zones) if ((z.from == null || v >= z.from) && (z.to == null || v < z.to)) return z.signal; return null; }
const bandRange = (zones, sig) => { const z = zones.find((q) => q.signal === sig); if (!z) return ''; return z.from == null ? `below ${z.to}` : z.to == null ? `${z.from} and above` : `${z.from} to ${z.to}`; };

// the points used for a fit: [x = days from today (negative), y, date]
function fitPoints(ctx, cfg) {
  const asOf = ctx.asOf, raw = (ctx.data.series[cfg.key] || []).filter((p) => daysBetween(p[0], asOf) <= cfg.back && p[0] <= asOf);
  if (!cfg.daily) return raw.map((p) => [daysBetween(asOf, p[0]), p[1], p[0]]);
  const by = new Map();
  raw.forEach((p) => { const i = Math.floor(daysBetween(p[0], asOf) / 7); (by.get(i) || by.set(i, []).get(i)).push(p[1]); });
  return [...by.entries()].sort((a, b) => b[0] - a[0]).map(([i, vs]) => [-(i * 7 + 3), vs.reduce((t, v) => t + v, 0) / vs.length, addDays(asOf, -(i * 7 + 3))]);
}

export function predict(ctx, cfg) {
  const v = ctx.data.vars[cfg.key]; if (!v) return null;
  const pts = fitPoints(ctx, cfg), dec = v.dec, unit = v.unit, n = pts.length;
  const out = { key: cfg.key, label: cfg.label, unit, dec, worse: cfg.worse, n, daily: !!cfg.daily, domain: PRED_DOMAIN[cfg.key], ok: false };
  const last = (ctx.data.series[cfg.key] || []).slice(-1)[0]; if (!last) return null;
  out.now = { d: last[0], v: last[1] };
  const minPts = cfg.daily ? 6 : 4, spanDays = n ? pts[n - 1][0] - pts[0][0] : 0;
  if (n < minPts || spanDays < (cfg.daily ? 28 : 120)) { out.reason = `Only ${n} reading${n === 1 ? '' : 's'} in the fitting window, too few to project.`; return out; }
  const xm = pts.reduce((t, p) => t + p[0], 0) / n, ym = pts.reduce((t, p) => t + p[1], 0) / n;
  let sxx = 0, sxy = 0; pts.forEach((p) => { sxx += (p[0] - xm) ** 2; sxy += (p[0] - xm) * (p[1] - ym); });
  const slope = sxx ? sxy / sxx : 0, icpt = ym - slope * xm;
  const sse = pts.reduce((t, p) => t + (p[1] - (icpt + slope * p[0])) ** 2, 0), s = Math.sqrt(sse / Math.max(1, n - 2)), t = T80[Math.min(n, 8)] || 1.4;
  const tol = v.direction && v.direction.tol != null ? v.direction.tol : Math.abs(out.now.v) * 0.03;
  if (cfg.daily) { out.now = { d: asOfDate(ctx), v: pts[n - 1][1] }; out.nowLabel = 'Now (7-day mean)'; }
  const H = cfg.ahead, anchor = out.now.v, base = out.now.d;
  const half = (x) => t * s * Math.sqrt(1 + 1 / n + (x - xm) ** 2 / (sxx || 1));
  // the best level in the window and the fastest adverse step between two of her own readings (at least 4 weeks apart for labs, 1 week for weekly means)
  const ys = pts.map((p) => p[1]), best = cfg.worse === 'up' ? Math.min(...ys, anchor) : Math.max(...ys, anchor);
  let worstRate = 0; const gap = cfg.daily ? 7 : 28;
  for (let i = 0; i < n; i++) for (let j = i + 1; j < n; j++) { const dx = pts[j][0] - pts[i][0]; if (dx < gap) continue; const r = (pts[j][1] - pts[i][1]) / dx * (cfg.worse === 'up' ? 1 : -1); if (r > worstRate) worstRate = r; }
  const spread = Math.max(...ys) - Math.min(...ys), capRate = spread / H, rateSlip = Math.min(Math.max(worstRate, Math.abs(slope)), Math.max(capRate, Math.abs(slope))); // never beyond the spread of her own readings
  // gentle curves instead of straight lines: the current pace eases off a little over time, a return to her best starts quickly and settles, and slipping starts gently, speeds up and then levels
  const steps = 24, proj = [], tau = H * 0.7, dir = cfg.worse === 'up' ? 1 : -1, slipTotal = rateSlip * H;
  const centre = (x) => Math.max(0, anchor + slope * tau * (1 - Math.exp(-x / tau)));
  for (let i = 0; i <= steps; i++) {
    const x = Math.round(H * i / steps), u = x / H, c = centre(x), hw = i === 0 ? 0 : half(x) * Math.sqrt(i / steps); // the range opens from the latest reading
    const imp = anchor + (best - anchor) * (1 - (1 - u) ** 2), slp = Math.max(0, anchor + dir * slipTotal * u * u * (3 - 2 * u));
    proj.push({ d: addDays(base, x), x, c, lo: c - hw, hi: c + hw, imp, slp });
  }
  Object.assign(out, { ok: true, pts, slope, perMonth: slope * 30.4, s, tol, ahead: H, best, rateSlip, proj, end: proj[proj.length - 1], endDate: proj[proj.length - 1].d });
  // history for the chart (all readings in the fitting window)
  out.hist = pts.map((p) => [p[2], p[1]]);
  const zones = ctx.zonesFor(cfg.key), refs = ctx.refsFor(cfg.key);
  out.zones = zones; out.refs = refs;
  out.bandNow = bandAt(zones, anchor); out.bandEnd = bandAt(zones, out.end.c);
  const delta = out.end.c - anchor, adverse = (cfg.worse === 'up' ? delta : -delta);
  out.move = Math.abs(delta) < tol ? 'steady' : adverse > 0 ? 'worse' : 'better';
  // when a threshold is crossed on the central line, within the horizon
  out.cross = null;
  for (const r of refs) { for (let x = 1; x <= H; x++) { const c0 = centre(x - 1), c1 = centre(x); if ((c0 - r.y) * (c1 - r.y) < 0) { if (!out.cross || x < out.cross.x) out.cross = { x, d: addDays(base, x), y: r.y, label: r.label }; break; } } }
  // verdict
  let tone = 'none';
  if (out.bandEnd) tone = out.bandEnd === 'green' ? 'green' : out.bandEnd === 'amber' ? 'amber' : 'red';
  out.tone = tone;
  out.verdict = out.move === 'steady' ? (out.bandEnd === 'green' ? 'okay' : out.bandEnd ? 'watch' : 'steady') : out.move === 'better' ? 'good' : (out.bandEnd === 'green' ? 'watch' : 'bad');
  const f = (x) => `${fix(x, dec)} ${unit}`.trim();
  out.short = out.move === 'steady' ? `Holds near ${f(out.end.c)} to ${mfmt(out.endDate)}` : `${delta > 0 ? 'Rises' : 'Falls'} to about ${f(out.end.c)} by ${mfmt(out.endDate)}`;
  out.range = `${fix(out.end.lo, dec)} to ${fix(out.end.hi, dec)}`;
  // the plain reading, as a few short lines
  const lines = []; const bn = out.bandNow, be = out.bandEnd;
  lines.push(`At her current pace ${cfg.label} goes from ${f(anchor)} (${dfmt(base)}) to about ${f(out.end.c)} by ${dfmt(out.endDate)}; the 80 % range is ${out.range} ${unit}.`.replace(/ +/g, ' '));
  if (out.cross) lines.push(`It would cross ${out.cross.label.replace(/^[A-Z]\d?:\s*/, '')} (${out.cross.label.split(':')[0]}) around ${mfmt(out.cross.d)}.`);
  if (be && bn) lines.push(be === bn ? `It stays in the ${SIGNAL_WORD[be]} band (${bandRange(zones, be)}).` : `It moves from the ${SIGNAL_WORD[bn]} band to the ${SIGNAL_WORD[be]} band (${bandRange(zones, be)}).`);
  out.lines = lines;
  const good = out.verdict === 'good', bad = out.verdict === 'bad';
  if (out.verdict === 'okay') out.why = 'Why this is fine: it holds about where it is, in the Green band.';
  if (out.verdict !== 'okay') out.why = bad ? `Why this is a concern: the value is moving the wrong way${be && be !== 'green' ? ` and ends in the ${SIGNAL_WORD[be]} band` : ''}, so waiting is likely to make it worse.`
    : good ? `Why this is encouraging: the value is moving the right way${be === 'green' ? ' and ends in the Green band' : ''}.`
    : out.verdict === 'watch' ? `Why this needs a look: it is not getting worse, but it is not improving either${be && be !== 'green' ? `, and it stays in the ${SIGNAL_WORD[be]} band` : ''}.`
    : 'It holds about where it is, and no colour band applies to this value.';
  out.scen = [
    { id: 'now', name: 'Continues as now', end: out.end.c, text: `carries on at the pace of her last ${n} readings, easing off a little` },
    { id: 'imp', name: 'Returns to her best', end: out.end.imp, text: `goes back to ${f(best)}, her best reading in the window` },
    { id: 'slp', name: 'Keeps slipping', end: out.end.slp, text: `worsens at the fastest pace seen between two of her own readings, but no further than the spread of her readings in the window (${f(Math.min(...ys))} to ${f(Math.max(...ys))})` },
  ].map((q) => ({ ...q, band: bandAt(zones, q.end) }));
  out.basis = `${n} ${cfg.daily ? 'weekly averages' : 'readings'} from ${dfmt(pts[0][2])} to ${dfmt(pts[n - 1][2])}, straight-line fit. It assumes her current medicines and habits stay the same.`;
  return out;
}

export function predictions(ctx) { return PRED.map((c) => predict(ctx, c)).filter(Boolean); }

// ---- recommendations -----------------------------------------------------------------------------------------------------------------------------------------
// state: negative (needs action), watch (keep an eye), positive (on track). verb: Improve, Reduce, Review, Continue, Stop.
export function recommendations(ctx, preds) {
  const { data, R, asOf } = ctx, V = data.vars, S = data.standing, out = [];
  const lv = (k) => (V[k] ? V[k].latest.v : null), val = (k, d) => (lv(k) == null ? '—' : fix(lv(k), d == null ? V[k].dec : d));
  const goal = (name) => goalOf(data, name);
  const last = S.visits.filter((x) => x.d < asOf).slice(-1)[0], prevLast = S.visits.filter((x) => x.d <= asOf).slice(-1)[0];
  const fu = (r) => R.followup.find((x) => x.rule === r);
  const pr = (k) => preds.find((p) => p.key === k && p.ok);
  const predLine = (k) => { const p = pr(k); return p ? `Projection: ${p.lines[0]}` : null; };
  const dom = (id) => R.domains.find((d) => d.id === id);
  const push = (o) => out.push({ id: `${o.domain}-${out.length}`, ...o, facts: o.facts.filter(Boolean), consider: o.consider.filter(Boolean), source: o.source.filter(Boolean) });
  const adh = Object.entries(data.adherence).map(([id, a]) => [S.meds.find((m) => m.adherence_id === id), a]).filter(([m]) => m);

  // glycemia
  const gH = goal('HbA1c'), a1c = lv('hba1c');
  if (a1c != null && gH) {
    const f5 = fu('F5'), above = a1c > gH.value;
    push({ domain: 'glycemia', state: above ? 'negative' : 'positive', verb: above ? 'Improve' : 'Continue',
      title: above ? `HbA1c ${val('hba1c')} % is above her goal of under ${gH.value.toFixed(1)} %` : `HbA1c ${val('hba1c')} % is within her goal of under ${gH.value.toFixed(1)} %`,
      facts: [`HbA1c ${val('hba1c')} % on ${dfmt(V.hba1c.latest.d)}${V.hba1c.prev ? `; the value before was ${fix(V.hba1c.prev.v, 1)} % on ${dfmt(V.hba1c.prev.d)}` : ''}.`, last && last.decision ? `Last visit (${dfmt(last.d)}): ${last.decision}.` : null, predLine('hba1c')],
      consider: above ? ['Weigh a second glucose-lowering agent against another stretch of lifestyle effort. The last visit deferred the second agent for three months.', f5 && f5.next ? `Re-check HbA1c at the planned review on ${dfmt(f5.next)}.` : null, adh.find(([m]) => /metformin/i.test(m.name)) ? `Check how regularly metformin is taken (${adh.find(([m]) => /metformin/i.test(m.name))[1].last90} % of days in the last 90).` : null] : ['Keep the current plan and the planned HbA1c review.', f5 && f5.next ? `Next HbA1c review: ${dfmt(f5.next)}.` : null],
      source: [{ rule: 'G4' }, { rule: 'F5' }, { text: `Clinic goal: under ${gH.value.toFixed(1)} % (set by the clinic, to be confirmed)` }, last ? { text: `Visit of ${dfmt(last.d)}` } : null] });
  }
  const n1 = R.notices.find((n) => /CGM differ/.test(n.title));
  if (n1) push({ domain: 'glycemia', state: 'watch', verb: 'Review', title: 'HbA1c and glucose monitoring give different pictures',
    facts: [n1.text.replace(/\s*\(document reference \d+\)/, '')], consider: ['Read HbA1c together with the CGM average and fructosamine before changing treatment on HbA1c alone.', 'Note that the lab HbA1c reads higher than the glucose-based estimate (GMI).'], source: [{ rule: 'X2' }, { text: 'Read with the values, notice 1' }] });
  const n2 = R.notices.find((n) => /sensor artifacts/.test(n.title));
  if (n2) push({ domain: 'glycemia', state: 'watch', verb: 'Stop', title: 'Do not count the isolated 65.0 mg/dL readings as low glucose',
    facts: [n2.title + '.', n2.text], consider: ['Leave these readings out when judging time below range; the cleaned series has no real reading under 70.'], source: [{ text: 'Read with the values, notice 2' }] });
  // medicine taking
  const low = adh.filter(([, a]) => a.last90 < 90);
  if (low.length) push({ domain: 'glycemia', state: 'negative', verb: 'Improve', title: 'Some medicines are not taken every day',
    facts: low.map(([m, a]) => `${m.name} ${m.dose}: taken ${a.last90} % of days in the last 90 (${a.year} % over the year).`).concat(['On 17 Sep she noted that medication timing had slipped.']),
    consider: ['Ask what gets in the way (timing, routine, side effects) before changing a dose.', 'Agree one simple cue, such as a fixed time with a meal.'], source: [{ text: 'Adherence record, last 90 days' }, { text: 'Diary of 17 Sep 2026' }] });
  // lipids
  const gL = goal('LDL-C'), ldl = lv('ldl'), noRx = /no lipid/i.test(dom('lipids').treatment || '');
  if (ldl != null && gL) push({ domain: 'lipids', state: ldl > gL.value ? 'negative' : 'positive', verb: ldl > gL.value ? 'Improve' : 'Continue',
    title: ldl > gL.value ? `LDL-C ${val('ldl')} mg/dL is above her goal of under ${gL.value}${noRx ? ', and she is on no lipid-lowering treatment' : ''}` : `LDL-C ${val('ldl')} mg/dL is within her goal of under ${gL.value}`,
    facts: [`LDL-C ${val('ldl')} mg/dL on ${dfmt(V.ldl.latest.d)}; the clinic goal is under ${gL.value} mg/dL for a person with diabetes aged 40 to 75 at higher cardiovascular risk.`, noRx ? 'No lipid-lowering therapy is recorded.' : null, predLine('ldl')],
    consider: ldl > gL.value ? [noRx ? 'Discuss starting lipid-lowering treatment against the goal.' : 'Review the current lipid-lowering treatment against the goal.', 'Recheck the lipid panel 4 to 12 weeks after any start or change.', 'Diet and weight help alongside treatment.'] : ['Keep the current plan.'],
    source: [{ rule: 'L2' }, { rule: 'L3' }, { rule: 'F7' }, { text: `Clinic goal: under ${gL.value} mg/dL (to be confirmed)` }] });
  if (lv('tg') != null && lv('tg') > 150) push({ domain: 'lipids', state: 'negative', verb: 'Reduce', title: `Triglycerides ${val('tg')} mg/dL and TG/HDL-C ${val('tg_hdl', 2)} are above the Green band`,
    facts: [`Triglycerides ${val('tg')} mg/dL (Green is under 150); HDL-C ${val('hdl')} mg/dL; TG/HDL-C ${val('tg_hdl', 2)} (Green is under 2.0).`, predLine('tg')],
    consider: ['Look at what drives triglycerides in her routine: refined carbohydrate, meals, alcohol (occasional use is recorded) and weight.', 'Re-measure with the next panel to see whether it moves.'], source: [{ rule: 'L2' }, { rule: 'L3' }] });
  // blood pressure
  const gB = goal('Blood pressure'), bp = data.bp;
  if (gB && lv('bp_clinic_sys') != null) {
    const cs = lv('bp_clinic_sys'), cd = lv('bp_clinic_dia'), above = cs > gB.value || cd > gB.value2;
    push({ domain: 'bp', state: above ? 'watch' : 'positive', verb: above ? 'Review' : 'Continue', title: above ? `Clinic blood pressure ${cs}/${cd} is above her goal of under ${gB.value}/${gB.value2}` : `Blood pressure ${cs}/${cd} is within her goal`,
      facts: [`Clinic reading ${cs}/${cd} on ${dfmt(V.bp_clinic_sys.latest.d)}.`, `Home readings over the last 28 days average ${bp.mean_last28[0]}/${bp.mean_last28[1]}.`, predLine('bp_clinic_sys')],
      consider: above ? ['Compare home and clinic readings before changing treatment: the home average is lower than the clinic reading.', 'Check how regularly amlodipine is taken.'] : ['Keep the current plan and home monitoring.'], source: [{ rule: 'N1' }, { text: `Clinic goal: under ${gB.value}/${gB.value2} mmHg (to be confirmed)` }] });
  }
  // weight
  const gW = goal('Weight'), w = lv('weight');
  if (w != null) { const m = gW && /(\d+)\s*kg/.exec(gW.text || gW.rule || ''), tgt = m ? +m[1] : 68; push({ domain: 'anthropometry', state: w > tgt + 1 ? 'negative' : 'positive', verb: w > tgt + 1 ? 'Reduce' : 'Continue',
    title: w > tgt + 1 ? `Weight ${val('weight')} kg is about ${fix(w - tgt, 0)} kg above her goal of ${tgt} kg` : `Weight ${val('weight')} kg is at her goal`,
    facts: [`Weight ${val('weight')} kg, BMI ${val('bmi', 1)}, waist ${val('waist')} cm; both BMI and waist are above the Asian cut-offs.`, predLine('weight')],
    consider: w > tgt + 1 ? ['Set a staged target (about 5 % over 12 months is the clinic goal) and review it at each visit.', 'Link it with the walking and sleep suggestions below, which also move glucose and blood pressure.'] : ['Keep the current plan.'],
    source: [{ rule: 'A3' }, { text: 'Clinic goal: reduce about 5 % to about 68 kg (to be confirmed)' }] }); }
  // activity and sleep
  const act = dom('activity');
  if (act && act.signal !== 'green') push({ domain: 'activity', state: 'negative', verb: 'Improve', title: 'Daily movement is low and the regular walks have slipped',
    facts: [act.headline + '.', 'Walks slipped from 7 Sep and three were missed in a row by 10 Sep (her diary).', 'The clinic goal is the IPAQ moderate category or higher.'],
    consider: ['Agree a realistic restart of her earlier walking pattern rather than a new target.', 'Reduce long unbroken sitting; she sits about 11 hours a day.'], source: [{ rule: 'P2' }, { text: 'Clinic goal: IPAQ moderate or higher (to be confirmed)' }] });
  const sl = data.derived.sleep;
  if (sl && sl.last7 < 7) push({ domain: 'lifestyle', state: 'negative', verb: 'Improve', title: `Sleep averaged ${sl.last7.toFixed(1)} h over the last 7 nights, under her goal of 7`,
    facts: [`Last night ${sl.last_night} h; the 7-night average is ${sl.last7.toFixed(1)} h and the 30-night average ${sl.last30.toFixed(1)} h.`, 'Her diary links the recent weeks to quarter-close at work and festival hosting.', predLine('sleep')],
    consider: ['Protect a regular bedtime through the busy fortnight.', 'Re-check once the quarter-close and festival pressure ease, as she plans.'], source: [{ rule: 'M2' }, { text: 'Clinic goal: at least 7 h a night (to be confirmed)' }] });
  // kidney
  const kd = dom('kidney'), f8 = fu('F8');
  if (kd) push({ domain: 'kidney', state: kd.signal === 'green' ? 'positive' : 'watch', verb: kd.signal === 'green' ? 'Continue' : 'Review', title: kd.signal === 'green' ? `Kidney values are in range (eGFR ${val('egfr')}, UACR ${val('uacr', 0)} mg/g)` : 'Kidney values need a look',
    facts: [kd.headline + '.', predLine('egfr')], consider: [f8 && f8.next ? `Keep eGFR and UACR at least yearly; the next check is due ${dfmt(f8.next)}.` : 'Keep eGFR and UACR at least yearly.'], source: [{ rule: 'K1' }, { rule: 'F8' }] });
  // liver
  if (lv('alt') != null) push({ domain: 'liver', state: lv('alt') > 35 ? 'watch' : 'positive', verb: lv('alt') > 35 ? 'Review' : 'Continue', title: `Liver: ALT ${val('alt')}, AST ${val('ast')}, GGT ${val('ggt')} U/L with grade 1 steatosis on ultrasound`,
    facts: ['A grade 1 hepatic steatosis was seen on the ultrasound of 17 Jun 2025.', predLine('alt')],
    consider: ['Repeat ALT, AST and GGT with the next panel and watch the trend.', 'Abnormal ALT or AST alone does not establish MASLD; steatosis plus a cardiometabolic risk factor does.'], source: [{ rule: 'N2' }] });
  // thyroid
  const tsh = (data.series.tsh || []).slice(-2);
  if (tsh.length === 2) push({ domain: 'glycemia', state: 'positive', verb: 'Continue', title: `Thyroid: TSH is ${fix(tsh[1][1], 1)}, down from ${fix(tsh[0][1], 1)}`,
    facts: [`The 17 Jun visit left levothyroxine unchanged and asked for a repeat TSH in 6 to 8 weeks; the latest value is ${fix(tsh[1][1], 1)}.`], consider: ['Keep levothyroxine 50 mcg unchanged and continue the planned TSH checks.'], source: [{ text: 'Visit of 17 Jun 2026' }] });
  const order = { negative: 0, watch: 1, positive: 2 };
  return out.sort((a, b) => order[a.state] - order[b.state]);
}
