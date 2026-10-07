"""The F2 sample report: every sampled version with its text, checks and source; first-attempt failure rates per check; retries, fallbacks, tokens and time; an audit of
sentences against their wording classes (a heuristic scan for a human to read, not a check). Reads the sample log written by `run_text`."""

import json
import re
import sys
from collections import Counter
from pathlib import Path

from v0_code.findings_engine.view import INTERNAL_WORDING, thing_index

LINKING = re.compile(r"\b(tended|linked|associated|together|goes? with|alongside|accompan\w*|coincid\w*|related|connected|tied to|contrasts?|moves? with|rises? with|go hand)\b", re.I)
RECURRENCE = r"come up before|came up before|has come up|have come up|early observation"
PI_WORDS = re.compile(r"come up before|early observation|has come up|came up before", re.I)
CLAIM = ("asserted", "asserted_same_day", "hedged", "hedged_same_day")


def load(path: Path) -> list[dict]:
    return [json.loads(l) for l in open(path)]


def audit_classes(rows: list[dict]) -> list[str]:
    flags = []
    for r in rows:
        if r["result"]["text_source"] != "llm":
            continue
        by_id = thing_index(r["view"])
        for i, s in enumerate(r["result"]["text"]["sentences"], 1):
            bundles = {g["id"]: g["members"] for g in r["view"]["sets"]}
            refs = [m for x in s["refs"] for m in [x] + bundles.get(x, [])]
            classes = [INTERNAL_WORDING[by_id[x]["wording"]] for x in refs if x in by_id]
            contrary_only = "contrary_note" in classes and re.search(r"\btended to be (lower|higher|smaller|longer|fewer)\b", s["text"], re.I)
            if LINKING.search(s["text"]) and any(c not in CLAIM for c in classes) and not contrary_only:
                flags.append(f"{r['finding_id']} s{i}: linking wording with cited class {sorted(set(classes))}: {s['text']}")
            if PI_WORDS.search(s["text"]) and not r["view"]["earlier_conclusions"]:
                flags.append(f"{r['finding_id']} s{i}: PI-style wording ('come up before' / 'early observation') but the view has no PI items: {s['text']}")
            if re.search(r"\b(has|have) tended to move\b|\bmay be linked\b", s["text"], re.I) and not any(c in CLAIM for c in classes):
                flags.append(f"{r['finding_id']} s{i}: claim wording but no claim-class factor cited: {s['text']}")
    return flags


