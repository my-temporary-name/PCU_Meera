"""Builds data/nmg.json for the NMG Lite view from CSV files only.

Reads  : final/*.csv (the existing input files) and doctors_requirement/doctors_pack/doctors_data/*.csv (the doctors' extra files).
Never reads: any database, output/, the pipeline's engines, or the dashboard's own JSON. Imports nothing from v0_code.
Writes : doctors_requirement/nmg_view/data/nmg.json (only this file).

Everything here is a display convention from doctors_tab_spec.md (latest value, her baseline, direction, change since diagnosis, events around the
last change) plus the derived values of doctors_derived_values.md. The colour rules (Green, Amber, Red) are NOT here: they are in js/rules.js.

    python3 doctors_requirement/nmg_view/build_nmg.py
"""

from __future__ import annotations

import csv
import hashlib
import json
import statistics
import sys
from collections import defaultdict
from datetime import date, datetime, timedelta
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]                                   # the repository root (holds final/)
FINAL = ROOT / "final"
DOC = ROOT / "doctors_requirement" / "doctors_pack" / "doctors_data"
OUT = HERE / "data" / "nmg.json"

AS_OF = date(2026, 9, 17)
DX_DATE = "2022-02-04"                                    # Type 2 diabetes diagnosis visit (conditions_standing_record.csv)
GLUCOSE_MD5_EXPECTED = "508468f16a3ab169fca3672a9efb9df1"

# direction tolerances (doctors_tab_spec.md section 5; invented display conventions, the doctors may change them). "pct" = share of the baseline.
TOL = {"hba1c": 0.3, "fpg": 10, "tc": 10, "ldl": 8, "tg": 15, "hdl": 3, "tg_hdl": 0.3, "egfr": 5, "alt": 5, "ast": 5, "ggt": 5, "uacr": 5, "tsh": 0.5,
       "weight": 1.0, "bmi": 0.4, "waist": 2, "whr": 0.01, "bp_sys": 5, "bp_dia": 5, "sleep": 0.5, "steps": ("pct", 0.15), "sedentary": 30, "rhr": 3}

# label, unit, decimals, kind (lab = a few dated values, daily = a daily series), the domain it belongs to
VARS = {
    "weight": ("Weight", "kg", 1, "lab", "anthropometry"), "bmi": ("BMI", "kg/m²", 2, "lab", "anthropometry"), "waist": ("Waist", "cm", 1, "lab", "anthropometry"),
    "hip": ("Hip", "cm", 1, "lab", "anthropometry"), "whr": ("Waist-hip ratio", "", 3, "lab", "anthropometry"), "whtr": ("Waist-to-height ratio", "", 3, "lab", "anthropometry"),
    "hba1c": ("HbA1c", "%", 1, "lab", "glycemia"), "fpg": ("Fasting glucose", "mg/dL", 0, "lab", "glycemia"), "fructosamine": ("Fructosamine", "µmol/L", 0, "lab", "glycemia"),
    "insulin": ("Fasting insulin", "µU/mL", 1, "lab", "glycemia"), "homa": ("HOMA1-IR", "", 2, "lab", "glycemia"), "cgm_mean": ("CGM mean glucose (daily)", "mg/dL", 1, "daily", "glycemia"),
    "bp_sys": ("Systolic BP, home", "mmHg", 0, "daily", "bp"), "bp_dia": ("Diastolic BP, home", "mmHg", 0, "daily", "bp"),
    "bp_clinic_sys": ("Systolic BP, clinic", "mmHg", 0, "lab", "bp"), "bp_clinic_dia": ("Diastolic BP, clinic", "mmHg", 0, "lab", "bp"),
    "tc": ("Total cholesterol", "mg/dL", 0, "lab", "lipids"), "ldl": ("LDL-C", "mg/dL", 0, "lab", "lipids"), "hdl": ("HDL-C", "mg/dL", 0, "lab", "lipids"),
    "tg": ("Triglycerides", "mg/dL", 0, "lab", "lipids"), "nonhdl": ("Non-HDL-C", "mg/dL", 0, "lab", "lipids"), "tg_hdl": ("TG/HDL-C", "", 2, "lab", "lipids"),
    "apob": ("ApoB", "mg/dL", 0, "lab", "lipids"), "lpa": ("Lp(a)", "nmol/L", 0, "lab", "lipids"),
    "creat": ("Creatinine", "mg/dL", 1, "lab", "kidney"), "egfr": ("eGFR", "mL/min/1.73 m²", 1, "lab", "kidney"), "uacr": ("UACR", "mg/g", 0, "lab", "kidney"),
    "alt": ("ALT", "U/L", 0, "lab", "liver"), "ast": ("AST", "U/L", 0, "lab", "liver"), "ggt": ("GGT", "U/L", 0, "lab", "liver"), "hsi": ("Steatosis index (HSI)", "", 1, "lab", "liver"),
    "tsh": ("TSH", "mIU/L", 1, "lab", "other"),
    "steps": ("Daily steps", "steps", 0, "daily", "activity"), "sedentary": ("Sedentary time", "min/day", 0, "daily", "activity"), "ipaq": ("IPAQ-Short", "MET-min/week", 0, "lab", "activity"),
    "sleep": ("Sleep", "h", 2, "daily", "lifestyle"), "rhr": ("Resting heart rate", "bpm", 0, "daily", "other"),
}


