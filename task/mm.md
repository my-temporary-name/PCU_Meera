# UMC Synthetic Dataset — Summary Document

**Subject:** Meera Iyer — Synthetic Type 2 Diabetes Patient, 12-Month Dataset
**Period Covered:** 18 October 2025 – 17 September 2026 (352 days)
**Purpose:** Realistic, internally-consistent synthetic patient data built to test and demonstrate the Unified Medical Context (UMC) system's ability to store, interpret, and explain a diabetic patient's health over time.

---

## What This Data Is

This is a **fully synthetic but clinically realistic** dataset representing one year in the life of a 43-year-old woman with Type 2 diabetes — a working mother in Pune balancing a demanding finance career, family caregiving, and her own health management.

Unlike a typical clean/idealized test dataset, this one was deliberately built to reflect **real life**: festivals, illness, a family medical emergency, a wedding, work deadlines, a health scare, habit lapses, and recovery — all woven together so that her glucose, sleep, activity, mood, and medication adherence tell one coherent, believable story across the year, not independent random numbers.

Every notable event in the data traces back to a written daily diary and a documented generation log, so any number in this dataset can be explained — *why* it is what it is — rather than being an unexplained data point.

**This dataset exists to prove one thing:** that a system built to detect patterns in real patient data (the "Pattern Discovery Engine") has genuinely different, distinguishable signals to work with — not one repeated template of "good day / bad day."

---

## File-by-File Breakdown, by Category

### 🧬 Biomarker (lab-derived and computed clinical values)

| File | What's In It | Rows | Frequency |
|---|---|---|---|
| `lab_panels_yearly.csv` | Full quarterly lab draws (glucose, HbA1c, lipids, liver, kidney, thyroid) | 44 | Every 3 months (4 draws/year) |
| `lab_panels_2025_09.csv` | Baseline lab panel, taken just before the tracked year begins | 11 | One-time baseline |
| `hba1c_full_year.csv` | HbA1c extracted on its own for easy trend tracking | 4 | Every 3 months |
| `lipid_panel_full_year.csv` | Cholesterol, LDL, HDL, triglycerides | 4 | Every 6-12 months |
| `hepatic_panel_full_year.csv` | Liver enzymes (ALT/AST/GGT) + computed fatty-liver risk score | 4 | Every 3-6 months |
| `renal_panel_full_year.csv` | Kidney function (creatinine) + computed filtration-rate score | 4 | Every 6-12 months |
| `bmi_full_year.csv` | Body Mass Index, computed from weight + height | 59 | Weekly (tied to weight readings) |
| `waist_hip_ratio_full_year.csv` | Waist-to-hip ratio, a cardiometabolic risk indicator | 59 | Weekly to monthly |

### 🩺 Clinical (day-to-day medical signals and events)

| File | What's In It | Rows | Frequency |
|---|---|---|---|
| `glucose_stream_yearly.csv` | Continuous glucose monitor (CGM) readings | 33,581 | Every 15 minutes |
| `vitals_yearly.csv` | Blood pressure and resting heart rate | 494 | BP every 2-3 days; HR daily |
| `adherence_yearly.csv` | Medication taken/missed, per medication, per day | 1,056 | Daily, per active medication |
| `allergies_standing_record.csv` | Known drug/substance allergies | 2 | Set once, updated only if new allergy appears |
| `vaccination_history.csv` | Vaccination records | 2 | Event-driven, 1-2x/year typical |

### 🌍 Context (lifestyle, environment, daily circumstances)

| File | What's In It | Rows | Frequency |
|---|---|---|---|
| `steps_hourly_yearly.csv` | Hourly step counts from wearable | 8,160 | Every hour |
| `sleep_yearly.csv` | Nightly sleep duration and quality | 352 | Daily |
| `meal_events_yearly.csv` | Timestamp and label for every meal | 1,055 | Multiple times/day |
| `food_content_full_year.csv` | Actual food eaten at every meal, linked to meal timestamps | 1,055 | Multiple times/day |
| `weight_yearly.csv` | Body weight | 59 | Weekly |
| `context_events_yearly.csv` | Life events, symptoms, travel, social context | 129 | Event-driven |
| `sedentary_time_full_year.csv` | Minutes spent sedentary each day | 352 | Daily |
| `screen_time_full_year.csv` | Hours of screen use each day | 352 | Daily |
| `hydration_full_year.csv` | Estimated daily water intake | 352 | Daily |
| `location_full_year.csv` | Where she was each day (home, office, hospital, travel, etc.) | 352 | Daily |

