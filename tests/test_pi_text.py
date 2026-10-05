"""PI text layer, redesigned (stage P2, prompt pp-v4, checks pck-v5): the association sentence is the P1 code text and is never written by the model; an optional situations line is
written from the diary-only sentences of the mid-term entries, checked, retried once and otherwise dropped."""

import json
import re
from pathlib import Path
from types import SimpleNamespace

import pytest

from pi_helpers import LIB, MISSED, PB, SLEEP, START, STRESS, finding, make_cfg, make_evidence, weekly
from test_pi_engine import S, SUG, NS, at, mk, rec, run_week
from v0_code.pi_engine import text_check, text_layer, text_view
from v0_code.pi_engine.storage import PiStore

ROOT = Path(__file__).resolve().parent.parent
TCFG = {"model": "m", "reasoning_effort": "low", "timeout_seconds": 90, "sdk_retries": 0, "retries": 1, "max_words": 25, "cache": True}
KINDS = {"dinner", "lunch"}
FRAME = "In the cases noted, the situations included"


def memory(tmp_path, entries=(("case_a", "Glucose rose after dinner on a deadline day.", ("A busy deadline day at work.",)),), pattern=(S, S, S), key=SLEEP, weeks=1):
    pi, _ = mk(tmp_path, {key: weekly(list(pattern))})
    for i, (case, head, sents) in enumerate(entries):
        rec(pi, case, 1, 1 + i, [(key, S, "exposed", [])], headline=head, sentences=sents)
    for n in range(weeks):
        run_week(pi, n)
    return pi, pi.get_long_term(key, "2030-01-01T00:00:00+05:30")


# ---- the view ----------------------------------------------------------------------------------------------------------------------------------------------------------
def stub(**by_fid):
    """The Findings text of each entry as build_view reads it: finding id -> [(sentence text, refs)]."""
    return lambda fid: by_fid.get(fid, [])


def test_the_view_has_the_link_for_context_the_previous_line_and_only_diary_only_sentences(tmp_path):
    sents = ("Glucose was clearly above her usual.", "Her father was in hospital that day.", "Missed doses were present.", "A festival and a missed dose.", "There is not enough history yet.",
             "It is not known yet how the day's mood was.", "An earlier summary says doses were missed.", "She sat a family dinner.")
    pi, m = memory(tmp_path, entries=(("case_a", "Glucose rose.", sents),))
    refs = stub(fnd_case_a_v1=list(zip(sents, (["m1"], ["d1"], ["f1"], ["d2", "f1"], ["h1"], ["n1"], ["s1"], ["d3"]))))
    v, ids = text_view.build_view(pi, m, None, False, PB, LIB, KINDS, refs)
    assert list(v) == ["link", "previous_situations", "sentences"] and v["previous_situations"] is None
    assert v["link"] == {"present": "short sleep the night before", "outcome": "higher glucose peaks after dinner"}
    assert v["sentences"] == ["Her father was in hospital that day.", "She sat a family dinner."] and ids == ["fnd_case_a_v1"]            # a mix of diary and anything else is skipped


def test_a_sentence_with_no_refs_or_refs_of_another_prefix_is_not_a_diary_sentence(tmp_path):
    sents = ("A sentence with no refs.", "A diary one.", "Another kind.")
    pi, m = memory(tmp_path, entries=(("case_a", "H.", sents),))
    refs = stub(fnd_case_a_v1=[(sents[0], []), (sents[1], ["d12"]), (sents[2], ["x1"])])
    assert text_view.build_view(pi, m, None, False, PB, LIB, KINDS, refs)[0]["sentences"] == ["A diary one."]
    v, _ = text_view.build_view(pi, m, None, False, PB, LIB, KINDS, refs, prefix="x")
    assert v["sentences"] == ["Another kind."]


