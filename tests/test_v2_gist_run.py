"""Stage C run logic: prompts verbatim from the spec, one retry per failed window, statuses, usage logging, storage. A fake client only: no model is called."""

import json
import re
import shutil
from pathlib import Path
from types import SimpleNamespace

import pytest

from v0_code.baseline_v2 import gist as G
from v0_code.baseline_v2.render import fallback_code_line
from v0_code.baseline_v2.storage import MemoryV2Store

SPEC = Path("task/baselineV2.md").read_text()


class Fake:
    """Stands in for the SDK client: replies are strings (the model's text) or Exceptions (an API error), in call order."""
    def __init__(self, replies):
        self.replies, self.calls = list(replies), []
        self.chat = SimpleNamespace(completions=SimpleNamespace(create=self._create))

    def _create(self, **kw):
        self.calls.append(kw)
        r = self.replies.pop(0)
        if isinstance(r, Exception):
            raise r
        return SimpleNamespace(choices=[SimpleNamespace(message=SimpleNamespace(content=r))],
                               usage=SimpleNamespace(prompt_tokens=1000, completion_tokens=300, completion_tokens_details=SimpleNamespace(reasoning_tokens=120)))


GOOD = json.dumps({"headline": "A hard week with a relative in hospital.", "sentences": ["Sleep fell markedly.", "Metformin was missed on a few days."]})
BAD_DIRECTION = json.dumps({"headline": "A hard week.", "sentences": ["Sleep rose sharply.", "Metformin was missed on a few days."]})
BAD_DIGITS = json.dumps({"headline": "A hard week.", "sentences": ["Sleep fell on 3 days.", "Metformin was missed."]})


def pending(v2_stored, wid):
    return next(r for rows in v2_stored[0].values() for r in rows if r["window_id"] == wid)


# ---- prompts are the spec's, verbatim ---------------------------------------------------------------------------------------------------------

def _block(after: str) -> str:
    i = SPEC.index(after)
    j = SPEC.index("```", i)
    k = SPEC.index("```", j + 3)
    return SPEC[j + 3:k].strip("\n")


TOP_ITEMS_RULE = "12. The headline must cover the first item in TOP ITEMS; mention the others in the sentences."


def test_the_system_prompt_is_the_specs_plus_the_top_items_rule():
    spec = _block("**System prompt (use verbatim):**")
    if "TOP ITEMS" not in spec:                       # the repo spec may or may not carry the added line yet: the prompt is the spec with that one rule after rule 11
        spec = spec.replace("11. Refer to the person with the pronoun in the view.\n", "11. Refer to the person with the pronoun in the view.\n" + TOP_ITEMS_RULE + "\n")
    assert G.SYSTEM_PROMPT == spec
    assert G.SYSTEM_PROMPT.count("TOP ITEMS") == 1 and TOP_ITEMS_RULE in G.SYSTEM_PROMPT


def test_the_user_template_retry_addendum_and_tier_guidance_are_the_specs_verbatim():
    assert G.USER_TEMPLATE == _block("**User prompt template:**")
    assert G.RETRY_ADDENDUM == _block("**Retry addendum")
    for tier in ("day", "week", "month"):
        assert f'- **{tier}:** "{G.TIER_GUIDANCE[tier]}"' in SPEC


def test_the_user_prompt_carries_tier_pronoun_guidance_and_the_view(v2_cfg):
    p = G.user_prompt(v2_cfg, "week", {"1": {"tier": "week", "reliable": "yes"}})
    assert p.startswith("TIER: week\nPRONOUN: she\n\nTIER GUIDANCE:\nSay what the week looked like") and p.rstrip().endswith("}") and '"reliable": "yes"' in p


# ---- one call per window: pass, retry, fallback, errors ----------------------------------------------------------------------------------------

