"""Load the rulebook files and validate them (spec 10.14 with the Amendments). The rulebook is data: nothing about its content is known here."""

import csv
import re
from dataclasses import dataclass
from pathlib import Path

from v0_code.rulebook_lookup.config import RulebookConfig
from v0_code.rulebook_lookup.grammar import GrammarError, ContextMatch, parse_applies, parse_context_match, parse_lookback, parse_requires

TIERS = ("primary", "secondary", "tertiary")
CHECK_TYPES = ("group_comparison", "percentile_vs_history", "shape_check", "presence_check", "pattern_repeat")
STATUS_CODES = ("available", "partial", "none", "skipped_by_rule", "unverified")
EVIDENCE = ("A", "B", "C", "D")
RULE_STATUSES = ("active", "deferred")
_SOURCE_ROW = re.compile(r"^\|\s*(S\d+)\s*\|")


class RulebookError(ValueError):
    """Loading failed; the message lists every problem found, in plain words."""


@dataclass(frozen=True)
class Rule:
    rule_id: str
    measure: str
    direction: str
    context_match: str
    ctx: ContextMatch
    status: str
    primary_count: int
    secondary_max: int
    tertiary_max: int
    max_total: int
    review_status: str
    version: str

    def cap(self, tier: str) -> int:
        return {"secondary": self.secondary_max, "tertiary": self.tertiary_max}[tier]


@dataclass(frozen=True)
class Candidate:
    rule_id: str
    rank: int
    tier: str
    candidate: str
    requires: tuple
    lookback_kind: str
    lookback_value: int | None
    lookback_text: str
    applies: tuple
    check_type: str
    check_text: str
    outcome_compared_text: str
    data_status_code: str
    evidence_level: str
    sources: tuple
    review_status: str
    note: str | None


@dataclass(frozen=True)
class Rulebook:
    version: str
    review_status: str
    rules: tuple
    candidates: dict                  # rule_id -> tuple of Candidate in rank order
    sources: frozenset


def _int(text, what, errors, where):
    try:
        return int(str(text).strip())
    except ValueError:
        errors.append(f"{where}: {what} must be a whole number, got {text!r}")
        return 0


def load_rulebook(directory: str | Path, cfg: RulebookConfig, validate: bool = True) -> Rulebook:
    d = Path(directory)
    errors: list[str] = []
    for f in (cfg.rules_file, cfg.candidates_file, cfg.sources_file):
        if not (d / f).exists():
            raise RulebookError(f"rulebook file not found: {d / f}")
    sources = frozenset(m.group(1) for line in (d / cfg.sources_file).read_text().splitlines() if (m := _SOURCE_ROW.match(line)))
    if not sources:
        errors.append(f"no source list (rows like '| S1 | ...') found in {cfg.sources_file}")
    with open(d / cfg.rules_file, newline="") as f:
        rule_rows = list(csv.DictReader(f))
    with open(d / cfg.candidates_file, newline="") as f:
        cand_rows = list(csv.DictReader(f))

    rules = []
    for r in rule_rows:
        w = f"rule {r['rule_id']}"
        try:
            ctx = parse_context_match(r["context_match"])
        except GrammarError as e:
            errors.append(f"{w}: context_match: {e}")
            ctx = parse_context_match("")
        if r["status"] not in RULE_STATUSES:
            errors.append(f"{w}: status must be one of {RULE_STATUSES}, got {r['status']!r}")
        if r["direction"] not in ("above", "below"):
            errors.append(f"{w}: direction must be above or below, got {r['direction']!r}")
        rules.append(Rule(r["rule_id"], r["measure"], r["direction"], r["context_match"].strip(), ctx, r["status"], _int(r["primary_count"], "primary_count", errors, w),
                          _int(r["secondary_max"], "secondary_max", errors, w), _int(r["tertiary_max"], "tertiary_max", errors, w), _int(r["max_total"], "max_total", errors, w),
                          r["review_status"], r["rulebook_version"]))

    by_rule: dict[str, list[Candidate]] = {}
    for c in cand_rows:
        w = f"candidate {c['rule_id']}#{c['rank']} ({c['candidate']})"
        try:
            requires = parse_requires(c["requires_streams"])
        except GrammarError as e:
            errors.append(f"{w}: requires_streams: {e}")
            requires = ()
        try:
            applies = parse_applies(c["applies_if_rule"])
        except GrammarError as e:
            errors.append(f"{w}: applies_if_rule: {e}")
            applies = ()
        try:
            lb_value = parse_lookback(c["lookback_kind"], c["lookback_value"])
        except GrammarError as e:
            errors.append(f"{w}: {e}")
            lb_value = None
        for col, allowed in (("weight_tier", TIERS), ("check_type", CHECK_TYPES), ("data_status_meera_code", STATUS_CODES), ("evidence_level", EVIDENCE)):
            if c[col] not in allowed:
                errors.append(f"{w}: {col} must be one of {allowed}, got {c[col]!r}")
        srcs = tuple(s for s in c["sources"].split(";") if s)
        for s in srcs:
            if s not in sources:
                errors.append(f"{w}: unknown source {s!r} (the source list has {', '.join(sorted(sources, key=lambda x: int(x[1:])))})")
        by_rule.setdefault(c["rule_id"], []).append(Candidate(
            c["rule_id"], _int(c["rank"], "rank", errors, w), c["weight_tier"], c["candidate"], requires, c["lookback_kind"], lb_value, c["lookback_text"], applies,
            c["check_type"], c["check_text"], c["outcome_compared_text"], c["data_status_meera_code"], c["evidence_level"], srcs, c["review_status"], c["note"].strip() or None))

    versions = {r.version for r in rules}
    book = Rulebook(next(iter(versions)) if len(versions) == 1 else "", "reviewed" if all(x.review_status == "reviewed" for x in rules) and
                    all(c.review_status == "reviewed" for cs in by_rule.values() for c in cs) else "unreviewed", tuple(rules),
                    {rid: tuple(sorted(cs, key=lambda c: c.rank)) if validate else tuple(cs) for rid, cs in by_rule.items()}, sources)
    if validate:
        errors.extend(_validate(book, rule_rows, by_rule, versions))
    if errors:                                                        # every problem found is reported together
        raise RulebookError("The rulebook cannot be loaded:\n - " + "\n - ".join(errors))
    return book


