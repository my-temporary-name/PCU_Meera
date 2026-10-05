"""One packet per hand-off (spec 6 and 7.1, Amendments). Pure function of (hand-off, rulebook, config): same inputs, same packet. Reads no data, writes nothing."""

import copy

from v0_code.rulebook_lookup.config import RulebookConfig
from v0_code.rulebook_lookup.rulebook import Candidate, Rule, Rulebook
from v0_code.rulebook_lookup.windows import resolve_lookback

SUMMARY_KEYS = ("measure", "direction", "size", "trigger", "position_z", "usual_basis", "value", "clinical_status", "opened_at")


def last_meal_minutes(handoff: dict) -> int | None:
    lm = (handoff.get("context") or {}).get("last_meal")
    return None if not lm else lm.get("minutes_ago")


def match_rules(handoff: dict, book: Rulebook) -> list[Rule]:
    """R1: rules with the hand-off's measure and direction whose context_match is true, in file order."""
    minutes = last_meal_minutes(handoff)
    return [r for r in book.rules if r.measure == handoff["measure"] and r.direction == handoff["direction"] and r.ctx.matches(minutes)]


def _streams(c: Candidate, cfg: RulebookConfig) -> tuple[list[dict], list[str]]:
    """One object per alternative, in order. Only the first available alternative is used; later alternatives name the first as `fallback_for`."""
    out, unavailable = [], []
    for group in c.requires:
        first_available = next((i for i, t in enumerate(group) if cfg.stream_available(t.name)), None)
        for i, t in enumerate(group):
            avail = cfg.stream_available(t.name)
            o = {"generic": t.generic, "patient_stream": cfg.patient_stream(t.name), "category": t.category, "available": avail, "used": i == first_available}
            if i > 0:
                o["fallback_for"] = group[0].generic
            out.append(o)
            if not avail:
                unavailable.append(t.generic)
    return out, unavailable


def _candidate_object(c: Candidate, cfg: RulebookConfig, streams: list[dict], opened_at: str) -> dict:
    return {
        "rank": c.rank, "weight_tier": c.tier, "candidate": c.candidate, "check_type": c.check_type, "check_text": c.check_text, "outcome_compared_text": c.outcome_compared_text,
        "streams": streams, "lookback": {"kind": c.lookback_kind, "value": c.lookback_value, "text": c.lookback_text},
        "resolved_window": resolve_lookback(c.lookback_kind, c.lookback_value, opened_at, cfg.timezone),
        "evidence_level": c.evidence_level, "sources": list(c.sources), "data_status_code": c.data_status_code, "review_status": c.review_status, "note": c.note}


def build_packet(handoff: dict, book: Rulebook, cfg: RulebookConfig) -> dict:
    hid = handoff["handoff_id"]
    summary = {k: copy.deepcopy(handoff.get(k)) for k in SUMMARY_KEYS}
    summary["last_meal_minutes_ago"] = last_meal_minutes(handoff)
    head = {"packet_id": f"packet_{hid}", "handoff_id": hid}
    tail = {"rulebook_version": book.version, "rulebook_review_status": book.review_status}

    matched = match_rules(handoff, book)
    if not matched:                                                  # R1: none -> unmatched, counted and logged, not an error
        return {**head, "status": "unmatched", **tail, "matched_rule": None, "handoff_summary": summary, "selected": [], "skipped": [], "not_selected": [],
                "counts": {"candidates_in_rule": 0, "selected": 0, "skipped": 0, "not_selected": 0}, "evidence_bar_hint": "standard"}
    rule = matched[0]
    status = "ambiguous" if len(matched) > 1 else ("deferred" if rule.status == "deferred" else None)
    matched_rule = {"rule_id": rule.rule_id, "status": rule.status, "context_match": rule.context_match,
                    "budget": {"primary": "all", "primary_count": rule.primary_count, "secondary_max": rule.secondary_max, "tertiary_max": rule.tertiary_max, "max_total": rule.max_total},
                    "review_status": rule.review_status}
    cands = book.candidates.get(rule.rule_id, ())
    selected, skipped, not_selected = [], [], []

    if rule.status == "deferred":                                    # R2 (amended): everything is listed as not selected, so completeness holds
        not_selected = [{"candidate": c.candidate, "weight_tier": c.tier, "reason": "rule_deferred"} for c in cands]
        hint = "standard"
    else:
        runnable = []
        for c in cands:                                              # R3 applicability, R4 availability
            ok, failing = cfg.evaluate_applies(c.applies, handoff["opened_at"])
            if not ok:
                skipped.append({"candidate": c.candidate, "reason": "applies_if_not_met", "detail": failing})
                continue
            streams, unavailable = _streams(c, cfg)
            if all(not s["available"] for s in streams):
                skipped.append({"candidate": c.candidate, "reason": "no_stream", "detail": "; ".join(unavailable)})
                continue
            runnable.append((c, streams))
        per_tier: dict = {}
        for c, streams in runnable:                                  # R5 budget: skipped candidates used none
            take = c.tier == "primary" or (len(selected) < rule.max_total and per_tier.get(c.tier, 0) < rule.cap(c.tier))
            if take:
                per_tier[c.tier] = per_tier.get(c.tier, 0) + 1
                selected.append(_candidate_object(c, cfg, streams, handoff["opened_at"]))      # R6 lookbacks, R7 provenance
            else:
                not_selected.append({"candidate": c.candidate, "weight_tier": c.tier, "reason": "budget"})
        hint = "raised" if len(selected) > cfg.raised_bar_above else "standard"          # R8

    return {**head, **({"status": status} if status else {}), **tail, "matched_rule": matched_rule, "handoff_summary": summary, "selected": selected, "skipped": skipped,
            "not_selected": not_selected,
            "counts": {"candidates_in_rule": len(cands), "selected": len(selected), "skipped": len(skipped), "not_selected": len(not_selected)}, "evidence_bar_hint": hint}
