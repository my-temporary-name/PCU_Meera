"""Text layer, fourth round (prompt p-v2, checks ck-v4): the mixed-strength rule, 2 to 8 sentences, code-appended required statements, a 7-word copy window, the cleanup step
and the prompt-version-aware cache."""

import json
import sqlite3

import pytest

import test_findings_factors as ff
from test_findings_text import (BANDS, DIARY, HANDOFFS, IST, MEMORY, PB, TEXT_CFG, FakeClient, good, names, record_a, run_checks, view_a)
from v0_code.findings_engine import run_text, textcheck, textclean, textlayer
from v0_code.findings_engine.codeline import code_sentences
from v0_code.findings_engine.storage import FindingsStore
from v0_code.findings_engine.view import build_view, view_hash, view_ids


# ---- versions, prompt and limits ---------------------------------------------------------------------------------------------------------------------------
def test_the_mixed_strength_rule_and_the_sentence_limit_are_in_the_prompt():
    p = textlayer.SYSTEM_PROMPT
    assert "two to eight short sentences" in p
    assert 'When one sentence cites things of different strengths, use "may be linked to" for the whole sentence, or put them in separate sentences' in p


# ---- check 7 is completed by code ----------------------------------------------------------------------------------------------------------------------------
def rec_history():
    rec = record_a()
    rec["history_note"] = "not_enough_history_yet"
    return rec


def test_missing_required_sentences_are_appended_by_code_with_no_retry():
    rec = rec_history()
    view = view_a(rec)
    answer = good()
    answer["sentences"][2] = {"text": "She was also clearly above her usual.", "refs": ["m1"]}          # neither statement is there
    c = FakeClient([answer])
    r = textlayer.generate(view, rec, code_sentences(rec, PB), c, TEXT_CFG, PB, None)
    assert (r.status, r.text_source, c.calls, [len(x) for x in r.checks]) == ("ok", "llm", 1, [0])
    assert r.text["appended"] == ["n1", "h1"]
    tail = r.text["sentences"][-2:]
    assert tail == [{"text": "Not known yet: the day's step total.", "refs": ["n1"], "appended": True},
                    {"text": "There is not enough history yet to say what usually goes with this.", "refs": ["h1"], "appended": True}]
    assert len(r.text["sentences"]) == 5


def test_nothing_is_appended_when_the_text_already_says_it():
    rec = rec_history()
    view = view_a(rec)
    ok = good()
    ok["sentences"][2]["refs"] = ["n1", "h1"]
    ok["sentences"][2]["text"] = "It is not known yet how active she was that day, and there is not enough history yet."
    r = textlayer.generate(view, rec, code_sentences(rec, PB), FakeClient([ok]), TEXT_CFG, PB, None)
    assert r.text.get("appended") == [] and len(r.text["sentences"]) == 3


# ---- the copy window ------------------------------------------------------------------------------------------------------------------------------------------
def test_the_copy_window_is_seven_words():
    g = good()
    g["sentences"][0] = {"text": "Her diary says quarter close deadline day delivered the.", "refs": ["d1"]}      # copies six words in a row
    assert 5 not in names(run_checks(g))
    g["sentences"][0] = {"text": "Her diary says quarter close deadline day delivered the numbers.", "refs": ["d1"]}  # seven
    assert 5 in names(run_checks(g))


# ---- the cleanup step -------------------------------------------------------------------------------------------------------------------------------------------
def test_cleanup_capitalises_lowercases_after_says_and_strips_quotes_around_view_phrases():
    view = view_a()
    raw = {"headline": "glucose was clearly above her usual.",
           "sentences": [{"text": "'short sleep the night before' has tended to move together with \"higher glucose peaks after dinner\".", "refs": ["f3"]},
                         {"text": "An earlier summary says Missed multiple medicines during a stressful day.", "refs": ["s1"]},
                         {"text": "she said 'not a phrase of the view' once.", "refs": ["d1"]},
                         {"text": "the day's step total is not known yet.", "refs": ["n1"]},
                         {"text": "An earlier summary says HbA1c was Missed.", "refs": ["s1"]}]}
    cleaned, changes = textclean.clean(raw, view)
    assert cleaned["headline"] == "Glucose was clearly above her usual."
    s = [x["text"] for x in cleaned["sentences"]]
    assert s[0] == "Short sleep the night before has tended to move together with higher glucose peaks after dinner."
    assert s[1] == "An earlier summary says missed multiple medicines during a stressful day."
    assert s[2] == "She said 'not a phrase of the view' once."                                    # other quotes stay
    assert s[3] == "The day's step total is not known yet."
    assert s[4] == "An earlier summary says HbA1c was Missed."                                    # not lowered when the word is not plainly capitalised
    assert {"capitalised", "lowercased_after_says", "quotes_stripped"} <= set(changes)
    assert [x["refs"] for x in cleaned["sentences"]] == [x["refs"] for x in raw["sentences"]]
    assert raw["sentences"][0]["text"].startswith("'short")                                       # the raw object is not changed


