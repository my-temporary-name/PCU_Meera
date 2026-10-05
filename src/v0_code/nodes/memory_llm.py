"""Baseline Engine memory LLM step: curated interpretation on top of the code-computed record.

record_json holds the complete detail; memory_json (this module's output) is selective — it
never restates fields one by one. Everything numeric, every direction and every co-movement
pairing is decided by code and handed to the model; the model only describes it.

Three things keep the model honest without fighting it:
1. PLAIN COPY (logic/record_view.py). The prompt gets the record under plain-English keys with
   units, so an echoed key reads like English instead of tripping the voice check. evidence_refs
   written against that copy are mapped back to internal paths here.
2. SANITIZER. Internal key names that still leak, and short dates like "12-24", are rewritten in
   code before validation and every substitution is logged. Approximations, causal language and
   ungrounded numbers are NOT sanitized — those still fail and go to the retry.
3. VALIDATION. Schema + per-window caps, numeric grounding with tolerance (V0 decision: rounding
   is fine, see _grounded), forbidden/voice language, refs resolution, exact quotes, co-movement
   vs the code candidates, direction agreement, notability.

A window failing twice is stored with its numeric record intact and llm_status='rejected';
nothing here can lose or block the code-computed record.
"""

import asyncio
import json
import os
import re
from typing import Any

from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from loguru import logger
from pydantic import BaseModel, Field, ValidationError

from v0_code.logic.anchors import ANCHORS
from v0_code.logic.record_view import VALUE_LABELS, annotate, plain_value, to_plain

load_dotenv()

MODEL = "openai/gpt-5-mini"
BATCH_SIZE = {"day": 4, "week": 2, "month": 1}  # week records ~1.8k tokens (+ prior): 2 per call keeps a call near 8k input tokens
MAX_CONCURRENT_BATCH_CALLS = 6
CAPS = {"trajectory": 5, "changes_vs_prior": 5, "co_movement": 4, "recurring_patterns": 3, "key_observations": 5}
# A window is quiet only when NOTHING deviated: record["quiet"] is true exactly when material_changes (built in
# code from anchors, missed doses, non-normal statuses, diary events and data gaps) is empty. A quiet day/week gets
# headline + 2 observations, no trajectory padding, and at most 2 co-moving measures. A checkpoint (month) is a
# long-run summary and is never quiet.
QUIET_CAPS = {"trajectory": 0, "changes_vs_prior": 0, "co_movement": 2, "recurring_patterns": 0, "key_observations": 2}


def caps_for(record: dict) -> dict[str, int]:
    return QUIET_CAPS if record.get("quiet") else CAPS


SYSTEM_PROMPT = """You write memory entries for a personal health record system. The patient has diabetes. Write about HER — what her day, week or month looked like — not about the software or the data.

You receive WINDOWS keyed by window_id. Each has:
1. RECORD: a record for one time window (a day, a rolling week, or a monthly checkpoint). Every number in it was computed by code. Its keys are plain English and carry their units.
2. PRIOR: the record for the previous comparable window (may be null).
3. entry_limits: the maximum number of items allowed in each list for that window.
You also receive ANCHORS (reference thresholds).

Your job is to turn RECORD into a curated memory entry that a later reasoning step will retrieve to answer: what is normal for this person, what happened in this window, and what else was happening alongside it. RECORD already holds every detail. Your entry is the interpretation on top of it, not a field-by-field restatement: be selective, put the most important things first, and leave normal, unchanged things out entirely.

RULES. Follow all of them.
1. Numbers. Every number you write must come from RECORD or PRIOR. You may round it, give it as an approximate value, or give a range — just stay close to the real value (within about a tenth of it). Never state a number that has no basis in RECORD or PRIOR, and never do arithmetic of your own. A metric that has a "note" key beside it already excludes the questionable readings: use that value.
2. Evidence. Every statement lists, in evidence_refs, the key paths that support it, copied exactly as they appear in RECORD or PRIOR (for example "glucose.time in range percent", "changes vs previous window.change in sleep hours", "day by day[0].average glucose mg/dL") — never prefixed with "record.", the window_id or any namespace. The numbers in a statement must come from the keys that statement cites. "things that deviated" is a checklist, not evidence: cite the keys the numbers actually live in (for example "activity.steps"), never an entry of that list.
3. Change. Describe change with a direction word plus the unsigned amount: "time in range fell about 3 points", "sleep rose half an hour". Never put a negative number after a direction word. Take every direction and difference from the supplied change keys ("changes vs previous window", "movement vs previous window", "glucose movement vs previous window") — never work one out yourself, and never state a direction the record contradicts. "not enough data" means not available: say so, never guess. "difference from her own history" compares this window with her own earlier record: state one only when it is not null. Pair a change only with the measurement it was computed from: "change in average heart rate at rest" belongs to "average heart rate at rest bpm", never to "daily resting heart rate bpm", which is a different measurement.
4. Co-movement. co_movement_required lists the measures that moved the same way as, or the opposite way to, glucose. Write exactly one co_movement item for each of them and nothing else. Each item covers ONE measure: put its name in "streams" exactly as given, and in the statement say whether it went up or down (rose, fell, higher, lower), the amount and unit given, and that it moved the same way as / the opposite way to glucose — for example "Her steps fell 800 steps, the opposite way to glucose, which rose." If co_movement_required is empty, return an empty co_movement list. Never invent a pairing.
5. Relationship words. Allowed: "coincided with", "alongside", "on the same days as", "moved in the same direction as", "moved the opposite way to". Forbidden anywhere in your output: cause, caused, causing, because, due to, led to, result/resulted/resulting/results, trigger/triggered/triggering, explains, attributable, driven by, responsible. This includes explaining a data problem: write "the flagged reading coincided with higher variability", never "because of the flagged reading".
6. No diagnosis, advice, recommendation or prediction.
7. If a value is null or missing, say it was not available. Never guess.
8. If reliable is false, say the window is not clinically reliable and keep every statement tentative.
9. Quote diary and event text exactly as given, in quoted_text. Do not add details that are not in the text. Write dates in full as YYYY-MM-DD. If the record says all seven days were identical, say so; do not name a best or worst day.
10. Voice. Write about her — her glucose, sleep, activity, heart rate, mood, medicines. Never write the words "anchor", "crossed", "stream", "record", "field", "note", "data quality flag" or "direction table", and never write a fragment like "(direction: down)" or "status: low", in the headline, key_observations, trajectory, changes_vs_prior, co_movement, context_from_diary_and_events or recurring_patterns. A measure outside its reference range is described exactly that way — "her steps were below the reference range", "sedentary time was above the reference range" — never "steps was low" or "was high". Refer to medicines by name (metformin, amlodipine, levothyroxine) and to moods in the plain words given (calm, uplifted, tired, ...). Only notable_reason may mention anchors.
11. Questionable readings. A metric with a "note" key beside it carries a caveat: when a statement uses that metric, say in plain words that it excludes, or may reflect, a questionable reading. Apply that caveat ONLY to metrics that carry a note — never to time in range, average glucose, GMI or any other metric that has none. The "questionable readings" section holds the flagged readings and what the metrics would be with them included: use it ONLY in data_quality_caveats (state the flagged reading and, if useful, the value with it included) — never in the headline, key_observations or any other statement. Mention every entry of RECORD.data_quality_flags in data_quality_caveats (flag names are allowed there, and only there). Never present a questionable reading as a confirmed clinical excursion.
12. Things that deviated and brevity. "things that deviated" is what code found worth reporting. Cover each deviation briefly: every missed dose by medicine name, any diary event (quoted exactly), any large change, any data problem (in data_quality_caveats). Measures outside the reference range: write at most ONE observation naming the few that matter most, not one per measure. Obey that window's entry_limits exactly; a limit of 0 means return an empty list. They are limits, not targets — empty lists are good. Do not list a measure that was normal and unchanged: code adds those separately. Rank key_observations with the most important first.
13. Notability is decided mostly by code. If "large changes found" is empty, is_notable MUST be false. If it is not empty, is_notable MUST be true — with one exception: if every entry of "large changes found" is also listed in "large changes that may be sensor artifacts", you may set is_notable false, and notable_reason must then say it may be a sensor artifact. When is_notable is true, notable_reason says in plain words what changed, using the wording those entries use. "has diary event" never makes a window notable; mention a diary event in notable_reason only as context.
14. Return valid JSON matching the schema. No text before or after the JSON."""