def make_report(log: Path, text_cfg: dict, pb, out: Path) -> str:
    rows = load(log)
    n = len(rows)
    first = [r["result"]["checks"][0] for r in rows if not r["from_cache"] or True]
    per_check_versions = Counter()
    per_check_instances = Counter()
    for r in rows:
        ch = r["result"]["checks"]
        for f in ch[0]:
            per_check_instances[f["check"]] += 1
        for c in {f["check"] for f in ch[0]}:
            per_check_versions[c] += 1
    names = {0: "call error", 1: "1 structure", 2: "2 refs exist", 3: "3 digits, dates, counting words", 4: "4 causal wording", 5: "5 copied diary text / internal words", 6: "6 claim level", 7: "7 required statements", 8: "8 recurrence wording"}
    usage = [u for r in rows for u in r["result"]["usage"]]
    retried = sum(len(r["result"]["checks"]) > 1 for r in rows)
    fallback = [r for r in rows if r["result"]["status"] != "ok"]
    o = ["# Findings Engine, stage F2: text layer, sample report\n",
         f"{n} versions from `{log.name}`; model `{text_cfg['model']}`, reasoning `{text_cfg['reasoning_effort']}`, timeout {text_cfg['timeout_seconds']} s, SDK retries {text_cfg['sdk_retries']}, one retry with the failed checks, then the code line.\n",
         "## Totals\n",
         f"- versions with a first-attempt failure: **{sum(bool(r['result']['checks'][0]) for r in rows)} of {n}** ({100 * sum(bool(r['result']['checks'][0]) for r in rows) / n:.0f}%)",
         f"- retried: {retried}; passed on the retry: {retried - len(fallback)}; **fallbacks to the code line: {len(fallback)} of {n}** ({100 * len(fallback) / n:.0f}%)",
         f"- model calls: {len(usage)}; tokens in {sum(u.get('input_tokens') or 0 for u in usage):,}, out {sum(u.get('output_tokens') or 0 for u in usage):,} (of which reasoning {sum(u.get('reasoning_tokens') or 0 for u in usage):,}); "
         f"call seconds {sum(u['wall_seconds'] for u in usage):.0f} in total, mean {sum(u['wall_seconds'] for u in usage) / len(usage):.1f}, longest {max(u['wall_seconds'] for u in usage):.1f}\n",
         ] + before_after(rows, before_log, rerun_log) + [
         "## First-attempt failures by check\n", "| check | versions failing at the first attempt | failure instances |", "|---|---:|---:|"]
    for c in range(0, 9):
        if c in per_check_versions or c in range(1, 9):
            o.append(f"| {names[c]} | {per_check_versions.get(c, 0)} ({100 * per_check_versions.get(c, 0) / n:.0f}%) | {per_check_instances.get(c, 0)} |")
    recur = [(r["finding_id"], x["text"], x["refs"]) for r in rows if r["result"]["text_source"] == "llm" for x in r["result"]["text"]["sentences"] if re.search(RECURRENCE, x["text"], re.I)]
    with_p = [t for t in recur if any(ref.startswith("p") for ref in t[2])]
    o.append(f"\n## Recurrence wording\n\nSentences using \"come up before\" or \"early observation\": {len(recur)}; with a p ref: {len(with_p)}; without one: {len(recur) - len(with_p)}.\n")
    summ = [(r["finding_id"], x["text"]) for r in rows if r["result"]["text_source"] == "llm" for x in r["result"]["text"]["sentences"] if re.search(r"earlier summary", x["text"], re.I)]
    o.append(f"Sentences saying \"an earlier summary\": {len(summ)}.\n")
    o.append("\n## Sentences against their wording classes (heuristic scan, for a human to read)\n")
    flags = audit_classes(rows)
    o += [f"- {f}" for f in flags] or ["- none"]
    o.append("\n## Every sampled version\n")
    for r in rows:
        res = r["result"]
        o.append(f"### {r['finding_id']} ({r['why']})\n")
        o.append(f"source `{res['text_source']}`, status `{res['status']}`, attempts {len(res['checks'])}, mode {r['view']['situation']['mode']}, view `{r['view_hash'][:10]}`\n")
        o.append(f"**{res['text']['headline']}**\n")
        for s in res["text"]["sentences"]:
            o.append(f"- {s['text']} `{s['refs']}`")
        for a, f in enumerate(res["checks"], 1):
            o.append(f"\n- attempt {a}: " + ("pass" if not f else "; ".join(f"check {x['check']}: {x['detail']}" for x in f)))
        if res["usage"]:
            o.append("- usage: " + ", ".join(f"{u.get('input_tokens')}/{u.get('output_tokens')} tokens {u['wall_seconds']} s" for u in res["usage"]))
        o.append("")
    out.write_text("\n".join(o))
    return "\n".join(o)


SCAN_WORDS = re.compile(r"\bexplanation\b|\breason\w*\b|\bwhy\b|\bbecause of\b|\bresult\w*\b", re.I)


def clinical_term_hits(rows: list[dict], pb) -> list[tuple]:
    """(finding id, term, sentence) for every clinical term in a model-written text that is not in the version's own view."""
    from v0_code.findings_engine.textcheck import view_text
    out = []
    for r in rows:
        if r["result"]["text_source"] != "llm":
            continue
        vt = view_text(r["view"])
        texts = [r["result"]["text"]["headline"]] + [x["text"] for x in r["result"]["text"]["sentences"]]
        for term in pb.raw["clinical_terms"]:
            pat = rf"\b{re.escape(term.lower())}(?:s|es)?\b"
            if re.search(pat, vt):
                continue
            out += [(r["finding_id"], term, t) for t in texts if re.search(pat, t.lower())]
    return out


