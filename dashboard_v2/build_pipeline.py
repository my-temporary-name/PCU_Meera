"""Dashboard v2: the pipeline data. Reads the component databases READ-ONLY and writes compact JSON into dashboard_v2/data/ (alerts, cases, one file per case, PI, quality, baselines, the pipeline
overview). Presentation only: every number comes from a database; nothing is analysed here and nothing from output_for_doctor/ is used.

    uv run python dashboard_v2/build_pipeline.py
"""

import csv
import json
import sqlite3
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path

import sys

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from v0_code.findings_engine.factors import parse_key  # noqa: E402
from v0_code.intel_common.phrasebook import Phrasebook  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "output"
DATA = Path(__file__).resolve().parent / "data"
FINDINGS_DB, PI_DB = "findings_loop_polish", "pi_loop_polish"


def ro(name: str) -> sqlite3.Connection:
    return sqlite3.connect(f"file:{OUT / (name + '.db')}?mode=ro", uri=True)


def wall_ms(ts: str) -> int:
    """'2025-10-01T08:05:00+05:30' -> epoch ms of the wall-clock time treated as UTC (the browser shows IST)."""
    return int(datetime.fromisoformat(ts[:19]).replace(tzinfo=timezone.utc).timestamp() * 1000)


def dump(name: str, obj) -> None:
    path = DATA / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, separators=(",", ":"), ensure_ascii=False), encoding="utf-8")


def sents(t: dict) -> list[dict]:
    return [s if isinstance(s, dict) else {"text": s, "refs": []} for s in t["sentences"]]


PB = Phrasebook.load(ROOT / "config/findings_phrasebook_v0.yaml")


def phrases(key):
    """(what was present, what it is compared with) in plain words, from the shared phrase book."""
    if not key:
        return None, None
    e, tag, o, kind = parse_key(key)
    return PB.exposure(e, tag), PB.outcome(o, kind)


def key_of(rel_id):
    """`rel|<relationship_key>|<date>|<method>` -> the relationship key."""
    return rel_id.split("|")[1] if rel_id else None