TIER_GUIDANCE = {
    "day": "Describe this single day for her: how glucose behaved across the day (glucose by time of day, after meals) and only what stood out in sleep, activity, heart rate, medicines, mood, meals and diary entries. Compare with PRIOR through the supplied changes. Cover everything under \"things that deviated\". A day where nothing deviated should produce a very short entry.",
    "week": "Describe the week: the trajectory across the 7 days in order (day by day), the best and worst day and what was recorded on them, and only the parts of the weekly totals (sleep, steps, heart rate, adherence by medicine, mood by time block, meals and post-meal peaks, location, readings out of range) that stood out. Cover everything under \"things that deviated\". Co-movement comes only from co_movement_required. Summarize the diary events and repeating patterns. Compare with PRIOR (the previous 7 days) through the supplied changes.",
    "month": "Describe the long-run picture: the whole history so far, the last 30 days, and month by month. Use the lab comparison (including its supplied HbA1c minus GMI gap) to place CGM-estimated GMI beside lab HbA1c; a lab result listed under \"things that deviated\" was drawn within these 30 days. Use the long run trends for sleep, steps, resting heart rate and adherence, quoting their supplied change and direction. co_movement must be an empty list at this tier. Compare with PRIOR (the previous checkpoint).",
}

USER_TEMPLATE = """TIER: {tier}

TIER GUIDANCE:
{tier_guidance}

ANCHORS:
{anchors_json}

WINDOWS (keyed by window_id — each has its own RECORD, PRIOR and entry_limits; PRIOR may be null):
{windows_json}

Return a single JSON object keyed by each window_id above (no other keys), where each value
is one memory entry matching exactly this schema:
{output_schema}"""

OUTPUT_SCHEMA = """{
  "window_id": "string", "tier": "day | week | month",
  "headline": "one plain sentence about her in this window",
  "key_observations": [{"statement": "string", "evidence_refs": ["key path"]}],   // ranked, most important first
  "trajectory": [{"statement": "string", "evidence_refs": ["key path"]}],
  "changes_vs_prior": [{"statement": "string", "evidence_refs": ["key path"]}],
  "co_movement": [{"statement": "string", "streams": ["ONE name, exactly as in co_movement_required"], "evidence_refs": ["key path"]}],
  "context_from_diary_and_events": [{"statement": "string", "quoted_text": "exact text or null", "date": "YYYY-MM-DD", "evidence_refs": ["key path"]}],
  "recurring_patterns": [{"statement": "string", "evidence_refs": ["key path"]}],
  "data_quality_caveats": ["string"],
  "is_notable": true,
  "notable_reason": "string or null (null only if is_notable is false)"
}"""


class Statement(BaseModel):
    statement: str
    evidence_refs: list[str] = Field(default_factory=list)


class CoMovement(Statement):
    streams: list[str] = Field(default_factory=list)


class DiaryStatement(Statement):
    quoted_text: str | None = None
    date: str | None = None


class MemoryEntry(BaseModel):
    window_id: str
    tier: str
    headline: str
    key_observations: list[Statement] = Field(default_factory=list)
    trajectory: list[Statement] = Field(default_factory=list)
    changes_vs_prior: list[Statement] = Field(default_factory=list)
    co_movement: list[CoMovement] = Field(default_factory=list)
    context_from_diary_and_events: list[DiaryStatement] = Field(default_factory=list)
    recurring_patterns: list[Statement] = Field(default_factory=list)
    data_quality_caveats: list[str] = Field(default_factory=list)
    is_notable: bool
    notable_reason: str | None = None
    # Both set by code after validation — the model does not write them.
    unremarkable_streams: list[str] = Field(default_factory=list)
    confidence: str = ""


# ---- reference resolution (plain paths -> internal paths) -----------------------------------------

_MISSING = object()  # path does not exist (distinct from a field that exists but is null)
IGNORED_REFS: list[str] = []  # refs into the "things that deviated" checklist (not evidence) dropped before validation
SUFFIX_RESOLVED: list[str] = []  # every ref resolved by its unique suffix, for the run report


def _norm(path: str) -> str:
    """Loose form for matching a path the model retyped: case, spaces and punctuation ignored."""
    return re.sub(r"[^a-z0-9\[\].]", "", path.lower())