def read_list(rows: list[dict], named_cases, seed: int, n_seeded: int = 30, n_early_descriptive: int = 5, early_before: str = "2025-12-10") -> list[tuple[str, dict]]:
    """Every fallback, every version with an entangled bundle, every artifact version, every version of the named cases, then `n_seeded` more by a fixed seed across months
    (at least `n_early_descriptive` of them descriptive versions before `early_before`)."""
    import random
    chosen: dict = {}

    def add(r, why):
        chosen.setdefault(r["finding_id"], (why, r))

    for r in rows:
        if r["result"]["status"] != "ok":
            add(r, "fallback")
    for r in rows:
        if any(b["reason"] == "often_together" for b in r["view"]["sets"]):
            add(r, "entangled bundle")
    for r in rows:
        if any(p["wording"] == "artifact_note" for p in r["view"]["things"]):
            add(r, "artifact case")
    for r in rows:
        if any(r["finding_id"].startswith(f"fnd_{c}_v") for c in named_cases):
            add(r, "named case")
    rng = random.Random(seed)
    rest = sorted((r for r in rows if r["finding_id"] not in chosen), key=lambda r: r["finding_id"])
    date = lambda r: r["finding_id"][9:19]
    early = [r for r in rest if date(r) < early_before and r["view"]["situation"]["mode"] == "describe_only"]
    rng.shuffle(early)
    for r in early[:n_early_descriptive]:
        add(r, "seeded: early descriptive")
    rest = [r for r in rest if r["finding_id"] not in chosen]
    months = sorted({date(r)[:7] for r in rest})
    pool = {m: [r for r in rest if date(r)[:7] == m] for m in months}
    for m in months:
        rng.shuffle(pool[m])
    k = 0
    target = n_seeded - min(n_early_descriptive, len(early))
    while k < target and any(pool.values()):
        for m in months:
            if pool[m] and k < target:
                add(pool[m].pop(), "seeded: across months")
                k += 1
    return list(chosen.values())


def stats(rows: list[dict]) -> dict:
    res = lambda r: r["result"]
    usage = [u for r in rows for u in res(r)["usage"]]
    return {"n": len(rows), "first_fail": sum(bool(res(r)["checks"] and res(r)["checks"][0]) for r in rows), "fallbacks": sum(res(r)["status"] != "ok" for r in rows),
            "retried": sum(len(res(r)["checks"]) > 1 for r in rows), "appended": sum(bool((res(r)["text"] or {}).get("appended")) for r in rows if res(r)["text_source"] == "llm"),
            "cleaned": sum(bool((res(r)["text"] or {}).get("cleaned")) for r in rows if res(r)["text_source"] == "llm"), "calls": len(usage),
            "tokens_in": sum(u.get("input_tokens") or 0 for u in usage), "tokens_out": sum(u.get("output_tokens") or 0 for u in usage)}


