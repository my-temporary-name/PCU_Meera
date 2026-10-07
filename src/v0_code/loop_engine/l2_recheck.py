"""The no-model re-check of a finished L2 run under the current checks (the polish round): every saved text is judged again under the current prompt's checks and cleanup, against the view the
current code would build for it (earlier conclusions as the previous run had them, things merged). Reports how many now fail, by check, how many views changed hash (merged things), how many
texts the cleanup changes, and whether each saved fallback's saved answers now pass. No call is made; nothing is written."""

import json
import sys
from collections import Counter
from pathlib import Path

from v0_code.findings_engine import run as frun
from v0_code.findings_engine import textlayer
from v0_code.findings_engine.run_text import view_builder
from v0_code.findings_engine.storage import FindingsStore
from v0_code.findings_engine.textcheck import NAMES
from v0_code.findings_engine.view import view_hash, view_ids
from v0_code.loop_engine import regress
from v0_code.loop_engine.config import LoopConfig
from v0_code.loop_engine.pi_live import earlier_conclusions
from v0_code.pi_engine.engine import PiReader
from v0_code.pi_engine.storage import PiStore

ROOT = Path(__file__).resolve().parents[3]


def recheck(cfg: LoopConfig, f_db: str, p_db: str) -> dict:
    lib, pb, data = frun.prepare(cfg.findings)
    store, pi = FindingsStore(f_db, readonly=True), PiStore(p_db, readonly=True)
    reader = PiReader(cfg.pi, pi, strict=True)
    build, ctx = view_builder(cfg.findings, pb, data, lib)
    tcfg = cfg.findings.text
    out = {"versions": 0, "llm": 0, "fallbacks": 0, "view_changed": [], "merged_views": 0, "now_fail": [], "fail_by_check": Counter(), "cleanup_changes_text": [], "fallbacks_now_pass": [], "fallbacks_still_fail": []}
    for fid, rec in sorted(regress.records(f_db).items(), key=lambda kv: (kv[1]["as_of"], kv[0])):
        row = store.own_row(fid)
        view = build(rec, earlier_conclusions(rec, reader, cfg.state_words, pi.situations_line))
        code = [rec["text"]["headline"]] + [s["text"] for s in rec["text"]["sentences"]]
        out["versions"] += 1
        out["merged_views"] += any("ids" in t for t in view["things"])
        if view_hash(view) != row["view_hash"]:
            out["view_changed"].append(fid)
        if row["text_source"] == "llm":
            out["llm"] += 1
            text, failures = textlayer.evaluate(json.dumps(row["text"]["raw"]), view, rec, pb, tcfg, view_ids(view))
            if text is None:
                out["now_fail"].append(fid)
                out["fail_by_check"].update({f["check"] for f in failures})
            elif [s["text"] for s in text["sentences"]] != [s["text"] if isinstance(s, dict) else s for s in row["text"]["sentences"]]:
                out["cleanup_changes_text"].append(fid)
        else:
            out["fallbacks"] += 1
            r = textlayer.reevaluate(row, view, rec, code, pb, tcfg, view_ids(view))
            (out["fallbacks_now_pass"] if r.status == "ok" else out["fallbacks_still_fail"]).append(fid)
    ctx.close()
    store.close()
    pi.close()
    return out


def render(r: dict) -> str:
    return "\n".join([
        f"- {r['versions']} saved texts re-checked with no model call ({r['llm']} model or kept texts, {r['fallbacks']} fallbacks)",
        f"- views whose hash changes under the current view code (things merged): **{len(r['view_changed'])}** ({r['merged_views']} views contain a merged thing)",
        f"- model or kept texts that now FAIL under ck-v7: **{len(r['now_fail'])} of {r['llm']}**" + ("" if not r["fail_by_check"] else " (" + ", ".join(f"{NAMES[c]} {n}" for c, n in sorted(r["fail_by_check"].items())) + ")"),
        f"- passing texts whose wording the cleanup changes (a final full stop): {len(r['cleanup_changes_text'])}",
        f"- saved fallbacks whose saved answers now pass: **{len(r['fallbacks_now_pass'])} of {r['fallbacks']}**; still failing: {len(r['fallbacks_still_fail'])}"])


if __name__ == "__main__":
    # usage: l2_recheck <loop config> <previous findings db> <previous pi db>
    cfg = LoopConfig.from_yaml(ROOT / sys.argv[1] if not Path(sys.argv[1]).is_absolute() else sys.argv[1], ROOT)
    print(render(recheck(cfg, sys.argv[2], sys.argv[3])))