class Refs:
    """Resolves an evidence_ref against RECORD then PRIOR, accepting either the plain key path the
    model was shown or the internal path, and tolerating a 'record.'/'prior.'/window_id prefix."""

    def __init__(self, record: dict, prior: dict | None, window_id: str = ""):
        self.record, self.prior, self.window_id = record, prior, window_id
        _, self.rmap, labels = to_plain(record)
        self.pmap: dict[str, str] = {}
        if prior:
            _, self.pmap, prior_labels = to_plain(prior)
            labels = {**prior_labels, **labels}
        self.labels = labels  # internal key -> plain label, for the sanitizer
        self.rnorm = {_norm(k): v for k, v in self.rmap.items()}
        self.pnorm = {_norm(k): v for k, v in self.pmap.items()}

    def _strip(self, path: str) -> tuple[str, bool]:
        explicit_prior = False
        for _ in range(3):
            m = re.match(r"^(record|RECORD)\.(.*)$", path)
            if m:
                path = m.group(2)
                continue
            m = re.match(r"^(prior|PRIOR)\.(.*)$", path)
            if m:
                path, explicit_prior = m.group(2), True
                continue
            if self.window_id and path.startswith(self.window_id + "."):
                path = path[len(self.window_id) + 1 :]
                continue
            break
        return path, explicit_prior

    def internal(self, ref: str) -> str:
        """The internal path a ref points at (for checks written against internal names)."""
        path, _ = self._strip(ref)
        return self.rmap.get(path) or self.rnorm.get(_norm(path)) or self.pmap.get(path) or self.pnorm.get(_norm(path)) or path

    def resolve(self, ref: str) -> Any:
        path, explicit_prior = self._strip(ref)
        order = [(self.prior, self.pmap, self.pnorm), (self.record, self.rmap, self.rnorm)] if explicit_prior \
            else [(self.record, self.rmap, self.rnorm), (self.prior, self.pmap, self.pnorm)]
        for root, pmap, pnorm in order:
            if root is None:
                continue
            internal = pmap.get(path) or pnorm.get(_norm(path)) or path  # plain path, loose plain path, or already internal
            v = _traverse(root, internal)
            if v is not _MISSING:
                return v
        # A ref that drops its leading section ("post-meal glucose peak.average per day" for
        # "weekly totals.post-meal glucose peak.average per day") resolves when exactly ONE real path ends with it.
        # Zero or several matches stay "not found": this normalises a dropped prefix, it never guesses between paths.
        for root, pmap, pnorm in order:
            if root is None:
                continue
            tail = "." + _norm(path)
            hits = {v for k, v in pnorm.items() if k.endswith(tail)}
            if len(hits) == 1:
                SUFFIX_RESOLVED.append(f"{ref!r} -> {next(iter(hits))!r}")
                return _traverse(root, next(iter(hits)))
        return _MISSING


def _traverse(root: Any, path: str) -> Any:
    cur = root
    try:
        for part in re.findall(r"[^.\[\]]+|\[\d+\]", path):
            cur = cur[int(part[1:-1])] if part.startswith("[") else cur[part]
        return cur
    except (KeyError, IndexError, TypeError):
        return _MISSING


# ---- sanitizer (code fixes wording, never meaning) ------------------------------------------------

SANITIZED: list[str] = []  # every substitution made, for the run report
_SHORT_DATE_RE = re.compile(r"(?<![-\d/])(\d{1,2})-(\d{1,2})(?![-\d/])")


def _full_date(month: str, day: str, record: dict) -> str | None:
    """A short 'MM-DD' is dated from the window itself: the year whose month it matches."""
    start = record.get("start_date") or record.get("date") or ""
    end = record.get("end_date") or record.get("date") or ""
    for ref in (end, start):
        if len(ref) == 10 and ref[5:7] == f"{int(month):02d}":
            return f"{ref[:4]}-{int(month):02d}-{int(day):02d}"
    if len(start) == 10:
        return f"{start[:4]}-{int(month):02d}-{int(day):02d}"
    return None


# Data-quality flag names are system words; outside data_quality_caveats they are rewritten to plain phrases.
_FLAG_PHRASES = {
    "known_clip_artifact_reading": "a questionable clipped reading", "max_reading_above_400": "a questionable very high reading",
    "implausible_rate_of_change": "a questionable sudden jump", "gap_hours": "a gap in the readings", "low_completeness": "incomplete data",
}
_FLAG_RE = re.compile(r"\b(" + "|".join(_FLAG_PHRASES) + r")(?::[\w.\-]+)*")


def sanitize_text(text: str, labels: dict[str, str], record: dict, where: str, flags: bool = True) -> str:
    """Swaps leaked internal key names (and flag names) for their plain labels and expands short dates. Logs each
    change. Deliberately does NOT touch approximations, causal words or ungrounded numbers."""
    out = text
    if flags:
        new = _FLAG_RE.sub(lambda m: _FLAG_PHRASES[m.group(1)], out)
        if new != out:
            SANITIZED.append(f"{where}: flag_name {out!r} -> {new!r}")
            out = new
    for internal, plain in labels.items():
        if "_" not in internal:
            continue  # single words are ordinary English, not a leaked key
        new = re.sub(rf"(?<![\w.]){re.escape(internal)}(?![\w])", plain, out)
        if new != out:
            SANITIZED.append(f"{where}: key_name {internal!r} -> {plain!r}")
            out = new

    def _date_sub(m: re.Match) -> str:
        full = _full_date(m.group(1), m.group(2), record)
        if not full:
            return m.group(0)
        SANITIZED.append(f"{where}: short_date {m.group(0)!r} -> {full!r}")
        return full

    # Only inside a date-looking context: "12-24" yes, "1600-2000" (a range) no — _SHORT_DATE_RE
    # already requires 1-2 digits on both sides.
    return _SHORT_DATE_RE.sub(_date_sub, out)


def sanitize_entry(entry: MemoryEntry, labels: dict[str, str], record: dict, window_id: str) -> None:
    entry.headline = sanitize_text(entry.headline, labels, record, f"{window_id}.headline")
    if entry.notable_reason:
        entry.notable_reason = sanitize_text(entry.notable_reason, labels, record, f"{window_id}.notable_reason")
    for name in ("key_observations", "trajectory", "changes_vs_prior", "co_movement", "context_from_diary_and_events", "recurring_patterns"):
        for i, s in enumerate(getattr(entry, name)):
            s.statement = sanitize_text(s.statement, labels, record, f"{window_id}.{name}[{i}]")