# ---- small helpers ---------------------------------------------------------------------------------------------------------------------------------------------------
def rd(p: Path) -> list[dict]:
    with p.open(encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def D(s: str) -> date:
    return date.fromisoformat(s[:10])


def badge(src: str | None) -> str:
    """'data' = an existing input file; otherwise the provenance in the row's source column."""
    s = (src or "").lower()
    if not s:
        return "data"
    if "synthetic_best_guess" in s and "persona_document" in s:      # "(anchors from persona)" only says what a best guess was anchored to: it is still a best guess
        return "mixed"
    if "synthetic_best_guess" in s:
        return "best_guess"
    if "persona" in s:
        return "persona"
    return "data"


def fnum(x) -> float | None:
    try:
        return float(x)
    except (TypeError, ValueError):
        return None


def edate_back(d: date, months: int) -> date:
    y, m = d.year, d.month - months
    while m <= 0:
        m += 12
        y -= 1
    day = d.day
    while True:
        try:
            return date(y, m, day)
        except ValueError:
            day -= 1


def pct(sorted_vals: list[float], q: float) -> float:
    """Percentile with linear interpolation (the numpy default)."""
    i = (len(sorted_vals) - 1) * q
    lo, hi = int(i // 1), min(int(i // 1) + 1, len(sorted_vals) - 1)
    return sorted_vals[lo] + (sorted_vals[hi] - sorted_vals[lo]) * (i - lo)


def r2(x, n=2):
    return None if x is None else round(x, n)


# ---- series ---------------------------------------------------------------------------------------------------------------------------------------------------------
series: dict[str, dict[str, dict]] = defaultdict(dict)     # key -> date -> {"v":..., "b":...}   (a later write for the same date replaces an earlier one)


def put(key: str, d: str, v, b: str, replace=False) -> None:
    if v is None:
        return
    if d in series[key] and not replace and series[key][d]["b"] == "data" and b != "data":
        return                                              # an existing file wins over a doctors' file for the same date (there are none, checked in the tests)
    series[key][d] = {"v": v, "b": b}


def load_all() -> dict:
    # ---- labs: existing files first, then the doctors' extra files
    lab_map = {"fasting_glucose": "fpg", "hba1c": "hba1c", "total_cholesterol": "tc", "ldl_c": "ldl", "hdl_c": "hdl", "triglycerides": "tg", "creatinine": "creat", "egfr": "egfr",
               "alt": "alt", "ast": "ast", "ggt": "ggt", "tsh": "tsh", "uacr": "uacr", "hsi": "hsi", "apob": "apob", "lp_a": "lpa", "fasting_insulin": "insulin", "homa_ir": "homa",
               "fructosamine": "fructosamine"}
    for r in rd(FINAL / "lab_panels_yearly.csv"):
        put(lab_map[r["type"]], r["timestamp"][:10], fnum(r["value"]), "data")
    for r in rd(FINAL / "hba1c_full_year.csv"):
        put("hba1c", r["date"], fnum(r["hba1c_percent"]), "data")
    for r in rd(FINAL / "lipid_panel_full_year.csv"):
        for src, k in (("total_cholesterol", "tc"), ("ldl_c", "ldl"), ("hdl_c", "hdl"), ("triglycerides", "tg")):
            put(k, r["date"], fnum(r[src]), "data")
    for r in rd(FINAL / "renal_panel_full_year.csv"):
        put("creat", r["date"], fnum(r["creatinine"]), "data"); put("egfr", r["date"], fnum(r["egfr"]), "data")
    for r in rd(FINAL / "hepatic_panel_full_year.csv"):
        for k in ("alt", "ast", "ggt", "hsi"):
            put(k, r["date"], fnum(r[k]), "data")
    overlaps = 0
    for fn in ("labs_history_2021_2025.csv", "labs_additional_2025_2026.csv"):
        for r in rd(DOC / fn):
            k, d = lab_map[r["type"]], r["timestamp"][:10]
            if d in series[k] and series[k][d]["b"] == "data":
                overlaps += 1
                continue
            put(k, d, fnum(r["value"]), badge(r["source"]))
    # ---- derived lab series (non-HDL, TG/HDL) on every date where the parts exist
    for d in sorted(set(series["tc"]) & set(series["hdl"])):
        put("nonhdl", d, series["tc"][d]["v"] - series["hdl"][d]["v"], "data" if series["tc"][d]["b"] == series["hdl"][d]["b"] == "data" else "best_guess")
    for d in sorted(set(series["tg"]) & set(series["hdl"])):
        put("tg_hdl", d, round(series["tg"][d]["v"] / series["hdl"][d]["v"], 2), "data" if series["tg"][d]["b"] == series["hdl"][d]["b"] == "data" else "best_guess")
    # ---- anthropometry: the doctors' history, then the weekly data-year series
    for r in rd(DOC / "anthropometry_history.csv"):
        b = badge(r["source"])
        for k, c in (("weight", "weight_kg"), ("bmi", "bmi"), ("waist", "waist_cm"), ("hip", "hip_cm"), ("whr", "whr"), ("whtr", "whtr")):
            put(k, r["date"], fnum(r[c]), b)
    height = 160.0
    for r in rd(FINAL / "bmi_full_year.csv"):
        height = fnum(r["height_cm"]) or height
        put("bmi", r["date"], fnum(r["bmi"]), "data")
    for r in rd(FINAL / "weight_yearly.csv"):
        put("weight", r["timestamp"][:10], fnum(r["value"]), "data")
    for r in rd(FINAL / "waist_hip_ratio_full_year.csv"):
        w, h = fnum(r["waist_cm"]), fnum(r["hip_cm"])
        put("waist", r["date"], w, "data"); put("hip", r["date"], h, "data"); put("whr", r["date"], fnum(r["whr"]), "data")
        put("whtr", r["date"], round(w / height, 3) if w else None, "data")
    # ---- blood pressure: clinic (doctors' history) and home (existing vitals)
    for r in rd(DOC / "bp_clinic_history.csv"):
        b = badge(r["source"])
        put("bp_clinic_sys", r["date"], fnum(r["systolic"]), b); put("bp_clinic_dia", r["date"], fnum(r["diastolic"]), b)
    home = []
    rhr_by_day: dict[str, tuple[str, float]] = {}
    for r in rd(FINAL / "vitals_yearly.csv"):
        if r["type"] == "blood_pressure":
            s, dd = r["value"].split("/")
            home.append((r["timestamp"], float(s), float(dd)))
        elif r["type"] == "resting_hr":
            d = r["timestamp"][:10]
            if d not in rhr_by_day or r["timestamp"] > rhr_by_day[d][0]:
                rhr_by_day[d] = (r["timestamp"], float(r["value"]))          # the last value of each day
    by_day = defaultdict(list)
    for ts, s, dd in home:
        by_day[ts[:10]].append((s, dd))
    for d, v in by_day.items():
        put("bp_sys", d, statistics.fmean(x[0] for x in v), "data"); put("bp_dia", d, statistics.fmean(x[1] for x in v), "data")
    for d, (_ts, v) in rhr_by_day.items():
        put("rhr", d, v, "data")
    # ---- sleep, steps, sedentary
    sleep_rows = rd(FINAL / "sleep_yearly.csv")
    for r in sleep_rows:
        put("sleep", r["timestamp"][:10], float(r["value"]), "data")
    steps = defaultdict(float)
    for r in rd(FINAL / "steps_hourly_yearly.csv"):
        steps[r["timestamp"][:10]] += float(r["value"])
    for d, v in steps.items():
        put("steps", d, v, "data")
    for r in rd(FINAL / "sedentary_time_full_year.csv"):
        put("sedentary", r["date"], fnum(r["sedentary_minutes"]), "data")
    ipaq = rd(DOC / "ipaq_short_quarterly.csv")
    for r in ipaq:
        put("ipaq", r["date"], fnum(r["met_min_week_total"]), badge(r["source"]))
    return {"overlaps": overlaps, "ipaq": ipaq, "sleep_rows": sleep_rows, "home_n": len(home)}


# ---- CGM ------------------------------------------------------------------------------------------------------------------------------------------------------------------
def cgm() -> dict:
    p = FINAL / "glucose_stream_yearly.csv"
    md5 = hashlib.md5(p.read_bytes()).hexdigest()
    rows = sorted(rd(p), key=lambda r: r["timestamp"])
    ts = [datetime.fromisoformat(r["timestamp"]) for r in rows]
    v = [float(r["value"]) for r in rows]
    kept: list[int] = []
    removed = []
    last = None
    for i in range(len(v)):                                 # the Baseline's rule: device range 40 to 400, then a jump of more than 75 mg/dL per 15 minutes from the last KEPT reading
        if not 40 <= v[i] <= 400:
            removed.append((rows[i]["timestamp"], v[i], "outside 40 to 400")); continue
        if last is not None:
            gap = max(1.0, (ts[i] - ts[last]).total_seconds() / 900)
            if abs(v[i] - v[last]) > 75 * gap:
                removed.append((rows[i]["timestamp"], v[i], "jump of more than 75 mg/dL per 15 minutes")); continue
        kept.append(i); last = i
    day = defaultdict(list)
    for i in kept:
        day[rows[i]["timestamp"][:10]].append(v[i])

    def metrics(idx: list[int]) -> dict:
        x = [v[i] for i in idx]
        m = statistics.fmean(x)
        return {"n": len(x), "mean": r2(m), "sd": r2(statistics.pstdev(x)), "cv": r2(100 * statistics.pstdev(x) / m, 1), "tir": r2(100 * sum(70 <= a <= 180 for a in x) / len(x)),
                "below70": r2(100 * sum(a < 70 for a in x) / len(x)), "above180": r2(100 * sum(a > 180 for a in x) / len(x)), "gmi": r2(3.31 + 0.02392 * m),
                "n_below70": sum(a < 70 for a in x), "n_above180": sum(a > 180 for a in x)}

    def window(n_days: int) -> list[int]:                    # n calendar days ending on the as-of date, both ends included
        s = AS_OF - timedelta(days=n_days - 1)
        return [i for i in kept if s <= ts[i].date() <= AS_OF]

    for d, x in day.items():
        put("cgm_mean", d, round(statistics.fmean(x), 2), "data")
    below = [(rows[i]["timestamp"], v[i]) for i in kept if v[i] < 70]
    # 2-hour value from CGM (NOT the OGTT value): the cleaned reading nearest to 120 minutes after the meal start, within 7 minutes
    kind_of = {"breakfast": "breakfast", "light_breakfast": "breakfast", "lunch": "lunch", "festive_lunch": "lunch", "snack_lunch": "lunch", "dinner": "dinner",
               "light_dinner": "dinner", "festive_dinner": "dinner", "late_dinner": "dinner"}
    kt = [ts[i] for i in kept]
    pm = defaultdict(list)
    import bisect
    for m in rd(FINAL / "meal_events_yearly.csv"):
        kind = kind_of.get(m["meal_label"])
        if not kind:
            continue
        t0 = datetime.fromisoformat(m["timestamp"]) + timedelta(minutes=120)
        j = bisect.bisect_left(kt, t0)
        cand = [k for k in (j - 1, j) if 0 <= k < len(kt)]
        best = min(cand, key=lambda k: abs((kt[k] - t0).total_seconds())) if cand else None
        if best is not None and abs((kt[best] - t0).total_seconds()) <= 7 * 60:
            pm[kind].append((m["timestamp"], v[kept[best]]))
    post = {}
    for kind, xs in pm.items():
        vals = sorted(a for _t, a in xs)
        last30 = [a for t, a in xs if D(t) > AS_OF - timedelta(days=30)]
        post[kind] = {"n": len(vals), "median": r2(statistics.median(vals), 1), "p90": r2(pct(vals, 0.9), 1), "max": vals[-1],
                      "share180": r2(100 * sum(a >= 180 for a in vals) / len(vals), 1), "median_30d": r2(statistics.median(last30), 1) if last30 else None,
                      "last": {"t": xs[-1][0], "v": xs[-1][1]}}
    return {"md5": md5, "md5_ok": md5 == GLUCOSE_MD5_EXPECTED, "raw_rows": len(rows), "kept": len(kept), "removed": removed, "year": metrics(kept), "w90": metrics(window(90)), "w14": metrics(window(14)),
            "w91": metrics(window(91)), "w15": metrics(window(15)), "readings_below_70": below, "post_meal_2h": post, "days_above_180": sum(1 for d, x in day.items() if any(a > 180 for a in x)),
            "ts": [rows[i]["timestamp"] for i in kept], "_kept_vals": [v[i] for i in kept], "_kept_ts": [rows[i]["timestamp"] for i in kept]}


def gmi_gap(c: dict) -> list[dict]:
    """HbA1c against the CGM estimate: the 90 days BEFORE the lab date's midnight (the lab day itself is excluded, the Baseline's convention)."""
    kts = [datetime.fromisoformat(t) for t in c["_kept_ts"]]
    kv = c["_kept_vals"]
    out = []
    for d, p in sorted(series["hba1c"].items()):
        t1 = datetime.combine(D(d), datetime.min.time(), tzinfo=kts[0].tzinfo)
        t0 = t1 - timedelta(days=90)
        w = [kv[i] for i in range(len(kv)) if t0 <= kts[i] < t1]
        if not w:
            continue
        m = statistics.fmean(w)
        gmi = round(3.31 + 0.02392 * m, 2)
        out.append({"d": d, "hba1c": p["v"], "mean": r2(m, 1), "gmi": gmi, "gap": round(p["v"] - gmi, 2), "n": len(w), "b": p["b"]})
    return out


# ---- the display conventions of the spec -------------------------------------------------------------------------------------------------------------------------
def tol_for(key: str, base: float | None):
    t = TOL.get(key)
    if t is None:
        return None
    if isinstance(t, tuple):
        return t[1] * abs(base) if base else None
    return t


def direction(key: str, latest: float, base: float | None) -> dict | None:
    if base is None:
        return None
    tol = tol_for(key, base)
    ch = latest - base
    if tol is None:
        return {"change": r2(ch, 3), "dir": None, "tol": None}
    steady = abs(ch) <= tol + 1e-9
    return {"change": r2(ch, 3), "dir": "steady" if steady else ("up" if ch > 0 else "down"), "tol": r2(tol, 3)}


def lab_var(key: str, events: list[dict]) -> dict | None:
    pts = sorted(series[key].items())
    if not pts:
        return None
    d_last, p_last = pts[-1]
    earlier = [(d, p) for d, p in pts[:-1] if edate_back(D(d_last), 24) <= D(d) < D(d_last)]
    base = statistics.median(p["v"] for _d, p in earlier) if len(earlier) >= 2 else None
    prev_d = pts[-2][0] if len(pts) > 1 else None
    dx = series[key].get(DX_DATE)
    out = {"latest": {"v": p_last["v"], "d": d_last, "age": (AS_OF - D(d_last)).days, "b": p_last["b"]}, "baseline": {"v": r2(base, 3), "n": len(earlier), "rule": "median of the earlier values in the previous 24 months"} if base is not None else None,
           "direction": direction(key, p_last["v"], base), "n_points": len(pts), "first": {"v": pts[0][1]["v"], "d": pts[0][0]}, "prev": {"v": pts[-2][1]["v"], "d": prev_d} if prev_d else None}
    if dx:
        out["since_dx"] = {"v": dx["v"], "d": DX_DATE, "delta": r2(p_last["v"] - dx["v"], 3), "b": dx["b"]}
    if prev_d:
        out["events"] = [e for e in events if prev_d < e["d"] <= d_last]
    return out


def daily_var(key: str, events: list[dict]) -> dict | None:
    pts = sorted(series[key].items())
    if not pts:
        return None
    d_last, p_last = pts[-1]
    end = D(d_last)
    base_end = end - timedelta(days=28)
    base_start = base_end - timedelta(days=89)
    last28_start = end - timedelta(days=27)
    base_vals = [p["v"] for d, p in pts if base_start <= D(d) <= base_end]
    last_vals = [p["v"] for d, p in pts if last28_start <= D(d) <= end]
    base = statistics.median(base_vals) if len(base_vals) >= 14 else None
    cur = statistics.median(last_vals) if last_vals else None
    out = {"latest": {"v": p_last["v"], "d": d_last, "age": (AS_OF - end).days, "b": p_last["b"]}, "baseline": {"v": r2(base, 3), "n": len(base_vals), "rule": "median of the 90 days that end 28 days before the latest date"} if base is not None else None,
           "last28": {"median": r2(cur, 3), "mean": r2(statistics.fmean(last_vals), 3) if last_vals else None, "n": len(last_vals)},
           "direction": direction(key, cur, base) if cur is not None else None, "n_points": len(pts), "first": {"v": pts[0][1]["v"], "d": pts[0][0]},
           "events": [e for e in events if last28_start <= D(e["d"]) <= end]}
    return out


# ---- the standing records -----------------------------------------------------------------------------------------------------------------------------------------
def standing() -> dict:
    conds = [{"name": r["condition"], "status": r["status"], "date": r["diagnosed_date"] or None, "date_basis": r["date_basis"], "note": r["note"], "b": badge(r["source"])} for r in rd(DOC / "conditions_standing_record.csv")]
    meds = [{"name": r["medication"], "indication": r["indication"], "dose": r["dose"], "freq": r["frequency"], "start": r["start_date"] or None, "end": r["end_date"] or None, "status": r["status"],
             "adherence_id": r["data_adherence_id"], "b": badge(r["source"])} for r in rd(DOC / "medications_history.csv")]
    alg = [{"name": r["allergen"], "reaction": r["reaction_type"], "date": r["confirmed_date"], "status": r["status"]} for r in rd(FINAL / "allergies_standing_record.csv")]
    fam = [{"relative": r["relative"], "condition": r["condition"], "onset": r["age_at_onset"] or None, "year": r["event_year"] or None, "premature": r["premature"], "b": badge(r["source"])} for r in rd(DOC / "family_history_standing_record.csv")]
    life = [{"domain": r["domain"], "value": r["value"], "detail": r["detail"], "b": badge(r["source"])} for r in rd(DOC / "lifestyle_standing_record.csv")]
    goals = [{"domain": r["goal_domain"], "target": r["target"], "rationale": r["rationale"], "set_by": r["set_by"], "date": r["set_date"] or None, "b": badge(r["source"])} for r in rd(DOC / "treatment_goals_standing_record.csv")]
    visits = [{"d": r["visit_date"], "type": r["visit_type"], "reason": r["reason"], "hba1c": fnum(r["hba1c_percent"]), "weight": fnum(r["weight_kg"]), "bp": r["clinic_bp"], "decision": r["key_decision"], "b": badge(r["source"])} for r in rd(DOC / "clinic_visits_history.csv")]
    imaging = [{"d": r["date"], "modality": r["modality"], "indication": r["indication"], "finding": r["finding"], "impression": r["impression"], "b": badge(r["source"])} for r in rd(DOC / "imaging_reports.csv")]
    diary = [{"d": r["timestamp"][:10], "category": r["category"], "text": r["description"], "note": r["severity_or_note"]} for r in rd(FINAL / "context_events_yearly.csv")]
    age = {r["field"]: r["value"] for r in rd(FINAL / "age_fact.csv")}
    sex = {r["field"]: r["value"] for r in rd(FINAL / "sex_fact.csv")}
    return {"conds": conds, "meds": meds, "alg": alg, "fam": fam, "life": life, "goals": goals, "visits": visits, "imaging": imaging, "diary": diary, "age": age, "sex": sex}


def adherence(meds: list[dict]) -> dict:
    rows = rd(FINAL / "adherence_yearly.csv")
    out = {}
    for mid in sorted({r["medication_id"] for r in rows}):
        x = [(r["date"], r["taken"] == "True") for r in rows if r["medication_id"] == mid]
        l90 = [t for d, t in x if D(d) > AS_OF - timedelta(days=90)]
        out[mid] = {"year": r2(100 * sum(t for _d, t in x) / len(x), 1), "last90": r2(100 * sum(l90) / len(l90), 1), "days": len(x)}
    return out


def main() -> int:
    ld = load_all()
    st = standing()
    c = cgm()
    gap = gmi_gap(c)
    # events that can sit "around a change": medicine starts and stops, visit decisions, imaging, diagnoses, and the diary's healthcare interactions and symptoms
    events: list[dict] = []
    for m in st["meds"]:
        if m["start"]:
            events.append({"d": m["start"], "kind": "medicine", "text": f"{m['name']} {m['dose']} {m['freq']} started".replace("  ", " "), "b": m["b"]})
        if m["end"]:
            events.append({"d": m["end"], "kind": "medicine", "text": f"{m['name']} {m['dose']} stopped ({m['status']})", "b": m["b"]})
    for v in st["visits"]:
        events.append({"d": v["d"], "kind": "visit", "text": f"{v['type']}: {v['decision']}", "b": v["b"]})
    for im in st["imaging"]:
        events.append({"d": im["d"], "kind": "imaging", "text": f"{im['modality']}: {im['impression'] or im['finding']}", "b": im["b"]})
    for cd in st["conds"]:
        if cd["date"]:
            events.append({"d": cd["date"], "kind": "diagnosis", "text": f"{cd['name']} diagnosed", "b": cd["b"]})
    for e in st["diary"]:
        if e["category"] in ("healthcare_interaction", "symptom"):
            events.append({"d": e["d"], "kind": e["category"], "text": e["text"], "b": "data"})
    events.sort(key=lambda e: e["d"])

    out_vars = {}
    for k, (label, unit, dec, kind, dom) in VARS.items():
        if not series.get(k):
            continue
        ev = (lab_var if kind == "lab" else daily_var)(k, events)
        if ev:
            out_vars[k] = {"label": label, "unit": unit, "dec": dec, "kind": kind, "domain": dom, **ev}
    ser = {}
    for k, pts in series.items():
        if k not in VARS or not pts:
            continue
        ser[k] = [[d, p["v"], p["b"]] for d, p in sorted(pts.items())]
    sleep_vals = [float(r["value"]) for r in ld["sleep_rows"]]
    sleep_rows = sorted(ld["sleep_rows"], key=lambda r: r["timestamp"])
    sv = [float(r["value"]) for r in sleep_rows]
    steps_vals = [p["v"] for _d, p in sorted(series["steps"].items())]
    sed_vals = [p["v"] for _d, p in sorted(series["sedentary"].items())]
    rhr_vals = [p["v"] for _d, p in sorted(series["rhr"].items())]
    steps_sorted = sorted(series["steps"].items())
    home = rd(FINAL / "vitals_yearly.csv")
    hbp = [(r["timestamp"], *map(float, r["value"].split("/"))) for r in home if r["type"] == "blood_pressure"]
    l28 = [x for x in hbp if AS_OF - timedelta(days=27) <= D(x[0]) <= AS_OF]
    l28b = [x for x in hbp if AS_OF - timedelta(days=28) <= D(x[0]) <= AS_OF]
    bp = {"n": len(hbp), "first": [hbp[0][1], hbp[0][2]], "last": {"d": hbp[-1][0][:10], "sys": hbp[-1][1], "dia": hbp[-1][2]},
          "median": [statistics.median(x[1] for x in hbp), statistics.median(x[2] for x in hbp)], "mean_last28": [r2(statistics.fmean(x[1] for x in l28), 1), r2(statistics.fmean(x[2] for x in l28), 1)], "n_last28": len(l28),
          "mean_last28_alt": [r2(statistics.fmean(x[1] for x in l28b), 1), r2(statistics.fmean(x[2] for x in l28b), 1)], "n_last28_alt": len(l28b),
          "share_130_80": r2(100 * sum(1 for x in hbp if x[1] >= 130 or x[2] >= 80) / len(hbp), 1), "share_140_90": r2(100 * sum(1 for x in hbp if x[1] >= 140 or x[2] >= 90) / len(hbp), 1),
          "range_sys": [min(x[1] for x in hbp), max(x[1] for x in hbp)], "range_dia": [min(x[2] for x in hbp), max(x[2] for x in hbp)]}
    derived = {
        "sleep": {"last_night": sv[-1], "last7": r2(statistics.fmean(sv[-7:]), 2), "last30": r2(statistics.fmean(sv[-30:]), 2), "median_year": r2(statistics.median(sv), 2), "mean_year": r2(statistics.fmean(sv), 2),
                  "share_under_7": r2(100 * sum(1 for x in sv if x < 7) / len(sv), 1), "nights": len(sv), "source": "wearable (synthetic)"},
        "steps": {"days": len(steps_vals), "median": r2(statistics.median(steps_vals), 0), "mean": r2(statistics.fmean(steps_vals), 0), "last30_mean": r2(statistics.fmean([p["v"] for d, p in steps_sorted if D(d) > AS_OF - timedelta(days=30)]), 0),
                  "share_ge_7000": r2(100 * sum(1 for x in steps_vals if x >= 7000) / len(steps_vals), 1), "share_lt_4000": r2(100 * sum(1 for x in steps_vals if x < 4000) / len(steps_vals), 1)},
        "sedentary": {"median": r2(statistics.median(sed_vals), 0), "last30_median": r2(statistics.median([p["v"] for d, p in sorted(series["sedentary"].items()) if D(d) > AS_OF - timedelta(days=30)]), 0)},
        "rhr": {"median": r2(statistics.median(rhr_vals), 0), "last30_median": r2(statistics.median([p["v"] for d, p in sorted(series["rhr"].items()) if D(d) > AS_OF - timedelta(days=30)]), 0), "min": min(rhr_vals), "max": max(rhr_vals)},
        "alcohol_dates": [e["d"] for e in st["diary"] if e["category"] == "substance_use"],
    }
    ipaq = [{"d": r["date"], "met": fnum(r["met_min_week_total"]), "category": r["category"], "sitting_h": fnum(r["sitting_hours_weekday"]), "b": badge(r["source"])} for r in ld["ipaq"]]
    cg = {k: v for k, v in c.items() if not k.startswith("_") and k != "ts"}
    cg["removed"] = c["removed"]
    data = {
        "meta": {"as_of": AS_OF.isoformat(), "dx_date": DX_DATE, "patient": "Meera Iyer", "patient_id": "meera_iyer_v1", "synthetic": True, "glucose_md5": c["md5"], "glucose_md5_ok": c["md5_ok"],
                 "inputs": {"final": sorted(p.name for p in FINAL.glob("*.csv")), "doctors_data": sorted(p.name for p in DOC.glob("*.csv"))}, "lab_overlaps_between_existing_and_doctors_files": ld["overlaps"]},
        "standing": st, "vars": out_vars, "series": ser, "cgm": cg, "gmi_gap": gap, "bp": bp, "derived": derived, "ipaq": ipaq, "adherence": adherence(st["meds"]), "events": events,
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(data, separators=(",", ":"), ensure_ascii=False), encoding="utf-8")
    print(f"wrote {OUT.relative_to(ROOT)}: {OUT.stat().st_size // 1024} KB; {len(out_vars)} variables, {sum(len(v) for v in ser.values())} points, glucose md5 ok: {c['md5_ok']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