def test_a_first_attempt_that_passes_is_gist_ok_with_usage_logged(v2_cfg, v2_stored):
    row = pending(v2_stored, "week_ENDING_2025-11-22")
    fake = Fake([GOOD])
    (res,) = G.run_gist(v2_cfg, [row], fake, batch_size={"week": 1})
    assert res.status == "gist_ok" and res.headline == "A hard week with a relative in hospital." and len(fake.calls) == 1
    u = res.attempts[0]["usage"]
    assert (u["input_tokens"], u["output_tokens"], u["reasoning_tokens"]) == (1000, 300, 120) and u["wall_seconds"] >= 0
    kw = fake.calls[0]
    assert kw["model"] == v2_cfg.gist["model"] and kw["extra_body"] == {"reasoning": {"effort": "low"}} and kw["response_format"] == {"type": "json_object"}
    assert kw["messages"][0] == {"role": "system", "content": G.SYSTEM_PROMPT}


def test_a_failed_window_is_retried_once_alone_with_the_failures_appended(v2_cfg, v2_stored):
    row = pending(v2_stored, "week_ENDING_2025-11-22")
    fake = Fake([BAD_DIRECTION, GOOD])
    (res,) = G.run_gist(v2_cfg, [row], fake, batch_size={"week": 1})
    assert res.status == "gist_retry_ok" and len(fake.calls) == 2 and [a["passed"] for a in res.attempts] == [False, True]
    msgs = fake.calls[1]["messages"]
    assert [m["role"] for m in msgs] == ["system", "user", "assistant", "user"] and msgs[2]["content"] == BAD_DIRECTION
    assert msgs[3]["content"].startswith("Your previous answer failed these checks: direction_size:") and "Rewrite it." in msgs[3]["content"]
    assert res.attempts[0]["failures"][0]["check"] == "direction_size"


def test_two_failures_store_the_code_line_as_code_line_fallback(v2_cfg, v2_stored):
    row = pending(v2_stored, "week_ENDING_2025-11-22")
    (res,) = G.run_gist(v2_cfg, [row], Fake([BAD_DIGITS, BAD_DIRECTION]), batch_size={"week": 1})
    assert res.status == "code_line_fallback" and res.headline == fallback_code_line(v2_cfg, row) and res.sentences == []
    assert res.headline.startswith("Diary, 2025-11-18") and "Missed dose: metformin" in res.headline            # the fallback uses the top_items priority: the diary theme, then every missed medicine


def test_the_stored_headline_is_capitalised_and_ends_with_a_full_stop_but_the_raw_answer_is_kept(v2_cfg, v2_stored):
    row = pending(v2_stored, "week_ENDING_2025-11-22")
    raw = json.dumps({"headline": "a hard week with a relative in hospital", "sentences": ["Sleep fell markedly.", "Metformin was missed on a few days."]})
    (res,) = G.run_gist(v2_cfg, [row], Fake([raw]), batch_size={"week": 1})
    assert res.status == "gist_ok" and res.headline == "A hard week with a relative in hospital." and res.attempts[0]["raw"] == raw


def test_warning_mode_counts_sentence_level_direction_failures_instead_of_rejecting(v2_cfg, v2_stored):
    row = pending(v2_stored, "week_ENDING_2025-11-22")
    (res,) = G.run_gist(v2_cfg, [row], Fake([BAD_DIRECTION]), batch_size={"week": 1}, sentence_mode="warn")
    assert res.status == "gist_ok" and len(fake_warnings(res)) == 1


def fake_warnings(res):
    return [w for a in res.attempts for w in a.get("warnings", [])]


def test_an_api_error_is_a_failed_attempt_and_is_retried_once(v2_cfg, v2_stored):
    row = pending(v2_stored, "week_ENDING_2025-11-22")
    (res,) = G.run_gist(v2_cfg, [row], Fake([TimeoutError("timed out"), GOOD]), batch_size={"week": 1})
    assert res.status == "gist_retry_ok" and res.attempts[0]["failures"][0]["check"] == "api_error" and res.attempts[0]["error"].startswith("TimeoutError")
    (res,) = G.run_gist(v2_cfg, [row], Fake([TimeoutError("a"), TimeoutError("b")]), batch_size={"week": 1})
    assert res.status == "code_line_fallback"


