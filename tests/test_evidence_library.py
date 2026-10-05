"""Evidence library and its load check (spec 6 and property 16)."""

import copy
import csv
import shutil
from pathlib import Path

import pytest
import yaml

from v0_code.evidence_engine.library import LibraryError, derive_ordering, load_library

ROOT = Path(__file__).resolve().parent.parent
LIB = ROOT / "config/evidence_library_v0.yaml"
RB = ROOT / "task/evidence_engine"
CAND = "rulebook_v0_candidates.csv"


def check(lib, rb=RB):
    lib.check(rb, CAND)


def test_real_library_loads_and_matches_the_rulebook():
    lib = load_library(LIB)
    assert len(lib.pairs) == 69 and len(lib.outcomes) == 10 and len(lib.exposures) == 16
    check(lib)
    runnable = [p for p in lib.pairs if p["status"] == "runnable"]
    assert len(runnable) == 49 and len({p["key"] for p in runnable}) == 49
    from collections import Counter
    assert Counter(p["ordering"] for p in runnable) == {"ordered": 25, "same_day_unverified": 22, "excludes_outcome_day": 1, "no_ordered_exposure": 1}


def test_declared_ordering_equals_the_ordering_derived_from_the_rules():
    lib = load_library(LIB)
    for p in lib.pairs:
        if p["status"] != "runnable" or p["ordering"] in ("no_ordered_exposure", "excludes_outcome_day"):
            continue
        assert derive_ordering(lib, p) == p["ordering"], p["key"]


@pytest.fixture()
def paths(tmp_path):
    lib = tmp_path / "lib.yaml"
    shutil.copy(LIB, lib)
    rb = tmp_path / "rb"
    rb.mkdir()
    shutil.copy(RB / CAND, rb / CAND)
    return lib, rb


def rewrite(lib_path, fn):
    d = yaml.safe_load(lib_path.read_text())
    fn(d)
    lib_path.write_text(yaml.safe_dump(d, sort_keys=False))


def expect_error(lib_path, rb, word):
    with pytest.raises(LibraryError) as e:
        load_library(lib_path).check(rb, CAND)
    assert word in str(e.value), str(e.value)


def test_unknown_exposure_or_outcome(paths):
    lib, rb = paths
    rewrite(lib, lambda d: d["pairs"][1].update(exposure="no_such_exposure"))
    expect_error(lib, rb, "no_such_exposure")
    shutil.copy(LIB, lib)
    rewrite(lib, lambda d: d["pairs"][1].update(outcome="no_such_outcome"))
    expect_error(lib, rb, "no_such_outcome")


def test_runnable_without_key(paths):
    lib, rb = paths
    rewrite(lib, lambda d: d["pairs"][1].pop("key"))
    expect_error(lib, rb, "relationship key")


def test_rulebook_candidate_without_pair_and_pair_without_candidate(paths):
    lib, rb = paths
    rewrite(lib, lambda d: d["pairs"].pop(3))
    expect_error(lib, rb, "no pair row")
    shutil.copy(LIB, lib)
    rows = list(csv.DictReader(open(rb / CAND)))
    with open(rb / CAND, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=rows[0].keys())
        w.writeheader()
        w.writerows(rows[:-1])
    expect_error(lib, rb, "no rulebook candidate")


def test_bad_form_and_unknown_lookback_kind(paths):
    lib, rb = paths
    rewrite(lib, lambda d: d["exposures"]["sleep_hours"].update(form="ordinal"))
    expect_error(lib, rb, "binary or continuous")
    shutil.copy(LIB, lib)
    rows = list(csv.DictReader(open(rb / CAND)))
    rows[1]["lookback_kind"] = "whenever"
    with open(rb / CAND, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=rows[0].keys())
        w.writeheader()
        w.writerows(rows)
    expect_error(lib, rb, "whenever")


def test_check_type_and_tier_disagree_with_the_rulebook(paths):
    lib, rb = paths
    rewrite(lib, lambda d: d["pairs"][1].update(check_type="percentile_vs_history"))
    expect_error(lib, rb, "check_type")
    shutil.copy(LIB, lib)
    rewrite(lib, lambda d: d["pairs"][1].update(tier="primary"))
    expect_error(lib, rb, "weight_tier")


def test_key_lookback_tag_must_equal_the_rulebooks(paths):
    lib, rb = paths
    rewrite(lib, lambda d: d["pairs"][1].update(key="missed_dose@3d->post_meal_peak:{meal_kind}"))
    expect_error(lib, rb, "lookback tag")


def test_ordering_must_be_allowed_and_consistent(paths):
    lib, rb = paths
    rewrite(lib, lambda d: d["pairs"][1].update(ordering="sort_of_ordered"))
    expect_error(lib, rb, "ordering")
    shutil.copy(LIB, lib)
    rewrite(lib, lambda d: d["pairs"][2].update(ordering="same_day_unverified"))              # sleep for a meal unit is ordered
    expect_error(lib, rb, "derived")


def test_presence_flags_must_agree_with_the_rulebook_config():
    from v0_code.rulebook_lookup.config import RulebookConfig
    lib = load_library(LIB)
    cfg = RulebookConfig.from_yaml(ROOT / "config/rulebook_meera_iyer_v1.yaml", ROOT)
    flags = {"other_medications": {"glucose_raising": False, "bp_raising": False}, "thyroid_status": {"thyroid_medication": True},
             "hypoglycemic_agent": {"insulin": False, "sulfonylurea": False}}
    sources = {"glucose_raising": {"class": "glucose_raising"}, "bp_raising": {"class": "bp_raising"}, "thyroid_medication": {"class": "thyroid"},
               "insulin": {"class": "insulin"}, "sulfonylurea": {"class": "sulfonylurea"}}
    lib.check(RB, CAND, presence=(flags, sources, cfg))
    bad = copy.deepcopy(flags)
    bad["thyroid_status"]["thyroid_medication"] = False
    with pytest.raises(LibraryError) as e:
        lib.check(RB, CAND, presence=(bad, sources, cfg))
    assert "thyroid_medication" in str(e.value)