def before_after(rows: list[dict], before_log: Path | None, rerun_log) -> list[str]:
    if before_log is None:
        return []
    b, a = stats(load(before_log)), stats(rows)
    o = ["## Before and after this round\n", "| | before this round | after this round |", "|---|---:|---:|",
         f"| first-attempt failures | {b['first_fail']} ({100 * b['first_fail'] / b['n']:.1f}%) | {a['first_fail']} ({100 * a['first_fail'] / a['n']:.1f}%) |",
         f"| retried | {b['retried']} | {a['retried']} |", f"| fallbacks to the code line | {b['fallbacks']} ({100 * b['fallbacks'] / b['n']:.1f}%) | {a['fallbacks']} ({100 * a['fallbacks'] / a['n']:.1f}%) |",
         f"| versions with a code-appended sentence | 0 | {a['appended']} |", f"| versions the cleanup changed | 0 | {a['cleaned']} |"]
    if rerun_log is not None:
        logs = rerun_log if isinstance(rerun_log, (list, tuple)) else [rerun_log]
        rr = [r for lg in logs for r in load(lg) if not r["from_cache"]]
        st = stats(rr)
        o += ["", f"Model work of this round (no-model re-check first, then the model for {len(rr)} versions): **{st['calls']} calls**, tokens in {st['tokens_in']:,}, out {st['tokens_out']:,}, "
              f"call seconds {sum(u['wall_seconds'] for r in rr for u in r['result']['usage']):.0f}; fallbacks among them {st['fallbacks']}."]
    prev = {r["finding_id"]: r for r in load(before_log)}
    o += ["", f"Of the {b['fallbacks']} earlier fallbacks, now accepted: {sum(1 for fid, r in prev.items() if r['result']['status'] != 'ok' and next((x for x in rows if x['finding_id'] == fid))['result']['status'] == 'ok')}; "
          f"versions that were accepted before and are fallbacks now: {sum(1 for fid, r in prev.items() if r['result']['status'] == 'ok' and next((x for x in rows if x['finding_id'] == fid))['result']['status'] != 'ok')}.", ""]
    return o