def test_the_client_has_the_configured_timeout_and_no_sdk_retries(v2_cfg, monkeypatch):
    monkeypatch.setenv("OPENROUTER_API_KEY", "x")
    c = G.make_client(v2_cfg)
    assert c.max_retries == 0 and c.timeout == 90.0


# ---- batching ----------------------------------------------------------------------------------------------------------------------------------

def test_a_batch_is_parsed_by_key_and_a_missing_key_is_retried_alone(v2_cfg, v2_stored):
    a, b = pending(v2_stored, "week_ENDING_2025-11-22"), pending(v2_stored, "week_ENDING_2026-03-20")
    good2 = json.dumps({"headline": "A calmer week.", "sentences": ["Sleep stayed fairly steady.", "Metformin was missed on one day."]})
    fake = Fake([json.dumps({"1": json.loads(GOOD)}), good2])
    res = G.run_gist(v2_cfg, [a, b], fake, batch_size={"week": 2})
    assert [r.status for r in res] == ["gist_ok", "gist_retry_ok"] and len(fake.calls) == 2
    assert '"1"' in fake.calls[0]["messages"][1]["content"] and '"2"' in fake.calls[0]["messages"][1]["content"]
    assert "key 2 is missing" in fake.calls[1]["messages"][-1]["content"]


# ---- selection and storage --------------------------------------------------------------------------------------------------------------------

def test_only_windows_without_a_gist_status_need_the_model(v2_stored):
    rows = [r for rs in v2_stored[0].values() for r in rs]
    need = [r for r in rows if G.needs_gist(r)]
    assert all(r["gist"]["status"] is None for r in need) and len(need) == sum(1 for r in rows if r["gist"]["status"] is None)
    assert not any(G.needs_gist(r) for r in rows if r["gist"]["status"] in ("code_line_early", "code_line_quiet"))


def test_results_are_saved_per_window_and_an_upsert_keeps_an_llm_gist_but_resets_a_fallback(v2_cfg, v2_stored, tmp_path):
    db = tmp_path / "copy.db"
    shutil.copy(v2_stored[1], db)
    a, b = pending(v2_stored, "week_ENDING_2025-11-22"), pending(v2_stored, "week_ENDING_2026-03-20")
    store = MemoryV2Store(db)
    G.run_gist(v2_cfg, [a, b], Fake([GOOD, BAD_DIGITS, BAD_DIGITS]), store=store, batch_size={"week": 1})
    got = store.get_memory("week", "2025-11-22")
    assert got["gist"]["status"] == "gist_ok" and got["gist"]["sentences"][0] == "Sleep fell markedly."
    fb = store.get_memory("week", "2026-03-20")
    assert fb["gist"]["status"] == "code_line_fallback" and fb["gist"]["sentences"] == []
    raw = store.conn.execute("SELECT llm_raw, usage_json FROM memory_v2 WHERE window_id='week_ENDING_2026-03-20'").fetchone()
    assert len(json.loads(raw["llm_raw"])) == 2 and len(json.loads(raw["usage_json"])) == 2 and json.loads(raw["usage_json"])[0]["reasoning_tokens"] == 120
    # is_notable / notable_reason were never touched by the model
    assert (got["is_notable"], got["notable_reason"]) == (a["is_notable"], a["notable_reason"])
    from v0_code.baseline_v2.data import StoreView
    import sqlite3
    # re-upserting the same facts: the LLM gist stays, the fallback goes back to pending
    store.upsert([{"window_id": r["window_id"], "tier": r["tier"], "start_date": r["start_date"], "end_date": r["end_date"], "reliable": r["reliable"], "confidence": r["confidence"],
                   "facts": r["facts"], "tags": r["tags"], "co_movement": r["co_movement"], "material_changes": r["material_changes"], "anchors_crossed": r["anchors_crossed"],
                   "anchors_questionable": r["anchors_questionable"], "is_notable": r["is_notable"], "notable_reason": r["notable_reason"], "deviation_text": r["deviation_text"],
                   "data_quality": r["data_quality"], "config_version": r["config_version"], "gist_status": None, "gist_headline": None, "gist_sentences": None} for r in (a, b)])
    assert store.get_memory("week", "2025-11-22")["gist"]["status"] == "gist_ok"
    assert store.get_memory("week", "2026-03-20")["gist"]["status"] is None
    store.close()


