"""Direction tags with size labels, and co-movement (spec sections 4.1 and 4.3). Pure code; the LLM never computes any of this.

A tag: {measure, label, unit, direction: up|down|flat|not_enough_data, size: none|small|moderate|large, delta, ratio}
 - flat when |delta| < the stream's flat band (0.5 x SD of her earlier daily values)
 - size is the delta in multiples of the band: 1x to <small_below = small, to <moderate_below = moderate, above that = large
 - no band yet (too little history) or no previous value -> not_enough_data (the delta is still kept when it can be computed)
"""

from v0_code.baseline_v2.config import Config, StreamCfg


def direction_word(direction: str, count_like: bool) -> str:
    """The word a person reads: up / down, except for a count of periods, which is always "more" / "fewer" (never "mood up/down")."""
    if count_like and direction in ("up", "down"):
        return "more" if direction == "up" else "fewer"
    return direction


def make_tag(sc: StreamCfg, value: float | None, prev: float | None, profile: dict, cfg: Config) -> dict:
    t = _make_tag(sc, value, prev, profile, cfg)
    t["direction_word"] = direction_word(t["direction"], sc.count_like)
    return t


def _make_tag(sc: StreamCfg, value: float | None, prev: float | None, profile: dict, cfg: Config) -> dict:
    delta = round(value - prev, 4) if value is not None and prev is not None else None
    base = {"measure": sc.name, "label": sc.display, "unit": sc.unit, "domain": sc.domain, "count_like": sc.count_like, "delta": delta}
    band = profile.get("flat_band")
    if delta is None or band is None:
        return {**base, "direction": "not_enough_data", "size": "none", "ratio": None}
    if delta == 0 or abs(delta) < band:
        return {**base, "direction": "flat", "size": "none", "ratio": round(abs(delta) / band, 3) if band else 0.0}
    ratio = float("inf") if band == 0 else abs(delta) / band          # a zero-spread stream: any change at all is large
    size = "small" if ratio < cfg.small_below else ("moderate" if ratio < cfg.moderate_below else "large")
    return {**base, "direction": "up" if delta > 0 else "down", "size": size, "ratio": round(ratio, 3) if ratio != float("inf") else 999.0}


def co_movement(tags: list[dict], glucose_measure: str) -> dict:
    """Which measures moved the same way as / the opposite way to glucose. Reported only if glucose itself moved beyond its flat band.
    One entry per domain (the strongest move in the domain, so heart-rate variants collapse to one); the glucose domain is the reference.
    Never reports flat/flat."""
    by_name = {t["measure"]: t for t in tags}
    g = by_name.get(glucose_measure)
    out = {"glucose_direction": g["direction"] if g else "not_enough_data", "same_direction": [], "opposite_direction": [], "flat": [], "not_enough_data": []}
    if not g:
        return out
    best: dict[str, dict] = {}
    for t in tags:
        if t["domain"] == g["domain"]:
            continue
        if t["direction"] == "flat":
            out["flat"].append(t["label"])
        elif t["direction"] == "not_enough_data":
            out["not_enough_data"].append(t["label"])
        elif t["direction"] in ("up", "down") and (t["domain"] not in best or (t["ratio"] or 0) > (best[t["domain"]]["ratio"] or 0)):
            best[t["domain"]] = t
    if g["direction"] in ("up", "down"):
        for t in best.values():
            entry = {"measure": t["label"], "direction": t["direction"], "direction_word": t["direction_word"], "size": t["size"], "domain": t["domain"]}
            out["same_direction" if t["direction"] == g["direction"] else "opposite_direction"].append(entry)
        out["same_direction"].sort(key=lambda e: e["measure"])
        out["opposite_direction"].sort(key=lambda e: e["measure"])
    return out
