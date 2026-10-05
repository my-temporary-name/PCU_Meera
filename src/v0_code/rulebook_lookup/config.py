"""The `rulebook:` config block (spec 4.3, Amendments). Everything patient-specific lives here: no stream, medicine, flag or time zone appears in the engine.
Time zone and the medicine-id pattern are read from the Baseline Engine config (the same setting the State Engine uses)."""

import re
from dataclasses import dataclass, field
from pathlib import Path

import yaml

from v0_code.rulebook_lookup.windows import local_time

DERIVED = "derived"                                   # stream_map value: always available (comes from timestamps)
DERIVED_FROM_CLASSES = "derived:medication_classes"   # stream_map value: available if medication_classes is non-empty


@dataclass(frozen=True)
class RulebookConfig:
    rulebook_dir: str
    rules_file: str
    candidates_file: str
    sources_file: str
    raised_bar_above: int
    stream_map: dict
    medication_classes: dict                          # normalised medicine name -> tuple of classes
    patient_flags: dict
    derived_flags: dict                               # flag -> medication class that makes it true
    timezone: str | None
    medication_id_regex: str = ""
    state_db: str = "output/state_engine.db"
    db_path: str = "output/rulebook_lookup.db"
    report_path: str = "output/rulebook_lookup_report.md"

    # ---- construction -----------------------------------------------------------------------------------------------------------------------------
    @classmethod
    def from_dict(cls, raw: dict, timezone: str | None = None, medication_id_regex: str = "") -> "RulebookConfig":
        norm = lambda n: _normalise(n, medication_id_regex)
        classes = {norm(k): tuple(v or ()) for k, v in (raw.get("medication_classes") or {}).items()}
        return cls(
            rulebook_dir=raw["rulebook_dir"], rules_file=raw.get("rules_file", "rulebook_v0_rules.csv"), candidates_file=raw.get("candidates_file", "rulebook_v0_candidates.csv"),
            sources_file=raw.get("sources_file", "rulebook_v0.md"), raised_bar_above=int(raw["raised_bar_above"]), stream_map=dict(raw.get("stream_map") or {}),
            medication_classes=classes, patient_flags=dict(raw.get("patient_flags") or {}), derived_flags=dict(raw.get("derived_flags") or {}),
            timezone=timezone, medication_id_regex=medication_id_regex, state_db=raw.get("state_db", "output/state_engine.db"),
            db_path=raw.get("db_path", "output/rulebook_lookup.db"), report_path=raw.get("report_path", "output/rulebook_lookup_report.md"))

    @classmethod
    def from_yaml(cls, path: str | Path, root: str | Path | None = None) -> "RulebookConfig":
        raw = yaml.safe_load(Path(path).read_text())["rulebook"]
        tz, regex = None, ""
        if raw.get("baseline_config"):
            base = Path(raw["baseline_config"])
            if not base.is_absolute() and root is not None:
                base = Path(root) / base
            patient = yaml.safe_load(base.read_text()).get("patient", {})
            tz, regex = patient.get("timezone"), patient.get("medication_id_regex", "")
        return cls.from_dict(raw, timezone=tz, medication_id_regex=regex)

    def rulebook_path(self, root: str | Path | None = None) -> Path:
        p = Path(self.rulebook_dir)
        return p if p.is_absolute() or root is None else Path(root) / p

    # ---- medicines, flags, streams ------------------------------------------------------------------------------------------------------------------
    @property
    def medicines(self) -> tuple:
        return tuple(self.medication_classes)

    def classes_of(self, medicine: str) -> tuple:
        return self.medication_classes.get(_normalise(medicine, self.medication_id_regex), ())

    def class_present(self, cls_name: str) -> bool:
        return any(cls_name in c for c in self.medication_classes.values())

    def flag(self, name: str) -> bool:
        """An explicit patient flag wins over a flag derived from medication classes. Unknown = false, never an error."""
        if name in self.patient_flags:
            return bool(self.patient_flags[name])
        if name in self.derived_flags:
            return self.class_present(self.derived_flags[name])
        return False

    def stream_available(self, token: str) -> bool:
        v = self.stream_map.get(token)
        if v is None:
            return False
        if v == DERIVED_FROM_CLASSES:
            return bool(self.medication_classes)
        return True

    def patient_stream(self, token: str) -> str | None:
        return self.stream_map.get(token) if self.stream_available(token) else None

    # ---- applicability (5.3) ----------------------------------------------------------------------------------------------------------------------
    def evaluate_applies(self, terms, opened_at: str) -> tuple[bool, str | None]:
        """All terms must hold (AND); a term holds if any of its atoms does (OR). Returns (ok, the first failing term as written)."""
        local = None
        for term in terms:
            ok = False
            for a in term.atoms:
                if a.kind == "patient_flag":
                    ok = self.flag(a.arg)
                elif a.kind == "medication_class_present":
                    ok = self.class_present(a.arg)
                elif a.kind == "stream_present":
                    ok = self.stream_available(a.arg)
                else:
                    local = local or local_time(opened_at, self.timezone)
                    t, (start, end) = local.hour * 60 + local.minute, a.window
                    ok = True if start == end else (start <= t < end if start < end else (t >= start or t < end))
                if ok:
                    break
            if not ok:
                return False, term.text
        return True, None


def _normalise(name: str, regex: str) -> str:
    return re.sub(regex, "", name) if regex else name
