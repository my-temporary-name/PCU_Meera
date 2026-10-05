"""The shared phrase book (config/findings_phrasebook_v0.yaml; findings_engine_spec.md Appendix A and Amendments). It turns library ids (exposure, outcome, window tag, event
candidate, hand-off measure) into plain words, once, so Findings and PI describe a relationship the same way. It is patient-independent data, checked at load against the
Evidence library: a missing phrase, class template or band fails loudly."""

import re
from pathlib import Path

import yaml

WORDING_CLASSES = ("asserted", "asserted_same_day", "hedged", "hedged_same_day", "exposure_only", "exposure_only_history", "contrary_note", "not_mentioned", "not_known_yet",
                   "event_unusual", "artifact_note")
TOP_KEYS = ("windows", "exposures", "outcomes", "event_checks", "classes", "elapsed_words", "meal_ago_words", "measures", "strength_words", "position_bands", "internal_words", "counting_words", "code_line", "kind_fallback", "clinical_terms", "pi_text")


class PhrasebookError(ValueError):
    pass


def cap(s: str) -> str:
    return s[:1].upper() + s[1:]


def plural(word: str) -> str:
    return word + ("es" if word.endswith(("s", "x", "z", "ch", "sh")) else "s")


def join_list(items: list[str]) -> str:
    return items[0] if len(items) == 1 else ", ".join(items[:-1]) + " and " + items[-1]


