"""The L1 report (docs/loop_l1_report.md): regression against F1 and P1, the as-of audits, what Findings now reads from PI (versions changed by field, earlier conclusions, seen_before), how
many views changed hash (so how many Findings texts L2 needs), how many PI situations-line calls L2 needs, and the final statuses against P1. Reads databases only (read-only)."""

import json
import sys
from collections import Counter
from pathlib import Path

from v0_code.evidence_engine.library import load_library
from v0_code.findings_engine import run as frun
from v0_code.findings_engine.run_text import build_views
from v0_code.findings_engine.view import view_hash
from v0_code.loop_engine import regress
from v0_code.loop_engine.config import LoopConfig
from v0_code.loop_engine.pi_live import earlier_conclusions
from v0_code.loop_engine.run import audits
from v0_code.pi_engine import text_view
from v0_code.pi_engine.engine import PiReader
from v0_code.pi_engine.storage import PiStore

ROOT = Path(__file__).resolve().parents[3]


def views_both(cfg: LoopConfig, versions: list[dict]) -> tuple[dict, dict]:
    """The Findings views of the loop's records without PI items and with them (the loop's PI, strict reads)."""
    lib, pb, data = frun.prepare(cfg.findings)
    store = PiStore(cfg.pi_db, readonly=True)
    reader = PiReader(cfg.pi, store, strict=True)
    without = build_views(cfg.findings, pb, data, versions, lib)
    with_pi = build_views(cfg.findings, pb, data, versions, lib, pi_items=lambda r: earlier_conclusions(r, reader, cfg.state_words))
    store.close()
    return without, with_pi


def examples(views: dict, n: int = 5) -> list[tuple[str, list]]:
    """Up to n versions whose earlier conclusions differ in state word and seen_before band, then the rest by id."""
    seen, out = set(), []
    for fid, v in sorted(views.items()):
        items = v["earlier_conclusions"]
        sig = tuple(sorted((i["state"], i["seen_before"]) for i in items))
        if items and sig not in seen:
            seen.add(sig)
            out.append((fid, items))
        if len(out) == n:
            break
    return out


def situations_calls(pi_p1_db: str, findings_db: str, cfg: LoopConfig) -> dict:
    """How many long-term versions of the P1 (full) run have at least one diary-only sentence, and how many distinct views that makes (the cache would send identical views once). An
    estimate for L2: its entries will carry new Findings texts, so the sentences may change, and the chain of previous lines is not modelled."""
    from v0_code.findings_engine.factors import parse_key
    from v0_code.intel_common.phrasebook import Phrasebook
    from v0_code.pi_engine import run_text
    pcfg = cfg.pi
    lib, pb = load_library(pcfg.paths["evidence_library"]), Phrasebook.load(pcfg.paths["phrasebook"])
    store = PiStore(pi_p1_db, readonly=True)
    pi = PiReader(pcfg, store)
    vs = run_text.load_versions(store, pcfg, pi)
    kinds = {parse_key(v["relationship_key"])[3] for v in vs} - {None}
    refs = text_view.FindingsSentences(findings_db)
    n_all = n_view = 0
    distinct = set()
    for m in vs:
        if m["status"] == "retracted":
            continue
        n_all += 1
        v, _ = text_view.build_view(pi, m, None, True, pb, lib, kinds, refs, pcfg.text.get("diary_ref_prefix", "d"))
        if v is not None:
            n_view += 1
            distinct.add(json.dumps(v, sort_keys=True))
    refs.close()
    store.close()
    return {"long_term_versions": len(vs), "not_retracted": n_all, "with_a_diary_only_sentence": n_view, "distinct_views": len(distinct)}


