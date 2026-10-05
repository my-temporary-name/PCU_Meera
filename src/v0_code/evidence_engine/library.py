"""The static library (config/evidence_library_v0.yaml) and its load check (spec section 13, property 16). The library is data derived from spec sections 5, 6.1,
6.2 and Appendix A; nothing generates it at run time, and every disagreement with the rulebook files fails loudly here."""

import csv
import re
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path

import yaml

from v0_code.evidence_engine.windows import window_for

OUTCOME_PRIMITIVES = ("max_after_event", "mean_outside_event_windows", "min_of_day", "mean_of_day", "mean_of_hour", "dated_record", "count_matching_by_day", "record_value")
EXPOSURE_PRIMITIVES = ("any_in_window", "value_in_window", "mean_in_window", "event_start_minute")
UNITS = ("meal", "day", "hour", "reading")
FORMS = ("binary", "continuous")
RESOLUTIONS = ("date", "timestamp", "block")
ORDERINGS = ("ordered", "same_day_unverified", "excludes_outcome_day", "no_ordered_exposure")
STATUSES = ("runnable", "event_level", "no_definition", "rule_deferred")
EVENT_CHECK_TYPES = ("percentile_vs_history", "shape_check", "pattern_repeat", "presence_check")
EVENT_MEASURES = {"percentile_vs_history": ("peak_at_elapsed", "hours_since_last_event"), "shape_check": ("isolated_reading",), "pattern_repeat": ("rise_in_window", "rate_by_group"),
                  "presence_check": (None,)}
KEY = re.compile(r"^(\w+)@(\w+)->(\w+)(:\{meal_kind\})?$")


class LibraryError(ValueError):
    """Loading failed; the message lists every problem found, in plain words."""


@dataclass(frozen=True)
class Library:
    version: str
    lookback_tags: dict
    shifted_tags: frozenset
    evening: tuple
    sources: dict
    outcomes: dict
    exposures: dict
    event_checks: dict
    pairs: tuple

    def tag_for(self, kind: str, value) -> str:
        t = self.lookback_tags[kind]
        return t.replace("{value}", str(value)) if "{value}" in t else t

    def pair(self, rule_id: str, rank: int) -> dict | None:
        return next((p for p in self.pairs if p["rule"] == rule_id and p["rank"] == rank), None)

    def runnable(self) -> list[dict]:
        return [p for p in self.pairs if p["status"] == "runnable"]

    # ---- the load check ---------------------------------------------------------------------------------------------------------------------------
    def check(self, rulebook_dir: str | Path, candidates_file: str, presence: tuple | None = None) -> None:
        """Compare the library with the rulebook's candidates file (and, if given, the presence flags with the Rulebook Lookup config)."""
        errors = list(self._structure_errors())
        rows = list(csv.DictReader(open(Path(rulebook_dir) / candidates_file, newline="")))
        by_key = {(r["rule_id"], int(r["rank"])): r for r in rows}
        pair_keys = {(p["rule"], p["rank"]) for p in self.pairs}
        for k in sorted(by_key.keys() - pair_keys):
            errors.append(f"rulebook candidate {k[0]}#{k[1]} ({by_key[k]['candidate']}) has no pair row in the library")
        for k in sorted(pair_keys - by_key.keys()):
            errors.append(f"library pair {k[0]}#{k[1]} has no rulebook candidate")
        for p in self.pairs:
            r = by_key.get((p["rule"], p["rank"]))
            if r is None:
                continue
            where = f"pair {p['rule']}#{p['rank']} ({p['candidate']})"
            if p["candidate"] != r["candidate"]:
                errors.append(f"{where}: candidate name differs from the rulebook's {r['candidate']!r}")
            if p["check_type"] != r["check_type"]:
                errors.append(f"{where}: check_type {p['check_type']!r} differs from the rulebook's {r['check_type']!r}")
            if p["tier"] != r["weight_tier"]:
                errors.append(f"{where}: weight_tier {p['tier']!r} differs from the rulebook's {r['weight_tier']!r}")
            if r["lookback_kind"] not in self.lookback_tags:
                errors.append(f"{where}: the rulebook's lookback_kind {r['lookback_kind']!r} is unknown to the library")
            elif p["status"] == "runnable" and KEY.match(p.get("key", "")):
                want = self.tag_for(r["lookback_kind"], r["lookback_value"])
                got = KEY.match(p["key"]).group(2)
                if got != want:
                    errors.append(f"{where}: the lookback tag in the key is {got!r} but the rulebook's lookback gives {want!r}")
        if presence is not None:
            errors.extend(self._presence_errors(*presence))
        if errors:
            raise LibraryError("The evidence library cannot be loaded:\n - " + "\n - ".join(errors))

    def _structure_errors(self):
        for name, o in self.outcomes.items():
            if o.get("unit") not in UNITS:
                yield f"outcome {name}: unit must be one of {UNITS}"
            if o["value"].get("primitive") not in OUTCOME_PRIMITIVES:
                yield f"outcome {name}: unknown primitive {o['value'].get('primitive')!r}"
            if o.get("worse_is") not in ("higher", "lower"):
                yield f"outcome {name}: worse_is must be higher or lower"
        for name, e in self.exposures.items():
            if e.get("form") not in FORMS:
                yield f"exposure {name}: the form must be binary or continuous, got {e.get('form')!r}"
            if e["value"].get("primitive") not in EXPOSURE_PRIMITIVES:
                yield f"exposure {name}: unknown primitive {e['value'].get('primitive')!r}"
            if e.get("resolution") not in RESOLUTIONS:
                yield f"exposure {name}: resolution must be one of {RESOLUTIONS}"
            if e.get("risk_side") not in ("exposed", "low", "high"):
                yield f"exposure {name}: risk_side must be exposed, low or high"
        for name, c in self.event_checks.items():
            if c.get("type") not in EVENT_CHECK_TYPES:
                yield f"event check {name}: type must be one of {EVENT_CHECK_TYPES}"
            elif c.get("measure") not in EVENT_MEASURES[c["type"]]:
                yield f"event check {name}: unknown measure {c.get('measure')!r} for {c['type']}"
        dates = {}
        for p in self.pairs:
            if p.get("status") == "runnable" and p.get("outcome") in self.outcomes:
                dates.setdefault(p["rule"], set()).add(self.outcomes[p["outcome"]].get("outcome_date"))
        for rule, ds in dates.items():
            if len(ds) > 1:
                yield f"rule {rule}: its outcomes disagree on the outcome date ({sorted(ds)})"
        for p in self.pairs:
            where = f"pair {p['rule']}#{p['rank']} ({p['candidate']})"
            if p.get("status") not in STATUSES:
                yield f"{where}: status must be one of {STATUSES}"
                continue
            if p["status"] == "event_level" and p.get("event_check") not in self.event_checks:
                yield f"{where}: unknown event check {p.get('event_check')!r}"
            if p["status"] != "runnable":
                continue
            if p.get("exposure") not in self.exposures:
                yield f"{where}: unknown exposure {p.get('exposure')!r}"
            if p.get("outcome") not in self.outcomes:
                yield f"{where}: unknown outcome {p.get('outcome')!r}"
            if not p.get("key"):
                yield f"{where}: a runnable pair has no relationship key"
                continue
            m = KEY.match(p["key"])
            if not m:
                yield f"{where}: the relationship key {p['key']!r} is not <exposure>@<tag>-><outcome>[:{{meal_kind}}]"
                continue
            if m.group(1) != p.get("exposure") or m.group(3) != p.get("outcome"):
                yield f"{where}: the key {p['key']!r} does not name the pair's exposure and outcome"
            scoped = p.get("outcome") in self.outcomes and self.outcomes[p["outcome"]].get("scope") == "event_kind"
            if scoped != bool(m.group(4)):
                yield f"{where}: the key's scope placeholder disagrees with the outcome's scope"
            if p.get("ordering") not in ORDERINGS:
                yield f"{where}: the ordering {p.get('ordering')!r} is not one of {ORDERINGS}"
            elif p.get("exposure") in self.exposures and p.get("outcome") in self.outcomes and p["ordering"] not in ("no_ordered_exposure", "excludes_outcome_day"):
                got = derive_ordering(self, p)
                if got != p["ordering"]:
                    yield f"{where}: the ordering is declared {p['ordering']!r} but the derived ordering is {got!r}"

    def _presence_errors(self, flags: dict, sources: dict, rulebook_cfg):
        """The presence flags copied into the evidence config must equal the Rulebook Lookup config's facts."""
        for fact, values in flags.items():
            for flag, value in values.items():
                src = sources.get(flag)
                if src is None:
                    yield f"presence flag {flag!r} has no source in the Rulebook Lookup config mapping"
                    continue
                truth = rulebook_cfg.class_present(src["class"]) if "class" in src else rulebook_cfg.flag(src["patient_flag"])
                if bool(value) != truth:
                    yield f"presence flag {flag!r} of {fact!r} is {bool(value)} in the evidence config but {truth} in the Rulebook Lookup config"