def test_no_diary_sentence_and_no_entry_mean_no_view(tmp_path):
    pi, _ = mk(tmp_path, {SLEEP: weekly([S] * 3), MISSED: weekly([S] * 3)})
    rec(pi, "case_a", 1, 1, [(MISSED, S, "exposed", [])], headline="Not about sleep.", sentences=("Her father was in hospital.",))
    rec(pi, "case_b", 1, 2, [(SLEEP, S, "exposed", [])], headline="About sleep.", sentences=("Glucose was high.", "A festival."))
    run_week(pi, 0)
    m = pi.get_long_term(SLEEP, "2030-01-01T00:00:00+05:30")
    refs = stub(fnd_case_a_v1=[("Her father was in hospital.", ["d1"])], fnd_case_b_v1=[("Glucose was high.", ["m1"]), ("A festival.", ["m1", "d1"])])
    assert text_view.build_view(pi, m, None, False, PB, LIB, KINDS, refs) == (None, [])                      # case_a is about another relationship; case_b has no diary-only sentence
    assert text_view.build_view(pi, m, None, False, PB, LIB, KINDS, stub()) == (None, [])                    # no Findings text at all
    run_week(pi, 1)
    later = pi.get_long_term(SLEEP, "2030-01-01T00:00:00+05:30")
    if later["written_at"] > m["written_at"]:
        assert text_view.build_view(pi, later, None, False, PB, LIB, KINDS, refs) == (None, [])


def test_the_sentences_are_capped_at_six_most_recent_first_with_earlier_entries_and_no_repeats(tmp_path):
    entries = tuple((f"case_{i}", f"Headline {i}.", (f"Family trip {i}.",)) for i in range(5))
    pi, m = memory(tmp_path, entries=entries)
    refs = {f"fnd_case_{i}_v1": [(f"Family trip {i}.", ["d1"])] for i in range(5)}
    earlier = [f"fnd_old_{i}_v1" for i in range(4)]
    for i, fid in enumerate(earlier):
        pi.store.conn.execute("INSERT INTO pi_mid_entries VALUES (?, ?, ?, ?, ?, ?, ?, ?)", (fid, "pi_mid_2025-W50", f"old_{i}", 1, "2025-12-01", "2025-12-01T10:00:00+05:30", 1764576000 + i,
                                                                                              json.dumps({"headline": f"Earlier {i}.", "sentences": [f"A festival {i}."], "relationship_keys": [SLEEP], "finding_id": fid,
                                                                                                          "as_of": f"2025-12-0{i + 1}T10:00:00+05:30"})))
        refs[fid] = [(f"A festival {i}.", ["d1"])]
    prev = {"line": f"{FRAME} a festival.", "entry_ids": earlier}
    v, ids = text_view.build_view(pi, m, prev, False, PB, LIB, KINDS, stub(**refs))
    assert v["previous_situations"] == prev["line"] and len(v["sentences"]) == 6 and len(ids) == 6
    assert v["sentences"] == [f"Family trip {i}." for i in (4, 3, 2, 1, 0)] + ["A festival 3."]                    # newest first; the cap leaves out the older ones
    v2, ids2 = text_view.build_view(pi, m, prev, True, PB, LIB, KINDS, stub(**refs))                           # regenerated: no previous line, no earlier entries
    assert v2["previous_situations"] is None and len(v2["sentences"]) == 5


def test_a_diary_sentence_repeated_in_several_entries_is_listed_once(tmp_path):
    pi, m = memory(tmp_path, entries=(("case_a", "H.", ("Her father was in hospital.",)), ("case_b", "H.", ("Her father was in hospital.", "A festival."))))
    refs = stub(fnd_case_a_v1=[("Her father was in hospital.", ["d1"])], fnd_case_b_v1=[("Her father was in hospital.", ["d1"]), ("A festival.", ["d2"])])
    v, ids = text_view.build_view(pi, m, None, False, PB, LIB, KINDS, refs)
    assert sorted(v["sentences"]) == ["A festival.", "Her father was in hospital."] and ids == ["fnd_case_b_v1"]          # the newest entry has both; the older adds nothing new


def test_the_findings_sentences_are_read_from_the_findings_database_read_only(tmp_path):
    import sqlite3
    db = tmp_path / "f.db"
    c = sqlite3.connect(db)
    c.execute("CREATE TABLE finding_text (finding_id TEXT, text_json TEXT)")
    c.execute("INSERT INTO finding_text VALUES (?, ?)", ("fnd_x_v1", json.dumps({"sentences": [{"text": "A festival.", "refs": ["d1"]}, {"text": "Glucose was high.", "refs": ["m1"]}, "a code line"]})))
    c.commit()
    c.close()
    src = text_view.FindingsSentences(db)
    assert src("fnd_x_v1") == [("A festival.", ["d1"]), ("Glucose was high.", ["m1"]), ("a code line", [])] and src("fnd_none") == []
    with pytest.raises(sqlite3.OperationalError):
        src.conn.execute("DELETE FROM finding_text")
    src.close()