# ---- validation ----------------------------------------------------------------------------------
#
# Numeric grounding (V0 rule — rounding and approximation are acceptable):
#   A stated number is grounded by a record value when it is within 10% of it, or within 1 unit
#   when the value is under 10. Comparison is sign-insensitive (prose says "fell 3.45" for a
#   stored -3.45). A range "1600-2000" is grounded when some record value falls inside it.
#   (ok) grounded by a value at one of the statement's own evidence_refs.
#   (a)  grounded only by a value elsewhere in RECORD/PRIOR -> accepted, warning logged.
#   (b)  grounded by nothing anywhere in RECORD/PRIOR -> rejected.
#   headline / notable_reason have no refs field, so they are checked against all of RECORD/PRIOR.
#   GROUNDING["tolerance_only"] counts statements that would have failed an exact-decimal match,
#   i.e. exactly how much the tolerance is doing.

# Band edges that appear inside plain labels ("time above 250 percent", "time below 54 percent") and in the anchor
# list shown to the model: quoting the label is not inventing a number.
LABEL_THRESHOLDS = (54, 70, 180, 250)
GROUNDING = {"ok": 0, "a_elsewhere_warned": 0, "b_nowhere_rejected": 0, "no_refs_field_ok": 0, "tolerance_only": 0}
STATUS_ECHOES: list[str] = []  # "steps was low"-style paraphrases of a status (soft: counted, not rejected)
WARNINGS: list[str] = []  # non-blocking findings (grounded-elsewhere, caveat coverage)

# Negative lookbehind for a digit: in "74-82" the hyphen is a range separator, not a sign.
NUMBER_RE = re.compile(r"(?<!\d)-?\d+\.?\d*")
RANGE_RE = re.compile(r"(\d+\.?\d*)\s*(?:-|–|—|to)\s*(\d+\.?\d*)")


def _flatten_numbers(obj: Any, out: list[float] | None = None) -> list[float]:
    out = [] if out is None else out
    if isinstance(obj, bool) or obj is None:
        return out
    if isinstance(obj, (int, float)):
        out.append(float(obj))
    elif isinstance(obj, dict):
        for v in obj.values():
            _flatten_numbers(v, out)
    elif isinstance(obj, (list, tuple)):
        for v in obj:
            _flatten_numbers(v, out)
    return out


def _grounded(num_str: str, actual: Any) -> bool:
    """Within 10% of the value, or within 1 unit for values under 10. Sign-insensitive."""
    if isinstance(actual, bool) or not isinstance(actual, (int, float)):
        return False
    stated, value = abs(float(num_str)), abs(float(actual))
    return abs(stated - value) <= (1.0 if value < 10 else 0.10 * value)


def _grounded_exact(num_str: str, actual: Any) -> bool:
    if isinstance(actual, bool) or not isinstance(actual, (int, float)):
        return False
    d = len(num_str.split(".")[1]) if "." in num_str else 0
    return abs(abs(float(num_str)) - abs(float(actual))) <= 0.5 * (10**-d)


# Stripped from a statement before number-extraction — structural/descriptive tokens, never a metric.
_ISO_TIMESTAMP_RE = re.compile(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:[+-]\d{2}:\d{2})?")
_ISO_DATE_RE = re.compile(r"\d{4}-\d{2}-\d{2}")
_YEAR_MONTH_RE = re.compile(r"\b\d{4}-\d{2}\b")  # "2025-10" month labels
_DMY_RE = re.compile(r"\b\d{1,2}[-/]\d{1,2}[-/]\d{4}\b")  # "12-18-2025" style dates
_CLOCK_TIME_RE = re.compile(r"\b\d{1,2}:\d{2}\b")
# Only our own fixed window lengths (7/14/30/90 days) are structural; "6.9 hours" stays a metric.
_WINDOW_SPAN_RE = re.compile(r"\b(?:7|14|30|90)[\s-]?d(?:ays?)?\b", re.IGNORECASE)
_MONTH_YEAR_RE = re.compile(
    r"\b(?:Jan(?:uary)?|Feb(?:ruary)?|Mar(?:ch)?|Apr(?:il)?|May|Jun(?:e)?|Jul(?:y)?|Aug(?:ust)?|"
    r"Sep(?:t(?:ember)?)?|Oct(?:ober)?|Nov(?:ember)?|Dec(?:ember)?)\.?\s+\d{4}\b",
    re.IGNORECASE,
)
_IDENTIFIER_RE = re.compile(r"\b[A-Za-z][A-Za-z0-9_]*\b")
# "Dec 18 2025", "Dec 18", "18 Dec 2025" — the day number is a date, not a measurement.
_MONTH_DAY_RE = re.compile(
    r"\b(?:\d{1,2}\s+)?(?:Jan(?:uary)?|Feb(?:ruary)?|Mar(?:ch)?|Apr(?:il)?|May|Jun(?:e)?|Jul(?:y)?|Aug(?:ust)?|"
    r"Sep(?:t(?:ember)?)?|Oct(?:ober)?|Nov(?:ember)?|Dec(?:ember)?)\.?(?:\s*\d{1,2}(?![\d.%]))?(?:,?\s*\d{4})?\b",
    re.IGNORECASE,
)
_THOUSANDS_RE = re.compile(r"(?<=\d),(?=\d{3}\b)")


def _strip_non_metric_numbers(text: str) -> str:
    text = _THOUSANDS_RE.sub("", text)  # "1,452.2" is one number, not 1 and 452.2
    for pattern in (_ISO_TIMESTAMP_RE, _ISO_DATE_RE, _DMY_RE, _YEAR_MONTH_RE, _MONTH_DAY_RE, _MONTH_YEAR_RE, _CLOCK_TIME_RE, _WINDOW_SPAN_RE, _IDENTIFIER_RE):
        text = pattern.sub("", text)
    return text