def main() -> None:
    st, rb, ev, ps, fd, pi = ro("state_engine"), ro("rulebook_lookup"), ro("evidence_engine"), ro("personal_data_store"), ro(FINDINGS_DB), ro(PI_DB)
    for old in (DATA / "case").glob("*.json") if (DATA / "case").exists() else []:
        old.unlink()

    # ---- inputs, indexed -------------------------------------------------------------------------------------------------------------------------------------
    handoffs = {}
    for (rj,) in st.execute("SELECT record_json FROM state_handoffs ORDER BY written_at"):
        h = json.loads(rj)
        handoffs[h["handoff_id"]] = h
    packets = {r[0]: json.loads(r[1]) for r in rb.execute("SELECT handoff_id, packet_json FROM rulebook_packets")}
    packet_status = {r[0]: r[1] for r in rb.execute("SELECT handoff_id, status FROM rulebook_packets")}
    evidence = {r[0]: json.loads(r[1]) for r in ev.execute("SELECT handoff_id, record_json FROM event_evidence")}
    completions = defaultdict(list)
    for eid, cand, sup, rj, frm in ev.execute("SELECT evidence_id, candidate, support, result_json, evaluated_from FROM event_completions"):
        completions[eid].append({"candidate": cand, "support": sup, "evaluated_from": json.loads(frm) if frm else None})
    case_of = {}
    counted = {}
    for cid, hid, c in fd.execute("SELECT case_id, handoff_id, counted FROM case_handoffs"):
        case_of[hid] = cid
        counted[hid] = bool(c)
    cases = {r[0]: dict(zip(("case_id", "local_date", "opened_at", "last_handoff_at", "closed_at", "status", "n_counted", "n_recorded", "n_versions"), r)) for r in fd.execute("SELECT * FROM cases ORDER BY opened_at")}
    versions = defaultdict(list)
    for fid, cid, rj in fd.execute("SELECT finding_id, case_id, record_json FROM findings ORDER BY case_id, version"):
        versions[cid].append(json.loads(rj))
    texts = {}
    for fid, src, tj, fp, pv, cv in fd.execute("SELECT finding_id, text_source, text_json, from_prompt, prompt_version, checks_version FROM finding_text"):
        texts[fid] = {"text": json.loads(tj), "source": src, "from_prompt": fp, "prompt": pv, "checks": cv}
    llm = {r[0]: (json.loads(r[1] or "[]"), json.loads(r[2] or "[]")) for r in fd.execute("SELECT finding_id, checks_json, usage_json FROM finding_llm")}
    mems = defaultdict(list)
    for mid, ver, rj in pi.execute("SELECT memory_id, version, record_json FROM pi_long_memories ORDER BY memory_id, version"):
        mems[mid].append(json.loads(rj))
    situations = {(r[0], r[1]): (json.loads(r[2]) or {}).get("situations") for r in pi.execute("SELECT memory_id, version, text_json FROM pi_text")}
    windows = {r[0]: r[1] for r in ps.execute("SELECT window_id, gist_headline FROM memory_v2")}
    fcfg = yaml.safe_load((ROOT / "config/findings_meera_iyer_v1.yaml").read_text())["findings"]["diary"]
    diary = {}
    for rid, ts, cat, val, mj in ps.execute("SELECT id, timestamp, category, value_text, meta_json FROM context_events WHERE stream = ?", (fcfg["stream"],)):
        m = json.loads(mj) if mj else {}
        diary[str(m.get(fcfg["id_field"]) or f"event_{rid}")] = {"t": wall_ms(ts), "category": cat, "text": val, "note": m.get(fcfg["note_field"])}

    # ---- alerts ---------------------------------------------------------------------------------------------------------------------------------------------
    alerts = []
    for hid, h in handoffs.items():
        pk = packets.get(hid)
        alerts.append({"id": hid, "t": wall_ms(h["opened_at"]), "date": h["opened_at"][:10], "month": h["opened_at"][:7], "measure": h["measure"], "direction": h["direction"], "size": h["size"], "trigger": h["trigger"],
                       "value": h.get("value"), "status": h.get("clinical_status"), "rule": (pk or {}).get("matched_rule", {}).get("rule_id"), "packet": packet_status.get(hid), "case": case_of.get(hid), "counted": counted.get(hid, False),
                       "item": h["item_id"]})
    dump("alerts.json", alerts)

    # ---- cases and the per-case files -------------------------------------------------------------------------------------------------------------------------
    def factor_row(f):
        ph, oc = phrases(f.get("relationship_key"))
        if f["kind"] == "event":
            ph = PB.event_phrase(f["candidate"])
        return {"id": f["factor_id"], "kind": f["kind"], "candidate": f["candidate"], "key": f.get("relationship_key"), "phrase": ph, "outcome": oc, "label": f["label"], "flags": f.get("flags") or [], "exposure": f["exposure"], "wording": f["wording_class"],
                "position": f.get("position"), "group": f.get("group"), "tier": f.get("weight_tier")}

    def evidence_block(hid):
        e = evidence.get(hid)
        if not e:
            return None
        out = []
        for f in e["factors"]:
            es = f.get("event_specific") or {}
            k = key_of(f.get("relationship_evidence_id"))
            ph, oc = phrases(k)
            if not k:
                ph = PB.event_phrase(f["candidate"]) if f["candidate"] in PB.raw["event_checks"] else f["candidate"].replace("_", " ")
            out.append({"rank": f["rank"], "candidate": f["candidate"], "tier": f.get("weight_tier"), "check": f.get("check_type"), "key": k, "phrase": ph, "outcome": oc, "support": f["support"],
                        "flags": f.get("flags") or [], "exposure": (f.get("event_exposure") or {}).get("state"), "reason": f.get("reason"),
                        "event": {k: es[k] for k in ("elapsed_minutes", "observed", "history_n", "history_median", "history_p90", "percentile") if k in es} or None})
        return {"evidence_id": e["evidence_id"], "counts": e["counts"], "factors": out, "overlap": e.get("overlap") or [], "not_tested": e.get("not_tested") or [], "method": e.get("method_version")}

    def packet_block(hid):
        p = packets.get(hid)
        if not p:
            return None
        return {"packet_id": p["packet_id"], "status": packet_status.get(hid), "rule": p["matched_rule"]["rule_id"], "rule_status": p["matched_rule"]["status"], "budget": p["matched_rule"].get("budget"),
                "selected": [{"rank": s["rank"], "tier": s["weight_tier"], "candidate": s["candidate"], "check": s["check_type"], "text": s.get("check_text"), "outcome": s.get("outcome_compared_text")} for s in p["selected"]],
                "n_skipped": len(p["skipped"]), "n_not_selected": len(p["not_selected"])}

    def pi_notes(refs):
        out = []
        for r in refs:
            if r.get("tier") != "long_term" or "view_id" not in r:
                continue
            m = next((x for x in mems[r["memory_id"]] if x["version"] == r["version"]), None)
            out.append({"view_id": r["view_id"], "memory_id": r["memory_id"], "key": r["relationship_key"], "version": r["version"], "status": r["status"], "written_at": r["written_at"],
                        "association": " ".join(m["text"]["sentences"]) if m else None, "situations": situations.get((r["memory_id"], r["version"]))})
        return out

    case_index = []
    sources_count = Counter()
    for cid, c in cases.items():
        vs = versions[cid]
        last = vs[-1]
        hids = [h for h, k in case_of.items() if k == cid]
        version_out = []
        for r in vs:
            t = texts[r["finding_id"]]
            failed = None
            if t["source"] != "llm":
                ch = llm.get(r["finding_id"], ([], []))[0]
                failed = [[{"check": x["name"], "detail": x["detail"]} for x in att] for att in ch]
            version_out.append({
                "id": r["finding_id"], "version": r["version"], "t": wall_ms(r["as_of"]), "as_of": r["as_of"], "mode": r["mode"], "handoffs": r["handoff_ids"], "completions": r.get("completion_ids") or [],
                "measures": [{"id": m["measure_id"], "measure": m["measure"], "direction": m["direction"], "strength": m["strength"], "t": wall_ms(m["opened_at"])} for m in r["measures"]],
                "factors": [factor_row(f) for f in r["factors"]], "groups": r["groups"], "history_note": r["history_note"], "not_known_yet": r["not_known_yet"], "repeat": r["repeat"],
                "diary": [dict(diary.get(d["context_id"], {}), id=d["view_id"], context_id=d["context_id"]) for d in r["refs"]["diary"]],
                "state_memory": [{"id": s["view_id"], "window": s["window_id"], "headline": windows.get(s["window_id"])} for s in r["refs"]["state_memory"]],
                "open_week": next((x["finding_ids"] for x in r["refs"]["pi_memories"] if x.get("tier") == "mid_term" and x.get("status") == "open"), []),
                "pi_notes": pi_notes(r["refs"]["pi_memories"]),
                "text": {"headline": t["text"]["headline"], "sentences": sents(t["text"]), "source": t["source"], "from_prompt": t["from_prompt"], "prompt": t["prompt"], "checks": t["checks"], "failed": failed}})
        sources_count[version_out[-1]["text"]["source"]] += 1
        usable = sorted({f["key"] for f in version_out[-1]["factors"] if f["key"] and f["label"] in ("supported", "suggestive") and f["wording"] not in ("not_mentioned", "not_known_yet")})
        detail = {"case": {**c, "t0": wall_ms(c["opened_at"]), "t1": wall_ms(c["closed_at"]) if c["closed_at"] else None, "month": c["local_date"][:7]},
                  "alerts": [{"id": h, "t": wall_ms(handoffs[h]["opened_at"]), **{k: handoffs[h].get(k) for k in ("measure", "direction", "size", "trigger", "value", "clinical_status", "position_z", "usual_basis", "context", "item_id")},
                              "counted": counted.get(h, False)} for h in sorted(hids, key=lambda x: handoffs[x]["opened_at"])],
                  "packets": {h: packet_block(h) for h in hids}, "evidence": {h: evidence_block(h) for h in hids}, "completions": {e["evidence_id"]: completions.get(e["evidence_id"], []) for e in evidence.values() if e["handoff_id"] in hids and completions.get(e["evidence_id"])},
                  "versions": version_out}
        dump(f"case/{cid}.json", detail)
        case_index.append({"id": cid, "date": c["local_date"], "month": c["local_date"][:7], "t0": detail["case"]["t0"], "t1": detail["case"]["t1"], "alerts": c["n_counted"], "unjoined": c["n_recorded"], "versions": c["n_versions"],
                           "mode": last["mode"], "headline": version_out[-1]["text"]["headline"], "first_headline": version_out[0]["text"]["headline"], "source": version_out[-1]["text"]["source"], "measures": sorted({m["measure"] for r in vs for m in r["measures"]}), "keys": usable, "phrases": [phrases(k)[0] for k in usable],
                           "p_notes": len(version_out[-1]["pi_notes"])})
    dump("cases.json", case_index)

    # ---- PI -----------------------------------------------------------------------------------------------------------------------------------------------------
    runs = [json.loads(r[0]) for r in pi.execute("SELECT record_json FROM pi_weekly_runs ORDER BY week")]
    mid = {r[0]: json.loads(r[1]) for r in pi.execute("SELECT week_iso, record_json FROM pi_mid_memories WHERE status = 'sealed'")}
    weeks = [{"week": r["week"], "written_at": r["written_at"], "entries": r["counts"]["entries"], "case_days": r["counts"]["case_days"], "memories_total": r["counts"]["memories_total"], "written": r["counts"]["memories_written"],
              "created": r["memories_created"], "changes": r["statuses_changed"], "touched": r["counts"]["touched"], "keys": (mid.get(r["week"]) or {}).get("relationship_keys_touched", []),
              "cases": sorted({e["case_id"] for e in (mid.get(r["week"]) or {}).get("entries", [])})} for r in runs]
    memories = []
    for mid_id, vs in sorted(mems.items()):
        last = vs[-1]
        ph, oc = phrases(last["relationship_key"])
        memories.append({"memory_id": mid_id, "key": last["relationship_key"], "phrase": ph, "outcome": oc, "status": last["status"], "same_day_only": last["same_day_only"], "created_week": last["created_week"], "counters": last["counters"],
                         "flags": last["flags_seen"], "status_history": last["status_history"], "weekly_labels": [[w["week"], w["label"], w["days_supported"], w["days_in_week"]] for w in last["weekly_labels"]],
                         "versions": [{"version": v["version"], "written_at": v["written_at"], "status": v["status"], "association": " ".join(v["text"]["sentences"]), "situations": situations.get((mid_id, v["version"])),
                                       "case_days": v["counters"]["case_days"], "finding_ids": len(v["finding_ids"])} for v in vs]})
    dump("pi.json", {"weeks": weeks, "memories": memories})

    # ---- quality ------------------------------------------------------------------------------------------------------------------------------------------------
    norm = lambda s: s.strip().lower().rstrip(".!?")
    fb, dup = [], []
    by_check = Counter()
    tokens = Counter()
    for fid, t in texts.items():
        ch, us = llm.get(fid, ([], []))
        if ch and ch[0]:
            for n in {x["name"] for x in ch[0]}:
                by_check[n] += 1
        for u in us:
            tokens["in"] += u.get("input_tokens") or 0
            tokens["out"] += u.get("output_tokens") or 0
        if t["source"] != "llm":
            fb.append({"id": fid, "case": fid.rsplit("_v", 1)[0][4:], "failed": [[{"check": x["name"], "detail": x["detail"]} for x in att] for att in ch]})
        else:
            ss = [norm(s["text"]) for s in sents(t["text"])]
            h, s2 = norm(t["text"]["headline"]) in ss, len(set(ss)) < len(ss)
            if h or s2:
                dup.append({"id": fid, "kind": "headline repeated as a sentence" if h else "sentence written twice"})
    src = Counter("fallback" if t["source"] != "llm" else ("kept from an earlier prompt" if t["from_prompt"] else "model text") for t in texts.values())
    pl = [(json.loads(r[0]), r[1]) for r in pi.execute("SELECT text_json, status FROM pi_text")]
    meta = dict(fd.execute("SELECT key, value FROM meta WHERE key != 'l2_call_log'").fetchall())
    dump("quality.json", {"text_sources": dict(src), "versions": len(texts), "fallbacks": fb, "first_attempt_failures_by_check": dict(by_check), "tokens": dict(tokens), "repeated": dup,
                          "pi_lines": dict(Counter(s for _, s in pl)), "pi_lines_with_text": sum(1 for t, _ in pl if t.get("situations")), "meta": meta})

    # ---- baselines (the Baseline Engine's real window records, with the numbers behind each gist) -----------------------------------------------------------------
    # Display only: names, units and decimals per measure; the "wrong way" direction comes from the State Engine's own config where it has one.
    DISPLAY = [  # key, label, unit, decimals, domain, fallback adverse direction (used only when the State Engine config has none)
        ("cgm_glucose_reading", "Average glucose", "mg/dL", 0, "Glucose", "above"), ("time_in_range", "Time in range", "%", 1, "Glucose", "below"),
        ("variability", "Glucose variability", "%", 1, "Glucose", "above"), ("post_meal_peak", "Post-meal glucose peak", "mg/dL", 0, "Glucose", "above"),
        ("continuous_heart_rate", "Heart rate", "bpm", 0, "Heart", "above"), ("resting_heart_rate", "Resting heart rate", "bpm", 0, "Heart", "above"),
        ("sleep_duration", "Sleep", "h", 1, "Sleep and activity", "below"), ("step_count", "Steps", "per day", 0, "Sleep and activity", "below"), ("sedentary_time", "Sedentary time", "min per day", 0, "Sleep and activity", "above"),
        ("medication_adherence", "Medication taken", "%", 0, "Medicines and mood", "below"), ("mood_state", "Strained periods", "per day", 1, "Medicines and mood", "above"),
        ("hydration", "Hydration", "mL per day", 0, "Lifestyle", "below"), ("screen_time", "Screen time", "h per day", 1, "Lifestyle", "above")]
    state_cfg = yaml.safe_load((ROOT / "config/state_meera_iyer_v1.yaml").read_text(encoding="utf-8"))
    adv_cfg = {k: (v.get("adverse_directions") or [None])[0] for k, v in ((state_cfg.get("state") or {}).get("streams") or {}).items() if isinstance(v, dict)}
    bands_all = json.loads((DATA / "bands.json").read_text(encoding="utf-8")) if (DATA / "bands.json").exists() else {}
    def ref_normal(key):  # the clinical "normal" band, not for glucose (its table is the fasting one; the CGM metrics use management targets)
        if key == "cgm_glucose_reading":
            return None
        nb = next((x for x in (bands_all.get(key) or {}).get("bands", []) if x[2] == "normal"), None)
        return [nb[0], nb[1]] if nb else None
    r2 = lambda v: None if v is None else round(v, 2)
    base = []
    for wid, tier, a, b, notable, reason, conf, rel, hl, gs, gst, dev, fj, tj, dqj in ps.execute(
            "SELECT window_id, tier, start_date, end_date, is_notable, notable_reason, confidence, reliable, gist_headline, gist_sentences, gist_status, deviation_text, facts_json, tags_json, data_quality_json FROM memory_v2 WHERE tier IN ('week','month') ORDER BY tier, end_date"):
        f, t, dq = json.loads(fj), json.loads(tj), json.loads(dqj)
        g = f.get("glucose") or f.get("last_30_days") or {}
        prof = {m: [v["n_days"], r2(v["median"]), r2(v["sd"]), r2(v.get("flat_band")), v.get("usual_status"), r2(v.get("share_non_normal"))] for m, v in (f.get("profile_asof") or {}).items()}
        tags = {x["measure"]: [x["direction"], x["size"], r2(x.get("delta"))] for x in (t.get("tags") or [])}
        row = {"id": wid, "tier": tier, "start": a, "end": b, "notable": bool(notable), "reason": reason, "confidence": conf, "reliable": bool(rel), "headline": hl, "sentences": json.loads(gs) if gs else [], "status": gst, "deviation": dev,
               "vals": {m: r2(v) for m, v in (f.get("window_values") or {}).items()}, "prev": {m: r2(v) for m, v in (f.get("prev_window_values") or {}).items()}, "prof": prof, "tags": tags,
               "glucose": {k: r2(g.get(k)) for k in ("mean", "gmi_pct", "tir_pct", "tar_pct", "tbr_pct", "cv_pct", "min_value", "max_value", "n_readings", "completeness_pct")}, "days": f.get("n_days"), "history_days": f.get("days_of_data_so_far")}
        base.append(row)
        if tier == "month":
            last_month = f
    dump("baselines.json", base)
    dump("baseline_meta.json", {
        "measures": [{"key": k, "label": lb, "unit": u, "decimals": d, "domain": dm, "adverse": adv_cfg.get(k) or fb, "adverse_from": "state engine config" if adv_cfg.get(k) else "display default", "ref": ref_normal(k)} for k, lb, u, d, dm, fb in DISPLAY],
        "labs": last_month.get("lab_link") or [], "chronic": last_month.get("chronic_findings") or []})

    # ---- the pipeline overview --------------------------------------------------------------------------------------------------------------------------------
    def csv_rows(name, n=3, where=None):
        with (OUT / name).open(encoding="utf-8", newline="") as f:
            rows = list(csv.DictReader(f))
        sel = [r for r in rows if where is None or where(r)]
        return len(rows), sel[:n]

    n_thr, thr_s = csv_rows("threshold_evaluation_results.csv", 3, lambda r: r["status"] not in ("normal", ""))
    n_pl, pl_s = csv_rows("plausibility_filter_results.csv", 3, lambda r: r["filter_result"] != "PASS")
    with (OUT / "plausibility_filter_results.csv").open(encoding="utf-8", newline="") as fh:
        n_rej = sum(1 for r in csv.DictReader(fh) if r["filter_result"] != "PASS")
    n_pair, pair_s = csv_rows("short_range_pairings.csv", 3)
    items = st.execute("SELECT item_class, COUNT(*) FROM state_items GROUP BY 1").fetchall()
    base_counts = ps.execute("SELECT tier, gist_status, COUNT(*) FROM memory_v2 GROUP BY 1, 2").fetchall()
    pair_types = ps.execute("SELECT candidate_type, COUNT(*) FROM raw_events WHERE candidate_type IS NOT NULL GROUP BY 1").fetchall()
    modes = Counter(c["mode"] for c in case_index)
    fcounts = Counter(c["source"] for c in case_index)
    h1 = next(iter(handoffs.values()))
    # ---- one real reading for each status, for the Plausibility / Threshold page -------------------------------------------------------------------------------
    with (OUT / "threshold_evaluation_results.csv").open(encoding="utf-8", newline="") as fh:
        thr_rows = list(csv.DictReader(fh))
    bands_json = json.loads((DATA / "bands.json").read_text(encoding="utf-8"))
    def pick(status, biomarker, how):
        rows = [r for r in thr_rows if r["status"] == status and r["biomarker"] == biomarker]
        vals = sorted(float(r["value"]) for r in rows)
        target = how(vals)
        r = min(rows, key=lambda x: (abs(float(x["value"]) - target), x["timestamp"]))
        b = bands_json.get(biomarker, {})
        return {"status": status, "biomarker": biomarker, "value": float(r["value"]), "when": r["timestamp"], "event_id": r["event_id"], "age_group": r["age_group_used"], "unit": b.get("unit"), "bands": b.get("bands"),
                "of_status": len(rows), "of_measure": sum(1 for x in thr_rows if x["biomarker"] == biomarker)}
    threshold_examples = [
        pick("normal", "resting_heart_rate", lambda v: v[len(v) // 2]), pick("borderline_high", "cgm_glucose_reading", lambda v: 112.0), pick("high", "hba1c", lambda v: v[-1]),
        pick("low", "sleep_duration", lambda v: v[0]), pick("borderline_low", "hydration", lambda v: 1750.0)]
    for e in threshold_examples:
        e["label"] = {"resting_heart_rate": "Resting heart rate", "cgm_glucose_reading": "CGM glucose", "hba1c": "HbA1c (lab)", "sleep_duration": "Sleep", "hydration": "Hydration"}[e["biomarker"]]

    # ---- the linker's flow numbers and one glucose reading with all its pairings ----------------------------------------------------------------------------------
    gl_status = Counter(r["status"] for r in thr_rows if r["biomarker"] == "cgm_glucose_reading")
    with (OUT / "short_range_pairings.csv").open(encoding="utf-8", newline="") as fh:
        pair_rows = list(csv.DictReader(fh))
    by_reading = defaultdict(list)
    for r in pair_rows:
        by_reading[(r["glucose_event_id"], r["glucose_timestamp"])].append(r)
    ex_key = ("evt_glu_00056", "2025-10-01T13:45:00+05:30")
    ex = by_reading[ex_key]
    linker_flow = {"status_rows": len(thr_rows), "glucose_status": dict(gl_status), "linked": gl_status["high"] + gl_status["low"], "pairings": len(pair_rows), "readings_linked": len(by_reading),
                   "context_streams": dict(ps.execute("SELECT stream, COUNT(*) FROM context_events GROUP BY stream ORDER BY 2 DESC").fetchall()),
                   "store_readings": ps.execute("SELECT COUNT(*) FROM raw_events WHERE source_type='reading'").fetchone()[0], "store_pairings": ps.execute("SELECT COUNT(*) FROM raw_events WHERE source_type='pairing'").fetchone()[0]}
    linker_example = {"event_id": ex_key[0], "when": ex_key[1], "value": float(ex[0]["glucose_value"]), "status": ex[0]["glucose_status"],
                      "pairings": [{"type": x["candidate_type"], "when": x["candidate_timestamp"], "lag": float(x["lag_minutes"]) if x["lag_minutes"] else None, "summary": x["candidate_summary"]} for x in ex]}

    # ---- the Baseline Engine's process numbers and one worked window --------------------------------------------------------------------------------------
    bl_tier = {}
    removed_total, removed_days, removed_ex = 0, 0, []
    for tier, notable, mat, dqj in ps.execute("SELECT tier, is_notable, material_changes_json, data_quality_json FROM memory_v2"):
        t = bl_tier.setdefault(tier, {"windows": 0, "notable": 0, "quiet": 0})
        t["windows"] += 1
        t["notable"] += 1 if notable else 0
        t["quiet"] += 1 if not json.loads(mat) else 0
        if tier == "day":
            q = (json.loads(dqj).get("questionable_readings") or [])
            removed_total += len(q)
            removed_days += 1 if q else 0
            removed_ex += q
    row = ps.execute("SELECT facts_json, tags_json, material_changes_json, anchors_crossed, notable_reason, gist_headline, gist_sentences, gist_status, data_quality_json FROM memory_v2 WHERE window_id='week_ENDING_2026-09-17'").fetchone()
    wf, wt, wm = json.loads(row[0]), json.loads(row[1]), json.loads(row[2])
    kinds = Counter(x["kind"] for x in wm)
    baseline_flow = {"tiers": bl_tier, "removed": removed_total, "removed_days": removed_days, "removed_examples": removed_ex, "learning_days": 14,
                     "in_status_rows": ps.execute("SELECT COUNT(*) FROM raw_events WHERE source_type='reading'").fetchone()[0], "in_context": ps.execute("SELECT COUNT(*) FROM context_events").fetchone()[0],
                     "not_used_pairings": ps.execute("SELECT COUNT(*) FROM raw_events WHERE source_type='pairing'").fetchone()[0], "not_used_hourly_steps": ps.execute("SELECT COUNT(*) FROM context_events WHERE stream='step_count_hourly'").fetchone()[0]}
    baseline_example = {"id": "week_ENDING_2026-09-17", "start": wf["start_date"], "end": wf["end_date"], "n_days": wf["n_days"], "glucose": wf["glucose"], "daily": wf["daily_trajectory"],
                        "per_medication": wf["aggregates"]["adherence"]["per_medication"], "prev": wf["prev_window_values"], "vals": wf["window_values"],
                        "prof": {m: [v["n_days"], v["median"], v["sd"], v["flat_band"]] for m, v in wf["profile_asof"].items()}, "tags": wt["tags"], "material_kinds": dict(kinds),
                        "material": wm, "anchors": json.loads(row[3]) if row[3] else [], "reason": row[4], "headline": row[5], "sentences": json.loads(row[6]), "gist_status": row[7], "removed": len((json.loads(row[8]).get("questionable_readings") or []))}

    # ---- State Engine: one adverse item (with its hand-off) and one favourable item, followed tick by tick ----------------------------------------------------------
    def _snap(as_of):
        r = st.execute("SELECT snapshot_json, n_open_items FROM state_log WHERE as_of = ?", (as_of,)).fetchone()
        return (json.loads(r[0]), r[1]) if r else (None, None)
    def _story(item_id, before=4, after=3):
        it = st.execute("SELECT item_id, measure, direction, size_at_open, size_peak, opened_at, peak_at, closed_at, peak_value, trigger, status, item_class, close_reason FROM state_items WHERE item_id = ?", (item_id,)).fetchone()
        cols = ["item_id", "measure", "direction", "size_at_open", "size_peak", "opened_at", "peak_at", "closed_at", "peak_value", "trigger", "status", "item_class", "close_reason"]
        item = dict(zip(cols, it))
        ticks_all = [r[0] for r in st.execute("SELECT as_of FROM state_log WHERE as_of >= ? AND as_of <= ? ORDER BY as_of", (item["opened_at"][:10] + "T00:00:00+05:30", (item["closed_at"] or item["opened_at"])[:10] + "T23:59:59+05:30"))]
        i0, i1 = ticks_all.index(item["opened_at"]), ticks_all.index(item["closed_at"])
        pts = []
        for ts in ticks_all[max(0, i0 - before): i1 + after + 1]:
            snap, n_open = _snap(ts)
            m = snap["measures"][item["measure"]]
            pos = m.get("position") if isinstance(m.get("position"), dict) else {}
            pts.append({"t": ts, "v": m.get("value"), "med": (m.get("usual") or {}).get("median"), "sd": (m.get("usual") or {}).get("sd"), "z": pos.get("z"), "label": pos.get("label"), "run": (m.get("run") or {}).get("count"), "close_run": (m.get("run") or {}).get("close_count"), "open": m.get("open_item_id") == item_id})
        item["points"] = pts
        item["unit"] = snap["measures"][item["measure"]].get("unit")
        h = st.execute("SELECT record_json FROM state_handoffs WHERE item_id = ?", (item_id,)).fetchone()
        item["handoff"] = json.loads(h[0]) if h else None
        return item
    def _tick_table(as_of):
        snap, n_open = _snap(as_of)
        rows = []
        for k, m in snap["measures"].items():
            v = m.get("value")
            if isinstance(v, dict):
                v = "/".join(str(int(x)) for x in v.values())
            if k == "medication_adherence":
                v = f"{m.get('taken')} of {m.get('expected')}"
            if k == "mood_state":
                v = m.get("label")
            us = m.get("usual") or {}
            pos = m.get("position") if isinstance(m.get("position"), dict) else {}
            rows.append({"measure": k, "value": v, "unit": m.get("unit"), "median": us.get("median"), "sd": us.get("sd"), "z": pos.get("z"), "label": pos.get("label"), "clinical": m.get("clinical_status"), "open_item": m.get("open_item_id"), "item_class": m.get("open_item_class"), "age": m.get("age_minutes"), "current": m.get("current")})
        return {"as_of": snap["as_of"], "n_open": n_open, "rows": rows}
    state_story = {"adverse": _story("glucose_2025-11-18T11:15"), "favourable": _story("glucose_2026-03-04T20:00")}
    state_story["tick"] = _tick_table(state_story["adverse"]["opened_at"])
    state_story["ticks_total"] = st.execute("SELECT COUNT(*) FROM state_log").fetchone()[0]

    # ---- the whole rulebook (10 rules, 69 candidates) with how each candidate was used across the year's packets --------------------------------------------------
    rule_rows = list(csv.DictReader((ROOT / "task/evidence_engine/rulebook_v0_rules.csv").open(encoding="utf-8", newline="")))
    cand_rows = list(csv.DictReader((ROOT / "task/evidence_engine/rulebook_v0_candidates.csv").open(encoding="utf-8", newline="")))
    use = defaultdict(lambda: {"selected": 0, "skipped": Counter(), "not_selected": Counter()})
    rule_alerts = Counter()
    for (pj,) in rb.execute("SELECT packet_json FROM rulebook_packets"):
        pk = json.loads(pj); rid = pk["matched_rule"]["rule_id"]; rule_alerts[rid] += 1
        for x in pk["selected"]:
            use[(rid, x["candidate"])]["selected"] += 1
        for x in pk["skipped"]:
            use[(rid, x["candidate"])]["skipped"][f'{x["reason"]}|{x.get("detail") or ""}'] += 1
        for x in pk["not_selected"]:
            use[(rid, x["candidate"])]["not_selected"][x["reason"]] += 1
    rulebook_table = []
    for r in rule_rows:
        cands = []
        for c in sorted((x for x in cand_rows if x["rule_id"] == r["rule_id"]), key=lambda x: int(x["rank"])):
            u = use[(r["rule_id"], c["candidate"])]
            cands.append({"rank": int(c["rank"]), "tier": c["weight_tier"], "candidate": c["candidate"], "requires": c["requires_streams"], "lookback": c["lookback_text"], "applies_if": c["applies_if_text"], "applies_code": c["applies_if_rule"],
                          "check": c["check_text"], "outcome": c["outcome_compared_text"], "level": c["evidence_level"], "data_kinds": c["data_kinds_text"], "her_data": c["meera_data_status_text"], "her_code": c["data_status_meera_code"],
                          "note": c["note"], "selected": u["selected"], "skipped": dict(u["skipped"]), "not_selected": dict(u["not_selected"])})
        rulebook_table.append({"rule_id": r["rule_id"], "measure": r["measure"], "direction": r["direction"], "when": r["context_condition"], "match": r["context_match"], "status": r["status"], "alerts": rule_alerts[r["rule_id"]],
                               "primary": int(r["primary_count"]), "secondary": int(r["secondary_max"]), "tertiary": int(r["tertiary_max"]), "max_total": int(r["max_total"]), "why_budget": r["budget_reason"], "review": r["review_status"], "candidates": cands})

    stages = [
        {"n": 1, "id": "threshold", "name": "Plausibility filter and Threshold evaluator", "db": "output/*.csv (threshold_evaluation_results.csv, plausibility_filter_results.csv)",
         "in": "Raw readings from the patient files (glucose, vitals, sleep, steps, labs, ...)", "out": "Each reading passed or rejected, and every passed reading with a status against its reference range",
         "counts": {"readings checked": n_pl, "rejected": n_rej, "status rows": n_thr}, "sample": {"rejected": pl_s, "abnormal": thr_s}, "examples": threshold_examples, "next": "readings with a status feed the Linker and the Store"},
        {"n": 2, "id": "linker", "name": "Short-range linker and Personal Data Store", "db": "output/personal_data_store.db (raw_events, context_events)",
         "in": "Threshold results (high or low glucose readings) and the context streams (meals, medication, activity, sleep, mood, diary, heart rate)", "out": "Pairings of each glucose reading with what happened nearby; the store that every later component reads",
         "counts": {"pairings": n_pair, **{f"pairings: {k}": v for k, v in pair_types}, "store rows": ps.execute("SELECT COUNT(*) FROM raw_events").fetchone()[0], "context events": ps.execute("SELECT COUNT(*) FROM context_events").fetchone()[0]}, "sample": {"pairings": pair_s}, "flow": linker_flow, "example": linker_example, "next": "the store is read by Baseline and State"},
        {"n": 3, "id": "baseline", "name": "Baseline Engine v2", "db": "output/personal_data_store.db (memory_v2)",
         "in": "The store: her readings and context by day", "out": "Day, week and month windows: what she usually does, what moved, material changes, and a short gist (code facts, model words)",
         "counts": {f"{t} windows ({s})": n for t, s, n in base_counts}, "sample": {"week": next((b for b in base if b["tier"] == "week" and b["notable"]), None)}, "flow": baseline_flow, "example_week": baseline_example, "next": "the State Engine reads her usual from these windows"},
        {"n": 4, "id": "state", "name": "State Engine", "db": "output/state_engine.db (state_items, state_handoffs, state_log)",
         "in": "The latest reading of each measure, her baseline", "out": "Deviation items that open and close, and an alert (hand-off) for each item that matters",
         "counts": {"ticks (15 minutes)": st.execute("SELECT COUNT(*) FROM state_log").fetchone()[0], "items": st.execute("SELECT COUNT(*) FROM state_items").fetchone()[0], **{f"items {k}": v for k, v in items}, "alerts": len(handoffs)},
         "sample": {"alert": {k: h1.get(k) for k in ("handoff_id", "measure", "direction", "size", "trigger", "value", "opened_at")}}, "story": state_story, "next": "each alert goes to the Rulebook Lookup (handoff_id)"},
        {"n": 5, "id": "rulebook", "name": "Rulebook Lookup", "db": "output/rulebook_lookup.db (rulebook_packets)",
         "in": "An alert", "out": "A packet: the ordered checklist of candidate factors to test (meal, sleep, medication, activity, ...) with the window to look in",
         "counts": {"packets": len(packets), **{f"packets {k}": v for k, v in Counter(packet_status.values()).items()}}, "sample": {"packet": packet_block(next(h for h in packets if packet_status[h] == "ok"))}, "rulebook_table": rulebook_table, "next": "the packet goes to the Evidence Engine (packet_id, handoff_id)"},
        {"n": 6, "id": "evidence", "name": "Evidence Engine", "db": "output/evidence_engine.db (event_evidence, relationship_evidence, event_completions)",
         "in": "A packet and her whole history", "out": "For each candidate factor a label (supported, suggestive, not supported, insufficient) with the statistics behind it; a daily record for every tested relationship",
         "counts": {"alert records": len(evidence), "completions": sum(len(v) for v in completions.values()), "daily relationship records": ev.execute("SELECT COUNT(*) FROM relationship_evidence").fetchone()[0],
                    **{f"daily labels {k}": v for k, v in ev.execute("SELECT json_extract(record_json, '$.support'), COUNT(*) FROM relationship_evidence GROUP BY 1").fetchall()}},
         "sample": {"evidence": evidence_block(next(h for h in evidence if any(f["support"] == "supported" for f in evidence[h]["factors"])))}, "next": "evidence of each alert goes to the Findings Engine (evidence_id = ev_<handoff_id>)"},
        {"n": 7, "id": "findings", "name": "Findings Engine", "db": "output/findings_loop_polish.db (cases, findings, finding_text)",
         "in": "Alerts, their evidence, diary and earlier summaries, and PI's earlier conclusions", "out": "Cases (alerts close in time) with a version each time something new arrives: a structured layer decided by code, and a text written from it",
         "counts": {"cases": len(cases), "versions": sum(len(v) for v in versions.values()), **{f"cases ({k} mode)": v for k, v in modes.items()}, **{f"text: {k}": v for k, v in src.items()}},
         "sample": {"case": case_index[40]}, "next": "every version goes into PI's open week (finding_id)"},
        {"n": 8, "id": "pi", "name": "PI (memory of findings)", "db": "output/pi_loop_polish.db (pi_mid_entries, pi_long_memories, pi_text)",
         "in": "Every version, weekly", "out": "Weekly memories and a long-term note for each relationship (candidate, supported, weakened, retracted) with its association sentence and a situations line; read back by Findings",
         "counts": {"weekly jobs": len(runs), "relationships": len(mems), "memory versions": sum(len(v) for v in mems.values()), **{f"final status: {k}": v for k, v in Counter(m["status"] for m in memories).items()}},
         "sample": {"memory": memories[0]}, "next": "long-term notes are referenced by later versions (refs.pi_memories)"},
    ]
    # ---- the tested relationships (one row each, with how often each label was given) ----------------------------------------------------------------------
    rels = {}
    for k, lab, n, last in ev.execute("SELECT relationship_key, json_extract(record_json,'$.support'), COUNT(*), MAX(as_of_date) FROM relationship_evidence GROUP BY 1, 2"):
        r = rels.setdefault(k, {"key": k, "days": {}})
        r["days"][lab] = n
    for k, r in rels.items():
        r["phrase"], r["outcome"] = phrases(k)
        r["group"] = parse_key(k)[2]
        r["same_day_unverified"] = bool(ev.execute("SELECT 1 FROM relationship_evidence WHERE relationship_key=? AND record_json LIKE '%same_day_unverified%' LIMIT 1", (k,)).fetchone())
        r["latest"] = json.loads(ev.execute("SELECT record_json FROM relationship_evidence WHERE relationship_key=? ORDER BY as_of_date DESC LIMIT 1", (k,)).fetchone()[0])["support"]
    next(x for x in stages if x["id"] == "evidence")["relationships"] = sorted(rels.values(), key=lambda r: (r["group"], r["key"]))

    dump("pipeline.json", {"stages": stages, "versions": {"findings": meta, "state": [r[0] for r in st.execute("SELECT DISTINCT config_version FROM state_log LIMIT 3")],
                                                         "rulebook": next(iter(packets.values()))["rulebook_version"], "evidence": next(iter(evidence.values()))["method_version"]},
                            "months": sorted({a["month"] for a in alerts}), "alerts_by_month": dict(Counter(a["month"] for a in alerts)), "cases_by_month": dict(Counter(c["month"] for c in case_index))})
    print(f"Wrote pipeline data to {DATA}: {len(alerts)} alerts, {len(case_index)} cases, {len(memories)} memories, {len(base)} baseline windows")


if __name__ == "__main__":
    main()
