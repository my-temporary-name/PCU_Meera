"""Read reference tables and patient files; normalize into Reading records."""

import csv
import re
from pathlib import Path

from v0_code.graph.state import Reading

# (file, {source_column: biomarker}) for files with one row per date/timestamp
WIDE_FILES: list[tuple[str, dict[str, str]]] = [
    ("hba1c_full_year.csv", {"hba1c_percent": "hba1c"}),
    (
        "lipid_panel_full_year.csv",
        {
            "total_cholesterol": "total_cholesterol",
            "ldl_c": "ldl_c",
            "hdl_c": "hdl_c",
            "triglycerides": "triglycerides",
        },
    ),
    ("hepatic_panel_full_year.csv", {"alt": "alt", "ast": "ast", "ggt": "ggt"}),
    ("renal_panel_full_year.csv", {"creatinine": "creatinine", "egfr": "egfr"}),
    ("bmi_full_year.csv", {"bmi": "bmi"}),
    ("waist_hip_ratio_full_year.csv", {"whr": "waist_hip_ratio"}),
    ("sedentary_time_full_year.csv", {"sedentary_minutes": "sedentary_time"}),
    ("screen_time_full_year.csv", {"screen_time_hours": "screen_time"}),
    ("hydration_full_year.csv", {"hydration_ml": "hydration"}),
]

# (file, {row `type` value: biomarker}) for event-style files
LONG_FILES: list[tuple[str, dict[str, str]]] = [
    ("glucose_stream_yearly.csv", {"glucose": "cgm_glucose_reading"}),
    ("weight_yearly.csv", {"weight": "weight"}),
    ("steps_hourly_yearly.csv", {"steps_hourly": "steps_hourly"}),
    ("sleep_yearly.csv", {"sleep_duration": "sleep_duration"}),
    ("vitals_yearly.csv", {"resting_hr": "resting_heart_rate"}),
    ("continuous_heart_rate_yearly.csv", {"continuous_heart_rate": "continuous_heart_rate"}),
    # Only fasting_glucose lives solely here; the other labs come from the split panel files.
    ("lab_panels_yearly.csv", {"fasting_glucose": "fasting_glucose"}),
]


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def load_plausibility_bounds(ranges_dir: Path) -> dict[str, dict[str, str]]:
    return {r["biomarker"]: r for r in read_csv(ranges_dir / "plausibility_bounds.csv")}


def load_threshold_rows(ranges_dir: Path) -> list[dict[str, str]]:
    return read_csv(ranges_dir / "threshold_ranges_full.csv")


def load_patient_facts(data_dir: Path) -> tuple[str, str]:
    age_rows = {r["field"]: r["value"] for r in read_csv(data_dir / "age_fact.csv")}
    sex_rows = {r["field"]: r["value"] for r in read_csv(data_dir / "sex_fact.csv")}
    return age_rows["date_of_birth"], sex_rows["sex"]


def load_context(data_dir: Path) -> tuple[dict[str, float], dict[str, str]]:
    """Steps keyed by 'YYYY-MM-DDTHH' (local hour bucket); location keyed by 'YYYY-MM-DD'."""
    steps = {
        r["timestamp"][:13]: float(r["value"])
        for r in read_csv(data_dir / "steps_hourly_yearly.csv")
    }
    location = {r["date"]: r["location_type"] for r in read_csv(data_dir / "location_full_year.csv")}
    return steps, location


def load_readings(data_dir: Path) -> list[Reading]:
    readings: list[Reading] = []

    for filename, columns in WIDE_FILES:
        for row in read_csv(data_dir / filename):
            for col, biomarker in columns.items():
                readings.append(
                    Reading(
                        event_id=f"{biomarker}_{row['date']}",
                        biomarker=biomarker,
                        timestamp=row["date"],
                        value=float(row[col]),
                        source_file=filename,
                    )
                )

    for filename, type_map in LONG_FILES:
        for row in read_csv(data_dir / filename):
            biomarker = type_map.get(row["type"])
            if biomarker is None:
                continue
            readings.append(
                Reading(
                    event_id=row["event_id"],
                    biomarker=biomarker,
                    timestamp=row["timestamp"],
                    value=float(row["value"]),
                    source_file=filename,
                )
            )

    for row in read_csv(data_dir / "vitals_yearly.csv"):
        if row["type"] != "blood_pressure":
            continue
        systolic, diastolic = row["value"].split("/")
        for suffix, biomarker, raw in (
            ("sys", "blood_pressure_systolic", systolic),
            ("dia", "blood_pressure_diastolic", diastolic),
        ):
            readings.append(
                Reading(
                    event_id=f"{row['event_id']}_{suffix}",
                    biomarker=biomarker,
                    timestamp=row["timestamp"],
                    value=float(raw),
                    source_file="vitals_yearly.csv",
                )
            )

    return readings