def _validate(book: Rulebook, rule_rows: list, by_rule: dict, versions: set) -> list[str]:
    p: list[str] = []
    ids = [r.rule_id for r in book.rules]
    for rid in sorted({i for i in ids if ids.count(i) > 1}):
        p.append(f"rule_id {rid!r} is repeated")
    if len(versions) != 1:
        p.append(f"the rules file carries different rulebook_version values: {sorted(versions)}")
    for rid in by_rule:
        if rid not in ids:
            p.append(f"candidates name rule {rid!r}, which is not in the rules file")
    for r in book.rules:
        cs = by_rule.get(r.rule_id, [])
        if not cs and r.status != "deferred":
            p.append(f"rule {r.rule_id} has no candidates (only a deferred rule may have none)")
            continue
        ranks = [c.rank for c in cs]
        if ranks != list(range(1, len(cs) + 1)):
            p.append(f"rule {r.rule_id}: ranks are not contiguous from 1 (got {ranks})")
        tiers = [TIERS.index(c.tier) for c in cs]
        if tiers != sorted(tiers):
            p.append(f"rule {r.rule_id}: tiers are not in the order primary, secondary, tertiary (got {[c.tier for c in cs]})")
        for tier in ("secondary", "tertiary"):
            ev = [c.evidence_level for c in cs if c.tier == tier]
            if ev != sorted(ev):
                p.append(f"rule {r.rule_id}: {tier} candidates are not ordered by evidence level A to D (got {ev})")
        n_primary = sum(c.tier == "primary" for c in cs)
        if n_primary != r.primary_count:
            p.append(f"rule {r.rule_id}: primary_count is {r.primary_count} but the rule has {n_primary} primary candidates")
        if r.max_total < r.primary_count:
            p.append(f"rule {r.rule_id}: max_total ({r.max_total}) is below primary_count ({r.primary_count}); every primary candidate is always tested")
    groups: dict = {}
    for r in book.rules:
        groups.setdefault((r.measure, r.direction), []).append(r)
    for (measure, direction), rs in groups.items():
        if len(rs) < 2:
            continue
        probes = {None, 0, 10 ** 6}
        for r in rs:
            for n in r.ctx.numbers:
                probes.update((n - 1, n, n + 1))
        for probe in sorted(probes, key=lambda x: (x is not None, x or 0)):
            hit = [r.rule_id for r in rs if r.ctx.matches(probe)]
            if len(hit) > 1:
                p.append(f"two rules could match the same hand-off ({measure}, {direction}): {hit} both match when the last meal is {'absent' if probe is None else f'{probe} minutes ago'}")
                break
    return p