def test_a_retracted_memory_has_no_view():
    with pytest.raises(ValueError):
        text_view.build_view(None, {"status": "retracted"}, None, False, PB, LIB, KINDS)


def test_regeneration_falls_due_every_four_weeks_from_the_creation_week():
    assert [text_view.regeneration_due("2026-W10", w, 4) for w in ("2026-W10", "2026-W13", "2026-W14", "2026-W18")] == [False, False, True, True]
    assert text_view.regeneration_due("2025-W51", "2026-W03", 4) is True


# ---- the checks --------------------------------------------------------------------------------------------------------------------------------------------------------
def view(sentences=None, prev=None):
    return {"link": {"present": "short sleep the night before", "outcome": "higher glucose peaks after dinner"}, "previous_situations": prev,
            "sentences": sentences or ["A very long deadline day with a family emergency.", "She was away on a work trip and then hosted a festival."]}


GOOD = f"{FRAME} a deadline day, a family emergency, a work trip and a festival."


def chk(line, v=None):
    return text_check.check(line, v or view(), PB, TCFG, LIB, KINDS)


def failing(fs):
    return sorted({f["check"] for f in fs})


def test_a_good_line_passes():
    assert chk(GOOD) == [] and chk(f"{FRAME} a work trip.") == []


def test_check_1_structure_one_sentence_of_at_most_25_words_with_the_frame():
    assert 1 in failing(chk(GOOD + " Another sentence."))
    assert 1 in failing(chk(f"{FRAME} " + " ".join(["trip"] * 20) + "."))
    assert 1 not in failing(chk(f"{FRAME} " + " ".join(["trip"] * 18) + "."))
    assert 1 in failing(chk("A deadline day and a work trip."))
    assert 1 in failing(chk(""))
    assert 1 in failing(chk(f"{FRAME} a deadline day.\nIn the cases noted, the situations included a festival."))


def test_parse_accepts_a_sentence_or_null_only():
    assert text_check.parse(json.dumps({"situations": GOOD})) == ({"situations": GOOD}, [])
    assert text_check.parse(json.dumps({"situations": None})) == ({"situations": None}, [])
    for bad in ("nope", json.dumps({"x": 1}), json.dumps({"situations": 3}), json.dumps({"situations": ["a"]}), json.dumps(["a"])):
        assert text_check.parse(bad)[0] is None and text_check.parse(bad)[1][0]["check"] == 1


@pytest.mark.parametrize("line", [f"{FRAME} 3 work trips.", f"{FRAME} a trip in March.", f"{FRAME} a first trip.", f"{FRAME} one trip.", f"{FRAME} several trips.", f"{FRAME} a trip at five p.m."])
def test_check_2_digits_dates_counting_words(line):
    assert 2 in failing(chk(line))


@pytest.mark.parametrize("line", [f"{FRAME} a trip because of work.", f"{FRAME} a trip that led to stress.", f"{FRAME} a trip that triggered it.", f"{FRAME} a trip that affected her.",
                                  f"{FRAME} a trip that moved together with it.", f"{FRAME} a trip linked to work.", f"{FRAME} a trip that tended to recur."])
def test_check_3_causal_and_claim_words(line):
    assert 3 in failing(chk(line))


@pytest.mark.parametrize("line", [f"{FRAME} a work trip and a family emergency.".replace("a family", "a status of a family"), f"{FRAME} a work_trip.", f"{FRAME} a relationship issue.", f"{FRAME} a bundle of trips."])
def test_check_4_internal_words_and_underscore_tokens_but_the_frame_is_exempt(line):
    assert 4 in failing(chk(line))
    assert 4 not in failing(chk(GOOD))                                                                       # "cases" is in the frame


@pytest.mark.parametrize("word", ["this week", "last week", "recently", "today", "yesterday", "tonight", "now", "currently", "lately", "so far", "again", "recent", "earlier", "previous", "prior"])
def test_check_5_time_relative_words(word):
    assert 5 in failing(chk(f"{FRAME} a work trip {word}."))
    assert 5 not in failing(chk(f"{FRAME} a work trip and a festival."))