def test_the_checks_run_on_the_cleaned_text_and_the_raw_is_stored(monkeypatch):
    seen = []
    real = textcheck.check_text
    monkeypatch.setattr(textlayer, "check_text", lambda obj, *a, **k: (seen.append(json.loads(json.dumps(obj))), real(obj, *a, **k))[1])
    g = good()
    g["headline"] = "glucose and heart rate were clearly above her usual."
    g["sentences"][0]["text"] = "the rise after this dinner was among the very highest she has had within the hour or so after dinners."
    rec = record_a()
    r = textlayer.generate(view_a(rec), rec, code_sentences(rec, PB), FakeClient([g]), TEXT_CFG, PB, None)
    assert seen[0]["headline"].startswith("Glucose") and seen[0]["sentences"][0]["text"].startswith("The rise")
    assert r.text["headline"].startswith("Glucose") and r.text["raw"]["headline"].startswith("glucose") and "capitalised" in r.text["cleaned"]


# ---- the cache, with prompt versions ------------------------------------------------------------------------------------------------------------------------------
def stored_under(store, fid, view, raws, prompt, checks="ck-v3", status="ok", text=None):
    store.put_text(fid, "old-exact-key", view_hash(view), {"text": text or {"headline": "old", "sentences": [], "source": "llm"}, "text_source": "llm" if status == "ok" else "code_line", "status": status,
                                                         "llm_raw": raws, "usage": [{"input_tokens": 1, "wall_seconds": 1}] * len(raws), "checks": [[] for _ in raws],
                                                         "prompt_version": prompt, "checks_version": checks, "settings_key": textlayer.settings_key(TEXT_CFG)})


def test_an_answer_stored_under_the_previous_prompt_is_accepted_if_it_passes_the_new_checks(tmp_path):
    s = FindingsStore(tmp_path / "f.db")
    rec, view = record_a(), view_a()
    bad = good()
    bad["sentences"][0]["text"] = "Sleep caused it."
    stored_under(s, "fnd_x_v2", view, [json.dumps(bad), json.dumps(good())], "p-v1")
    c = FakeClient([])
    r = textlayer.generate(view, rec, code_sentences(rec, PB), c, TEXT_CFG, PB, s)
    assert c.calls == 0 and r.status == "ok" and r.from_cache and r.from_prompt == "p-v1" and r.prompt_version == "p-v1"
    assert [len(x) for x in r.checks] == [1, 0] and r.checks[0][0]["check"] == 4                  # rechecked under the current checks
    assert r.text["sentences"][0]["refs"] == good()["sentences"][0]["refs"]


def test_a_previous_prompt_answer_that_fails_the_new_checks_is_not_accepted_and_the_model_is_asked(tmp_path):
    s = FindingsStore(tmp_path / "f.db")
    rec, view = record_a(), view_a()
    bad = good()
    bad["sentences"][0]["text"] = "Sleep caused it."
    stored_under(s, "fnd_x_v2", view, [json.dumps(bad), json.dumps(bad)], "p-v1", status="code_line_fallback")
    no_model = textlayer.generate(view, rec, code_sentences(rec, PB), FakeClient([]), TEXT_CFG, PB, s, allow_model=False)
    assert no_model.status == "code_line_fallback" and no_model.from_cache and no_model.needs_model and [len(x) for x in no_model.checks] == [1, 1]
    c = FakeClient([good()])
    r = textlayer.generate(view, rec, code_sentences(rec, PB), c, TEXT_CFG, PB, s)
    assert c.calls == 1 and r.status == "ok" and not r.from_cache and r.prompt_version == textlayer.PROMPT_VERSION and r.from_prompt is None


