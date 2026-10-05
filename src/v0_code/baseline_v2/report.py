"""Stage reports (spec section 12): counts, quiet fraction, anchor fire rates, dead anchors, flagged windows, known upstream data issues."""

import random
import sqlite3
import statistics
from collections import Counter
from datetime import datetime, timedelta

from v0_code.baseline_v2 import anchors as anchors_mod
from v0_code.baseline_v2.config import Config
from v0_code.baseline_v2.data import StoreView
from v0_code.baseline_v2.trust import clean_series, glucose_metrics

NOTABLE_HIGH, NOTABLE_LOW = 0.60, 0.03


def anchor_report(cfg: Config, tier: str, rows: list[dict]) -> dict:
    n = len(rows)
    names = anchors_mod.configured_for(cfg, tier)
    fired = {a: sum(a in r["anchors_crossed"] for r in rows) for a in names}
    suppressed = {a: sum(a in r["anchors_questionable"] for r in rows) for a in names}
    notable = sum(r["is_notable"] for r in rows)
    rate = notable / n if n else 0.0
    return {"windows": n, "fired": fired, "suppressed_as_questionable": suppressed, "dead": [a for a, c in fired.items() if c == 0], "notable": notable, "notable_rate": round(rate, 3),
            "notable_rate_flag": ("ABOVE 60%" if rate > NOTABLE_HIGH else ("BELOW 3%" if rate < NOTABLE_LOW else None))}


def flagged_windows(rows: list[dict]) -> dict:
    out = {"questionable_reading_removed": [], "gap_hours": [], "low_completeness": Counter(), "unreliable": []}
    for r in rows:
        for f in r["data_quality"]["flags"]:
            kind = f["flag"].split(":")[0]
            if kind == "questionable_reading_removed":
                out[kind].append((r["end_date"], [(x["value"], x["time"][11:16]) for x in r["data_quality"]["questionable_readings"]]))
            elif kind == "gap_hours":
                out[kind].append((r["end_date"], f["flag"].split(":")[1]))
            elif kind == "low_completeness":
                out["low_completeness"][f["flag"].split(":")[1]] += 1
        if not r["reliable"]:
            out["unreliable"].append(r["end_date"])
    out["low_completeness"] = dict(out["low_completeness"])
    return out


def known_upstream_issues(cfg: Config, conn: sqlite3.Connection) -> dict:
    """Reported, never patched (spec section 5): isolated 65.0 mg/dL glucose readings the cleaning rules cannot catch, and labs above the GMI."""
    view = StoreView(conn, cfg)
    sixty_five = [(r.ts, r.value) for r in view.glucose_series if r.value == 65.0]
    kept, removed = clean_series(view.glucose_series, cfg)
    removed_ts = {x.ts for x in removed}
    labs = []
    for ts, v in conn.execute("SELECT timestamp, value FROM raw_events WHERE biomarker = 'hba1c' AND source_type = 'reading' ORDER BY timestamp"):
        d = datetime.fromisoformat(ts).astimezone(cfg.tz)
        window = [r.value for r in kept if d - timedelta(days=90) <= r.dt < d]
        gmi = glucose_metrics(window, cfg.glucose_expected_per_day * 90)["gmi_pct"] if window else None
        labs.append({"date": d.date().isoformat(), "hba1c": v, "gmi_90d_prior": gmi, "gap": round(v - gmi, 2) if gmi is not None else None, "cgm_days_in_window": len({r.dt.date() for r in kept if d - timedelta(days=90) <= r.dt < d})})
    return {"isolated_65_readings": sixty_five, "removed_by_rules": [x for x in sixty_five if x[0] in removed_ts],
            "still_in_the_data": [x for x in sixty_five if x[0] not in removed_ts], "labs_vs_gmi": labs}


