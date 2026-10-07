// Data loading, indexes and small helpers shared by every view.
export const S = {};
export const DAY = 86400000;

const FILES = ['meta', 'glucose', 'glucose_daily', 'hr', 'daily', 'hourly_steps', 'meals', 'context', 'vitals', 'labs', 'body', 'bands', 'diary', 'alerts', 'cases', 'pi', 'quality', 'baselines', 'baseline_meta', 'pipeline'];

export const ms = (d) => Date.parse(d + 'T00:00:00Z');
export const ds = (t) => new Date(t).toISOString().slice(0, 10);
export const addDays = (d, n) => ds(ms(d) + n * DAY);
export const mondayOf = (d) => {
  const dow = new Date(ms(d)).getUTCDay();
  return addDays(d, -((dow + 6) % 7));
};
const MON = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];
const DOW = ['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat'];
const MONFULL = ['January', 'February', 'March', 'April', 'May', 'June', 'July', 'August', 'September', 'October', 'November', 'December'];
export const fmtDate = (d, opts = {}) => {
  const dt = new Date(ms(d));
  const base = `${dt.getUTCDate()} ${MON[dt.getUTCMonth()]}`;
  const y = opts.year ? ` ${dt.getUTCFullYear()}` : '';
  return (opts.dow ? DOW[dt.getUTCDay()] + ' ' : '') + base + y;
};
export const fmtTime = (t) => new Date(t).toISOString().slice(11, 16);
export const fmtDateTime = (t) => `${fmtDate(ds(t))} · ${fmtTime(t)}`;
export const monthName = (ym, short = false) => {
  const [y, m] = ym.split('-').map(Number);
  return `${short ? MON[m - 1] : MONFULL[m - 1]} ${y}`;
};
export const n1 = (x, d = 1) => (x == null || Number.isNaN(x) ? '—' : Number(x).toLocaleString('en-US', { minimumFractionDigits: 0, maximumFractionDigits: d }));

export const NAMES = {
  cgm_glucose_reading: 'Glucose (CGM)', fasting_glucose: 'Fasting glucose', hba1c: 'HbA1c', total_cholesterol: 'Total cholesterol', ldl_c: 'LDL-C',
  hdl_c: 'HDL-C', triglycerides: 'Triglycerides', alt: 'ALT', ast: 'AST', ggt: 'GGT', creatinine: 'Creatinine', egfr: 'eGFR', tsh: 'TSH',
  blood_pressure_systolic: 'BP systolic', blood_pressure_diastolic: 'BP diastolic', resting_heart_rate: 'Resting heart rate', bmi: 'BMI',
  waist_hip_ratio: 'Waist-hip ratio', weight: 'Weight', sleep_duration: 'Sleep', step_count: 'Steps', sedentary_time: 'Sedentary time',
  screen_time: 'Screen time', hydration: 'Hydration',
};

export async function loadAll() {
  await Promise.all(FILES.map(async (f) => {
    const r = await fetch(`data/${f}.json`);
    if (!r.ok) throw new Error(`Missing data/${f}.json — run: uv run python dashboard_v2/build_data.py`);
    S[f] = await r.json();
  }));
  S.alertById = new Map(S.alerts.map((a) => [a.id, a]));
  S.caseById = new Map(S.cases.map((c) => [c.id, c]));
  S.months = [...new Set([...S.alerts.map((a) => a.month), ...S.cases.map((c) => c.month)])].sort();
  S.alertsByMonth = groupBy(S.alerts, (a) => a.month);
  S.casesByMonth = groupBy(S.cases, (c) => c.month);
  S.diaryByDate = new Map(S.diary.map((d) => [d.date, d]));
  S.mealsByDate = groupBy(S.meals, (m) => m.date);
  S.ctxByDate = groupBy(S.context, (c) => c.date);
  S.gDaily = new Map(S.glucose_daily.map((r) => [r[0], r]));
  S.dates = Object.keys(S.daily).sort();
  S.first = S.meta.range.start;
  S.last = S.meta.range.end;
  S.memByKey = new Map(S.pi.memories.map((m) => [m.key, m]));
}

const caseCache = new Map();
export async function loadCase(id) {
  if (!caseCache.has(id)) {
    const r = await fetch(`data/case/${encodeURIComponent(id)}.json`);
    if (!r.ok) throw new Error(`No data for case ${id}`);
    caseCache.set(id, await r.json());
  }
  return caseCache.get(id);
}

export function groupBy(arr, fn) {
  const m = new Map();
  for (const x of arr) {
    const k = fn(x);
    if (!m.has(k)) m.set(k, []);
    m.get(k).push(x);
  }
  return m;
}

// Glucose points in [from, to) as [t, v] pairs.
export function glucoseSlice(from, to) {
  const t = S.glucose.t;
  let lo = 0, hi = t.length;
  while (lo < hi) { const mid = (lo + hi) >> 1; if (t[mid] < from) lo = mid + 1; else hi = mid; }
  const start = lo;
  hi = t.length;
  while (lo < hi) { const mid = (lo + hi) >> 1; if (t[mid] < to) lo = mid + 1; else hi = mid; }
  const out = new Array(lo - start);
  for (let i = start; i < lo; i++) out[i - start] = [t[i], S.glucose.v[i]];
  return out;
}

// Alerts and cases that touch a time range (wall-clock ms) or a date.
export const alertsInRange = (a, b) => S.alerts.filter((x) => x.t >= a && x.t < b);
export const casesInRange = (a, b) => S.cases.filter((c) => (c.t1 ?? c.t0) >= a && c.t0 < b);
export const casesOnDate = (d) => casesInRange(ms(d), ms(d) + DAY);

// Heart-rate points in [from, to) as [t, v].
export function hrSlice(from, to) {
  const t = S.hr.t;
  let lo = 0, hi = t.length;
  while (lo < hi) { const mid = (lo + hi) >> 1; if (t[mid] < from) lo = mid + 1; else hi = mid; }
  const out = [];
  for (let i = lo; i < t.length && t[i] < to; i++) out.push([t[i], S.hr.v[i]]);
  return out;
}

export const MEASURE = {
  glucose: 'Glucose', heart_rate: 'Heart rate', resting_heart_rate: 'Resting heart rate', blood_pressure: 'Blood pressure', medication_adherence: 'Medication taken',
  sleep_duration: 'Sleep', screen_time: 'Screen time', hydration: 'Hydration',
};
export const measureName = (m) => MEASURE[m] || m.replace(/_/g, ' ');
export const DIRECTION = { above: 'above usual', below: 'below usual' };