def make_full_report(log: Path, text_cfg: dict, out: Path, named_cases, seed: int, wall: str = "", before_log: Path | None = None, rerun_log: Path | None = None, n_seeded: int = 30,
                     title: str = "full run report", checks_version: str = "ck-v3", pb=None, recheck_log: Path | None = None, prev_log: Path | None = None) -> str:
    rows = load(log)
    n = len(rows)
    res = lambda r: r["result"]
    mode = lambda r: r["view"]["situation"]["mode"]
    fail1 = [r for r in rows if res(r)["checks"][0]]
    names = {0: "call error", 1: "1 structure", 2: "2 refs exist", 3: "3 digits, dates, counting words, view ids", 4: "4 causal wording", 5: "5 copied diary text / internal words", 6: "6 claim level",
             7: "7 required statements", 8: "8 recurrence wording", 9: "9 often-together wording", 10: "10 one summary sentence", 11: "11 clinical term not in the view", 12: "12 object of a claim", 13: "13 repeated phrase"}
    usage = [u for r in rows for u in res(r)["usage"]]
    fallback = [r for r in rows if res(r)["status"] != "ok"]
    retried = [r for r in rows if len(res(r)["checks"]) > 1]
    sents = [len(res(r)["text"]["sentences"]) + 1 for r in rows if res(r)["text_source"] == "llm"]
    o = [f"# Findings Engine, stage F2: text layer, {title}\n",
         f"{n} versions from `{log.name}`; model `{text_cfg['model']}`, reasoning `{text_cfg['reasoning_effort']}`, one retry with the failed checks, then the code line. Checks version `{checks_version}`.\n",
         "## Totals\n",
         f"- first-attempt failures: **{len(fail1)} of {n} ({100 * len(fail1) / n:.1f}%)**",
         f"- retried: {len(retried)}; passed on the retry: {len(retried) - len(fallback)}; **fallbacks to the code line: {len(fallback)} ({100 * len(fallback) / n:.1f}%)**",
         f"- model stored attempts {len(usage)}; tokens in {sum(u.get('input_tokens') or 0 for u in usage):,}, out {sum(u.get('output_tokens') or 0 for u in usage):,} (reasoning {sum(u.get('reasoning_tokens') or 0 for u in usage):,}); "
         f"call seconds {sum(u['wall_seconds'] for u in usage):.0f}, mean {sum(u['wall_seconds'] for u in usage) / len(usage):.1f}, longest {max(u['wall_seconds'] for u in usage):.1f}" + (f"; wall time of the run {wall}" if wall else ""),
         f"- sentences per model-written version (headline included): mean {sum(sents) / len(sents):.1f}, " + ", ".join(f"{k}: {v}" for k, v in sorted(Counter(sents).items())) + "\n",
         "## First-attempt failures by check\n", "| check | versions | share of all versions |", "|---|---:|---:|"]
    i = o.index("## First-attempt failures by check\n")
    o[i:i] = before_after(rows, before_log, rerun_log)
    by_check = Counter(c for r in fail1 for c in {f["check"] for f in res(r)["checks"][0]})
    for c in sorted(names):
        if c in by_check or c in range(1, 14):
            o.append(f"| {names[c]} | {by_check.get(c, 0)} | {100 * by_check.get(c, 0) / n:.1f}% |")
    o.append("\n## By mode\n\n| mode | versions | first-attempt failures | fallbacks |\n|---|---:|---:|---:|")
    for m in sorted({mode(r) for r in rows}):
        sub = [r for r in rows if mode(r) == m]
        o.append(f"| {m} | {len(sub)} | {sum(bool(res(r)['checks'][0]) for r in sub)} ({100 * sum(bool(res(r)['checks'][0]) for r in sub) / len(sub):.1f}%) | {sum(res(r)['status'] != 'ok' for r in sub)} |")
    o.append("\n## Fallbacks and why\n")
    for r in fallback:
        o.append(f"- {r['finding_id']}: " + " | ".join(f"attempt {i}: " + "; ".join(f"check {f['check']} {f['detail'][:110]}" for f in att) for i, att in enumerate(res(r)["checks"], 1)))
    if not fallback:
        o.append("- none")
    o.append("\n## Scans over the model-written sentences\n")
    llm = [r for r in rows if res(r)["text_source"] == "llm"]
    hits = [(r["finding_id"], x["text"]) for r in llm for x in [{"text": res(r)["text"]["headline"]}] + res(r)["text"]["sentences"] if SCAN_WORDS.search(x["text"])]
    o.append(f"Sentences with \"explanation\", \"reason\", \"why\", \"because of\" or \"result\": **{len(hits)}**" + ("" if not hits else "\n" + "\n".join(f"- {f}: {t}" for f, t in hits[:40])))
    art = []
    for r in llm:
        points = thing_index(r["view"])
        for x in res(r)["text"]["sentences"]:
            cites_art = any(points.get(ref, {}).get("wording") == "artifact_note" for ref in x["refs"])
            other = [ref for ref in x["refs"] if not ref.startswith("m") and points.get(ref, {}).get("wording") != "artifact_note"]
            if (cites_art or re.search(r"artifact", x["text"], re.I)) and other:
                art.append((r["finding_id"], x["text"], x["refs"]))
    o.append(f"\nSentences linking a sensor artifact to anything other than the artifact statement (cited ids beyond the measure and the artifact point): **{len(art)}**" + ("" if not art else "\n" + "\n".join(f"- {f}: {t} {rf}" for f, t, rf in art)))
    summ = [(r, x) for r in llm for x in res(r)["text"]["sentences"] if any(re.fullmatch(r"s\d+", ref) for ref in x["refs"])]
    is_s = lambda ref: re.fullmatch(r"s\d+", ref) is not None
    multi = sum(1 for r in llm if sum(any(is_s(ref) for ref in x["refs"]) for x in res(r)["text"]["sentences"]) > 1)
    with_art = sum(1 for r in rows if r["view"]["earlier_summaries"] and any(p["wording"] == "artifact_note" for p in r["view"]["things"]))
    o.append(f"\nSentences that cite an earlier summary: **{len(summ)}** in {len({r['finding_id'] for r, _ in summ})} versions; versions with more than one: {multi}; "
             f"versions whose view had an earlier summary: {sum(bool(r['view']['earlier_summaries']) for r in rows)}; artifact versions with one: {with_art}.")
    pr = [(r["finding_id"], x["text"]) for r in llm for x in res(r)["text"]["sentences"] if re.search(RECURRENCE, x["text"], re.I)]
    o.append(f"\nSentences with recurrence wording (come up before / early observation): {len(pr)}.")
    o.append("\n## Sentences against their wording classes (heuristic scan)\n")
    flags = audit_classes(rows)
    o += [f"- {f}" for f in flags] or ["- none"]
    if pb is not None:
        hits = clinical_term_hits(rows, pb)
        o.append(f"\n## Clinical terms not in the version's own view (all {n} versions)\n\n**{len(hits)}**" + ("" if not hits else "\n" + "\n".join(f"- {f}: {t!r}: {x}" for f, t, x in hits)))
    if recheck_log is not None:
        rc = load(recheck_log)
        failed = [r for r in rc if res(r)["status"] != "ok"]
        by = Counter(c for r in failed for c in {f["check"] for f in res(r)["checks"][-1]})
        o.append(f"\n## The re-check under {checks_version} (no model calls)\n\nSaved answers judged again: {len(rc)}; **{len(failed)} have no saved answer that passes** and went back to the model.\n")
        o.append("| check | versions failing |\n|---|---:|")
        for c in sorted(by):
            o.append(f"| {names[c]} | {by[c]} |")
        o.append("\nThe versions and why (last saved attempt):\n")
        o += [f"- {r['finding_id']}: " + "; ".join(sorted({f"check {f['check']} {f['detail'][:100]}" for f in res(r)['checks'][-1]})) for r in failed]
    if prev_log is not None:
        prev = {r["finding_id"]: r for r in load(prev_log)}
        same = lambda t: [t["headline"]] + [x["text"] for x in t["sentences"]]
        changed = [r for r in rows if same(res(r)["text"]) != same(prev[r["finding_id"]]["result"]["text"])]
        o.append(f"\n## Changed versions: previous text and new text ({len(changed)})\n")
        for r in changed:
            for label, rr in (("previous", prev[r["finding_id"]]), ("new", r)):
                t = res(rr)["text"]
                o.append(f"### {r['finding_id']} ({label}; `{res(rr)['text_source']}`)\n\n**{t['headline']}**\n")
                o += [f"- {x['text']} `{x['refs']}`" for x in t["sentences"]]
                o.append("")
    chosen = read_list(rows, named_cases, seed, n_seeded)
    o.append(f"\n## Read list ({len(chosen)} versions)\n")
    for why, r in chosen:
        t = res(r)["text"]
        o.append(f"### {r['finding_id']} ({why})\n\n`{res(r)['text_source']}` / `{res(r)['status']}`, attempts {len(res(r)['checks'])}, {mode(r)}\n\n**{t['headline']}**\n")
        o += [f"- {x['text']} `{x['refs']}`" for x in t["sentences"]]
        o.append("")
    out.write_text("\n".join(o))
    return "\n".join(o)


