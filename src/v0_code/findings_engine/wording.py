"""Wording classes (findings_engine_spec.md 7.3 as amended). The class decides what a sentence may say about a factor. Weight tiers, ranks and PI statuses never enter."""

from v0_code.intel_common.phrasebook import WORDING_CLASSES

CLASSES = WORDING_CLASSES
CLAIM = ("asserted", "asserted_same_day", "hedged", "hedged_same_day")          # classes that carry a link
HISTORY_REASONS = ("history", "small_group")


def classify_relationship(label: str, flags: list[str], exposure: str | None, reason: str | None) -> str:
    """Precedence: not yet available, then not exposed or no data, then the label."""
    if exposure == "not_yet_available":
        return "not_known_yet"
    if exposure != "exposed":
        return "not_mentioned"
    placebo, same_day = "placebo_fired" in flags, "same_day_unverified" in flags
    if label in ("supported", "suggestive"):
        if placebo:
            return "exposure_only"
        return ("asserted_same_day" if same_day else "asserted") if label == "supported" else ("hedged_same_day" if same_day else "hedged")
    if label == "not_supported":
        return "contrary_note" if "contrary" in flags and not placebo else "exposure_only"
    if label == "insufficient":
        return "exposure_only_history" if reason in HISTORY_REASONS else "not_mentioned"
    return "not_mentioned"


def classify_event(check_type: str, label: str, exposure: str | None, present: bool | None) -> str:
    if check_type == "percentile_vs_history":
        return "event_unusual" if label == "supported" and exposure == "exposed" else "not_mentioned"
    if check_type == "shape_check":
        return {"supported": "artifact_note", "not_yet_available": "not_known_yet"}.get(label, "not_mentioned")
    if check_type == "presence_check":
        return "exposure_only" if present else "not_mentioned"
    if check_type == "pattern_repeat":
        return "exposure_only" if label == "supported" else "not_mentioned"
    return "not_mentioned"