def derive_ordering(lib: Library, pair: dict) -> str:
    """The Ordering that spec 3.1 rules 6 and 7 give a pair: a day-level unit cannot show anything inside its own date to come first; a date-only exposure inside the
    unit's own date cannot be ordered either; everything else is ordered. (`no_ordered_exposure` depends on the data and `excludes_outcome_day` on the pair.)"""
    o, e = lib.outcomes[pair["outcome"]], lib.exposures[pair["exposure"]]
    tag = KEY.match(pair["key"]).group(2)
    unit = o["unit"]
    if tag == "prev_night":
        return "same_day_unverified" if unit == "day" else "ordered"
    shift = int(o.get("exposure_shift_days", 0))
    start = datetime(2000, 1, 5, 0 if unit == "day" else 12, tzinfo=timezone(timedelta(0)))
    w = window_for(tag, unit, start, start.date(), shift, tag in lib.shifted_tags, False, lib.evening)
    if unit == "day":
        return "same_day_unverified" if w.includes_unit_date else "ordered"
    return "same_day_unverified" if e["resolution"] == "date" and w.includes_unit_date else "ordered"


def load_library(path: str | Path) -> Library:
    raw = yaml.safe_load(Path(path).read_text())
    ev = raw.get("evening", {"start": "18:00", "end": "24:00"})
    return Library(version=raw["library_version"], lookback_tags=dict(raw["lookback_tags"]), shifted_tags=frozenset(raw.get("shifted_tags", ())), evening=(ev["start"], ev["end"]),
                   sources=dict(raw.get("sources") or {}), outcomes=dict(raw["outcomes"]), exposures=dict(raw["exposures"]), event_checks=dict(raw.get("event_checks") or {}),
                   pairs=tuple(raw["pairs"]))