def md_report(cfg: Config, rows: list[dict], conn: sqlite3.Connection, stage: str) -> str:
    ar = anchor_report(cfg, "day", rows)
    fl = flagged_windows(rows)
    up = known_upstream_issues(cfg, conn)
    status = Counter(r["gist_status"] or "gist pending (needs the LLM, Stage C/D)" for r in rows)
    quiet = sum(r["quiet"] for r in rows)
    kinds = Counter(i["kind"] for r in rows for i in r["material_changes"])
    n = len(rows)
    o = [f"# Baseline Engine v2 — Stage {stage} report (day tier, no LLM)\n", f"Config: `{cfg.version}` | windows: {n} ({rows[0]['start_date']} to {rows[-1]['end_date']})\n",
         "## Counts by tier and status\n", "| tier | gist status | windows |", "|---|---|---:|"] + [f"| day | {k} | {v} |" for k, v in sorted(status.items())]
    o += [f"\n## Quiet fraction\n\nquiet (no material changes): **{quiet} of {n} ({100*quiet/n:.1f}%)**. Material changes by kind: " + ", ".join(f"{k} {v}" for k, v in sorted(kinds.items())) + ".\n",
          "## Anchor fire rates (day tier, evaluated on cleaned values)\n", "| anchor | fired | rate | would have fired only on a removed reading |", "|---|---:|---:|---:|"]
    o += [f"| {a} | {c} | {100*c/n:.1f}% | {ar['suppressed_as_questionable'][a]} |" for a, c in ar["fired"].items()]
    o += [f"\nWindows with at least one crossing (notable): **{ar['notable']} of {n} ({100*ar['notable_rate']:.1f}%)**" + (f" — **{ar['notable_rate_flag']}: report before anything else**" if ar["notable_rate_flag"] else " — inside the 3%–60% band."),
          f"\nDead anchors (configured, never fired on this tier): {', '.join(ar['dead']) or 'none'}. (Anchors that are week/month-only are not evaluated in the day tier.)\n",
          "## Flagged windows\n", f"- questionable readings removed: {len(fl['questionable_reading_removed'])} day(s): " + "; ".join(f"{d} {v}" for d, v in fl["questionable_reading_removed"]),
          f"- glucose gaps over {cfg.gap_hours_flag:g} h: {len(fl['gap_hours'])} day(s): " + "; ".join(f"{d} ({h} h)" for d, h in fl["gap_hours"]),
          f"- low completeness by stream (days): {fl['low_completeness']}", f"- not reliable: {len(fl['unreliable'])} day(s), {fl['unreliable'][0]} to {fl['unreliable'][-1]}" if fl["unreliable"] else "- not reliable: none",
          "\n## Known upstream data issues (reported, not patched)\n",
          f"1. Isolated glucose readings of exactly 65.0 mg/dL (a data-repair artifact): **{len(up['isolated_65_readings'])}** — " + "; ".join(t[:16] for t, _ in up["isolated_65_readings"]) + ". "
          f"The generic detector removed **{len(up['removed_by_rules'])}** of them (" + ", ".join(t[:16] for t, _ in up["removed_by_rules"]) + f", by the jump rule, because its neighbours were more than the limit away); **{len(up['still_in_the_data'])}** remain in the data and in the metrics (" + ", ".join(t[:16] for t, _ in up["still_in_the_data"]) + ").",
          "2. Lab HbA1c runs above the CGM-derived GMI:\n", "| lab date | HbA1c | GMI over prior 90 days | gap | days of CGM in that window |", "|---|---:|---:|---:|---:|"]
    o += [f"| {l['date']} | {l['hba1c']} | {l['gmi_90d_prior']} | {l['gap']} | {l['cgm_days_in_window']} |" for l in up["labs_vs_gmi"]]
    return "\n".join(o) + "\n"


