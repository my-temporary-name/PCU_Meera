"""Normal profile (spec section 3): what is normal for her, learned only from history STRICTLY BEFORE the window.

Per stream: typical level (median), spread (SD), flat band (sd_multiplier x SD), usual status (most common day-level threshold status) and
how often she is non-normal. Before `min_days_for_compare` days of history there is no flat band and no usual status — nothing to compare
against — so no direction tag can be made. Everything is therefore as-of the window's date by construction.
"""

import statistics
from collections import Counter

from v0_code.baseline_v2.config import Config

# Severity of a threshold status; "worse than usual" means a higher rank than the stream's usual status.
STATUS_RANK = {"normal": 0, "borderline_low": 1, "borderline_high": 1, "low": 2, "high": 2}


def day_status(statuses: list[str | None]) -> str | None:
    """A day's status for one stream: its most common reading status (ties broken by name, so it is deterministic)."""
    c = Counter(s for s in statuses if s)
    return max(c, key=lambda k: (c[k], k)) if c else None


def build_profile(values: list[float], statuses: list[str], cfg: Config) -> dict:
    """values / statuses: one entry per EARLIER day that has data (strictly before the window)."""
    n, n_status = len(values), len(statuses)
    enough = n >= cfg.min_days_for_compare
    sd = statistics.pstdev(values) if n >= 2 else None
    usual = None
    if n_status >= cfg.min_days_for_compare:
        c = Counter(statuses)
        usual = max(c, key=lambda k: (c[k], k))
    return {
        "n_days": n,
        "median": round(statistics.median(values), 3) if values else None,
        "sd": round(sd, 4) if sd is not None else None,
        "flat_band": round(cfg.sd_multiplier * sd, 4) if enough and sd is not None else None,
        "usual_status": usual,
        "status_days": n_status,
        "share_non_normal": round(sum(1 for s in statuses if s != "normal") / n_status, 3) if n_status else None,
    }