FORBIDDEN_RE = re.compile(
    r"\b(caus\w*|trigger\w*|led to|result(?:s|ed|ing)?|due to|because(?: of)?|explains?|attributable|driven by|responsible)\b", re.I
)
SIGNED_AFTER_DIRECTION_RE = re.compile(
    r"\b(?:increas\w*|decreas\w*|rose|rise|rises|fell|fall\w*|drop\w*|declin\w*|shorten\w*|lower\w*|higher|reduc\w*|climb\w*|up|down)\s+(?:by\s+|of\s+)?-\s?\d", re.I
)
# System voice: words about the data rather than about her, and machine fragments such as "(direction: down)".
# "anchor"/"crossed" are allowed in notable_reason only (rule 13 asks for them there).
VOICE_RE = re.compile(
    r"\b(anchors?|crossed|streams?|fields?|direction table|data quality flags?|note key|(?:the|this|that|whole|full)\s+records?|records?\s+(?:shows?|lists?|says?|states|holds|has|indicates)|(?:percent|mg/dL|bpm|hours|points|minutes|steps)\s+note"
    r"|(?:direction|status|confidence)\s*[:=])(?=\W|$)", re.I)
# A measure's reference-range status echoed as a verdict ("steps was low") instead of "below the reference range".
STATUS_ECHO_RE = re.compile(
    r"\b(?:steps?|sleep|hydration|screen time|sedentary time|heart rate|blood pressure|BMI|waist-to-hip ratio)\s+(?:was|were|is|are|remained|stayed)\s+(?:slightly\s+|borderline\s+)?(?:low|high)\b", re.I
)
# Wording that signals "this is a questionable reading" — it may only be attached to metrics a flag affects.
QUESTIONABLE_RE = re.compile(r"\b(questionable|artifact|artefact|sensor)\b", re.I)
FLAG_NAME_RE = re.compile(r"known_clip_artifact_reading|max_reading_above_400|implausible_rate_of_change|gap_hours|low_completeness")
# Glucose-section metric keys (window metrics, changes, post-meal peaks): the ones a questionable-reading caveat can be misapplied to.
GLUCOSE_LEAVES = {"mean", "gmi_pct", "tir_pct", "tar_pct", "tar_severe_pct", "tbr_pct", "tbr_severe_pct", "cv_pct", "min_value", "max_value",
                  "completeness_pct", "n_readings", "glucose_mean", "glucose_tir_pct", "glucose_cv_pct", "glucose_gmi_pct",
                  "glucose_severe_total_curr", "glucose_severe_total_prior", "peak_glucose", "post_meal_peak_mean", "post_meal_peak_max"}
VAGUE_COMOVE_RE = re.compile(r"\bother (?:logged|recorded) data\b|\bother data\b", re.I)

# A change must not be paired with a different measurement that is easy to confuse with its own basis.
DELTA_CONFUSABLE = {"deltas.resting_hr_mean": {"heart_rate.resting_heart_rate_daily", "heart_rate.continuous_mean"}}

_UP = ("increase", "rose", "rise", "higher", "went up", "climb", "gained", "more than")
_DOWN = ("decrease", "fell", "drop", "lower", "declin", "shorten", "went down", "less than")


def _words(text: str) -> tuple[bool, bool]:
    """(mentions an upward move, mentions a downward move)."""
    low = text.lower()
    return (any(w in low for w in _UP) or bool(re.search(r"\bup\b", low)), any(w in low for w in _DOWN) or bool(re.search(r"\bdown\b", low)))


def _direction_failure(text: str, delta_values: list[float]) -> str | None:
    """A direction word that contradicts the sign of a cited change. Rejected: a statement that
    says a value fell when the record shows it rose is wrong, not merely loose."""
    up, down = _words(text)
    if up == down:
        return None
    for v in delta_values:
        if v != 0 and ((up and v < 0) or (down and v > 0)):
            return f"wrong_direction: text says {'up' if up else 'down'} but the cited change is {v}: {text!r}"
    return None


def _check_numbers(scan: str, usable: list[Any], all_numbers: list[float], has_refs_field: bool,
                   refs: list[str], text: str, failures: list[str]) -> None:
    """Ranges first (a range is grounded when a record value falls inside it), then bare numbers."""
    stripped = _strip_non_metric_numbers(scan)
    for m in RANGE_RE.finditer(stripped):
        lo, hi = sorted((float(m.group(1)), float(m.group(2))))
        pool = [v for v in usable if isinstance(v, (int, float)) and not isinstance(v, bool)]
        if any(lo <= abs(v) <= hi for v in pool):
            GROUNDING["ok"] += 1
        elif any(lo <= abs(v) <= hi for v in all_numbers):
            GROUNDING["a_elsewhere_warned" if has_refs_field else "no_refs_field_ok"] += 1
            if has_refs_field:
                WARNINGS.append(f"grounded_elsewhere:range {m.group(0)} not at its refs {refs} in: {text!r}")
        else:
            GROUNDING["b_nowhere_rejected"] += 1
            failures.append(f"ungrounded_number:{m.group(0)} (no value in RECORD/PRIOR falls in that range) in: {text!r}")
        stripped = stripped.replace(m.group(0), " ", 1)

    for num_str in NUMBER_RE.findall(stripped):
        if len(num_str) <= 2 and num_str.lstrip("-") in ("0", "1", "2", "3", "4", "5", "6", "7"):
            continue  # small counts in prose ("2 of 7 days")
        hit_usable = [v for v in usable if _grounded(num_str, v)]
        if hit_usable:
            GROUNDING["ok"] += 1
            if not any(_grounded_exact(num_str, v) for v in hit_usable):
                GROUNDING["tolerance_only"] += 1
        elif any(_grounded(num_str, v) for v in all_numbers):
            if has_refs_field:
                GROUNDING["a_elsewhere_warned"] += 1
                WARNINGS.append(f"grounded_elsewhere:{num_str} not at its refs {refs} in: {text!r}")
            else:
                GROUNDING["no_refs_field_ok"] += 1
        else:
            GROUNDING["b_nowhere_rejected"] += 1
            failures.append(f"ungrounded_number:{num_str} (no value within 10% anywhere in RECORD/PRIOR) in: {text!r}")


def _is_checklist_ref(ref: str, resolver: "Refs") -> bool:
    path = resolver._strip(ref)[0].lower()
    return path.startswith("things that deviated") or resolver.internal(ref).startswith("material_changes")


def _leaf(internal_path: str) -> str:
    parts = re.findall(r"[^.\[\]]+", internal_path)
    leaf = parts[-1] if parts else ""
    return leaf[: -len("__note")] if leaf.endswith("__note") else leaf


