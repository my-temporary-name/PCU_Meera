# New Data Points — Generation Plan (Sample Rows + Dependencies)

**Purpose:** Before generating anything, this document shows what each new data point's table will look like (2 sample rows) and exactly which existing files/diary entries it must read from to stay internally consistent. Order below is the actual build sequence.

---

## Phase A — Trivial Facts

### 1. Age
**Depends on:** Persona document only (DOB / stated age).

| field | value |
|---|---|
| age_years | 43 |
| as_of_date | 2026-09-17 |

### 2. Sex
**Depends on:** Persona document only.

| field | value |
|---|---|
| sex | female |

---

## Phase B — Anthropometric Computed/Raw

### 3. BMI
**Depends on:** All 12 existing `weight_YYYY_MM.csv` files + persona's fixed height (160cm). Pure computation, no new raw data.

| date | weight_kg | height_cm | bmi |
|---|---|---|---|
| 2025-10-01 | 71.6 | 160 | 27.97 |
| 2026-09-17 | 72.1 | 160 | 28.17 |

### 4. Waist-to-Hip Ratio
**Depends on:** Existing `weight_YYYY_MM.csv` files (for correlated trend direction — WHR should drift in the same general direction as weight) + persona's baseline waist/hip figures (91cm/104cm from persona doc's original anthropometric table). New raw waist/hip values generated monthly, then ratio computed.

| date | waist_cm | hip_cm | whr |
|---|---|---|---|
| 2025-10-01 | 91.2 | 104.0 | 0.877 |
| 2026-09-17 | 92.4 | 104.5 | 0.884 |

---

## Phase C — Periodic Clinical Facts

### 5. HbA1c (standalone)
**Depends on:** The 4 existing `lab_panels_YYYY_MM.csv` files (Sep'25, Dec'25, Mar'26, Sep'26) — this is a direct extraction/restatement of the HbA1c row already locked in those files, not new generation.

| date | hba1c_percent |
|---|---|
| 2025-12-18 | 7.6 |
| 2026-03-06 | 7.0 |

### 6. Lipid Panel
**Depends on:** Same 4 existing `lab_panels_YYYY_MM.csv` files — extraction only.

| date | total_chol | ldl_c | hdl_c | triglycerides |
|---|---|---|---|---|
| 2025-12-18 | 212 | 130 | 44 | 195 |
| 2026-03-06 | 198 | 118 | 47 | 162 |

### 7. Hepatic Panel
**Depends on:** Same 4 existing `lab_panels_YYYY_MM.csv` files — extraction only.

| date | alt | ast | ggt | hsi |
|---|---|---|---|---|
| 2025-12-18 | 44 | 33 | 50 | — |
| 2026-03-06 | 39 | 30 | 43 | — |

*(HSI needs BMI from Phase B, computed alongside — so HSI specifically has a soft dependency on Phase B being done first.)*

### 8. Renal Panel
**Depends on:** Same 4 existing `lab_panels_YYYY_MM.csv` files — extraction only.

| date | creatinine | egfr |
|---|---|---|
| 2025-12-18 | 0.8 | — |
| 2026-03-06 | 0.8 | — |

*(eGFR needs age+sex from Phase A — computed alongside, soft dependency on Phase A.)*

### 9. Allergies (standing record)
**Depends on:** Persona document (sulfa drug allergy, stated at persona creation) + existing `context_events_2026_01.csv` (the soap/detergent reaction on Jan 17-18).

| allergen | reaction_type | confirmed_date |
|---|---|---|
| Sulfa drugs | rash | 2019-04-02 |
| Unknown detergent/soap | mild skin reaction | 2026-01-17 |

### 10. Vaccination History
**Depends on:** Nothing existing — genuinely new, only needs persona's age/timeline to place plausible dates within the year.

| vaccine_name | date_administered |
|---|---|
| Influenza | 2025-11-05 |
| — | — |

---

## Phase D — Daily Signals

### 11. Sedentary Time
**Depends on:** All 12 `steps_hourly_YYYY_MM.csv` files — must be inversely correlated. A high-step day (e.g., Feb 13 wedding, 8,385 steps) must show LOW sedentary minutes; a crisis day (e.g., Nov 18, 747 steps) must show HIGH sedentary minutes.

