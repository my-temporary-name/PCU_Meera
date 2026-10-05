"""PI: the status lifecycle (pi_spec.md 6.3 as amended, item 35): runs of equal decisive labels reset by the opposite decisive label."""

import pytest

from v0_code.pi_engine.lifecycle import LifecycleCfg, Wk, initial, run, step

CFG = LifecycleCfg(promote_after=2, weaken_after=2, retract_after=6, contrary_days=5, contrary_of=7, contrary_weeks=4, repromote_after=2, placebo_max_share=0.5, min_days=4, scale=True)


def wk(n, label, days=7, placebo=0, contrary=0, end=None):
    return Wk(iso=f"2026-W{n:02d}", end=end or f"2026-{1 + n // 5:02d}-{n % 28 + 1:02d}", label=label, days_in_week=days, placebo_days=placebo, contrary_days=contrary)


def statuses(labels, **kw):
    s, out = initial(), []
    for i, l in enumerate(labels, 1):
        s = step(s, wk(i, l, **kw), CFG)
        out.append(s.status)
    return out


def test_the_specs_example_timeline():
    # W38 supported, W39 supported, W40 suggestive, W41 not_supported, W42 not_supported, W43..W48 not_supported
    labels = ["supported", "supported", "suggestive", "not_supported", "not_supported"] + ["not_supported"] * 6
    assert statuses(labels) == ["candidate", "supported", "supported", "supported", "weakened"] + ["weakened"] * 5 + ["retracted"]


def test_one_supported_week_is_not_enough_and_the_opposite_label_resets_the_run():
    assert statuses(["supported", "not_supported", "supported"]) == ["candidate"] * 3
    assert statuses(["supported", "suggestive", "supported"]) == ["candidate", "candidate", "supported"]       # a suggestive week neither extends nor resets
    assert statuses(["supported", "insufficient", "insufficient", "supported"]) == ["candidate", "candidate", "candidate", "supported"]


def test_a_candidate_is_never_weakened_by_not_supported_weeks():
    assert statuses(["not_supported"] * 5) == ["candidate"] * 5


def test_a_supported_status_needs_two_consecutive_not_supported_weeks_to_weaken():
    assert statuses(["supported", "supported", "not_supported", "supported"]) == ["candidate", "supported", "supported", "supported"]
    assert statuses(["supported", "supported", "not_supported", "suggestive", "not_supported"]) == ["candidate", "supported", "supported", "supported", "weakened"]


def test_retraction_needs_six_unbroken_not_supported_weeks_after_the_week_of_weakening():
    base = ["supported", "supported", "not_supported", "not_supported"]
    s = statuses(base + ["not_supported"] * 5)
    assert s[3] == "weakened" and s[-1] == "weakened"                                              # five further weeks: not yet
    assert statuses(base + ["not_supported"] * 6)[-1] == "retracted"
    # a decisive supported week resets the count; suggestive and insufficient weeks do not
    assert statuses(base + ["not_supported"] * 3 + ["supported"] + ["not_supported"] * 5)[-1] == "weakened"
    assert statuses(base + ["not_supported"] * 3 + ["suggestive", "insufficient"] + ["not_supported"] * 3)[-1] == "retracted"


def test_a_weakened_status_returns_to_supported_after_two_supported_weeks():
    base = ["supported", "supported", "not_supported", "not_supported"]
    assert statuses(base + ["supported"]) [-1] == "weakened" and statuses(base + ["supported", "supported"])[-1] == "supported"
    assert statuses(base + ["supported", "not_supported", "supported"])[-1] == "weakened"


def test_retraction_by_the_contrary_flag_needs_four_consecutive_qualifying_weeks_after_weakening():
    s, out = initial(), []
    for i, (lab, c) in enumerate([("supported", 0), ("supported", 0), ("not_supported", 0), ("not_supported", 0), ("suggestive", 5), ("insufficient", 6), ("suggestive", 7), ("insufficient", 5)], 1):
        s = step(s, wk(i, lab, contrary=c), CFG)
        out.append(s.status)
    assert out[3] == "weakened" and out[-1] == "retracted" and out[-2] == "weakened"
    s = initial()
    for i, (lab, c) in enumerate([("supported", 0), ("supported", 0), ("not_supported", 0), ("not_supported", 0), ("suggestive", 5), ("suggestive", 5), ("suggestive", 4), ("suggestive", 5), ("suggestive", 5)], 1):
        s = step(s, wk(i, lab, contrary=c), CFG)
    assert s.status == "weakened"                                                                  # a week below the threshold broke the run


def test_a_retracted_memory_becomes_a_candidate_again_after_two_supported_weeks():
    labels = ["supported", "supported", "not_supported", "not_supported"] + ["not_supported"] * 6
    assert statuses(labels)[-1] == "retracted"
    assert statuses(labels + ["supported"])[-1] == "retracted" and statuses(labels + ["supported", "supported"])[-1] == "candidate"
    assert statuses(labels + ["supported", "supported", "supported"])[-1] == "supported"


def test_the_placebo_flag_blocks_promotion_while_it_fires_on_half_the_days_or_more():
    s = initial()
    s = step(s, wk(1, "supported", placebo=4), CFG)
    s = step(s, wk(2, "supported", placebo=4), CFG)                                               # 8 of 14 days
    assert s.status == "candidate"
    s = step(s, wk(3, "supported", placebo=1), CFG)                                               # the latest two weeks: 5 of 14
    assert s.status == "supported"
    t = initial()
    t = step(t, wk(1, "supported", placebo=3), CFG)
    t = step(t, wk(2, "supported", placebo=3), CFG)                                               # 6 of 14: fewer than half
    assert t.status == "supported"


def test_status_since_and_the_history_record_every_transition_with_its_week():
    s = initial()
    for i, l in enumerate(["supported", "supported", "not_supported", "not_supported"], 1):
        s = step(s, wk(i, l, end=f"2026-01-{i * 7:02d}"), CFG)
    assert s.history == [{"week": "2026-W02", "from": "candidate", "to": "supported"}, {"week": "2026-W04", "from": "supported", "to": "weakened"}]
    assert s.since == "2026-01-28"


def test_back_fill_equals_stepping_one_week_at_a_time():
    labels = ["insufficient", "supported", "supported", "suggestive", "not_supported", "not_supported", "not_supported", "supported", "supported"]
    weeks = [wk(i, l) for i, l in enumerate(labels, 1)]
    inc = initial()
    for w in weeks:
        inc = step(inc, w, CFG)
    back = run(weeks, CFG)
    assert (inc.status, inc.since, inc.history, inc.run_label, inc.run_len) == (back.status, back.since, back.history, back.run_label, back.run_len)
    assert back.status == "supported"


def test_step_does_not_change_the_state_it_was_given():
    s = initial()
    t = step(s, wk(1, "supported"), CFG)
    assert s.run_len == 0 and t.run_len == 1 and s is not t
