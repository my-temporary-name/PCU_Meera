"""The daily refresh (spec 8, D1 to D5): every runnable relationship as of the start of an outcome date, from her completed earlier days."""

import re
from collections import Counter
from datetime import date, datetime, time

import numpy as np

from v0_code.evidence_engine import stats
from v0_code.evidence_engine.config import EvidenceConfig
from v0_code.evidence_engine.data import EvidenceData
from v0_code.evidence_engine.exposures import ExposureEvaluator
from v0_code.evidence_engine.history import Hist, Series
from v0_code.evidence_engine.library import KEY, Library
from v0_code.evidence_engine.storage import EvidenceStore
from v0_code.evidence_engine.units import build_units

LABELS = ("supported", "suggestive", "not_supported", "insufficient")


def _tokens(outcome: dict) -> list[str]:
    v = outcome["value"]
    return [t for t in (v.get("source"), v.get("event_source"), outcome.get("unit_source")) if t]


class DailyRefresh:
    def __init__(self, data: EvidenceData, lib: Library, cfg: EvidenceConfig, store: EvidenceStore | None = None):
        self.data, self.lib, self.cfg, self.store = data, lib, cfg, store
        self.ev = ExposureEvaluator(lib, cfg, data)
        self._units: dict[str, dict] = {}
        self._series: dict[tuple, Series] = {}

    # ---- relationships ------------------------------------------------------------------------------------------------------------------------------
    def units(self, outcome_name: str) -> dict:
        if outcome_name not in self._units:
            self._units[outcome_name] = build_units(self.lib.outcomes[outcome_name], self.data, self.cfg)
        return self._units[outcome_name]

    def scopes(self, pair: dict, D: date) -> list:
        outcome = self.lib.outcomes[pair["outcome"]]
        if outcome.get("scope") != "event_kind":
            return [None]
        cut = datetime.combine(D, time(0), tzinfo=self.data.tz)
        have = {k for k, us in self.units(pair["outcome"]).items() if us and us[0].end <= cut}
        return [k for k in self.data.kinds if k in have]                          # D1: every meal kind that occurs in her history

    def relationships(self, D: date) -> list[tuple[dict, str | None]]:
        return [(p, s) for p in self.lib.runnable() for s in self.scopes(p, D)]

    def series(self, pair: dict, scope) -> Series:
        k = (pair["key"], scope)
        if k not in self._series:
            tag = KEY.match(pair["key"]).group(2)
            self._series[k] = Series(self.ev, self.lib.outcomes[pair["outcome"]], self.lib.exposures[pair["exposure"]], tag, pair["ordering"] == "excludes_outcome_day",
                                     self.units(pair["outcome"]).get(scope, []))
        return self._series[k]

    # ---- one relationship ---------------------------------------------------------------------------------------------------------------------------
    def _evaluate(self, pair: dict, scope, D: date) -> dict:
        cfg = self.cfg
        outcome, exposure = self.lib.outcomes[pair["outcome"]], self.lib.exposures[pair["exposure"]]
        key = pair["key"].replace("{meal_kind}", scope) if scope else pair["key"]
        binary = exposure["form"] == "binary"
        rec = {
            "evidence_id": f"rel|{key}|{D.isoformat()}|{cfg.method_version}", "relationship_key": key, "exposure_id": pair["exposure"], "outcome_id": pair["outcome"],
            "outcome_scope": {"meal_kind": scope} if scope else {}, "unit": outcome["unit"], "form": exposure["form"], "check_type": pair["check_type"], "as_of_date": D.isoformat(),
            "history": None,
            "orientation": {"outcome_worse_is": outcome["worse_is"], "exposure_risk_side": exposure["risk_side"]},
            "detrend": {"method": "trailing_median", "window_days": cfg.detrend_window_days, "min_prior_values": cfg.detrend_min_prior},
            "n_exposed": None, "n_reference": None, "effect_kind": "smd" if binary else "spearman_rho", "effect": None, "raw_difference": None, "permutation": None,
            "adjustment": None, "support": "insufficient", "insufficient_reason": None, "flags": ["same_day_unverified"] if pair["ordering"] == "same_day_unverified" else [],
            "placebo": None, "method_version": cfg.method_version, "config_version": cfg.config_version, "inputs_hash": "", "status": "current"}
        needed = [exposure["value"]["source"]] + [t for t in _tokens(outcome)]
        if any(not self.data.has(t) for t in needed):
            rec["insufficient_reason"] = "no_stream"
            return rec
        h: Hist = self.series(pair, scope).at(D, self.data.tz)
        n = len(h.y)
        rec["inputs_hash"] = h.inputs_hash
        n_dates = int(len(np.unique(h.dates)))
        rec["history"] = {"first_day": h.first_day.isoformat() if h.first_day else None, "last_day": h.last_day.isoformat() if h.last_day else None, "n_units": n,
                          "n_dates": n_dates, "n_dropped_by_detrend": h.n_dropped_by_detrend}
        if binary:
            rec["n_exposed"], rec["n_reference"] = int(h.x.sum()), int(n - h.x.sum())
        else:
            rec["n_exposed"] = n
        if n == 0 and h.n_unordered > 0 and h.n_missing == 0:
            rec["insufficient_reason"] = "no_ordered_exposure"
        elif n < cfg.min_history_units or n_dates < cfg.min_history_days:                  # both minimums must be met: usable units AND distinct outcome dates
            rec["insufficient_reason"] = "history"
        elif binary and (rec["n_exposed"] < cfg.min_exposed or rec["n_reference"] < cfg.min_reference):
            rec["insufficient_reason"] = "small_group"
            rec["flags"].append("small_group")
        elif np.ptp(h.y) == 0 or (not binary and np.ptp(h.x) == 0):
            rec["insufficient_reason"] = "no_variation"
        else:
            r = stats.permutation_test(h.x, h.y, binary, cfg.n_perm, cfg.min_shift_fraction, cfg.placebo_shift_fraction, stats.seed_from(key, D.isoformat(), cfg.method_version))
            fired = stats.placebo_fires(r["placebo_effect"], r["placebo_p"], binary, cfg.labels)
            sign = -1.0 if outcome["worse_is"] == "lower" else 1.0
            rec.update(effect=round(r["effect"], 6), permutation={"method": "circular_shift", "n": cfg.n_perm, "p": r["p"], "p_contrary": r["p_contrary"]},
                       placebo={"effect": round(r["placebo_effect"], 6), "p": r["placebo_p"], "fired": fired})
            if binary:
                rec["raw_difference"] = round(stats.raw_difference(h.x, h.y) * sign, 6)       # in the outcome's own (detrended) unit
            rec["_tested"] = True
        return rec

    # ---- the day ------------------------------------------------------------------------------------------------------------------------------------
    def compute(self, D: date) -> tuple[list[dict], dict]:
        recs = [self._evaluate(p, s, D) for p, s in self.relationships(D)]
        tested = [r for r in recs if r.pop("_tested", False)]
        adj = stats.benjamini_hochberg([r["permutation"]["p"] for r in tested])           # D3: the family is the relationships that passed the minimums
        for r, pa in zip(tested, adj):
            binary = r["form"] == "binary"
            label, flags = stats.label_relationship(r["effect"], r["permutation"]["p"], pa, r["permutation"]["p_contrary"], r["placebo"]["fired"], binary, self.cfg.labels)
            r["adjustment"] = {"method": "benjamini_hochberg", "family_size": len(tested), "p_adjusted": round(pa, 6)}
            r["support"] = label
            r["flags"] = flags + [f for f in r["flags"] if f not in flags]
        summary = {
            "as_of_date": D.isoformat(), "method_version": self.cfg.method_version, "n_relationships": len(recs), "n_tested": len(tested), "family_size": len(tested),
            "placebo_tested": len(tested), "placebo_fired": sum(1 for r in tested if r["placebo"]["fired"]),
            "counts": {k: sum(1 for r in recs if r["support"] == k) for k in LABELS},
            "reasons": dict(Counter(r["insufficient_reason"] for r in recs if r["insufficient_reason"])),
            "flags": dict(Counter(f for r in recs for f in r["flags"]))}
        return recs, summary

    def refresh(self, D: date) -> dict:
        """D1 to D5: compute, write each relationship record (reused when nothing changed) and the run summary."""
        recs, summary = self.compute(D)
        if self.store is not None:
            outcomes = Counter(self.store.put_relationship(r) for r in recs)
            summary["writes"] = dict(outcomes)
            self.store.put_run(D.isoformat(), self.cfg.method_version, {k: v for k, v in summary.items() if k != "writes"})
        return summary
