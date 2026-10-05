"""PI's code text (pi_spec.md 8.5, amendment 39): built from the shared phrase book and the status. No model, no numbers."""

from v0_code.findings_engine.factors import parse_key
from v0_code.intel_common.phrasebook import Phrasebook, cap


def same_day_only(lib, key: str) -> bool:
    """True if the relationship's pair is marked `same_day_unverified` in the Evidence library (read only)."""
    _, _, _, kind = parse_key(key)
    generic = key.rsplit(":", 1)[0] + ":{meal_kind}" if kind else key
    pair = next((p for p in lib.pairs if p.get("key") == generic), None)
    return bool(pair) and pair.get("ordering") == "same_day_unverified"


def code_text(key: str, status: str, same_day: bool, pb: Phrasebook) -> dict:
    exposure, tag, outcome, kind = parse_key(key)
    phrase = pb.exposure(exposure, tag)
    sentence = pb.raw["pi_text"][status].format(Exposure=cap(phrase), has="have" if pb.is_plural(exposure) else "has", outcome=pb.outcome(outcome, kind),
                                                same_day=", on the same day" if same_day and "same day" not in phrase else "")
    return {"sentences": [sentence], "source": "code_text"}