| date | sedentary_minutes | cross_check |
|---|---|---|
| 2026-02-13 | 210 | low (wedding, high steps) |
| 2025-11-18 | 640 | high (crisis, low steps) |

### 12. Screen Time
**Depends on:** Diary text directly — office days (WFH/office mentions) and quarter-close stress periods should show elevated screen time; festival/hosting days should show reduced screen time (she's physically hosting, not at a screen).

| date | screen_time_hours | diary_basis |
|---|---|---|
| 2026-03-17 | 9.5 | audit deadline day, deskbound |
| 2026-02-14 | 1.2 | sangeet, hosting, no screens |

### 13. Hydration
**Depends on:** Diary text + existing `steps_hourly` (higher activity days → higher hydration need) + illness days from `context_events` (fever typically increases fluid intake awareness, or decreases appetite for it — flagged qualitatively).

| date | hydration_ml | diary_basis |
|---|---|---|
| 2026-02-13 | 2400 | wedding, high activity, hot festive day |
| 2025-10-15 | 1600 | fever day, reduced intake |

### 14. Menstrual/Hormonal Cycle
**Depends on:** Persona document Section 2b (perimenopause, irregular cycle guidance) only — this is a self-contained biological signal not tied to daily events, though occasional overlap with mood-related diary entries (e.g., a "low energy" day) should be checked for plausible alignment, not forced.

| date | cycle_day | cycle_phase |
|---|---|---|
| 2025-10-05 | 18 | luteal |
| 2026-06-12 | 3 | menstrual (irregular, skipped cycle before this) |

---

## Phase E — Event-Driven, Diary-Dependent

### 15. Location
**Depends on:** All 12 `context_events_YYYY_MM.csv` files directly — location must match the event described. Nov 18-20 (hospitalization) → location=hospital. Apr 14 (diabetologist) → location=clinic. Jan 12-14 (Chennai trip) → location=other_city. Feb 13-15 (wedding) → location=family_home/venue.

| date | location_type | source_context_event |
|---|---|---|
| 2025-11-19 | hospital | ctx_107 (hospital day 2) |
| 2026-04-14 | clinic | ctx_606 (diabetologist appointment) |

### 16. Food Content
**Depends on:** All 12 `meal_events_YYYY_MM.csv` files (must attach content to existing meal timestamps by `event_id`, not invent new meal times) + diary text for what was actually described (festive food, light/skipped meals, client dinner richness, snacking pattern on wedding day, etc.) + `glucose_stream` meal-response magnitude as a soft cross-check (a meal tagged "light" should correspond to a smaller glucose rise already generated).

| meal_event_id | food_description | source |
|---|---|---|
| meal_2026-02-15_snack_2 | Festive snacks, mostly fried/sweet items, wedding buffet | diary: "mostly snacking through the day" |
| meal_2025-10-15_light_dinner | Soup, toast | diary: fever day, low appetite |

---

## Phase F — Blocked

### 17. Cognitive/Mental Health Status (3x/day)
**Depends on:** Persona document's psychosocial traits (intermittent anxiety) + diary mood language across all 12 months (e.g., March's anxiety window, April's fear-response, July's worry) — but **cannot start until the value scale/shape is specified** (e.g., a 1-5 mood scale, a categorical tag, something else).

| date | time_block | status_value |
|---|---|---|
| 2026-03-17 | morning | ? — awaiting scale decision |
| 2026-03-17 | evening | ? — awaiting scale decision |

---

## Summary: Build Order

```
A (Age, Sex)
  ↓
B (BMI ← weight files; WHR ← new raw + weight files)
  ↓
C (HbA1c, Lipid, Hepatic, Renal ← lab_panels files; 
   Allergies ← persona + Jan context_events; 
   Vaccination ← new, independent)
  ↓
D (Sedentary ← steps_hourly; Screen Time ← diary; 
   Hydration ← diary + steps_hourly; 
   Menstrual Cycle ← persona doc, independent)
  ↓
E (Location ← context_events; 
   Food Content ← meal_events + diary + glucose_stream)
  ↓
F (Cognitive/Mental Health — BLOCKED on scale decision)
```
