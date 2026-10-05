"""Evidence Engine statistics (spec 7.2): effects, circular-shift permutation, placebo, Benjamini-Hochberg, labels. numpy only."""

import hashlib

import numpy as np
import pytest

from v0_code.evidence_engine import stats


def brute_effect(x, y, binary, s):
    xs = np.roll(np.asarray(x, float), -s)                       # xs[i] = x[(i + s) % n]
    y = np.asarray(y, float)
    if binary:
        e, r = y[xs == 1], y[xs == 0]
        pooled = np.sqrt((((e - e.mean()) ** 2).sum() + ((r - r.mean()) ** 2).sum()) / (len(y) - 2))
        return (e.mean() - r.mean()) / pooled
    rx, ry = stats.ranks(xs), stats.ranks(y)
    return float(np.corrcoef(rx, ry)[0, 1])


def test_ranks_use_average_for_ties():
    assert list(stats.ranks(np.array([10.0, 20.0, 20.0, 5.0]))) == [2.0, 3.5, 3.5, 1.0]


@pytest.mark.parametrize("binary", [True, False])
def test_circular_effects_match_brute_force(binary):
    rng = np.random.default_rng(3)
    n = 80
    x = (rng.random(n) < 0.3).astype(float) if binary else np.round(rng.normal(size=n), 1)     # the continuous exposure has ties
    y = np.round(rng.normal(size=n) + 0.5 * x, 1)
    eff = stats.circular_effects(x, y, binary)
    assert eff.shape == (n,)
    for s in (0, 1, 7, 33, n - 1):
        assert eff[s] == pytest.approx(brute_effect(x, y, binary, s), abs=1e-9)


def test_binary_effect_is_the_standardised_mean_difference():
    x = np.array([1, 1, 1, 0, 0, 0, 0, 0], float)
    y = np.array([5, 6, 7, 1, 2, 3, 2, 1], float)
    e, r = y[:3], y[3:]
    pooled = np.sqrt((((e - e.mean()) ** 2).sum() + ((r - r.mean()) ** 2).sum()) / 6)
    assert stats.circular_effects(x, y, True)[0] == pytest.approx((e.mean() - r.mean()) / pooled)
    assert stats.raw_difference(x, y) == pytest.approx(e.mean() - r.mean())


def test_seed_is_a_stable_hash_of_key_date_and_version():
    s = stats.seed_from("k@1d->o", "2026-01-01", "ev-v0")
    assert s == int.from_bytes(hashlib.sha256(b"k@1d->o|2026-01-01|ev-v0").digest()[:8], "big")
    assert s == stats.seed_from("k@1d->o", "2026-01-01", "ev-v0")
    assert s != stats.seed_from("k@1d->o", "2026-01-02", "ev-v0") and s != stats.seed_from("k@1d->o", "2026-01-01", "ev-v1")


def test_offsets_respect_the_minimum_shift():
    rng = np.random.default_rng(1)
    off = stats.draw_offsets(200, 2000, 0.05, rng)
    assert len(off) == 2000 and off.min() >= 10 and off.max() <= 190


def make_assoc(n=120, strength=1.0, seed=5, binary=True):
    rng = np.random.default_rng(seed)
    x = (rng.random(n) < 0.33).astype(float) if binary else rng.normal(size=n)       # not periodic: a periodic exposure re-aligns with itself under rotation
    y = rng.normal(size=n) + strength * x
    return x, y


def test_permutation_is_deterministic_and_bounded():
    x, y = make_assoc()
    a = stats.permutation_test(x, y, True, 2000, 0.05, 0.30, seed=11)
    b = stats.permutation_test(x, y, True, 2000, 0.05, 0.30, seed=11)
    assert a == b
    assert 1 / 2001 <= a["p"] <= 1 and 1 / 2001 <= a["p_contrary"] <= 1
    assert stats.permutation_test(x, y, True, 2000, 0.05, 0.30, seed=12)["effect"] == a["effect"]      # the effect does not depend on the seed


def test_strong_positive_association_gives_small_p_and_large_p_contrary():
    x, y = make_assoc(strength=3.0, n=240)
    r = stats.permutation_test(x, y, True, 2000, 0.05, 0.30, seed=1)
    assert r["effect"] > 1 and r["p"] < 0.05 and r["p_contrary"] > 0.9


def test_negative_association_reports_contrary_side():
    x, y = make_assoc(strength=-3.0, n=240)
    r = stats.permutation_test(x, y, True, 2000, 0.05, 0.30, seed=1)
    assert r["effect"] < -1 and r["p_contrary"] < 0.05 and r["p"] > 0.9


def test_placebo_is_the_effect_at_exactly_thirty_percent_and_uses_the_same_null():
    x, y = make_assoc(n=100)
    r = stats.permutation_test(x, y, True, 2000, 0.05, 0.30, seed=2)
    assert r["placebo_effect"] == pytest.approx(brute_effect(x, y, True, 30), abs=1e-9)
    assert 1 / 2001 <= r["placebo_p"] <= 1


def test_benjamini_hochberg():
    adj = stats.benjamini_hochberg([0.01, 0.04, 0.03, 0.2])
    assert adj == pytest.approx([0.04, 0.0533333333, 0.0533333333, 0.2])
    assert stats.benjamini_hochberg([]) == []
    assert stats.benjamini_hochberg([0.5]) == [0.5]
    assert max(stats.benjamini_hochberg([0.9, 0.95])) <= 1.0


LAB = dict(p_suggestive=0.10, effect_floor_binary=0.10, effect_floor_continuous=0.10, contrary_p=0.10)


def lab(effect=0.3, p=0.01, p_adj=0.05, p_contrary=0.99, placebo_fired=False, binary=True):
    return stats.label_relationship(effect, p, p_adj, p_contrary, placebo_fired, binary, LAB)


def test_labels():
    assert lab() == ("supported", [])
    assert lab(p_adj=0.2) == ("suggestive", [])
    assert lab(p=0.5, p_adj=0.6) == ("not_supported", [])
    assert lab(effect=0.05) == ("not_supported", [])                                  # below the floor
    assert lab(placebo_fired=True) == ("suggestive", ["placebo_fired"])               # a fired placebo caps supported at suggestive
    assert lab(placebo_fired=True, p=0.4, p_adj=0.5) == ("not_supported", ["placebo_fired"])
    assert lab(effect=-0.5, p=0.99, p_adj=0.99, p_contrary=0.02) == ("not_supported", ["contrary"])
    assert lab(effect=-0.5, p=0.99, p_adj=0.99, p_contrary=0.5) == ("not_supported", [])
    assert lab(effect=0.10, p=0.10, p_adj=0.5)[0] == "suggestive"                    # both limits are inclusive