@pytest.mark.parametrize("word", ["unknown", "unspecified", "unclear", "felt", "feel", "feeling", "proud", "relieved", "tired", "stressed", "anxious", "happy", "sad", "guilty", "drained", "exhausted", "stayed up"])
def test_check_4_also_bans_unknown_unspecified_unclear_and_feelings_states_and_habits(word):
    assert 4 in failing(chk(f"{FRAME} a {word} trip."))
    assert 4 not in failing(chk(f"{FRAME} a work trip."))


def test_check_6_the_line_never_repeats_the_association_or_names_another_relationship():
    assert 6 in failing(chk(f"{FRAME} a work trip and short sleep the night before."))
    assert 6 in failing(chk(f"{FRAME} a trip with higher glucose peaks after dinner."))
    assert 6 in failing(chk(f"{FRAME} a work trip and missed doses on the same day or the day before."))
    assert 6 in failing(chk(f"{FRAME} a trip and higher glucose peaks after lunch."))


def test_check_7_clinical_terms_only_if_the_sentences_have_them():
    assert 7 in failing(chk(f"{FRAME} a work trip and insulin dosing."))
    v = view(["Insulin before dinner on a work trip.", "A trip."])
    assert 7 not in failing(chk(f"{FRAME} a work trip and insulin.", v))


def test_check_8_no_phrase_repeated_but_a_word_may_come_back():
    assert 8 in failing(chk(f"{FRAME} a festival and festival."))
    assert 8 in failing(chk(f"{FRAME} a work trip, a festival and a work trip."))
    assert 8 not in failing(chk(f"{FRAME} a work trip, a family emergency and a work festival."))               # "work" twice in different phrases is fine
    v = view(["Fewer evening doses and missed doses.", "A festival."])
    assert 8 not in failing(chk(f"{FRAME} fewer doses and missed doses.", v))


def test_check_9_every_situation_word_comes_from_the_sentences():
    assert 9 not in failing(chk(GOOD))
    assert 9 not in failing(chk(f"{FRAME} a festival and a trip."))                                          # inflections share a stem with the entries' words
    assert 9 in failing(chk(f"{FRAME} a wedding, a hospital admission and a marathon."))
    assert 9 not in failing(chk(f"{FRAME} a festival and an outing."))                                       # one word not in the entries is tolerated


@pytest.mark.parametrize("line,entry", [("missed doses", "She missed a dose."), ("missed medication", "Missed medicines on a few days."), ("staying up late", "She stayed up late."),
                                         ("a celebration", "Family celebrations were held."), ("an outing", "She went out for a walk.")])
def test_the_stem_overlap_reads_plurals_endings_and_related_forms(line, entry):
    v = view([entry])
    from v0_code.pi_engine.text_check import unmatched_words
    assert unmatched_words(f"{FRAME} {line}.", v) in ([], ["outing"])                                          # "outing" is the one that is not in the entry


def test_check_9_fails_only_when_several_words_and_a_quarter_of_the_line_are_not_from_the_entries():
    assert 9 not in failing(chk(f"{FRAME} a deadline day, a family emergency, a work trip, a festival and a picnic."))
    assert 9 in failing(chk(f"{FRAME} a picnic and a concert."))


def test_check_10_no_names():
    assert 10 in failing(chk(f"{FRAME} a trip to Chennai and a festival."))
    assert 10 in failing(chk(f"{FRAME} a festival hosted by Meera."))


# ---- cleanup ---------------------------------------------------------------------------------------------------------------------------------------------------------------
def test_cleanup_capitalises_strips_wrapping_quotes_and_the_raw_is_kept():
    cleaned, changes = text_view.clean("in the cases noted, the situations included a work trip.", view())
    assert cleaned == f"{FRAME} a work trip." and changes == ["capitalised"]
    assert text_view.clean(f'"{FRAME} a work trip."', view()) == (f"{FRAME} a work trip.", ["quotes_stripped"])
    assert text_view.clean(f"{FRAME} a work trip", view()) == (f"{FRAME} a work trip.", ["full_stop_added"])
    assert text_view.clean(GOOD, view()) == (GOOD, [])