def test_an_answer_under_an_unrelated_prompt_or_a_twin_with_another_view_is_ignored(tmp_path):
    s = FindingsStore(tmp_path / "f.db")
    rec, view = record_a(), view_a()
    stored_under(s, "fnd_x_v2", view, [json.dumps(good())], "p-v0")
    c = FakeClient([good()])
    assert textlayer.generate(view, rec, code_sentences(rec, PB), c, TEXT_CFG, PB, s).from_cache is False and c.calls == 1
    other = view_a()
    other["situation"]["mode"] = "describe_only"
    s2 = FindingsStore(tmp_path / "g.db")
    stored_under(s2, "fnd_other_v1", other, [json.dumps(good())], "p-v1")                           # another version, another view: not this version's answer
    c2 = FakeClient([good()])
    assert textlayer.generate(view, rec, code_sentences(rec, PB), c2, TEXT_CFG, PB, s2).from_cache is False and c2.calls == 1


def test_a_versions_own_older_answer_is_judged_against_the_current_view_even_if_the_view_has_changed(tmp_path):
    """The view's words changed between prompts; the version's facts did not. Its own saved answer is checked against today's view and kept if it passes."""
    s = FindingsStore(tmp_path / "f.db")
    rec, view = record_a(), view_a()
    old_view = view_a()
    old_view["situation"]["mode"] = "an older word for the mode"
    stored_under(s, "fnd_x_v2", old_view, [json.dumps(good())], "p-v2", checks="ck-v4")
    c = FakeClient([])
    r = textlayer.generate(view, rec, code_sentences(rec, PB), c, TEXT_CFG, PB, s)
    assert c.calls == 0 and r.status == "ok" and r.from_prompt == "p-v2"
    bad = good()
    bad["sentences"][0] = {"text": "A stray ref.", "refs": ["f99"]}                              # an answer that cites something the current view does not have fails
    s3 = FindingsStore(tmp_path / "h.db")
    stored_under(s3, "fnd_x_v2", old_view, [json.dumps(bad)], "p-v2", status="code_line_fallback", checks="ck-v4")
    assert textlayer.generate(view, rec, code_sentences(rec, PB), FakeClient([]), TEXT_CFG, PB, s3, allow_model=False).status == "code_line_fallback"


def test_the_prompt_and_checks_versions_are_stored_with_every_text_and_an_exact_hit_is_served_as_is(tmp_path):
    s = FindingsStore(tmp_path / "f.db")
    rec, view = record_a(), view_a()
    r = textlayer.generate(view, rec, code_sentences(rec, PB), FakeClient([good()]), TEXT_CFG, PB, None)
    s.put_text("fnd_x_v2", textlayer.cache_key(view, TEXT_CFG), view_hash(view), r.as_dict())
    row = s.conn.execute("SELECT prompt_version, checks_version, from_prompt, settings_key FROM finding_text").fetchone()
    assert row == (textlayer.PROMPT_VERSION, textcheck.CHECKS_VERSION, None, textlayer.settings_key(TEXT_CFG))
    c = FakeClient([])
    again = textlayer.generate(view, rec, code_sentences(rec, PB), c, TEXT_CFG, PB, s)
    assert c.calls == 0 and again.from_cache and again.text == r.text and again.prompt_version == textlayer.PROMPT_VERSION


def test_an_old_database_is_migrated_and_its_texts_are_adopted_as_the_previous_prompt(tmp_path):
    path = tmp_path / "old.db"
    conn = sqlite3.connect(path)
    conn.executescript("""CREATE TABLE finding_text (finding_id TEXT PRIMARY KEY, cache_key TEXT NOT NULL, view_hash TEXT NOT NULL, text_source TEXT, status TEXT, text_json TEXT NOT NULL);
                          CREATE TABLE finding_llm (finding_id TEXT PRIMARY KEY, view_hash TEXT, llm_raw TEXT, usage_json TEXT, checks_json TEXT);
                          INSERT INTO finding_text VALUES ('a', 'k', 'h', 'llm', 'ok', '{}');""")
    conn.commit()
    conn.close()
    s = FindingsStore(path)
    assert s.conn.execute("SELECT prompt_version, checks_version FROM finding_text").fetchone() == (None, None)
    assert s.adopt_legacy(textlayer.settings_key(TEXT_CFG), "p-v1", "ck-v3") == 1
    assert s.conn.execute("SELECT prompt_version, checks_version, settings_key FROM finding_text").fetchone() == ("p-v1", "ck-v3", textlayer.settings_key(TEXT_CFG))
    assert s.adopt_legacy(textlayer.settings_key(TEXT_CFG), "p-v1", "ck-v3") == 0