def validate_entry(entry: MemoryEntry, record: dict, prior: dict | None, refs_resolver: Refs, window_id: str = "") -> list[str]:
    """Returns specific failure strings; empty means valid. Non-blocking findings go to WARNINGS.

    `record`/`prior` are the stored (code-side) records: caps, co-movement, material changes, notability and flag
    details come from them. Numbers and evidence refs are checked against refs_resolver.record/.prior — the
    annotated copies the model was actually shown (cleaned values in place, raw flagged values only in the
    `questionable_readings` section)."""
    failures: list[str] = []
    ann, ann_prior = refs_resolver.record, refs_resolver.prior
    all_numbers = _flatten_numbers(ann) + _flatten_numbers(ann_prior)
    # Numbers that live inside STRING values the record exposes: flag strings ("gap_hours:2.2") and
    # recurring-pattern names ("..._peak_above_180").
    for rec_ in (ann, ann_prior):
        if rec_:
            strings = list(rec_.get("data_quality_flags", [])) + [x.get("pattern", "") for x in rec_.get("recurring_in_window", [])]
            all_numbers += [float(n) for t in strings for n in NUMBER_RE.findall(t)]
    all_numbers += [float(n) for n in LABEL_THRESHOLDS]
    # Values that exist only as "the flagged reading / what the metric would be with it": caveats only.
    raw_only = [v for r in (ann, ann_prior) if r for v in _flatten_numbers(r.get("questionable_readings"))]
    allowed_exact = [v for r in (ann, ann_prior) if r for v in _flatten_numbers({k: x for k, x in r.items() if k != "questionable_readings"})]
    affected_leaves = {k for d in record.get("data_quality_details", []) for k in d["affects"]}
    if prior:
        affected_leaves |= {k for d in prior.get("data_quality_details", []) for k in d["affects"]}

    # (text, refs, has_refs_field, apply_voice_rules, quoted_to_ignore, kind)
    Item = tuple[str, list[str], bool, bool, str | None, str]
    items: list[Item] = [(entry.headline, [], False, True, None, "headline")]
    for group in (entry.key_observations, entry.trajectory, entry.changes_vs_prior, entry.co_movement, entry.recurring_patterns):
        items += [(s.statement, s.evidence_refs, True, True, None, "statement") for s in group]
    items += [(s.statement, s.evidence_refs, True, True, s.quoted_text, "statement") for s in entry.context_from_diary_and_events]
    if entry.notable_reason:
        items.append((entry.notable_reason, [], False, False, None, "notable"))
    items += [(c, [], False, False, None, "caveat") for c in entry.data_quality_caveats]

    for name, cap in caps_for(record).items():
        n = len(getattr(entry, name))
        if n > cap:
            failures.append(f"too_many_items:{name} has {n}, limit for this window is {cap}")

    for text, refs, has_refs_field, voice, quoted, kind in items:
        scan = text.replace(quoted, "") if quoted else text
        if m := FORBIDDEN_RE.search(scan):
            failures.append(f"forbidden_language:'{m.group(0)}' in: {text!r}")
        if m := SIGNED_AFTER_DIRECTION_RE.search(scan):
            failures.append(f"signed_magnitude:'{m.group(0)}' in: {text!r} (direction word + unsigned amount)")
        if voice:
            if m := VOICE_RE.search(scan):
                failures.append(f"system_voice:'{m.group(0)}' in: {text!r} (describe her, not the data)")
            if m := STATUS_ECHO_RE.search(scan):  # soft: a paraphrase of the reference-range status, reported not rejected
                STATUS_ECHOES.append(f"{window_id}: {m.group(0)!r} in: {text!r}")
        if kind != "caveat" and (m := FLAG_NAME_RE.search(scan)):
            failures.append(f"flag_name_outside_caveats:'{m.group(0)}' in: {text!r}")

        # "things that deviated" is a checklist, not evidence (rule 2). A ref into it is dropped, not failed: its
        # list indexes are positions in a list the model counts by eye. The statement's numbers must then be
        # grounded by its remaining refs or sit elsewhere in the record, exactly as for any other statement.
        kept = [r for r in refs if not _is_checklist_ref(r, refs_resolver)]
        if len(kept) != len(refs):
            IGNORED_REFS.append(f"{window_id}: {[r for r in refs if r not in kept]} in: {text!r}")
            refs = kept
        bare = [refs_resolver.internal(r) for r in refs]  # plain paths mapped back to internal names
        for dref, confusable in DELTA_CONFUSABLE.items():
            if dref in bare and (stray := [r for r in bare if r in confusable]):
                failures.append(f"mixed_measurements:{dref} is the change in the resting-period mean, but the statement also cites {stray} in: {text!r}")
        refd_values: list[Any] = []
        delta_values: list[float] = []
        for ref in refs:
            v = refs_resolver.resolve(ref)
            if v is _MISSING:
                failures.append(f"evidence_ref_not_found:{ref!r} in: {text!r}")
            elif v is not None:  # a null field is a valid reference ("not available"); it grounds no number
                refd_values.append(v)
                if re.search(r"delta|change", ref, re.I) and isinstance(v, (int, float)) and not isinstance(v, bool):
                    delta_values.append(float(v))
        usable = [v for v in refd_values if isinstance(v, (int, float)) and not isinstance(v, bool)]

        _check_numbers(scan, usable, all_numbers, has_refs_field, refs, text, failures)
        if f := _direction_failure(scan, delta_values):
            failures.append(f)

        if kind != "caveat":  # the flagged reading (and the metric "with it") belong in data_quality_caveats only
            for num_str in NUMBER_RE.findall(_strip_non_metric_numbers(scan)):
                if any(_grounded_exact(num_str, v) for v in raw_only) and not any(_grounded_exact(num_str, v) for v in allowed_exact):
                    failures.append(f"flagged_value_outside_caveats:{num_str} (a questionable reading's value belongs in data_quality_caveats) in: {text!r}")

        if kind == "statement" and refs:
            leaves = {_leaf(p) for p in bare}
            if QUESTIONABLE_RE.search(scan):  # a caveat may only ride on metrics a flag actually affects
                if wrong := sorted(l for l in leaves & GLUCOSE_LEAVES if l not in affected_leaves):
                    msg = f"caveat_on_unaffected_metric:{wrong} carry no questionable-reading note, but the statement calls them questionable: {text!r}"
                    if leaves & affected_leaves:  # cites an affected metric too: the caveat may be scoped to that one — can't tell, so soft
                        WARNINGS.append(msg + " (statement also cites an affected metric)")
                    else:
                        failures.append(msg)
            elif noted := sorted(l for l in leaves if any(f"{l}__note" in (sec or {}) for sec in (ann.get("deltas"),)) and l in affected_leaves):
                WARNINGS.append(f"change_without_caveat:{noted} may reflect a questionable reading but the statement does not say so ({window_id}): {text!r}")

    # --- co-movement: the top-K co-movers chosen by code, one measure per item, direction + amount stated ---
    cand = record.get("co_movement_candidates")
    k = caps_for(record)["co_movement"]
    required = {r["name"]: r for r in (cand or {}).get("ranked", [])[:k]}
    if not cand:
        if entry.co_movement:
            failures.append("co_movement_not_allowed: this window has no co-movement candidates (return an empty list)")
    else:
        mentioned: set[str] = set()
        for c in entry.co_movement:
            if len(c.streams) != 1:
                failures.append(f"co_movement_one_measure_per_item: got {c.streams} in: {c.statement!r}")
                continue
            name = c.streams[0]
            mentioned.add(name)
            r = required.get(name)
            if r is None:
                failures.append(f"co_movement_streams_not_in_candidates:[{name!r}] (only the measures listed in co_movement_required)")
                continue
            up, down = _words(c.statement)
            if (r["direction"] == "up" and not up) or (r["direction"] == "down" and not down):
                failures.append(f"co_movement_direction_missing:{name!r} went {r['direction']} but the statement does not say so: {c.statement!r}")
            nums = NUMBER_RE.findall(_strip_non_metric_numbers(c.statement))
            if r["amount"] is not None and not any(_grounded(n, r["amount"]) for n in nums):
                failures.append(f"co_movement_magnitude_missing:{name!r} moved {r['amount']} {r['unit']}; the statement must give that amount: {c.statement!r}")
        if set(required) - mentioned:
            failures.append(f"co_movement_missing_candidates:{sorted(set(required) - mentioned)} (one item for each measure in co_movement_required)")
    for c in entry.co_movement:
        if VAGUE_COMOVE_RE.search(c.statement):
            failures.append(f"vague_co_movement: {c.statement!r}")

    # --- material changes: a missed dose must be named (the old entry for 2025-12-26 lost it) ---
    blob = " ".join([entry.headline, entry.notable_reason or ""] + entry.data_quality_caveats
                    + [s.statement for g in (entry.key_observations, entry.trajectory, entry.changes_vs_prior, entry.co_movement,
                                             entry.context_from_diary_and_events, entry.recurring_patterns) for s in g]).lower()
    for m in record.get("material_changes", []):
        if m["kind"] in ("missed_dose", "missed_doses") and plain_value(m["medicine"]).lower() not in blob:
            failures.append(f"material_change_omitted:{m['kind']} for {plain_value(m['medicine'])} is not mentioned (name the medicine)")
    if any(m["kind"] == "diary_events" for m in record.get("material_changes", [])) and not entry.context_from_diary_and_events:
        WARNINGS.append(f"material_change_not_covered:diary events not quoted ({window_id})")

    # --- quotes ---
    if entry.context_from_diary_and_events:
        diary_texts = [e.get("text", "") for e in record.get("diary_events", []) if e.get("text")]
        diary_texts += [e.get("text", "") for e in record.get("events_in_window", []) if e.get("text")]
        for d in entry.context_from_diary_and_events:
            if d.quoted_text and not any(d.quoted_text in t for t in diary_texts):
                failures.append(f"quote_not_exact:{d.quoted_text!r}")

    # --- notability: code decides, except when every crossed anchor is a probable artifact ---
    crossed = record.get("anchors_crossed") or []
    questionable = set(record.get("anchors_questionable") or [])
    if not crossed and entry.is_notable:
        failures.append("is_notable_true_with_empty_anchors_crossed")
    if crossed and not entry.is_notable:
        if not set(crossed) <= questionable:
            failures.append(f"is_notable_false_but_non_questionable_anchor_crossed:{sorted(set(crossed) - questionable)}")
        elif "artifact" not in (entry.notable_reason or "").lower():
            failures.append("is_notable_false_requires_notable_reason_stating_possible_sensor_artifact")
    if entry.is_notable and not entry.notable_reason:
        failures.append("notable_reason_missing_for_notable_window")

    # --- soft: every data-quality flag should be named in the caveats ---
    caveat_blob = " ".join(entry.data_quality_caveats).lower()
    for flag in record.get("data_quality_flags", []):
        if flag.split(":")[0].lower() not in caveat_blob:
            WARNINGS.append(f"caveat_missing_flag:{flag} ({window_id})")

    return failures