# ---- the call: ok, null, retry, drop ----------------------------------------------------------------------------------------------------------------------------------
class FakeClient:
    def __init__(self, answers):
        self.answers, self.calls, self.prompts = list(answers), 0, []
        self.chat = SimpleNamespace(completions=SimpleNamespace(create=self.create))

    def create(self, **kw):
        self.calls += 1
        self.prompts.append(kw["messages"])
        a = self.answers.pop(0)
        if isinstance(a, Exception):
            raise a
        usage = SimpleNamespace(prompt_tokens=10, completion_tokens=5, completion_tokens_details=SimpleNamespace(reasoning_tokens=2))
        return SimpleNamespace(usage=usage, choices=[SimpleNamespace(message=SimpleNamespace(content=a if isinstance(a, str) else json.dumps(a)))])


ASSOC = {"sentences": ["Short sleep the night before may be linked to higher glucose peaks after dinner in her history. This is an early observation."], "source": "code_text"}


def gen(client, v=None, ids=("f1",), assoc=ASSOC, previous=None, retracted=False, rows=None, uid=("pi_long_x", 1), allow_model=True):
    return text_layer.generate(v if v is not None else view(), list(ids), assoc, previous, retracted, client, TCFG, PB, LIB, KINDS, rows, uid, allow_model=allow_model)


def test_an_accepted_line_is_added_after_the_association_which_is_never_changed():
    c = FakeClient([{"situations": "in the cases noted, the situations included a deadline day and a festival"}])
    r = gen(c)
    assert (r.status, c.calls) == ("ok", 1) and r.text["situations"] == f"{FRAME} a deadline day and a festival." and r.text["sentences"] == ASSOC["sentences"] and r.text["source"] == "code_text"
    assert r.text["raw"] == {"situations": "in the cases noted, the situations included a deadline day and a festival"} and r.text["cleaned"] == ["capitalised", "full_stop_added"] and r.text["entry_ids"] == ["f1"]
    assert text_layer.note_sentences(r.text) == ASSOC["sentences"] + [f"{FRAME} a deadline day and a festival."]
    assert c.prompts[0][0]["content"] == text_layer.SYSTEM_PROMPT and c.prompts[0][1]["content"].startswith("VIEW:\n")


def test_the_view_the_model_sees_never_carries_the_association_sentence_or_the_state():
    c = FakeClient([{"situations": None}])
    gen(c)
    sent = c.prompts[0][1]["content"]
    assert "early observation" not in sent and "may be linked" not in sent and "state" not in json.loads(sent[len("VIEW:\n"):])


def test_null_is_a_valid_answer_and_stores_a_null_line():
    r = gen(FakeClient([{"situations": None}]))
    assert r.status == "null" and r.text["situations"] is None and r.text["sentences"] == ASSOC["sentences"]


def test_a_failed_check_is_retried_once_and_two_failures_drop_the_line_but_keep_the_association():
    bad = {"situations": f"{FRAME} a trip because of work."}
    c = FakeClient([bad, {"situations": GOOD}])
    r = gen(c)
    assert r.status == "ok" and c.calls == 2 and r.checks[0][0]["check"] == 3 and r.checks[1] == [] and "Your previous answer failed these checks" in c.prompts[1][1]["content"]
    d = gen(FakeClient([bad, bad]))
    assert d.status == "dropped" and d.text["situations"] is None and d.text["sentences"] == ASSOC["sentences"] and [len(x) for x in d.checks] == [1, 1]


def test_a_call_error_and_bad_json_are_failed_attempts():
    r = gen(FakeClient([TimeoutError("slow"), "nope"]))
    assert r.status == "dropped" and r.checks[0][0]["name"] == "call_error" and r.checks[1][0]["check"] == 1 and r.llm_raw[0].startswith("ERROR")
    assert gen(FakeClient([TimeoutError("slow"), {"situations": GOOD}])).status == "ok"


