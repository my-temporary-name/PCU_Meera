"""The code line (findings_engine_spec.md 7.8 and Appendix C): the finding's text built from the structured layer with the phrase book, no model and no numbers. It is the
text of a version when the text layer is off, fails its checks twice, or has no model."""

from v0_code.findings_engine.factors import parse_key
from v0_code.findings_engine.wording import CLAIM
from v0_code.intel_common.phrasebook import Phrasebook, cap, join_list


def _base(f: dict, pb: Phrasebook) -> str:
    if f["kind"] == "relationship":
        exposure, tag, _, _ = parse_key(f["relationship_key"])
        return pb.exposure(exposure, tag)
    return pb.event_phrase(f["candidate"])


def _phrases(factors: list[dict], pb: Phrasebook, skip: frozenset = frozenset()) -> list[str]:
    """The factors in plain words, each phrase once (the same exposure tested against several outcomes is one thing present), with position words in brackets when it has them."""
    out: dict = {}
    for f in factors:
        text = _base(f, pb)
        if text in skip:
            continue
        pos = f.get("position") if f["kind"] == "relationship" else None
        if text not in out or (pos and not out[text][1]):
            out[text] = (text, pos)
    return [f"{t} ({p})" if p else t for t, p in out.values()]


def _claim_sentence(f: dict, pb: Phrasebook) -> str:
    exposure, tag, outcome, kind = parse_key(f["relationship_key"])
    return pb.claim_sentence(f["wording_class"], exposure, tag, outcome, kind)


def code_sentences(content: dict, pb: Phrasebook) -> list[str]:
    factors = content["factors"]
    cls = lambda *names: [f for f in factors if f["wording_class"] in names]
    cl = pb.raw["code_line"]
    out = [pb.measures_sentence(content["measures"])]
    claims = [f for f in cls(*CLAIM) if f["kind"] == "relationship"]
    contrary = cls("contrary_note")
    others = [f for f in cls("exposure_only", "exposure_only_history") if not (f["kind"] == "event" and pb.is_static(f["candidate"]))]
    relationship = content["mode"] == "relationship"
    # what is present: the claim-class factors (relationship mode), or every exposed factor (descriptive mode); a contrary factor's exposure is always named, because the sentence
    # "On days like this, ..." needs a "this"
    listed = [f for f in factors if f in contrary or (f in claims if relationship else f in others)]
    if listed:
        out.append(cl["present"].format(list=", ".join(_phrases(listed, pb))))
    shown = frozenset(_base(f, pb) for f in listed)
    for f in cls("event_unusual"):
        out.append(pb.event_sentence(f["candidate"], f["position"]))
    if relationship:
        out += _group_sentences(content, claims, pb)
        out += [_claim_sentence(f, pb) for f in claims]
    for f in cls("contrary_note"):
        e, tag, o, kind = parse_key(f["relationship_key"])
        out.append(pb.contrary_sentence(e, tag, o, kind))
    rest = _phrases(others, pb, shown)
    if rest:
        out.append(cl["also_present"].format(list=join_list(rest)))
    if cls("artifact_note"):
        out.append(pb.raw["classes"]["artifact_note"])
    if content["not_known_yet"]:
        out.append(cl["not_known_yet"].format(list=join_list(content["not_known_yet"])))
    if content["mode"] == "descriptive" and content["history_note"] != "enough":
        out.append(cl["history_short"])
    return [s for s in out if s]


def build_code_line(content: dict, pb: Phrasebook) -> str:
    return " ".join(code_sentences(content, pb))


def _group_sentences(content: dict, claims: list[dict], pb: Phrasebook) -> list[str]:
    """One sentence per group so its members are described together: entangled groups say they often occur together, the co-exposed group that none stands alone."""
    by_id = {f["factor_id"]: f for f in claims}
    out = []
    for g in content["groups"]:
        names = list(dict.fromkeys(_base(by_id[m], pb) for m in g["members"]))
        if len(names) > 1:
            template = pb.raw["code_line"]["co_exposed_many" if g["reason"] == "co_exposed" and len(names) > 2 else g["reason"]]
            out.append(template.format(List=join_list([cap(names[0])] + names[1:])))
    return out