class Phrasebook:
    def __init__(self, raw: dict):
        self.raw = raw

    @classmethod
    def load(cls, path: str | Path) -> "Phrasebook":
        return cls(yaml.safe_load(Path(path).read_text()))

    # ---- load check ---------------------------------------------------------------------------------------------------------------------------------
    def all_phrases(self) -> list[str]:
        """Every phrase with its slots filled by neutral words (for the word checks)."""
        r, out = self.raw, []
        out += list((r.get("windows") or {}).values())
        for e in (r.get("exposures") or {}).values():
            out += [e.get("phrase", "").replace("{window}", "").strip(), e.get("pending", "")]
        for o in (r.get("outcomes") or {}).values():
            out += [o.get("phrase", "").replace("{kind}", "sample"), o.get("contrary", "").replace("{kind}", "sample")]
        for c in (r.get("event_checks") or {}).values():
            out += [c.get("phrase", ""), c.get("position_suffix", "").replace("{elapsed}", "hour or so").replace("{kind}", "sample"), c.get("pending", "")]
        out += [w["words"] for w in (r.get("elapsed_words") or []) + (r.get("meal_ago_words") or [])]
        for m in (r.get("measures") or {}).values():
            out += [m.get(d, "").replace("{strength}", "clearly") for d in ("above", "below")]
        out += list((r.get("strength_words") or {}).values())
        for band in (r.get("position_bands") or {}).values():
            out += [b[2] for b in band]
        out += [v.replace("{list}", "").replace("{List}", "") for v in (r.get("code_line") or {}).values()]
        return [t for t in out if t]

    def check(self, lib) -> None:
        """Every exposure, outcome, window tag and event-level candidate of the Evidence library has a phrase; every wording class a template; no phrase has a digit, an
        internal word or a counting word."""
        from v0_code.evidence_engine.library import KEY
        r, errors = self.raw, []
        for k in TOP_KEYS:
            if not r.get(k):
                errors.append(f"the phrase book has no {k!r}")
        for c in WORDING_CLASSES:
            if c not in (r.get("classes") or {}):
                errors.append(f"wording class {c!r} has no clause template")
        for side in ("low_side", "high_side"):
            if not (r.get("position_bands") or {}).get(side):
                errors.append(f"position_bands has no {side!r}")
        for p in lib.pairs:
            where = f"{p['rule']}#{p['rank']}"
            if p["status"] == "runnable":
                e, tag, o, _ = KEY.match(p["key"]).groups()
                if e not in (r.get("exposures") or {}):
                    errors.append(f"exposure {e!r} ({where}) has no phrase")
                if o not in (r.get("outcomes") or {}):
                    errors.append(f"outcome {o!r} ({where}) has no phrase")
                if tag not in (r.get("windows") or {}):
                    errors.append(f"window tag {tag!r} ({where}) has no phrase")
            elif p["status"] == "event_level" and p.get("event_check") not in (r.get("event_checks") or {}):
                errors.append(f"event-level candidate {p.get('event_check')!r} ({where}) has no phrase")
        for name, check in lib.event_checks.items():
            if name not in (r.get("event_checks") or {}):
                errors.append(f"event check {name!r} has no phrase")
            elif bool(r["event_checks"][name].get("static")) != (check["type"] == "presence_check"):
                errors.append(f"event check {name!r}: `static` must be set exactly for presence checks")
        for status in ("candidate", "supported", "weakened", "retracted"):
            t = (r.get("pi_text") or {}).get(status)
            if not t:
                errors.append(f"PI status {status!r} has no text template")
            elif re.search(r"\d", t):
                errors.append(f"PI text template for {status!r} contains a digit")
        for name, m in (r.get("measures") or {}).items():
            for d in ("above", "below"):
                if "{strength}" not in (m or {}).get(d, ""):
                    errors.append(f"measure {name!r} has no {d!r} phrase with a {{strength}} slot")
        banned = list(r.get("internal_words") or []) + list(r.get("counting_words") or [])
        for text in self.all_phrases():
            if re.search(r"\d", text):
                errors.append(f"phrase {text!r} contains a digit")
            for w in banned:
                if re.search(r"\b" + re.escape(w.lower()) + r"\b", text.lower()):
                    errors.append(f"phrase {text!r} contains the word {w!r}")
        if errors:
            raise PhrasebookError("The phrase book cannot be loaded:\n - " + "\n - ".join(errors))

    def _fallback(self, plural: bool = False) -> str:
        """The noun used for an event whose kind is unknown (config `kind_fallback`)."""
        word = self.raw["kind_fallback"]
        return globals()["plural"](word) if plural else word

    # ---- phrases ------------------------------------------------------------------------------------------------------------------------------------
    def exposure(self, exposure_id: str, tag: str) -> str:
        phrase = self.raw["exposures"][exposure_id]["phrase"]
        return re.sub(r"\s+", " ", phrase.replace("{window}", self.raw["windows"][tag])).strip()

    def is_plural(self, exposure_id: str) -> bool:
        return self.raw["exposures"][exposure_id].get("number") == "plural"

    def pending(self, exposure_id: str) -> str:
        return self.raw["exposures"][exposure_id]["pending"]

    def outcome(self, outcome_id: str, kind: str | None) -> str:
        return self.raw["outcomes"][outcome_id]["phrase"].replace("{kind}", kind or self._fallback(plural=True))

    def contrary(self, outcome_id: str, kind: str | None) -> str:
        return self.raw["outcomes"][outcome_id]["contrary"].replace("{kind}", kind or self._fallback(plural=True))

    def event_phrase(self, candidate: str) -> str:
        return self.raw["event_checks"][candidate]["phrase"]

    def event_pending(self, candidate: str) -> str:
        return self.raw["event_checks"][candidate].get("pending", self.raw["event_checks"][candidate]["phrase"])

    def claim_sentence(self, cls: str, exposure_id: str, tag: str, outcome_id: str, kind: str | None) -> str:
        phrase = self.exposure(exposure_id, tag)
        same = "" if "same day" in phrase else ", on the same day"
        return self.raw["classes"][cls].format(Exposure=cap(phrase), has="have" if self.is_plural(exposure_id) else "has", outcome=self.outcome(outcome_id, kind), same_day=same)

    def contrary_sentence(self, exposure_id: str, tag: str, outcome_id: str, kind: str | None) -> str:
        return self.raw["classes"]["contrary_note"].format(exposure=self.exposure(exposure_id, tag), contrary=self.contrary(outcome_id, kind))

    def is_static(self, candidate: str) -> bool:
        """A presence check: a standing fact about her, not something that happened around this event."""
        return bool(self.raw["event_checks"].get(candidate, {}).get("static"))

    def event_sentence(self, candidate: str, position: str) -> str:
        return self.raw["classes"]["event_unusual"].format(Event=cap(self.event_phrase(candidate)), position=position)

    # ---- words from numbers (never a digit in text) -----------------------------------------------------------------------------------------------------
    def position(self, percentile: float, side: str) -> str | None:
        bands = self.raw["position_bands"]["low_side" if side == "low" else "high_side"]
        for lo, hi, words in bands:
            if lo <= percentile < hi or (hi == 100 and percentile == 100):
                return words
        return None

    def _band(self, table: list[dict], minutes: float) -> str:
        return next(b["words"] for b in table if minutes <= b["up_to"])

    def elapsed(self, minutes: float) -> str:
        return self._band(self.raw["elapsed_words"], minutes)

    def meal_ago(self, minutes: float) -> str:
        return self._band(self.raw["meal_ago_words"], minutes)

    @staticmethod
    def meal_label(label: str) -> str:
        words = " ".join(t for t in label.split("_") if t and not t.isdigit())
        return ("an " if words[:1] in "aeiou" else "a ") + words

    def position_suffix(self, candidate: str, bucket_minutes: float, kind: str | None) -> str:
        s = self.raw["event_checks"][candidate].get("position_suffix", "")
        return s.replace("{elapsed}", self.elapsed(bucket_minutes)).replace("{kind}s", plural(kind or self._fallback())).replace("{kind}", kind or self._fallback())

    def measure_clause(self, measure: str, direction: str, strength: str) -> str:
        """'<measure> was clearly above her usual' / 'clearly fewer <things> were taken than usual': the phrase of the measure and direction with the strength word filled in."""
        m = self.raw["measures"].get(measure)
        if m is None or direction not in m:
            raise PhrasebookError(f"the measure {measure!r} has no {direction!r} phrase in the phrase book")
        return m[direction].replace("{strength}", self.raw["strength_words"][strength])

    def measures_sentence(self, measures: list[dict]) -> str:
        """One sentence per measure, in order: '<Measure> was clearly above her usual. <Measure> was far below her usual.'"""
        return " ".join(cap(self.measure_clause(m["measure"], m["direction"], m["strength"])) + "." for m in measures)