def test_no_diary_sentences_means_no_call_a_previous_line_is_kept_else_null():
    c = FakeClient([])
    r = text_layer.generate(None, [], ASSOC, None, False, c, TCFG, PB, LIB, KINDS, None, ("m", 1))
    assert c.calls == 0 and r.status == "no_diary_sentences" and r.text["situations"] is None
    prev = {"line": GOOD, "entry_ids": ["old"]}
    k = text_layer.generate(None, [], ASSOC, prev, False, c, TCFG, PB, LIB, KINDS, None, ("m", 2))
    assert c.calls == 0 and k.status == "kept_previous_line" and k.text["situations"] == GOOD and k.text["entry_ids"] == ["old"]


def test_a_retracted_memory_takes_the_code_text_and_never_goes_to_the_model():
    c = FakeClient([])
    r = text_layer.generate(None, [], {"sentences": ["This link, once suspected, is no longer supported by her history."], "source": "code_text"}, None, True, c, TCFG, PB, LIB, KINDS, None, ("m", 1))
    assert c.calls == 0 and r.status == "code_text_retracted" and r.text["situations"] is None and r.llm_raw == []


# ---- the cache ------------------------------------------------------------------------------------------------------------------------------------------------------------
def test_the_cache_key_covers_the_view_prompt_model_settings_and_checks_version(monkeypatch):
    base = text_layer.cache_key(view(), TCFG)
    assert text_layer.cache_key(view(), TCFG) == base and text_layer.cache_key(view(prev=GOOD), TCFG) != base
    for k, val in (("model", "o"), ("reasoning_effort", "high"), ("retries", 2), ("max_words", 20)):
        assert text_layer.cache_key(view(), {**TCFG, k: val}) != base, k
    assert text_layer.cache_key(view(), {**TCFG, "timeout_seconds": 1, "concurrency": 1}) == base
    for name in ("SYSTEM_PROMPT", "USER_TEMPLATE", "RETRY_ADDENDUM", "PROMPT_VERSION"):
        monkeypatch.setattr(text_layer, name, getattr(text_layer, name) + "x")
        assert text_layer.cache_key(view(), TCFG) != base, name
        monkeypatch.undo()
    monkeypatch.setattr(text_check, "CHECKS_VERSION", "other")
    assert text_layer.cache_key(view(), TCFG) != base


def test_a_second_run_makes_no_call_and_a_refresh_recomputes(tmp_path):
    s = PiStore(tmp_path / "t.db")
    r = gen(FakeClient([{"situations": GOOD}]))
    s.put_text("pi_long_x", 1, text_layer.cache_key(view(), TCFG), text_layer.view_hash(view()), r.as_dict())
    rows = s.text_rows()
    c2 = FakeClient([])
    again = gen(c2, rows=rows)
    assert c2.calls == 0 and again.from_cache and again.text == r.text and again.usage == r.usage
    c3 = FakeClient([{"situations": GOOD}])
    text_layer.generate(view(), ["f1"], ASSOC, None, False, c3, TCFG, PB, LIB, KINDS, rows, ("pi_long_x", 1), refresh=True)
    assert c3.calls == 1


def test_a_versions_own_stored_line_comes_before_a_twins(tmp_path):
    s = PiStore(tmp_path / "t.db")
    key, vh = text_layer.cache_key(view(), TCFG), text_layer.view_hash(view())
    for mid, ver, line in (("pi_long_a", 1, "twin"), ("pi_long_b", 1, "mine")):
        s.put_text(mid, ver, key, vh, {"text": {"sentences": ASSOC["sentences"], "source": "code_text", "situations": line, "entry_ids": []}, "text_source": "code_text", "status": "ok", "llm_raw": [], "usage": [],
                                       "checks": [], "prompt_version": text_layer.PROMPT_VERSION, "checks_version": text_check.CHECKS_VERSION})
    rows = s.text_rows()
    assert gen(FakeClient([]), rows=rows, uid=("pi_long_b", 1)).text["situations"] == "mine" and gen(FakeClient([]), rows=rows, uid=("pi_long_c", 1)).text["situations"] == "twin"


