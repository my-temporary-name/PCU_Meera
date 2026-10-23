# 4. State Engine

You can read Part A without opening any code. Part B is the technical detail for engineers. Numbers come from the engine's own database (`output/state_engine.db`) and the notes in `docs/state_engine_notes.md`, unless said otherwise.

---

# Part A. The idea in plain words

## A1. The problem it solves

The Baseline Engine (component 3) tells us what is **usual** for her: "her resting heart rate is normally about 76, give or take 5". But a summary written once a day cannot answer the question a doctor or a later component actually asks:

> **"Right now, is something off?"**

The State Engine answers that. Every 15 minutes it takes the **newest reading of each watched measure**, compares it with her usual, and decides:

1. Where does this reading sit against her usual? (normal for her, slightly off, clearly off, far off)
2. Has it stayed off long enough to be worth raising?
3. If yes, open a **deviation item** and, if the direction is a bad one for her, pass an **alert (hand-off)** to the next component.

Think of a **night nurse doing rounds every 15 minutes**. She glances at the monitor and doesn't react to one odd number. She also doesn't wait forever. She notes "this has been clearly above her usual for two checks in a row" and writes a short note for the doctor: what, when, how far off, and what was happening around her (last meal, missed medicines, last night's sleep).

## A2. A worked example, glucose on 9 Sep 2026

**22:15 and 22:30.** Her glucose readings come in at 22:15 and 22:30. The usual for her at this moment is not one fixed number. The State Engine asks: "what is her glucose usually, about 2.5 hours after a dinner?" Looking at her earlier days only, the answer is a typical value and a spread. The reading of **143.1** is **2.06 spreads above** that usual, which is labelled **"clearly above"**.

**Is that enough to act on?** One reading could be a blip, so the rule is: clearly off in the same direction on **two readings in a row**. At 22:30 the second one lands. The engine **opens a deviation item** and, because "above" is the bad direction for glucose, writes a **hand-off** (an alert):

```
measure   glucose      direction above      size  clearly
value     143.1        clinical status high (from component 1)
usual     based on "time since her last meal"   position z = 2.06
context   last meal: dinner, 148 minutes ago
          medicines today: 2 of 3 taken, levothyroxine missed
          last night's sleep: 6.0 h, "slightly below" her usual
          other open items: screen time
```

The item stays open until her glucose is back to "slightly off or better" on two readings in a row. Then it closes. One item is one episode, however long it lasts.

**Another example, a daily measure.** On 15 Oct 2025 at 21:00 the medicine record for the day arrived: 1 of 3 taken, metformin and amlodipine missed. That is something she rarely does, compared with her own history. Medicines arrive once a day, so one record is enough to open the item (no "two in a row" wait). A hand-off was written.

The State Engine does **not** say why. It only writes down what was happening around the moment.

## A3. What "tick" means

A tick is a **moment in time**, not a reading. The engine replays the year as **33,792 ticks**: one every 15 minutes, from 1 Oct 2025 00:00 to 17 Sep 2026 23:45 (352 days × 96). At each tick it looks at the newest available value of every watched measure.

- Glucose and heart rate have a fresh value at every tick.
- Daily measures (sleep, steps and so on) have a new value once a day. In between, the engine keeps the last one.

## A4. The three ideas to hold on to

**1. Her usual, as of the start of the day.** The engine compares a value with the baseline as it stood **before the day began**. A reading can never be part of its own yardstick.

**2. Position: how far off is "off"?** It is measured in her own spread (standard deviation), not in a textbook range:

| Label | How far from her usual |
|---|---|
| within | under 1 spread |
| slightly | 1 to 2 spreads |
| clearly | 2 to 4 spreads |
| far | 4 or more spreads |

Example: a heart rate of 95 at 22:45, with her usual about 74.4 and spread about 9.6, is (95 − 74.4) / 9.6 ≈ 2.1 spreads above, so "clearly above". These labels are **not** the Baseline Engine's small/moderate/large (those use half a spread). The same word means a different distance.

**3. Persistence: don't jump at one blip.** An item opens only when the measure is at least "clearly" off in the same direction **twice in a row** (once for daily and slower measures, which only report once a day or less). A reading that is **"far"** off opens an item **at once** (a "severe" item). An item closes when the measure is back to "slightly" or better twice in a row.

## A5. Adverse or favourable

Each watched measure has a direction that is bad for her. For glucose, heart rate and screen time it is "above". For sleep, steps, medicines and hydration it is "below".

- A deviation in the bad direction is an **adverse** item and becomes an **alert**.
- A deviation the other way (glucose below her usual, heart rate below, steps above) is a **favourable** item. It is recorded in the engine's own database but **not** handed on, unless the reading is "far" off (or, for non-continuous measures, its clinical status is abnormal on that side).

This is about **direction**, not about recovery. A "recovering" item simply closes.

## A6. What the numbers look like on this patient

| | Count |
|---|---|
| Ticks | 33,792 |
| Deviation items | **565** |
| Adverse items, each became an alert (hand-off) | **287** |
| Favourable items, recorded only | 278 |
| Alerts opened by persistence (twice in a row) | 264 |
| Alerts opened as severe ("far") | 23 |

Glucose and heart rate account for 458 of the 565 items. Of the 565: 557 closed because the value recovered, 1 closed as expired, 1 as stale, and 6 were still open when the data ended. Adverse items stayed open about 9.7 hours on average.

No item opens in the **first 14 days**, because her usual does not exist yet (same rule as the Baseline Engine). The first items appear on 15 Oct 2025.

## A7. What it deliberately does NOT do

- It does not explain **why** a value is off. No candidates, no statistics, no relationships. Those come later (Rulebook Lookup, Evidence Engine).
- It does not compare today with yesterday or this week with last week. That is the Baseline Engine's job.
- It does not compute or change the baseline. It only **reads** it.
- It does not use a language model. Everything is rules.
- It does not recompute clinical statuses. It carries component 1's status as given.
- It never writes to the Personal Data Store or the Baseline. The Baseline never reads an alert.

## A8. Where its output goes

Each of the **287 alerts** goes to the **Rulebook Lookup** (component 5), which picks the list of candidate factors to test for that alert, one packet per alert. The 278 favourable items stay in the State Engine's own database.

---

# Part B. Technical detail

## B1. Position in the system

```
Personal Data Store (raw_events, context_events)  ── read-only ──┐
Baseline Engine v2 (memory_v2: her usual)         ── read-only ──┼─► STATE ENGINE ─► output/state_engine.db
config/state_meera_iyer_v1.yaml                                  ┘     state_log · state_items · state_handoffs
                                                                              │
                                                                              └─► Rulebook Lookup (one packet per hand-off)
```

Not part of the LangGraph. It runs on its own after the store and the Baseline exist.

```bash
uv run python -m v0_code.state_engine.run --replay             # every 15-minute tick into output/state_engine.db (about 30 s); a second run continues after the last tick
uv run python -m v0_code.state_engine.run --replay --rebuild   # drop and recreate the state tables first (explicit)
uv run python -m v0_code.state_engine.run --replay --from 2026-09-17 --to 2026-09-17   # one day
```

Spec: `task/state_engine.md` (marked superseded by `docs/state_engine_notes.md` and `docs/state_engine_reference_examples.md` wherever they differ). Tests: `tests/test_state_logic.py`, `test_state_inputs.py`, `test_state_engine.py`. The engine code names no stream, medicine or patient (a test enforces it). Patient settings (time zone, medicine-id pattern, units) are read from the Baseline config that the State config names.

## B2. Modules (`src/v0_code/state_engine/`)

| Module | Role |
|---|---|
| `config.py` | YAML to `StateConfig`; versioned by content hash on every snapshot |
| `inputs.py` | `StateInputs`: observations per measure from the store, with the time each became **available** |
| `baseline.py` | `BaselineView`: read-only access to `memory_v2` profiles (as of the start of a date) |
| `usual.py` | `ReadingUsual`: reading-level usuals (clock-time and meal-relative) |
| `position.py` | z-score and percentile position labels |
| `runs.py` | `Tracker`: run counting and the open/close life of one item (pure) |
| `engine.py` | `StateEngine.tick()`: the rules R1–R12, items and hand-offs |
| `storage.py` | `StateStore`: own SQLite file, idempotent upserts |
| `run.py` | CLI, replay, resume from the last logged tick |

## B3. What is watched (12 streams in config, 10 can open items)

Kind decides how a value arrives and how its usual is built.

| Measure | Kind | New value | Usual based on | Bad direction | n_open / n_close | Items | Adverse |
|---|---|---|---|---|---|---|---|
| Glucose (cleaned as in Baseline) | continuous | every 15 min | time since last meal of the same kind; clock-time fallback | above | 2 / 2 | 285 | 104 |
| Heart rate | continuous | every 15 min | same time of day on earlier days (±30 min band) | above | 2 / 2 | 173 | 124 |
| Resting heart rate | daily | daily | Baseline profile (median, SD) | above | 1 / 1 | 26 | 12 |
| Medication taken | count | daily at 21:00 | her earlier days, by percentile | below | 1 / 1 | 24 | 24 |
| Screen time | daily | end of day | Baseline profile | above | 1 / 1 | 14 | 8 |
| Blood pressure | periodic (about every 3 days) | each measurement | her earlier readings (needs 14) | above | 1 / 1 | 10 | 3 |
| Sleep | daily | when recorded | Baseline profile | below | 1 / 1 | 10 | 10 |
| Sedentary time | daily | end of day | Baseline profile | above | 1 / 1 | 9 | 0 |
| Steps | daily | end of day | Baseline profile | below | 1 / 1 | 9 | 0 |
| Hydration | daily | end of day | Baseline profile | below | 1 / 1 | 5 | 2 |
| **Total** | | | | | | **565** | **287** |

Listed but never open an item: **mood** (a label, `position_method: none`) and **HbA1c** (a lab every 90 days, no usual). **Meals and diary** are context only (described, never compared). Everything else in the store is not watched.

Deviation from the spec: **hourly steps are not in the store** (`step_count` is one date-only row per day), so steps are a **daily** measure here.

## B4. Rules per tick (`StateEngine.tick`, rules R1–R12)

Each tick evaluates every configured measure at one moment `as_of`.

1. **R1/R2: intake and validity.** Take the newest observation available at or before `as_of` that has not been seen yet. A rejected reading (glucose that the Baseline's cleaning would drop) is not used as the "last good value". A continuous value must be fresh to count. A daily or periodic one is judged when it arrives, however late.
2. **Freshness.**
   - *Continuous* values older than their limit (`freshness_minutes`, 30 for glucose and heart rate) are **stale**: the run is cleared and the open item closes with `close_reason: stale`.
   - *Daily, periodic, count and lab* values are **overdue** when their age exceeds `cadence × overdue_grace` (1.5). Until then the last value stands and its item stays open. Past it, the item closes with `close_reason: expired`. Labels (mood) are informational only.
   - `any_stale` is true on 18.8% of ticks (HbA1c overdue 5,759 ticks, steps overdue 564, glucose stale 187).
3. **R5: the usual** (`evaluate`).
   - Continuous, `usual_basis: glucose`: **meal-relative** (readings from earlier days at the same number of minutes since a meal of the same kind, nearest 15-minute bucket, up to 180 min). Falls back to **clock time** (earlier readings within ±30 min of the time of day, wrapping at midnight) when there is no usable meal context. Meal kind is a label text match in the configured order (breakfast, lunch, dinner; `snack_lunch` counts as lunch).
   - Continuous heart rate: clock time.
   - Daily: the Baseline's profile for the **date the value belongs to** (an end-of-day value is judged against the profile as of the start of its own date, so the usual never contains the value). Needs at least 14 earlier days.
   - Blood pressure: the Baseline has no BP profile, so the median and population SD come from earlier BP readings (needs 14), per component, worst component wins.
   - Medicines: `history_percentile` (the share of earlier days at least as bad as today).
   - A reading-level usual built on fewer than **30** samples (`min_samples_usual`) is left empty. Nothing is judged (`no_usual:<key>` quality code).
   - Spread is the **population** SD, the same definition the Baseline uses.
4. **R6: position** (`position.sd_position`). `z = (value − median) / sd`, with thresholds `[1, 2, 4]` for within / slightly / clearly / far. A zero spread with a different value is a capped `z` of 99. Medicines use percentile thresholds `[0.35, 0.15, 0.05]` on the share of earlier days at least as bad (far at ≤ 5%).
5. **R7–R10: runs and items** (`runs.Tracker`).
   - A reading qualifies when its level is at least `open_label` (clearly) with a direction. Same direction as the run adds 1; a different direction restarts at 1; anything weaker resets to 0.
   - While an item is open, readings at `close_label` (slightly) or better, **or** in the opposite direction, count toward closing. After `n_close` of them it closes. The item's direction is fixed at opening.
   - An item opens when `run_count >= n_open`, or at once if the reading is severe. A severe reading is position `far` or a clinical status in `severe.statuses` (`critical_high` / `critical_low`, which the evaluator never emits, so only `far` fires in practice).
   - The peak (largest position in the item's direction) is tracked while it is open.
6. **R11: hand-off.** Written once per adverse item (`handoff_<item_id>`, never twice).
7. **Early days.** For the first `min_history_days` (14) days there is no usual, no position and no persistence-triggered items (`no_baseline_yet`).

**Times.** `opened_at`, `peak_at`, `closed_at` and the hand-off's `written_at` are the moment the triggering value **became available**, not the 15-minute tick that noticed it. The snapshot's `as_of` is the tick.

### Adverse versus favourable (`_item_class`)

Class is fixed when the item opens. An item is **adverse** if: its direction is in the measure's `adverse_directions`, **or** its trigger is `severe`, **or** (not for a continuous measure) the carried clinical status is abnormal (low/high, not borderline) on the side of the deviation. Otherwise it is **favourable**: recorded, opened and closed by the same rules, but no hand-off. For a continuous measure only `far` can rescue a favourable item, because continuous heart rate's status comes from judging sleeping readings against an awake resting range.

Real data check (glucose): above → 93 persistence + 6 severe, all adverse; below → 181 favourable (persistence) + **5 adverse (severe, "far" below)**. Hand-offs went 565 → 316 → 287 as this rule was added (`docs/state_engine_handoff_change.md`).

## B5. Output tables (`output/state_engine.db`, its own file)

| Table | Key | Content |
|---|---|---|
| `state_log` | `as_of` (the tick) | one row per tick: `baseline_asof`, `config_version`, `n_open_items`, `any_stale`, `snapshot_json` (the full Current State Snapshot) |
| `state_items` | `item_id` = `<measure>_<opened_at>` | measure, direction, `size_at_open`, `size_peak`, `opened_at`, `peak_at`, `closed_at`, `peak_value`, `trigger` (persistence or severe), `status` (open/closed), `item_class`, `close_reason` (recovered / stale / expired), `context_json` |
| `state_handoffs` | `handoff_id` | `record_json`, the hand-off record |

All writes are upserts, so running a tick again writes the same rows (idempotent). The run resumes from the newest `state_log` row, restoring last values, runs and open items.

**Hand-off record** (real example, 9 Sep 2026 22:30):

```
handoff_id        handoff_glucose_2026-09-09T22:30
measure           glucose            direction above        size clearly
trigger           persistence        value 143.1            clinical_status high
usual_basis       meal_relative      position_z 2.06
context           last_meal {dinner, 148 min ago} · medication {taken 2 of 3, missed levothyroxine}
                  sleep_last_night {6.0 h, "slightly below"} · other_open_items [screen_time]
                  diary_today_count 0
opened_at         2026-09-09T22:30   snapshot_as_of 2026-09-09T22:30
```

The context is only a description of what was around the moment, never a claim about cause.

**Snapshot** (per tick) holds, per measure: value, unit, age, `current`, clinical status, the usual (basis, context, n, median, SD, and `usual_alt` for glucose), position, run counters and the open item. Plus context: last meal, diary today, and `yesterday_memory_headline` (the Baseline's gist or code line for yesterday).

## B6. Results (full replay)

- 33,792 ticks · 565 items · 287 adverse / 278 favourable · 287 hand-offs
- by trigger among hand-offs: 264 persistence, 23 severe (glucose 11, heart rate 7, resting heart rate 3, medicines 2)
- by close reason: 557 recovered, 1 expired, 1 stale, 6 still open at the end
- 22,067 ticks (65%) have no open item; at most 9 items open at once; average about 0.7
- alerts by month: Oct 40, Nov 41, Dec 15, Jan 46, Feb 31, Mar 54, Apr 17, May 1, Jun 3, Jul 6, Aug 2, Sep 31
- worked example from the spec reproduces (items open/close at 21:45 / 22:30 / 23:00); differences and assumptions are listed in `docs/state_engine_notes.md`

## B7. Gotchas and decisions to check before changing anything

1. **Read-only toward everything else.** The store and `memory_v2` are opened read-only. Only `output/state_engine.db` is written. `--rebuild` drops only the three state tables.
2. **Position labels are not the Baseline's size labels.** Position uses 1 / 2 / 4 spreads; the Baseline uses a flat band of half a spread, with 1× / 2× / 4× of that band.
3. **Time is availability, not the tick.** Reasoning about "when" must use `opened_at`, never the snapshot's `as_of`.
4. **Daily values are judged against the profile as of the start of their own date**, so the usual never contains the value. This changed 4 items when it was introduced (a test recomputes the usual independently for every daily value).
5. **Steps are daily here** because hourly steps are not in the store (they are an ingest-only stream used by the Rulebook).
6. **Continuous heart rate:** the clinical status carried on a reading is not used to rescue a favourable item (see B4), and heart rate and glucose are the only measures with a new value at every tick.
7. **Blood pressure has no baseline profile**; its usual is computed here from earlier readings, with the same definition.
8. **Adverse directions are mandatory config** for any measure that can open an item (a stream without them is refused).
9. **Opposite direction while open:** a reading in the other direction counts toward closing the open item, and a new run in that direction can open a new item at once.
10. **Not built:** a scheduler for live ticks. The engine replays; the same rules apply live (the tick takes "now" as input).
11. **Known differences from the spec** (full list in `docs/state_engine_notes.md`): hourly steps, BP profile, no `critical_*` statuses from the evaluator, a few example numbers (for instance the spec's heart-rate `n 1733` is the glucose count; the data give 1755).

## B8. Quick checks (read-only)

```bash
sqlite3 -readonly output/state_engine.db \
  "select item_class, count(*) from state_items group by 1;"                 # adverse 287 / favourable 278

sqlite3 -readonly output/state_engine.db \
  "select measure, direction, item_class, trigger, count(*) from state_items group by 1,2,3,4;"

sqlite3 -readonly output/state_engine.db \
  "select record_json from state_handoffs where handoff_id like 'handoff_glucose_2026-09-09%';"
```

Further material: `docs/state_engine_reference_examples.md` (a real snapshot, item, hand-off and tick table for 17 Sep 2026), `docs/state_engine_final_counts.md`, `docs/state_engine_item_report.md` (written before the adverse/favourable change, not regenerated). Dashboard page: `#/stage/state`.