# ---- the Stage C sample ------------------------------------------------------------------------------------------------------------------------

def test_the_sample_has_the_named_windows_and_a_seeded_random_rest(v2_stored):
    from v0_code.baseline_v2.run_gist import FIXED, choose_sample
    rows = v2_stored[0]
    a, b = choose_sample(rows, seed=4817), choose_sample(rows, seed=4817)
    assert {s["window_id"] for s in a} == {"week_ENDING_2025-11-22", "week_ENDING_2026-03-20", "month_ENDING_2025-12-29", "day_2025-12-26", "day_2026-04-23", "day_2025-12-25",
                                          "day_2026-01-16", "day_2025-10-13", "week_ENDING_2025-10-22", "week_ENDING_2026-01-30", "month_ENDING_2026-02-27"}        # the first run's eleven
    assert a == b and choose_sample(rows, seed=1) != a
    ids = [s["window_id"] for s in a]
    assert len(ids) == len(set(ids)) == 11
    assert set(FIXED) <= set(ids)
    by_role = {s["role"]: s["window_id"] for s in a}
    status = {r["window_id"]: r["gist"]["status"] for rs in rows.values() for r in rs}
    assert status[by_role["quiet day"]] == "code_line_quiet" and status[by_role["early day"]] == "code_line_early"
    llm = [s["window_id"] for s in a if s["role"] not in ("quiet day", "early day")]
    assert len(llm) == 9 and all(status[w] is None for w in llm)
    diary_day = pending(v2_stored, by_role["diary-heavy day"])
    assert sum(1 for i in diary_day["material_changes"] if i["kind"] == "diary_event") >= 2
    assert [s["window_id"].split("_")[0] for s in a if s["role"].startswith("random")] == ["week", "week", "month"]


def test_the_sample_is_the_same_whatever_gist_statuses_the_windows_have_now(v2_stored):
    """A re-run must pick the same windows even after the first run stored gists (and fallbacks) on them."""
    import copy
    from v0_code.baseline_v2.run_gist import choose_sample
    rows = v2_stored[0]
    before = choose_sample(rows, seed=4817)
    changed = copy.deepcopy(rows)
    for r in changed["week"] + changed["day"] + changed["month"]:
        if r["window_id"] in {s["window_id"] for s in before} and r["gist"]["status"] is None:
            r["gist"]["status"] = "code_line_fallback"
    assert choose_sample(changed, seed=4817) == before


def test_the_batch_test_windows_are_seeded_eligible_and_disjoint_from_the_sample(v2_stored):
    from v0_code.baseline_v2.run_gist import choose_batch_test, choose_sample
    rows = v2_stored[0]
    sample = {s["window_id"] for s in choose_sample(rows, 4817)}
    b = choose_batch_test(rows, 4817, n_days=16, n_weeks=6)
    ids = [r["window_id"] for r in b]
    assert len(ids) == len(set(ids)) == 22 and not (set(ids) & sample)
    assert sum(w.startswith("day_") for w in ids) == 16 and sum(w.startswith("week_") for w in ids) == 6
    assert all(r["gist"]["status"] is None for r in b) and ids == [r["window_id"] for r in choose_batch_test(rows, 4817, n_days=16, n_weeks=6)]