# ---- the structured layer; the prompt is the spec's ----------------------------------------------------------------------------------------------------------------------------
def test_writing_texts_leaves_every_structured_table_byte_identical(tmp_path):
    pi, m = memory(tmp_path)
    before = json.dumps(pi.store.dump(), sort_keys=True)
    pi.store.put_text(m["memory_id"], m["version"], "k", "h", {"text": {"sentences": ["x"], "source": "code_text", "situations": None, "entry_ids": []}, "text_source": "code_text", "status": "null",
                                                               "llm_raw": ["r"], "usage": [{}], "checks": [[]], "prompt_version": "pp-v4", "checks_version": "pck-v5"})
    assert json.dumps(pi.store.dump(), sort_keys=True) == before and (m["memory_id"], m["version"]) in pi.store.texts()
    pi.store.close()
    PiStore(tmp_path / "pi.db", rebuild=True)
    assert PiStore(tmp_path / "pi.db", readonly=True).texts() != {}


def test_the_prompt_is_the_specs_verbatim_and_has_the_rules():
    spec = (ROOT / "task/pi_spec.md").read_text()
    block = spec.split("## Appendix A.")[1].split("**System prompt**")[1].split("```")[1].strip()
    assert text_layer.SYSTEM_PROMPT == block
    retry = spec.split("**Retry addendum (appended once):**")[1].split("```")[1].strip()
    assert text_layer.RETRY_ADDENDUM == retry
    assert text_layer.PROMPT_VERSION == "pp-v4" and text_check.CHECKS_VERSION == "pck-v5"
    p = text_layer.SYSTEM_PROMPT
    body, listing = p.split("Do not use the words:")
    listing = listing.split("\n")[0]
    stripped = body.replace(FRAME, "")
    for w in text_check.internal_words(PB):
        if w != "case":                                                                                    # "cases" is allowed in the opening phrase, as the prompt says
            assert (w in listing or w.rstrip("s") in listing) and not re.search(rf"\b{re.escape(w)}", stripped.lower()), w
    for needed in (FRAME, "at most 25 words", "at most four situations", "this week, last week, recently, today, yesterday, tonight, currently, lately, so far, again, earlier, previous, prior, recent",
                   '{"situations": null}', "moved together", "are NOT situations", "Null is a good answer", "noun phrases only", "no verbs and no past tense", "never list feelings, states or habits", 'The word "cases" is allowed only in the opening phrase.'):
        assert needed in p
    assert "diabetes" not in p.lower()


# ---- the sample -------------------------------------------------------------------------------------------------------------------------------------------------------------
def test_the_sample_has_every_kind_a_chain_and_is_fixed_by_the_seed():
    from v0_code.pi_engine import run_text
    vs = []
    for k in range(10):
        for ver in range(1, 8):
            i = k * 7 + ver
            vs.append({"memory_id": f"pi_long_k{k}", "relationship_key": f"k{k}", "version": ver, "status": "candidate" if (k % 5 == 0 and ver < 3) else "supported", "same_day_only": k % 3 == 0,
                       "flags_seen": ["placebo_fired"] if k % 4 == 0 else [], "created_week": "2026-W10", "week": f"2026-W{(i % 30) + 10:02d}", "regenerated": ver == 5, "backfilled": ver == 1 and k % 2 == 0,
                       "entries_this_week": 1 if ver % 4 else 0})
    vs.append({"memory_id": "pi_long_w", "relationship_key": "w", "version": 5, "status": "weakened", "same_day_only": False, "flags_seen": [], "created_week": "2026-W10", "week": "2026-W22",
               "regenerated": False, "backfilled": False, "entries_this_week": 1})
    vs.append({"memory_id": "pi_long_r", "relationship_key": "r", "version": 6, "status": "retracted", "same_day_only": False, "flags_seen": [], "created_week": "2026-W10", "week": "2026-W26",
               "regenerated": False, "backfilled": False, "entries_this_week": 0})
    plan = {"n_total": 25, "weakened_key": "w", "chain_length": 3}
    a, b = run_text.select_sample(vs, plan, 7), run_text.select_sample(vs, plan, 7)
    assert a == b and len(a) == 25 and run_text.select_sample(vs, plan, 8) != a
    why = {w.split(":")[0] for w, _ in a}
    assert {"same-day only", "candidate", "supported", "back-filled supported", "weakened", "regenerated", "placebo_fired", "retracted", "chain"} <= why
    chain = sorted(u for w, u in a if w.startswith("chain"))
    assert len(chain) == 3 and len({m for m, _ in chain}) == 1 and [v for _, v in chain] == list(range(chain[0][1], chain[0][1] + 3))
    assert len({u for _, u in a}) == 25