def code_unremarkable(record: dict, entry: MemoryEntry) -> list[str]:
    """Streams the code considers unremarkable: flat direction, no anchor naming them, and not
    already mentioned in the entry. Computed here so the entry can never call a stream unchanged
    while also reporting it as having moved."""
    dirs = record.get("stream_direction_table") or {}
    blob = " ".join(
        [entry.headline, entry.notable_reason or ""]
        + [s.statement for name in ("key_observations", "trajectory", "changes_vs_prior", "co_movement", "recurring_patterns", "context_from_diary_and_events")
           for s in getattr(entry, name)]
    ).lower()
    anchor_blob = " ".join(record.get("anchors_crossed") or []).lower()
    out = []
    for label, d in dirs.items():
        if d != "flat" or label.lower() in blob:
            continue
        if any(tok in anchor_blob for tok in label.lower().split()):
            continue
        out.append(label)
    return out


def _llm() -> ChatOpenAI:
    return ChatOpenAI(model=MODEL, api_key=os.getenv("OPENROUTER_API_KEY"), base_url="https://openrouter.ai/api/v1",
                      model_kwargs={"response_format": {"type": "json_object"}})


async def _call(llm, system: str, user: str) -> dict:
    response = await llm.ainvoke([("system", system), ("human", user)])
    content = getattr(response, "content", response)
    return json.loads(content if isinstance(content, str) else str(content))