def make(cfg: LoopConfig, f1_db: str, p1_code_only_db: str, p1_full_db: str, out: Path) -> str:
    vers = regress.records(cfg.findings_db)
    versions = list(vers.values())
    cmp_f1 = regress.compare_findings(f1_db, cfg.findings_db)
    before = regress.before_first_memory(f1_db, cfg.findings_db, cfg.pi_db)
    cmp_pi = regress.compare_pi(p1_code_only_db, cfg.pi_db)
    fin_loop, fin_p1 = regress.final_statuses(cfg.pi_db), regress.final_statuses(p1_code_only_db)
    bad, n = audits(cfg, versions)
    without, with_pi = views_both(cfg, versions)
    holds = {f: v for f, v in with_pi.items() if v["earlier_conclusions"]}
    changed = [f for f in with_pi if view_hash(with_pi[f]) != view_hash(without[f])]
    bands = Counter((r["pi_status"], r["seen_before"]) for v in versions for r in v["repeat"])
    sizes = Counter(len(v["earlier_conclusions"]) for v in with_pi.values())
    sit = situations_calls(p1_full_db, f1_db, cfg)
    o = ["# Stage L1 report: Findings reads PI as-of (the loop, code layer only)\n",
         f"Loop config `{cfg.version}`. {len(versions)} versions in {len({v['case_id'] for v in versions})} cases, written by Findings running live in time order with PI; "
         "PI wrote to `output/pi_loop.db`, Findings to `output/findings_loop.db`. No model was called. PI reads are strict (a version sees only what was written strictly before its own time).\n",
         "## As-of audits\n", "- " + ("**clean**" if not bad else f"**{len(bad)} violations**") + f": {json.dumps(n)}", "".join(f"\n  - {b}" for b in bad[:10]), ""]
    o += ["## Regression against F1 and P1\n",
          f"- **3b, all versions**: {cmp_f1['f1']} F1 versions, {cmp_f1['loop']} loop versions, same ids: {cmp_f1['same_ids']}; versions that differ outside `repeat` and `refs.pi_memories`: **{len(cmp_f1['violations'])}** "
          "(labels, flags, exposure states, wording classes, groups, factor ids, mode, measures, case and version ids, text, diary and state-memory refs are identical)",
          f"- versions changed versus F1, by field: `repeat.pi_status` {cmp_f1['changed']['repeat.pi_status']} entries, `repeat.seen_before` {cmp_f1['changed']['repeat.seen_before']} entries, "
          f"`refs.pi_memories` {cmp_f1['changed']['refs.pi_memories']} versions; **{cmp_f1['changed']['any']} of {cmp_f1['f1']} versions differ in at least one of them**",
          f"- **3a, before the first long-term memory** (written {before['first_memory']}): {before['versions']} versions; structure outside `repeat` / `refs.pi_memories` identical to F1: "
          f"{'yes' if not before['other_difference'] else 'NO ' + str(before['other_difference'])}; `pi_status` null everywhere: {not before['pi_status_not_null']}; long-term refs: {before['long_term_refs']}; "
          f"`repeat` identical to F1 in {before['identical_but_pi_memories']} of them, `seen_before` changed in {len(before['seen_before_changed'])} (each explained by an entry of another case with that relationship in the open week: "
          f"unexplained {len(before['unexplained'])}): " + ", ".join(before["seen_before_changed"]) + ". `refs.pi_memories` is not empty in all of them (the open week and the sealed weeks are listed), so a strict byte comparison of the whole record "
          "differs only there",
          "- **3c, PI against a P1 code-only run**: " + "; ".join(f"`{t}` {v['p1']} / {v['loop']} rows {'identical' if v['identical'] else 'DIFFERENT (' + str(v['different_rows']) + ' rows)'}" for t, v in cmp_pi.items()),
          f"- statuses at the end, loop against P1: {'identical' if fin_loop == fin_p1 else 'DIFFERENT'} ({len(fin_loop)} memories): " + Counter(fin_loop.values()).__repr__(), ""]
    o += ["## What Findings now reads\n",
          "- `repeat` entries by (PI status, seen_before): " + ", ".join(f"{k[0] or 'no memory'} / {k[1]}: {c}" for k, c in sorted(bands.items(), key=lambda x: str(x[0]))),
          f"- views holding `earlier_conclusions`: **{len(holds)} of {len(with_pi)}** (items per view: " + ", ".join(f"{k}: {c}" for k, c in sorted(sizes.items())) + ")",
          f"- views whose hash changed (current view code, with PI items against without): **{len(changed)}**: Findings texts L2 needs to write again. The other {len(with_pi) - len(changed)} views are unchanged, so their F2 texts stand "
          "(the cache key is the view hash plus prompt and checks)",
          f"- PI situations-line calls L2 would need (estimate from the P1 full run's {sit['long_term_versions']} long-term versions, {sit['not_retracted']} not retracted): **{sit['with_a_diary_only_sentence']} versions have a diary-only sentence**, "
          f"{sit['distinct_views']} distinct views (the cache sends identical views once). The sentences will change when L2 rewrites the Findings texts, and the chain of previous lines is not modelled", ""]
    retracted_refs = sum(r.get("status") == "retracted" for v in versions for r in v["refs"]["pi_memories"] if r["tier"] == "long_term")
    fallback_items = sum(1 for v in versions for r in v["refs"]["pi_memories"] if "view_id" in r and r["relationship_key"] not in {x["relationship_key"] for x in v["repeat"]})
    o.append("## Where the specs were ambiguous when Findings reads PI (decisions taken, to be written into the specs)\n")
    o += [f"1. **Events at the same instant.** The specs say PI returns what was written \"at or before `as_of`\", but a version and PI's own writes can share a time (an entry is stamped with its version's `as_of`; the weekly job is stamped 23:59:59). "
          "A resume test showed that an inclusive read depends on whether the write already exists, so a rerun read something the first run did not. The loop reads strictly before (`PiReader(strict=True)`); the stored results of the other components are unchanged.",
          "2. **State words.** Findings spec 8.1 names `early`, `repeated` and `fading` but not how they follow PI's statuses, and 7.6 says a retracted memory is mentioned only if today's label is usable, without a word for it. "
          f"Config `pi_state_words`: candidate to early, supported to repeated, weakened to fading; a retracted memory has no word, so it is listed in `refs.pi_memories` but has no view id and no earlier conclusion ({retracted_refs} such references).",
          f"3. **Which relationships.** `repeat` (F1) covers claim-class factors only; 7.6 says \"each usable factor\". The long-term read covers every usable relationship factor in the version; an earlier conclusion is made for any of them the view shows. "
          f"{fallback_items} earlier conclusions are about a shown factor that has no `repeat` entry; their `seen_before` band is read from PI when the view is built (as-of the version, its own case left out).",
          "4. **`refs.pi_memories` has no specified shape.** Chosen: long-term entries (`memory_id`, `relationship_key`, `version`, `status`, `written_at`, and `view_id` when the view shows it), the open week (`memory_id`, the finding ids of its entries, only when it has any) and the last two sealed weeks (`memory_id`, `sealed_at`). The view is rebuilt from these exact versions.",
          "5. **Seen before counts the open week** (Findings spec 13), so a version can have `seen_before` other than `none` before the first long-term memory exists (3 versions here), and the mid-term references are never empty after the first week. \"Byte-identical before the first memory\" therefore holds for everything except those.",
          "6. **The situations line.** In L1 it is null, so the key is left out of the item (not `null`). The item's `text` is the association sentence(s) only.",
          "7. **The mid-term reads** (open week, last two sealed weeks) are recorded as references but no L1 view shows them. Whether the text layer should show their headlines is open (the Findings spec table says \"text and status only\").",
          "8. **Order of versions at the same time.** P1's replay driver orders entries by `(as_of, finding_id)`; the live loop uses the event order (hand-offs before completions). PI's tables come out identical anyway.", ""]
    o.append("## Five examples of a view's `earlier_conclusions`\n")
    for fid, items in examples(with_pi):
        o += [f"### {fid}", "", "```json", json.dumps(items, indent=2, ensure_ascii=False), "```", ""]
    o += ["## Final statuses (loop, equal to P1 code-only)\n", "| relationship | status |", "|---|---|"] + [f"| `{k}` | {v} |" for k, v in sorted(fin_loop.items())]
    o.append("")
    out.write_text("\n".join(o))
    return "\n".join(o)


if __name__ == "__main__":
    # usage: report <loop config> <F1 findings db> <P1 code-only pi db> <P1 full pi db> <report path>
    cfg = LoopConfig.from_yaml(ROOT / sys.argv[1] if not Path(sys.argv[1]).is_absolute() else sys.argv[1], ROOT)
    make(cfg, sys.argv[2], sys.argv[3], sys.argv[4], Path(sys.argv[5]))