# ---- which versions go back to the model -----------------------------------------------------------------------------------------------------------------------
def result(status="ok", first_checks=(), n=1):
    checks = [[{"check": c, "name": "x", "detail": "d"} for c in first_checks]] + [[]] * (n - 1)
    return textlayer.TextResult({"headline": "h", "sentences": [], "source": "llm"}, "llm" if status == "ok" else "code_line", status, ["r"] * n, [{}] * n, checks, from_cache=True)


def test_the_versions_for_the_model_are_the_ones_that_fail_plus_the_named_extras():
    rechecked = {"a": result(), "b": result("code_line_fallback", (5,), 2), "c": result(first_checks=(6,), n=2), "d": result(first_checks=(5,), n=2), "e": result("code_line_fallback", (6,), 2)}
    assert run_text.select_rerun(rechecked) == ["b", "e"]                                          # a first-attempt failure that was rescued by the retry is not sent back
    assert run_text.select_rerun(rechecked, extra=["c", "b", "zz"]) == ["b", "c", "e"]            # extras that exist are added once; unknown ids are ignored


def test_a_new_fallback_never_replaces_an_accepted_older_answer():
    old, new = result(first_checks=(6,), n=2), result("code_line_fallback", (6,), 2)
    assert run_text.better_of(old, new) is old
    assert run_text.better_of(result("code_line_fallback", (5,), 2), result()).status == "ok"
    assert run_text.better_of(old, result()).status == "ok" and run_text.better_of(old, result()) is not old


# ---- twins: versions with an identical view ----------------------------------------------------------------------------------------------------------------------------
def other_text(headline):
    t = good()
    t["headline"] = headline
    return json.dumps(t)


def test_a_version_keeps_its_own_stored_answer_over_a_twins(tmp_path):
    s = FindingsStore(tmp_path / "f.db")
    rec, view = record_a(), view_a()
    a = textlayer.generate(view, {**rec, "finding_id": "fnd_a_v1"}, code_sentences(rec, PB), FakeClient([json.loads(other_text("The twin's headline."))]), TEXT_CFG, PB, None)
    s.put_text("fnd_a_v1", textlayer.cache_key(view, TEXT_CFG), view_hash(view), a.as_dict())                       # the twin: an exact, current row
    stored_under(s, "fnd_x_v2", view, [other_text("My own headline.")], "p-v1")                                      # this version: its own older row
    c = FakeClient([])
    r = textlayer.generate(view, rec, code_sentences(rec, PB), c, TEXT_CFG, PB, s)
    assert c.calls == 0 and r.text["headline"] == "My own headline." and r.from_prompt == "p-v1"


def test_a_version_whose_own_answer_fails_takes_a_twins_accepted_answer_without_a_call(tmp_path):
    s = FindingsStore(tmp_path / "f.db")
    rec, view = record_a(), view_a()
    a = textlayer.generate(view, {**rec, "finding_id": "fnd_a_v1"}, code_sentences(rec, PB), FakeClient([json.loads(other_text("The twin's headline."))]), TEXT_CFG, PB, None)
    s.put_text("fnd_a_v1", textlayer.cache_key(view, TEXT_CFG), view_hash(view), a.as_dict())
    bad = good()
    bad["sentences"][0]["text"] = "Sleep caused it."
    stored_under(s, "fnd_x_v2", view, [json.dumps(bad), json.dumps(bad)], "p-v1", status="code_line_fallback")
    c = FakeClient([])
    r = textlayer.generate(view, rec, code_sentences(rec, PB), c, TEXT_CFG, PB, s)
    assert c.calls == 0 and r.status == "ok" and r.text["headline"] == "The twin's headline."


def test_the_rerun_can_be_limited_to_named_versions():
    rechecked = {"a": result("code_line_fallback", (5,), 2), "b": result("code_line_fallback", (5,), 2), "c": result()}
    assert run_text.select_rerun(rechecked, only=["b", "c"]) == ["b"]                              # only the named ones, and only if they fail
    assert run_text.select_rerun(rechecked, extra=["c"], only=["c"]) == ["c"]                      # an extra is sent back even though it passes