### 👤 Individual (static personal facts and internal state)

| File | What's In It | Rows | Frequency |
|---|---|---|---|
| `age_fact.csv` | Date of birth and stated age | 2 | Set once |
| `sex_fact.csv` | Biological sex | 1 | Set once |
| `menstrual_cycle_full_year.csv` | Menstrual cycle phase and irregularity tracking (perimenopause-relevant) | 352 | Daily |
| `cognitive_mental_health_full_year.csv` | Mood/mental state, tagged 3 times a day | 1,056 | 3x/day |

### 📄 Supporting Documentation

| File | What's In It |
|---|---|
| `Meera_Diary_Yearly_Oct2025_Sep2026.md` | Full daily diary — a plain-English, day-by-day narrative that every data file above was generated to match |
| `Generation_Logs_Yearly_Oct2025_Sep2026.md` | Month-by-month technical log explaining the reasoning behind every generated number |
| `new_datapoints_generation_plan.md` | Planning document showing how each additional data category was built and what it depends on |

---

## How These Files Correlate and Stay in Sync

No file in this dataset stands alone — each one was either generated from, or cross-checked against, others so the whole year tells one consistent story:

- **Diary → everything.** The daily diary is the source of truth. Every Clinical, Context, and Individual file was generated to match what the diary says happened on that specific day.
- **Context drives Clinical.** Steps, sleep, and meals directly shape the glucose stream — a high-activity day (e.g., a wedding) pulls glucose down; a low-activity, high-stress day (e.g., a work deadline) pushes it up. Vitals (BP, heart rate) move the same way.
- **Individual shapes Clinical.** Mood/mental state on a given day lines up with that day's glucose and adherence — a "frightened/overwhelmed" day shows elevated glucose and lower medication adherence on the same date. Menstrual cycle irregularity adds a layer of realistic, unexplained day-to-day glucose variability, as real hormonal fluctuation does.
- **Biomarker confirms the trend.** The quarterly lab panels are the "ground truth" check — the slow-moving lab numbers (HbA1c, lipids) rise and fall in the same direction as the fast-moving daily glucose trend, just measured less often.
- **Location and Context match by design.** Where she was (hospital, office, home, travel) always matches what the diary and adherence/glucose data say was happening that day — a hospital day shows both `location = hospital` and a genuine adherence dip.

---

## Patterns Present in the Data (per clinical advisor's framework)

Our doctor-advisor specified six longitudinal patterns real clinicians look for in patient data over time. All six are present and verifiable in this dataset:

| Pattern | Where It Appears |
|---|---|
| **Inflection point** | A sudden, sharp change — the father's hospitalization (November) causes an overnight jump in glucose and a collapse in activity |
| **Lag correlation** | Glucose's *worst* reading lands 1-2 days *after* the triggering event (November), not on the same day — a realistic delayed physiological response |
| **Therapeutic response curve** | After a health scare and a doctor visit (April), glucose gradually improves over the following weeks — not an instant fix |
| **Relapse cycle** | April's improvement → May's realistic wobble (missed routine) → a deliberate restart → a stronger recovery — an honest "two steps forward, one step back" shape |
| **Plateau** | August is a genuinely calm, stable month with no crisis — included specifically to prove the data doesn't manufacture drama when nothing is wrong |
| **Risk convergence** | September (the final month) shows glucose, sleep, and medication adherence all declining *together*, from two overlapping stressors (work deadline + festival) — multiple risk factors worsening at once |

Six distinct real-life causes for disruption are represented across the year — a medical crisis, a joyful celebration, work-related anxiety, a health scare, caregiving worry, and layered stress — each producing a **measurably different data signature**, not one repeated template of "good day / bad day."