# ---- Raw context data for the Short-Range Event Linker (not folded into Reading) ----


def load_meals(data_dir: Path) -> list[dict]:
    """Meals sorted by timestamp, with food description attached by meal_event_id."""
    food = {r["meal_event_id"]: r["food_description"] for r in read_csv(data_dir / "food_content_full_year.csv")}
    meals = [
        {"id": r["event_id"], "timestamp": r["timestamp"], "label": r["meal_label"], "food": food.get(r["event_id"], "")}
        for r in read_csv(data_dir / "meal_events_yearly.csv")
    ]
    meals.sort(key=lambda m: m["timestamp"])
    return meals


def load_adherence_by_date(data_dir: Path) -> dict[str, list[dict]]:
    out: dict[str, list[dict]] = {}
    for r in read_csv(data_dir / "adherence_yearly.csv"):
        out.setdefault(r["date"], []).append(
            {"id": r["adherence_id"], "medication": r["medication_id"], "taken": r["taken"] == "True"}
        )
    return out


def load_context_events_by_date(data_dir: Path) -> dict[str, list[dict]]:
    out: dict[str, list[dict]] = {}
    for r in read_csv(data_dir / "context_events_yearly.csv"):
        out.setdefault(r["timestamp"][:10], []).append(
            {"id": r["event_id"], "timestamp": r["timestamp"], "category": r["category"], "description": r["description"], "note": r["severity_or_note"]}
        )
    return out


def load_sleep_by_date(data_dir: Path) -> dict[str, dict]:
    return {
        r["timestamp"][:10]: {"id": r["event_id"], "timestamp": r["timestamp"], "hours": float(r["value"]), "quality": r["quality"]}
        for r in read_csv(data_dir / "sleep_yearly.csv")
    }


def load_mood_by_date_block(data_dir: Path) -> dict[str, dict]:
    """Keyed by 'date|time_block' (tuple keys don't survive the state round-trip)."""
    return {
        f"{r['date']}|{r['time_block']}": {"id": f"mood_{r['date']}_{r['time_block']}", "label": r["label"], "category": r["category"]}
        for r in read_csv(data_dir / "cognitive_mental_health_full_year.csv")
    }


_DIARY_DAY = re.compile(r"^\*\*([A-Z][a-z]{2}) (\d{1,2}) \(([A-Z][a-z]{2})\)(?: — (.+?))?\*\*$")
_DIARY_MONTH_NUM = {m: i for i, m in enumerate(["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"], 1)}


def load_diary_by_date(data_dir: Path) -> dict[str, dict]:
    """date -> {title, lines}. Only the per-day entries; month summary blocks are skipped."""
    path = data_dir / "Meera_Diary_Yearly_Oct2025_Sep2026.md"
    entries: dict[str, dict] = {}
    year, in_summary, current_date = None, False, None
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.startswith("## ") and re.match(r"^## [A-Z][a-z]+ \d{4}$", line):
            year, in_summary, current_date = int(line.rsplit(" ", 1)[1]), False, None
            continue
        if line.startswith("## "):
            in_summary, current_date = True, None
            continue
        if in_summary or year is None:
            continue
        m = _DIARY_DAY.match(line.strip())
        if m:
            mon, day, _dow, title = m.groups()
            current_date = f"{year}-{_DIARY_MONTH_NUM[mon]:02d}-{int(day):02d}"
            entries[current_date] = {"title": title or "", "lines": []}
        elif current_date is not None and line.strip() and not line.startswith(("---", "**Shape", "#")):
            entries[current_date]["lines"].append(line.strip())
    return entries