def stage_b_report(cfg: Config, by_tier: dict[str, list[dict]], conn: sqlite3.Connection) -> str:
    """Week and month counts, quiet fraction, notable rate, anchor fire rates, dead anchors, flagged windows, lab-vs-GMI gaps, chronic findings."""
    o = ["# Baseline Engine v2: Stage B report (week and month tiers, no LLM)\n", f"Config: `{cfg.version}`\n", "## Counts by tier and status\n", "| tier | gist status | windows |", "|---|---|---:|"]
    for tier in ("week", "month"):
        status = Counter(r["gist_status"] or "gist pending (needs the LLM, Stage C/D)" for r in by_tier[tier])
        o += [f"| {tier} | {k} | {v} |" for k, v in sorted(status.items())]
    for tier in ("week", "month"):
        rows = by_tier[tier]
        n, q = len(rows), sum(r["quiet"] for r in rows)
        ar = anchor_report(cfg, tier, rows)
        kinds = Counter(i["kind"] for r in rows for i in r["material_changes"])
        o += [f"\n## {tier.capitalize()} tier\n", f"- windows: {n} ({rows[0]['end_date']} to {rows[-1]['end_date']})",
              f"- quiet (no material changes): **{q} of {n} ({100*q/n:.1f}%)**", f"- notable: **{ar['notable']} of {n} ({100*ar['notable_rate']:.1f}%)**" + (f" — **{ar['notable_rate_flag']}: report before anything else**" if ar["notable_rate_flag"] else " (inside the 3%-60% band)"),
              "- material items by kind: " + ", ".join(f"{k} {v}" for k, v in sorted(kinds.items())), "", "| anchor | fired | rate | only on a removed reading |", "|---|---:|---:|---:|"]
        o += [f"| {a} | {c} | {100*c/n:.1f}% | {ar['suppressed_as_questionable'][a]} |" for a, c in ar["fired"].items()]
        o += [f"\nDead anchors on this tier: {', '.join(ar['dead']) or 'none'}."]
        fl = flagged_windows(rows)
        o += [f"\nFlagged {tier} windows: questionable readings removed in {len(fl['questionable_reading_removed'])}; low completeness (windows by stream) {fl['low_completeness']}; "
              f"glucose gaps in {len(fl['gap_hours'])}; not reliable {len(fl['unreliable'])}" + (f" ({fl['unreliable'][0]} to {fl['unreliable'][-1]})" if fl["unreliable"] else "") + "."]
    o += ["\n## Lab HbA1c vs glucose-based estimate (GMI over the 90 days before the lab), by checkpoint\n", "Each row lists the labs that existed at that checkpoint (never a later one). Gap = lab minus GMI. The anchor looks only at labs drawn in the checkpoint's own last 30 days (threshold inclusive).\n",
          "| checkpoint | labs seen so far (lab date: HbA1c vs GMI, gap) | lab drawn in the last 30 days | lab_cgm_discordance |", "|---|---|---|---|"]
    for r in by_tier["month"]:
        links = r["facts"]["lab_link"]
        seen = "; ".join(f"{l['lab_date']}: {l['hba1c_pct']} vs {l['gmi_90d_prior']}, gap {l['gap_hba1c_minus_gmi']}" for l in links) or "none"
        o += [f"| {r['end_date']}{' (partial)' if r['facts']['partial'] else ''} | {seen} | {r['facts']['_lab_gap'] if '_lab_gap' in r['facts'] else r['deltas_clean']['lab_gap']} | {'FIRED' if 'lab_cgm_discordance' in r['anchors_crossed'] else '-'} |"]
    o += ["\n## Chronic findings (month tier, as of each checkpoint)\n", "| checkpoint | chronic findings (share of days non-normal so far) |", "|---|---|"]
    for r in by_tier["month"]:
        o += [f"| {r['end_date']} | " + ("; ".join(f"{c['label']} {c['share_pct']}% of {c['days']} days (usually {c['usual_status']})" for c in r["facts"]["chronic_findings"]) or "none yet") + " |"]
    return "\n".join(o) + "\n"


def stage_b_entries_md(cfg: Config, by_tier: dict[str, list[dict]], seed: int = 4242, n: int = 10) -> str:
    """n random entries per tier plus the two named weeks, as stored (deviations, numbers, day-by-day list, and so on)."""
    rng = random.Random(seed)
    o = [f"# Stage B entries: {n} random per tier (seed {seed}) + two named weeks\n"]
    week_by = {r["window_id"]: r for r in by_tier["week"]}
    picks = [("week (named)", week_by["week_ENDING_2025-11-22"]), ("week (named)", week_by["week_ENDING_2025-12-09"])]
    picks += [(f"week (random {i+1})", r) for i, r in enumerate(sorted(rng.sample(by_tier["week"], n), key=lambda r: r["end_date"]))]
    picks += [(f"month (random {i+1})", r) for i, r in enumerate(sorted(rng.sample(by_tier["month"], n), key=lambda r: r["end_date"]))]
    for label, r in picks:
        o += [f"\n---\n\n## {r['window_id']} | {label} | reliable={r['reliable']} | confidence={r['confidence']} | notable={r['is_notable']} | quiet={r['quiet']} | gist_status={r['gist_status']}\n",
              f"gist line: {r['gist_headline']}\n", f"notable_reason: {r['notable_reason']}\n", f"anchors_crossed: {r['anchors_crossed']} | anchors_questionable: {r['anchors_questionable']}\n", "```", r["deviation_text"], "```"]
    return "\n".join(o) + "\n"


def sample_entries_md(rows: list[dict], n: int = 10, seed: int = 2026) -> str:
    """n random day entries, exactly as stored, for hand-reading."""
    pick = sorted(random.Random(seed).sample(range(len(rows)), n))
    o = [f"# Stage A: {n} random day entries (seed {seed}), as stored\n"]
    for i in pick:
        r = rows[i]
        o += [f"\n---\n\n## {r['window_id']} | reliable={r['reliable']} | confidence={r['confidence']} | is_notable={r['is_notable']} | quiet={r['quiet']} | gist_status={r['gist_status']}\n",
              f"gist line: {r['gist_headline']}\n", f"notable_reason: {r['notable_reason']}\n", f"anchors_crossed: {r['anchors_crossed']} | anchors_questionable: {r['anchors_questionable']}\n", "```", r["deviation_text"], "```"]
    return "\n".join(o) + "\n"