if __name__ == "__main__":
    # usage: python -m v0_code.findings_engine.report_text <log> <findings config> <report path> [--full <wall time text>]
    from v0_code.findings_engine.config import FindingsConfig
    from v0_code.intel_common.phrasebook import Phrasebook
    root = Path(__file__).resolve().parents[3]
    cfg = FindingsConfig.from_yaml(Path(sys.argv[2]) if Path(sys.argv[2]).is_absolute() else root / sys.argv[2], root)
    if len(sys.argv) > 4 and sys.argv[4] == "--full":
        opts = dict(zip(sys.argv[6::2], sys.argv[7::2]))                      # --before <log> --rerun <log> --seeded <n> --title <text> --checks <version>
        make_full_report(Path(sys.argv[1]), cfg.text, Path(sys.argv[3]), cfg.text_sample["named_cases"], 20260, sys.argv[5] if len(sys.argv) > 5 else "", Path(opts["--before"]) if "--before" in opts else None,
                         [Path(x) for x in opts["--rerun"].split(",")] if "--rerun" in opts else None, int(opts.get("--seeded", 30)), opts.get("--title", "full run report"), opts.get("--checks", "ck-v3"), Phrasebook.load(cfg.paths["phrasebook"]),
                         Path(opts["--recheck"]) if "--recheck" in opts else None, Path(opts["--prev"]) if "--prev" in opts else None)
    else:
        make_report(Path(sys.argv[1]), cfg.text, Phrasebook.load(cfg.paths["phrasebook"]), Path(sys.argv[3]))
