"""Convert final/, output/ and output_for_doctor/ into compact JSON for the dashboard.

Presentation-only transforms: no new analysis. Wall-clock IST timestamps are encoded as
epoch-ms-as-if-UTC so the browser (ECharts useUTC) shows the original IST time.
"""

import asyncio
import csv
import json
import re
from collections import Counter, defaultdict
from datetime import datetime, timedelta, timezone
from pathlib import Path

from v0_code.data import loaders
from v0_code.graph.executor import run_pipeline
from v0_code.logic.threshold import age_on, select_row
from v0_code.viz.plots import bands

ROOT = Path(__file__).resolve().parents[1]
FINAL, RANGES, OUT, DOC = ROOT / "final", ROOT / "ranges", ROOT / "output", ROOT / "output_for_doctor"
DATA = Path(__file__).resolve().parent / "data"
IST = timezone(timedelta(hours=5, minutes=30))
MONTH_FILES = ["october", "november", "december", "january", "february", "march", "april", "may", "june", "july", "august", "september"]


def read(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def wall_ms(ts: str) -> int:
    """'2025-10-01T08:05:00+05:30' -> epoch ms of the wall-clock time treated as UTC."""
    return int(datetime.fromisoformat(ts[:19]).replace(tzinfo=timezone.utc).timestamp() * 1000)


def utc_to_wall_ms(ts: str) -> int:
    dt = datetime.fromisoformat(ts).astimezone(IST).replace(tzinfo=timezone.utc)
    return int(dt.timestamp() * 1000)


def dump(name: str, obj) -> None:
    DATA.mkdir(parents=True, exist_ok=True)
    (DATA / name).write_text(json.dumps(obj, separators=(",", ":"), ensure_ascii=False), encoding="utf-8")


def fnum(x: str):
    return float(x) if x not in ("", None) else None


def ensure_pipeline_outputs() -> None:
    if not (OUT / "threshold_evaluation_results.csv").exists():
        asyncio.run(run_pipeline(str(FINAL), str(RANGES), str(OUT)))


def build_diary() -> list[dict]:
    entries, year_for_month, current = [], {}, None
    month_re = re.compile(r"^## ([A-Z][a-z]+) (\d{4})$")
    day_re = re.compile(r"^\*\*([A-Z][a-z]{2}) (\d{1,2}) \(([A-Z][a-z]{2})\)(?: — (.+?))?\*\*$")
    months = {m: i for i, m in enumerate(["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"], 1)}
    year, in_summary = None, False
    for line in (FINAL / "Meera_Diary_Yearly_Oct2025_Sep2026.md").read_text(encoding="utf-8").splitlines():
        m = month_re.match(line)
        if m:
            year, in_summary, current = int(m.group(2)), False, None
            continue
        if line.startswith("## "):
            in_summary, current = True, None
            continue
        if in_summary or year is None:
            continue
        d = day_re.match(line.strip())
        if d:
            mon = months[d.group(1)]
            current = {"date": f"{year}-{mon:02d}-{int(d.group(2)):02d}", "dow": d.group(3), "title": d.group(4) or "", "lines": []}
            entries.append(current)
        elif current is not None and line.strip() and not line.startswith(("---", "**Shape", "#")):
            current["lines"].append(line.strip())
    return entries


def main() -> None:
    ensure_pipeline_outputs()
    threshold = read(OUT / "threshold_evaluation_results.csv")
    plaus = read(OUT / "plausibility_filter_results.csv")
    status_by_event = {(r["event_id"], r["timestamp"]): r["status"] for r in threshold}  # event_ids repeat across months
    status_by_bio_date = {(r["biomarker"], r["timestamp"][:10]): r["status"] for r in threshold}

    dob, sex = loaders.load_patient_facts(FINAL)
    age = age_on(dob, "2026-09-17")

    # ---------- glucose ----------
    rejected_keys = {(r["event_id"], r["timestamp"]) for r in plaus if r["filter_result"] != "PASS"}
    gl = read(FINAL / "glucose_stream_yearly.csv")
    t, v, rejected = [], [], []
    daily = defaultdict(list)
    for r in gl:
        ms, val = wall_ms(r["timestamp"]), float(r["value"])
        if (r["event_id"], r["timestamp"]) in rejected_keys:
            rejected.append({"t": ms, "v": val, "id": r["event_id"], "ts": r["timestamp"]})
            continue
        t.append(ms)
        v.append(val)
        daily[r["timestamp"][:10]].append(val)
    for p in plaus:
        if p["filter_result"] != "PASS":
            for rj in rejected:
                if rj["id"] == p["event_id"] and rj["ts"] == p["timestamp"]:
                    rj["reason"], rj["result"] = p["reason"], p["filter_result"]
    dump("glucose.json", {"t": t, "v": v, "rejected": rejected})
    dump(
        "glucose_daily.json",
        [[d, min(x), round(sum(x) / len(x), 1), max(x), len(x)] for d, x in sorted(daily.items())],
    )

    # ---------- daily context ----------
    days: dict[str, dict] = defaultdict(dict)
    for r in read(FINAL / "sedentary_time_full_year.csv"):
        days[r["date"]]["sedentary"] = float(r["sedentary_minutes"])
    for r in read(FINAL / "screen_time_full_year.csv"):
        days[r["date"]]["screen"] = float(r["screen_time_hours"])
    for r in read(FINAL / "hydration_full_year.csv"):
        days[r["date"]]["hydration"] = float(r["hydration_ml"])
    for r in read(FINAL / "sleep_yearly.csv"):
        days[r["timestamp"][:10]].update(sleep=float(r["value"]), sleep_q=r["quality"])
    for r in read(FINAL / "location_full_year.csv"):
        days[r["date"]]["loc"] = r["location_type"]
    for r in read(FINAL / "menstrual_cycle_full_year.csv"):
        days[r["date"]]["cycle"] = {
            "day": int(r["cycle_day"]),
            "phase": r["cycle_phase"],
            "anovulatory": r["anovulatory_cycle"] == "True",
        }
    for r in read(FINAL / "cognitive_mental_health_full_year.csv"):
        days[r["date"]].setdefault("mood", {})[r["time_block"]] = [r["label"], r["category"]]
    meds = {}
    for r in read(FINAL / "adherence_yearly.csv"):
        name = r["medication_id"].split("_", 2)[2].title()
        meds[r["medication_id"]] = name
        days[r["date"]].setdefault("adh", []).append({"m": name, "taken": r["taken"] == "True"})
    for r in read(FINAL / "vitals_yearly.csv"):
        d = r["timestamp"][:10]
        if r["type"] == "resting_hr":
            days[d]["hr"] = float(r["value"])
        else:
            days[d]["bp"] = [int(x) for x in r["value"].split("/")]
    for d, rec in days.items():
        rec["st"] = {
            k: status_by_bio_date[(b, d)]
            for k, b in (
                ("sleep", "sleep_duration"),
                ("steps", "step_count"),
                ("sedentary", "sedentary_time"),
                ("screen", "screen_time"),
                ("hydration", "hydration"),
            )
            if (b, d) in status_by_bio_date
        }

    hourly = defaultdict(lambda: [0] * 24)
    for r in read(FINAL / "steps_hourly_yearly.csv"):
        hourly[r["timestamp"][:10]][int(r["timestamp"][11:13])] = int(float(r["value"]))
    for d, hrs in hourly.items():
        days[d]["steps"] = sum(hrs)
    dump("hourly_steps.json", dict(sorted(hourly.items())))
    dump("daily.json", dict(sorted(days.items())))

    # ---------- events, meals, vitals ----------
    food = {r["meal_event_id"]: r["food_description"] for r in read(FINAL / "food_content_full_year.csv")}
    meals = [
        {"id": r["event_id"], "t": wall_ms(r["timestamp"]), "date": r["timestamp"][:10], "label": r["meal_label"], "food": food.get(r["event_id"], "")}
        for r in read(FINAL / "meal_events_yearly.csv")
    ]
    dump("meals.json", meals)
    dump(
        "context.json",
        [
            {"id": r["event_id"], "t": wall_ms(r["timestamp"]), "date": r["timestamp"][:10], "category": r["category"], "description": r["description"], "note": r["severity_or_note"]}
            for r in read(FINAL / "context_events_yearly.csv")
        ],
    )
    bp, hr = [], []
    for r in read(FINAL / "vitals_yearly.csv"):
        if r["type"] == "blood_pressure":
            s, d = (int(x) for x in r["value"].split("/"))
            bp.append({"t": wall_ms(r["timestamp"]), "sys": s, "dia": d, "ss": status_by_event.get((r["event_id"] + "_sys", r["timestamp"])), "ds": status_by_event.get((r["event_id"] + "_dia", r["timestamp"]))})
        else:
            hr.append({"t": wall_ms(r["timestamp"]), "v": float(r["value"]), "s": status_by_event.get((r["event_id"], r["timestamp"]))})
    dump("vitals.json", {"bp": bp, "hr": hr})

    # ---------- labs & body ----------
    labs: dict[str, list] = defaultdict(list)
    for r in read(FINAL / "lab_panels_yearly.csv"):
        labs[r["type"]].append({"d": r["timestamp"][:10], "v": float(r["value"]), "u": r["unit"], "s": status_by_event.get((r["event_id"], r["timestamp"])) or status_by_event.get((f"{r['type']}_{r['timestamp'][:10]}", r["timestamp"][:10]))})
    for r in read(FINAL / "renal_panel_full_year.csv"):
        labs["egfr"].append({"d": r["date"], "v": float(r["egfr"]), "u": "mL/min/1.73m2", "s": status_by_event.get((f"egfr_{r['date']}", r["date"]))})
    dump("labs.json", dict(labs))

    body = defaultdict(dict)
    for r in read(FINAL / "weight_yearly.csv"):
        body[r["timestamp"][:10]]["weight"] = float(r["value"])
    for r in read(FINAL / "bmi_full_year.csv"):
        body[r["date"]].update(bmi=float(r["bmi"]), bmi_s=status_by_event.get((f"bmi_{r['date']}", r["date"])))
    for r in read(FINAL / "waist_hip_ratio_full_year.csv"):
        body[r["date"]].update(whr=float(r["whr"]), waist=float(r["waist_cm"]), hip=float(r["hip_cm"]), whr_s=status_by_event.get((f"waist_hip_ratio_{r['date']}", r["date"])))
    dump("body.json", [{"d": d, **x} for d, x in sorted(body.items())])

    # ---------- reference bands ----------
    rows = loaders.load_threshold_rows(RANGES)
    band_out = {}
    for bio in sorted({r["biomarker"] for r in threshold} | {"fasting_glucose"}):
        row = select_row(rows, bio, age, sex)
        if row:
            band_out[bio] = {
                "unit": row["unit"],
                "group": row["age_group"],
                "bands": [[None if lo == float("-inf") else lo, None if hi == float("inf") else hi, k] for lo, hi, k in bands(row)],
            }
    dump("bands.json", band_out)

    # ---------- doctor outputs ----------
    dump("baseline.json", json.loads((DOC / "weekly_baseline_v2.json").read_text()))
    events, episodes, unlinked = [], [], {}
    ep_of_event = {}
    for m in MONTH_FILES:
        ep_doc = json.loads((DOC / f"{m}_episodes_final.json").read_text())
        for ep in ep_doc["episodes"]:
            ep["month"] = ep_doc["month"]
            episodes.append(ep)
            for eid in ep["linked_event_ids"]:
                ep_of_event[eid] = ep["episode_id"]
        unlinked[ep_doc["month"]] = ep_doc["events_not_in_any_episode"]
    for m in MONTH_FILES:
        ev_doc = json.loads((DOC / f"{m}_events_final.json").read_text())
        for e in ev_doc["events"]:
            e["month"] = ev_doc["month"]
            if "window" in e:
                e["win"] = [utc_to_wall_ms(e["window"]["start"]), utc_to_wall_ms(e["window"]["end"])]
                e["ist_date"] = datetime.fromtimestamp(e["win"][0] / 1000, timezone.utc).strftime("%Y-%m-%d")
                e.pop("window")
            else:
                e["win"], e["ist_date"] = None, e["date"]
            e["ep"] = ep_of_event.get(e["event_id"])
            events.append(e)
    dump("events.json", events)
    dump("episodes.json", {"episodes": episodes, "unlinked": unlinked})
    dump("diary.json", build_diary())

    # ---------- meta ----------
    age_rows = {r["field"]: r["value"] for r in read(FINAL / "age_fact.csv")}
    cycle = read(FINAL / "menstrual_cycle_full_year.csv")
    sources = []
    spec = [
        ("glucose_stream_yearly.csv", "CGM glucose (15-min)", "timestamp", "Year · Month · Week · Event · Episode"),
        ("vitals_yearly.csv", "Blood pressure & resting heart rate", "timestamp", "Week · Labs & Body"),
        ("steps_hourly_yearly.csv", "Steps (hourly)", "timestamp", "Week"),
        ("sedentary_time_full_year.csv", "Daily steps & sedentary time", "date", "Year · Month · Week"),
        ("sleep_yearly.csv", "Sleep duration & quality", "timestamp", "Year · Month · Week"),
        ("screen_time_full_year.csv", "Screen time", "date", "Month · Week"),
        ("hydration_full_year.csv", "Hydration", "date", "Month · Week"),
        ("adherence_yearly.csv", "Medication adherence", "date", "Month · Week · Event"),
        ("cognitive_mental_health_full_year.csv", "Mood (3x daily)", "date", "Week · Event"),
        ("menstrual_cycle_full_year.csv", "Menstrual cycle", "date", "Week"),
        ("meal_events_yearly.csv", "Meals", "timestamp", "Week · Event"),
        ("food_content_full_year.csv", "Food description", "date", "Week · Event"),
        ("context_events_yearly.csv", "Life & symptom events", "timestamp", "Week · Episode"),
        ("location_full_year.csv", "Daily location", "date", "Week"),
        ("weight_yearly.csv", "Weight", "timestamp", "Labs & Body"),
        ("bmi_full_year.csv", "BMI", "date", "Labs & Body"),
        ("waist_hip_ratio_full_year.csv", "Waist-hip ratio", "date", "Labs & Body"),
        ("lab_panels_yearly.csv", "Lab panels", "timestamp", "Labs & Body"),
        ("renal_panel_full_year.csv", "Renal panel (eGFR)", "date", "Labs & Body"),
        ("Meera_Diary_Yearly_Oct2025_Sep2026.md", "Diary", None, "Week · Diary"),
    ]
    for fname, label, col, shown in spec:
        path = FINAL / fname
        if col:
            rws = read(path)
            ds = sorted(r[col][:10] for r in rws)
            sources.append({"file": fname, "label": label, "kind": "Patient data", "rows": len(rws), "start": ds[0], "end": ds[-1], "shown": shown})
        else:
            sources.append({"file": fname, "label": label, "kind": "Patient data", "rows": len(build_diary()), "start": "2025-10-01", "end": "2026-09-17", "shown": shown})
    for fname, label, shown in [
        ("weekly_baseline_v2.json", "Weekly baselines", "Baselines · Year · Event"),
        ("*_events_final.json", "Glucose events (12 files)", "Events · Month · Event"),
        ("*_episodes_final.json", "Episodes (12 files)", "Episodes · Year · Month"),
    ]:
        sources.append({"file": fname, "label": label, "kind": "Derived (output_for_doctor)", "rows": {"weekly_baseline_v2.json": 50 * 11, "*_events_final.json": len(events), "*_episodes_final.json": len(episodes)}[fname], "start": "2025-10-01", "end": "2026-09-17", "shown": shown})

    filter_counts = Counter(p["filter_result"] for p in plaus)
    dump(
        "meta.json",
        {
            "patient": {"id": "meera_iyer_v1", "name": "Meera Iyer", "age": age, "dob": dob, "sex": sex, "menopause_status": cycle[0]["menopause_status"]},
            "range": {"start": "2025-10-01", "end": "2026-09-17"},
            "allergies": read(FINAL / "allergies_standing_record.csv"),
            "vaccinations": read(FINAL / "vaccination_history.csv"),
            "medications": sorted(set(meds.values())),
            "sources": sources,
            "pipeline": {
                "filter_counts": dict(filter_counts),
                "status_counts": dict(Counter(r["status"] for r in threshold)),
                "evaluated": len(threshold),
                "rejected": [
                    {"event_id": p["event_id"], "biomarker": p["biomarker"], "timestamp": p["timestamp"], "value": float(p["raw_value"]), "result": p["filter_result"], "reason": p["reason"]}
                    for p in plaus
                    if p["filter_result"] != "PASS"
                ],
            },
        },
    )
    print(f"Wrote dashboard data to {DATA} ({len(events)} events, {len(episodes)} episodes, {len(t)} glucose points)")


if __name__ == "__main__":
    main()
