"""The statistics of spec 7.2: effects, circular-shift permutation, placebo, Benjamini-Hochberg and the labels. Pure numpy.

All shifted effects are computed together: with the exposure rotated by s, the effect is a function of the circular cross-correlation of the exposure with the
outcome, so one FFT gives every rotation at once. A binary exposure keeps its group sizes under rotation, so the standardised mean difference is a function of
the mean difference alone."""

import hashlib
import math

import numpy as np

TOL = 1e-9          # comparisons "at least as large as the real one" use this tolerance so float noise cannot change a p-value


def seed_from(key: str, as_of: str, version: str) -> int:
    """A stable seed (SHA-256, not Python's salted hash) from the relationship key, the as-of date and the method version."""
    return int.from_bytes(hashlib.sha256(f"{key}|{as_of}|{version}".encode()).digest()[:8], "big")


def ranks(a: np.ndarray) -> np.ndarray:
    """Average ranks (1-based), ties share the mean rank."""
    a = np.asarray(a, float)
    order = np.argsort(a, kind="mergesort")
    sorted_a = a[order]
    new = np.concatenate(([True], sorted_a[1:] != sorted_a[:-1]))
    group = np.cumsum(new) - 1
    first = np.flatnonzero(new)
    counts = np.diff(np.concatenate((first, [len(a)])))
    avg = first + (counts + 1) / 2.0
    out = np.empty(len(a))
    out[order] = avg[group]
    return out


def _ccorr(x: np.ndarray, y: np.ndarray) -> np.ndarray:
    """out[s] = sum_i y[i] * x[(i + s) mod n]: the cross-correlation at every circular shift."""
    n = len(x)
    return np.fft.irfft(np.fft.rfft(x) * np.conj(np.fft.rfft(y)), n)


def circular_effects(x, y, binary: bool) -> np.ndarray:
    """The effect for every rotation s of the exposure (s = 0 is the real one)."""
    x = np.asarray(x, float)
    y = np.asarray(y, float)
    n = len(y)
    if binary:
        n1 = x.sum()
        n0 = n - n1
        s1 = _ccorr(x, y)
        delta = s1 / n1 - (y.sum() - s1) / n0
        tss = ((y - y.mean()) ** 2).sum()
        within = np.maximum(tss - n * (n1 / n) * (n0 / n) * delta ** 2, 1e-300)
        return delta / np.sqrt(within / (n - 2))
    rx, ry = ranks(x), ranks(y)
    cov = _ccorr(rx, ry) / n - rx.mean() * ry.mean()
    return cov / (rx.std() * ry.std())


def raw_difference(x, y) -> float:
    """Mean of y over the exposed minus the mean over the reference (binary exposure), in y's own unit."""
    x = np.asarray(x, float)
    y = np.asarray(y, float)
    return float(y[x == 1].mean() - y[x == 0].mean())


def draw_offsets(n: int, n_perm: int, min_shift_fraction: float, rng: np.random.Generator) -> np.ndarray:
    lo = max(1, math.ceil(min_shift_fraction * n))
    return rng.integers(lo, n - lo + 1, size=n_perm)


def permutation_test(x, y, binary: bool, n_perm: int, min_shift_fraction: float, placebo_fraction: float, seed: int) -> dict:
    """One-sided circular-shift permutation (the usual +1 correction, so the smallest p is 1 / (n_perm + 1)), the p for the opposite direction, and the placebo
    (the exposure rotated by exactly `placebo_fraction` of the series, its p read from the same null)."""
    n = len(y)
    all_eff = circular_effects(x, y, binary)
    eff = float(all_eff[0])
    null = all_eff[draw_offsets(n, n_perm, min_shift_fraction, np.random.default_rng(seed))]
    shift = int(round(placebo_fraction * n)) % n
    pe = float(all_eff[shift])
    return {"effect": eff, "p": (1 + int(np.sum(null >= eff - TOL))) / (n_perm + 1), "p_contrary": (1 + int(np.sum(null <= eff + TOL))) / (n_perm + 1),
            "placebo_effect": pe, "placebo_p": (1 + int(np.sum(null >= pe - TOL))) / (n_perm + 1), "placebo_shift": shift}


def benjamini_hochberg(p: list[float]) -> list[float]:
    m = len(p)
    if m == 0:
        return []
    order = sorted(range(m), key=lambda i: p[i])
    adj = [0.0] * m
    running = 1.0
    for rank in range(m, 0, -1):
        i = order[rank - 1]
        running = min(running, p[i] * m / rank)
        adj[i] = min(1.0, running)
    return adj


def label_relationship(effect: float, p: float, p_adj: float, p_contrary: float, placebo_fired: bool, binary: bool, labels: dict) -> tuple[str, list[str]]:
    """spec 7.2 labels. A fired placebo caps `supported` at `suggestive`; `contrary` is a flag, never a label."""
    floor = labels["effect_floor_binary"] if binary else labels["effect_floor_continuous"]
    q = labels["p_suggestive"]
    flags = []
    if effect < 0 and p_contrary <= labels["contrary_p"] + TOL:
        flags.append("contrary")
    if placebo_fired:
        flags.append("placebo_fired")
    suggestive = p <= q + TOL and effect >= floor - TOL
    if suggestive and p_adj <= q + TOL and not placebo_fired:
        return "supported", flags
    return ("suggestive" if suggestive else "not_supported"), flags


def placebo_fires(placebo_effect: float, placebo_p: float, binary: bool, labels: dict) -> bool:
    floor = labels["effect_floor_binary"] if binary else labels["effect_floor_continuous"]
    return placebo_p <= labels["p_suggestive"] + TOL and placebo_effect >= floor - TOL