def _batch_prompt(tier: str, batch: list[dict]) -> str:
    windows_json = {}
    for w in batch:
        k = caps_for(w["record"])["co_movement"]
        plain_record, _, _ = to_plain(annotate(w["record"], k))
        plain_prior, _, _ = to_plain(annotate(w["prior_record"], k)) if w.get("prior_record") else (None, {}, {})
        windows_json[w["window_id"]] = {"record": plain_record, "prior": plain_prior, "entry_limits": caps_for(w["record"])}
    return USER_TEMPLATE.format(
        tier=tier, tier_guidance=TIER_GUIDANCE[tier], anchors_json=json.dumps(ANCHORS[tier]),
        windows_json=json.dumps(windows_json), output_schema=OUTPUT_SCHEMA,
    )


# Internal names that may leak into prose and are replaced by their plain label (underscore / mixed-case ones only —
# a plain English word is not a leak).
_SANITIZE_VALUE_LABELS = {k: plain_value(k) for k in VALUE_LABELS if "_" in k or k != k.lower()}


def _validate_one(window_id: str, raw_entry: dict, record: dict, prior: dict | None) -> tuple[MemoryEntry | None, list[str]]:
    try:
        entry = MemoryEntry.model_validate(raw_entry)
    except ValidationError as exc:
        return None, [f"schema_invalid:{exc}"]
    k = caps_for(record)["co_movement"]
    resolver = Refs(annotate(record, k), annotate(prior, k) if prior else None, window_id)
    sanitize_entry(entry, {**_SANITIZE_VALUE_LABELS, **resolver.labels}, record, window_id)  # wording fixed in code, before validation
    failures = validate_entry(entry, record, prior, resolver, window_id)
    if not failures:
        entry.confidence = record.get("confidence", "")
        entry.unremarkable_streams = code_unremarkable(record, entry)
    return (entry if not failures else None), failures


async def _attempt_batch(llm, tier: str, batch: list[dict], extra: str = "") -> dict[str, dict]:
    """Returns {window_id: raw_entry_dict} for whatever the model returned (may be partial)."""
    raw = await _call(llm, SYSTEM_PROMPT, _batch_prompt(tier, batch) + extra)
    if not isinstance(raw, dict):
        raise ValueError(f"Expected a JSON object keyed by window_id, got {type(raw).__name__}")
    return raw


async def process_batch(llm, tier: str, batch: list[dict], semaphore: asyncio.Semaphore) -> list[dict]:
    """batch: list of {'window_id','record','prior_record'} for ONE tier (size per BATCH_SIZE[tier]).
    Returns one result dict per window: {'window_id','llm_status','memory','raw','failures',
    'first_attempt_ok'} — the last so the report can separate first-attempt from final failures."""
    by_id = {w["window_id"]: w for w in batch}
    results: dict[str, dict] = {}

    ids = [w["window_id"] for w in batch]
    logger.info(f"memory_llm: calling LLM for {tier} batch {ids}")
    async with semaphore:
        try:
            raw_batch = await _attempt_batch(llm, tier, batch)
            logger.info(f"memory_llm: {tier} batch {ids} returned ({len(raw_batch)} keys)")
        except Exception as exc:
            logger.warning(f"memory_llm: batch call failed ({tier}, {len(batch)} windows): {exc}")
            raw_batch = {}

    pending: list[tuple[str, list[str]]] = []  # (window_id, failures) needing individual retry
    for wid, w in by_id.items():
        if wid not in raw_batch:
            pending.append((wid, ["missing_from_batch_response"]))
            continue
        entry, failures = _validate_one(wid, raw_batch[wid], w["record"], w.get("prior_record"))
        if entry is None:
            logger.info(f"memory_llm: {wid} failed validation, queuing individual retry: {failures}")
            pending.append((wid, failures))
        else:
            logger.info(f"memory_llm: {wid} ok (is_notable={entry.is_notable})")
            results[wid] = {"window_id": wid, "llm_status": "ok", "memory": entry, "raw": json.dumps(raw_batch[wid]),
                            "failures": [], "first_attempt_ok": True}

    for wid, failures in pending:
        w = by_id[wid]
        extra = f"\n\nYour previous attempt for window_id {wid!r} failed validation for these specific reasons — fix them:\n{json.dumps(failures)}"
        async with semaphore:
            try:
                raw_retry = await _attempt_batch(llm, tier, [w], extra)
            except Exception as exc:
                results[wid] = {"window_id": wid, "llm_status": "failed", "memory": None, "raw": None,
                                "failures": [f"retry_call_failed:{exc}"], "first_attempt_ok": False}
                continue
        if wid in raw_retry:
            entry2, failures2 = _validate_one(wid, raw_retry[wid], w["record"], w.get("prior_record"))
            if entry2 is not None:
                results[wid] = {"window_id": wid, "llm_status": "ok", "memory": entry2, "raw": json.dumps(raw_retry[wid]),
                                "failures": [], "first_attempt_ok": False, "first_attempt_failures": failures}
                continue
            logger.warning(f"memory_llm: {wid} rejected after retry: {failures2}")
            results[wid] = {"window_id": wid, "llm_status": "rejected", "memory": None, "raw": json.dumps(raw_retry[wid]),
                            "failures": failures2, "first_attempt_ok": False, "first_attempt_failures": failures}
        else:
            results[wid] = {"window_id": wid, "llm_status": "rejected", "memory": None, "raw": None,
                            "failures": failures + ["missing_from_retry_response"], "first_attempt_ok": False}

    return [results[w["window_id"]] for w in batch]


async def run_llm_step(windows: list[dict]) -> list[dict]:
    """windows: list of {'window_id','tier','record': dict,'prior_record': dict|None}, any order.
    Groups by tier and batches per BATCH_SIZE. Never raises — a client-construction failure marks
    every window 'failed' rather than losing the numeric data."""
    try:
        llm = _llm()
    except Exception as exc:
        logger.error(f"memory_llm: could not start LLM client: {exc}")
        return [{"window_id": w["window_id"], "llm_status": "failed", "memory": None, "raw": None,
                 "failures": [str(exc)], "first_attempt_ok": False} for w in windows]

    semaphore = asyncio.Semaphore(MAX_CONCURRENT_BATCH_CALLS)
    by_tier: dict[str, list[dict]] = {}
    for w in windows:
        by_tier.setdefault(w["tier"], []).append(w)

    batches = []
    for tier, ws in by_tier.items():
        size = BATCH_SIZE[tier]
        batches += [(tier, ws[i : i + size]) for i in range(0, len(ws), size)]

    batch_results = await asyncio.gather(*(process_batch(llm, tier, b, semaphore) for tier, b in batches))
    return [r for batch in batch_results for r in batch]
