"""The State Engine tick (spec 6, rules R1 - R12). One tick evaluates every configured measure at one moment `as_of` and returns the Current State
Snapshot (spec 7.1); items and hand-offs that open or close during the tick are collected for the caller to write.

Everything is deterministic: the same inputs and config give the same snapshots, tick by tick, live or in a replay."""

import statistics
from bisect import bisect_right
from dataclasses import dataclass, field
from datetime import date as _date, datetime, timedelta

from v0_code.baseline_v2.profile import STATUS_RANK
from v0_code.state_engine.baseline import BaselineView
from v0_code.state_engine.config import LABEL_RANK, StateConfig, StreamCfg
from v0_code.state_engine.inputs import Obs, StateInputs, end_of_day
from v0_code.state_engine.position import percentile_label, sd_position
from v0_code.state_engine.runs import Tracker
from v0_code.state_engine.usual import ReadingUsual

NUMBER_WORDS = {1: "one", 2: "two", 3: "three", 4: "four", 5: "five", 6: "six", 7: "seven", 8: "eight", 9: "nine", 10: "ten"}


def iso(dt: datetime | None) -> str | None:
    return dt.isoformat() if dt else None


def minute_stamp(dt: datetime) -> str:
    return dt.strftime("%Y-%m-%dT%H:%M")


@dataclass
class MeasureState:
    cfg: StreamCfg
    tracker: Tracker
    seen_idx: int = -1                         # index (in the stream's availability order) of the newest observation already taken in
    value: Obs | None = None                   # the last GOOD value
    rejected_latest: bool = False
    item: dict | None = None                   # the open item, if any
    stale_handled: bool = False


class StateEngine:
    def __init__(self, cfg: StateConfig, inputs: StateInputs, baseline: BaselineView):
        self.cfg, self.inputs, self.baseline = cfg, inputs, baseline
        tz = cfg.tz
        self.states: dict[str, MeasureState] = {
            s.name: MeasureState(s, Tracker(cfg.open_label, cfg.close_label)) for s in cfg.streams}
        self.readings: dict[str, ReadingUsual] = {}
        meals = [(m[0], m[1]) for m in inputs.meals]
        for s in cfg.streams:
            if s.kind == "continuous" and s.usual_basis in ("glucose", "clock_time"):
                good = [o for o in inputs.obs[s.name] if not o.rejected]
                rd = [(inputs.day_index(o.value_time.date()), o.value_time.hour * 60 + o.value_time.minute, o.value, o.value_time) for o in sorted(good, key=lambda o: o.value_time)]
                self.readings[s.name] = ReadingUsual(s.name, rd, meals, cfg.meal_kinds, cfg.meal_window_minutes, cfg.meal_bucket_minutes)
        self.items_changed: list[dict] = []
        self.handoffs: list[dict] = []
        self._handed: set[str] = set()
        self._bp_hist: dict = {}

    # ---- helpers ------------------------------------------------------------------------------------------------------------------------------
    def _band(self, s: StreamCfg) -> int:
        return s.clock_band_minutes or self.cfg.clock_band_minutes

    def stale_at(self, s: StreamCfg, vt: datetime) -> datetime:
        if s.freshness_end_of_day:
            return end_of_day(vt)
        return vt + timedelta(minutes=s.freshness_minutes) if s.freshness_minutes is not None else datetime.max.replace(tzinfo=vt.tzinfo)

    def overdue_at(self, s: StreamCfg, vt: datetime) -> datetime:
        """When a daily / periodic / count / lab value becomes overdue: cadence x grace after it became available. It is overdue once its age EXCEEDS this."""
        return vt + timedelta(minutes=s.cadence_minutes * self.cfg.overdue_grace)

    def is_current(self, s: StreamCfg, vt: datetime, as_of: datetime) -> bool:
        if s.freshness_end_of_day:
            return as_of.date() == vt.date()
        return s.freshness_minutes is None or (as_of - vt).total_seconds() / 60 <= s.freshness_minutes

    def medicine(self, med_id: str) -> str:
        return self.cfg.baseline.medicine_name(med_id)

    # ---- R5 / R6: the usual and the position -------------------------------------------------------------------------------------------------
    def evaluate(self, s: StreamCfg, o: Obs, D: _date, D_idx: int, early: bool, quality: list[str], key: str) -> dict:
        """(usual, usual_alt, position) of observation `o` against the usual as of the start of D. Returns {"usual", "usual_alt", "position", "level",
        "direction", "metric", "status_dir"}; position is the string "no_baseline_yet" when there is no usual."""
        c = self.cfg
        none = {"usual": None, "usual_alt": None, "position": "no_baseline_yet", "level": None, "direction": None, "metric": None}
        method = c.method(s)
        if method == "none":
            return {**none, "position": None}
        if early:
            return none
        thr = c.thresholds_sd
        if s.kind == "continuous":
            ru = self.readings[s.name]
            t = o.value_time
            clock = ru.clock_time(D_idx, t.hour * 60 + t.minute, self._band(s))
            clock = clock if clock and clock["n"] >= c.min_samples_usual else None
            meal = None
            if s.usual_basis == "glucose":
                lm = self.inputs.last_meal(t, c.meal_window_minutes)
                kind = ru.kind_of(lm["label"]) if lm else None
                if kind:
                    meal = ru.meal_relative(D_idx, kind, (t - lm["time"]).total_seconds() / 60)
                    if meal and meal["n"] < c.min_samples_usual:
                        meal = None
                    if meal is None and c.glucose_usual_basis == "meal_relative_with_clock_fallback":
                        quality.append(f"usual_fallback:{key}")
            if s.usual_basis == "glucose" and c.glucose_usual_basis == "clock_time":
                primary, alt = clock, meal
            else:
                primary, alt = (meal, clock) if meal else (clock, None)
            if primary is None:
                quality.append(f"no_usual:{key}")
                return none
            pos = sd_position(o.value, primary["median"], primary["sd"], thr)
            out = {"usual": self._usual_view(primary), "position": {"z": round(pos["z"], 2), "label": pos["label"]}, "level": pos["level"], "direction": pos["direction"], "metric": abs(pos["z"]), "usual_alt": None}
            if alt:
                ap = sd_position(o.value, alt["median"], alt["sd"], thr)
                out["usual_alt"] = {**self._usual_view(alt), "z": round(ap["z"], 2), "label": ap["label"]}
            return out
        ref = o.record_date or D                      # the usual for a value never contains the value: it is the profile as of the START of the date the record belongs to
        if s.kind == "daily":
            prof, late = self.baseline.profile(s.name, ref)
            if late:
                quality.append("baseline_late")
            if not prof or prof.get("n_days", 0) < c.min_history_days or prof.get("median") is None:
                return none
            pos = sd_position(o.value, prof["median"], prof["sd"], thr)
            return {"usual": {"basis": "profile", "n": prof["n_days"], "median": round(prof["median"], 2), "sd": round(prof["sd"] or 0.0, 2)}, "usual_alt": None,
                    "position": {"z": round(pos["z"], 2), "label": pos["label"]}, "level": pos["level"], "direction": pos["direction"], "metric": abs(pos["z"])}
        if s.kind == "periodic":
            day0 = datetime.combine(ref, datetime.min.time(), tzinfo=c.tz)
            hist = self._bp_hist.get((s.name, ref))
            if hist is None:
                hist = self.inputs.history(s.name, day0)
                self._bp_hist[(s.name, ref)] = hist
            if len(hist) < c.min_history_days:
                return none
            usual, poss = {"basis": "profile"}, {}
            worst = None
            for comp, v in o.value.items():
                vals = [h.value[comp] for h in hist]
                sd = statistics.pstdev(vals)
                med = statistics.median(vals)
                usual[comp] = {"n": len(vals), "median": round(med, 2), "sd": round(sd, 2)}
                p = sd_position(v, med, sd, thr)
                poss[comp] = {"z": round(p["z"], 2), "label": p["label"]}
                if worst is None or abs(p["z"]) > abs(worst[1]["z"]):
                    worst = (comp, p)
            wc, wp = worst
            return {"usual": usual, "usual_alt": None, "position": {**poss, "worst": wc, "label": wp["label"]}, "level": wp["level"], "direction": wp["direction"], "metric": abs(wp["z"])}
        if s.kind == "count":
            day0 = datetime.combine(ref, datetime.min.time(), tzinfo=c.tz)
            hist = self.inputs.history(s.name, day0)
            if len(hist) < c.min_history_days:
                return none
            frac = lambda v: v["missed"].__len__() / v["expected"] if v["expected"] else 0.0
            today = frac(o.value)
            h = [frac(x.value) for x in hist]
            share_all = sum(1 for x in h if x == 0) / len(h)
            share_bad = sum(1 for x in h if x >= today) / len(h)
            k = len(o.value["missed"])
            usual = {"basis": "history_percentile", "share_all_taken": round(share_all, 2)}
            if k:
                usual[f"share_{NUMBER_WORDS.get(k, str(k))}_or_more_missed"] = round(sum(1 for x in hist if len(x.value["missed"]) >= k) / len(hist), 2)
            lvl = percentile_label(share_bad, c.thresholds_percentile) if k else "within"
            direction = "below" if (k and lvl != "within") else None
            return {"usual": usual, "usual_alt": None, "position": {"share_at_least_as_bad": round(share_bad, 2), "label": lvl if direction is None else f"{lvl} {direction}"},
                    "level": lvl, "direction": direction, "metric": 1.0 - share_bad}
        return {**none, "position": None}

    @staticmethod
    def _usual_view(u: dict) -> dict:
        return {"basis": u["basis"], "context": u["context"], "n": u["n"], "median": round(u["median"], 2), "sd": round(u["sd"], 2)}

    # ---- the tick -----------------------------------------------------------------------------------------------------------------------------
    def tick(self, as_of: datetime) -> dict:
        c = self.cfg
        D = as_of.date()
        D_idx = self.inputs.day_index(D)
        early = D_idx < c.min_history_days
        quality: list[str] = []
        if early:
            quality.append("no_baseline_yet")
        _, late = self.baseline.day_for(D)
        if late:
            quality.append("baseline_late")
        self.items_changed, self.handoffs = [], []
        self._ctx = (D, D_idx, early)
        measures: dict[str, dict] = {}
        for name, st in self.states.items():
            measures[st.cfg.key] = self._measure(st, as_of, D, D_idx, early, quality)
        open_items = [i["item_id"] for i in sorted((st.item for st in self.states.values() if st.item), key=lambda i: (i["opened_at"], i["item_id"]))]
        lm = self.inputs.last_meal(as_of, c.last_meal_window_minutes)
        snap = {
            "as_of": iso(as_of), "baseline_asof": (D - timedelta(days=1)).isoformat(), "config_version": c.version, "baseline_config_version": self.baseline.config_version(D),
            "early_days": early, "measures": measures,
            "context": {"last_meal": {"label": lm["label"], "time": iso(lm["time"]), "minutes_ago": lm["minutes_ago"]} if lm else None,
                        "diary_today": self.inputs.diary_today(as_of), "yesterday_memory_headline": self.baseline.yesterday_headline(D)},
            "open_items": open_items, "open_item_classes": {i["item_id"]: i["item_class"] for i in sorted((st.item for st in self.states.values() if st.item), key=lambda i: (i["opened_at"], i["item_id"]))},
            "quality": list(dict.fromkeys(quality))}
        return snap

    def _measure(self, st: MeasureState, as_of: datetime, D: _date, D_idx: int, early: bool, quality: list[str]) -> dict:
        s, c = st.cfg, self.cfg
        key = s.key
        avail = self.inputs._avail[s.name]
        idx = bisect_right(avail, as_of) - 1
        # R1 intake and R2 validity
        if idx > st.seen_idx:
            st.seen_idx = idx
            o = self.inputs.obs[s.name][idx]
            if o.rejected:
                st.rejected_latest = True
            else:
                st.rejected_latest = False
                st.value = o
                st.stale_handled = False
                # a continuous value must be fresh to count; a daily / periodic value is judged when it arrives, however late (it is newer than the last one)
                if s.tracks_overdue or self.is_current(s, o.value_time, as_of):
                    self._feed(st, o, D, D_idx, early, quality, as_of)
        if st.value is None:
            quality.append(f"no_data:{key}")
            return {"value": None, "current": False, "no_data": True}
        o = st.value
        age = round((as_of - o.value_time).total_seconds() / 60)
        current = self.is_current(s, o.value_time, as_of)
        overdue = False
        if s.tracks_overdue:
            # daily / periodic: the last value stands (`current` is informational) and its item stays open until a newer value arrives or the measure is overdue
            overdue = age > s.cadence_minutes * c.overdue_grace
            if overdue:
                quality.append(f"overdue:{key}")
                if not st.stale_handled:
                    st.stale_handled = True
                    if st.tracker.go_stale()["closed"] and st.item:
                        self._close(st, self.overdue_at(s, o.value_time), "expired")
        elif s.kind == "continuous" and not current:
            # R3, unchanged for continuous measures: a stale value has no run and keeps no item open
            quality.append(f"stale:{key}")
            if not st.stale_handled:
                st.stale_handled = True
                at = self.stale_at(s, o.value_time)
                if st.tracker.go_stale()["closed"] and st.item:
                    self._close(st, at, "stale")
        if st.rejected_latest:
            quality.append(f"rejected_latest:{key}")
        entry = self._entry(st, o, age, current, D, D_idx, early, quality)
        if s.tracks_overdue:
            entry["overdue"] = overdue
        return entry

    def _entry(self, st: MeasureState, o: Obs, age: int, current: bool, D: _date, D_idx: int, early: bool, quality: list[str]) -> dict:
        s = st.cfg
        key = s.key
        e: dict = {}
        if s.kind in ("continuous", "daily", "lab"):
            e["value"] = o.value
        elif s.kind == "periodic":
            e["value"] = dict(o.value)
        elif s.kind == "count":
            e.update({"taken": o.value["taken"], "expected": o.value["expected"], "missed": [self.medicine(m) for m in o.value["missed"]]})
        elif s.kind == "label":
            e.update({"label": o.value["label"], "block": o.value["block"]})
        if s.kind in ("continuous", "daily", "periodic", "lab"):
            e["unit"] = self.cfg.unit(s)
        e["value_time"] = iso(o.value_time)
        if s.kind not in ("count", "label"):
            e["age_minutes"] = age
        e["current"] = current
        if s.kind == "continuous":
            e["rejected_latest"] = st.rejected_latest
        if s.kind in ("continuous", "daily", "periodic", "lab"):
            e["clinical_status"] = o.status
        if self.cfg.method(s) != "none":
            ev = self.evaluate(s, o, D, D_idx, early, quality, key)
            e["usual"] = ev["usual"]
            if s.kind == "continuous" and s.usual_basis == "glucose":
                e["usual_alt"] = ev["usual_alt"]
            e["position"] = ev["position"]
            if s.kind == "continuous" or self.cfg.opens_after(s) > 1:
                e["run"] = st.tracker.snapshot()
            e["open_item_id"] = st.item["item_id"] if st.item else None
            e["open_item_class"] = st.item["item_class"] if st.item else None
        return e

    # ---- R7 - R11: runs, items, hand-offs ----------------------------------------------------------------------------------------------------
    def _feed(self, st: MeasureState, o: Obs, D: _date, D_idx: int, early: bool, quality: list[str], as_of: datetime) -> None:
        s, c = st.cfg, self.cfg
        key = s.key
        severe_status = o.status in c.severe_statuses
        has_pos = c.method(s) != "none"
        if has_pos:
            ev = self.evaluate(s, o, D, D_idx, early, [], key)             # quality notes are added when the entry is rendered
            level, direction, metric = ev["level"], ev["direction"], ev["metric"]
        else:
            ev, level, direction, metric = None, "within", None, None
        if level is None:                                                    # no usual: only a severe status can act
            level, direction = "within", None
        status_dir = None
        if severe_status:
            status_dir = "below" if o.status.endswith("low") else "above"
        severe_pos = has_pos and level != "within" and LABEL_RANK[level] >= LABEL_RANK[c.severe_position]
        severe = severe_pos or severe_status
        if severe_status and direction is None:
            direction = status_dir
        if not has_pos and not severe_status:
            return
        was_open = st.item
        res = st.tracker.new_reading(level, direction, c.opens_after(s), c.closes_after(s), severe=severe)
        # while open: track the peak (largest position, in the item's direction)
        if was_open and direction == was_open["direction"] and metric is not None and metric > was_open["peak_metric"]:
            was_open.update({"size_peak": level, "peak_at": iso(o.value_time), "peak_value": self._peak_value(o), "peak_metric": metric})
            self.items_changed.append(was_open)
        if res["closed"] and st.item:
            self._close(st, o.value_time, "recovered")
        if res["opened"]:
            self._open(st, o, level, direction, metric, "severe" if severe else "persistence", ev, as_of)

    @staticmethod
    def _peak_value(o: Obs):
        return dict(o.value) if isinstance(o.value, dict) else o.value

    @staticmethod
    def _abnormal_on_side(status: str | None, direction: str) -> bool:
        """The carried clinical status is abnormal (low / high, not borderline) on the side of the deviation."""
        return status is not None and STATUS_RANK.get(status, 0) >= 2 and status.endswith("low" if direction == "below" else "high")

    def _item_class(self, s: StreamCfg, direction: str, trigger: str, status: str | None) -> str:
        """adverse: a direction that is bad for her, a severe item, or (not for a continuous measure) a clinical status that is abnormal on that side.
        Otherwise favourable (recorded, no hand-off). A continuous measure's carried status is NOT used here: for continuous heart rate it comes from judging
        sleeping readings against an awake resting range, so for continuous measures only a `far` position can rescue a favourable item."""
        status_rescues = s.kind != "continuous" and self._abnormal_on_side(status, direction)
        return "adverse" if direction in s.adverse_directions or trigger == "severe" or status_rescues else "favourable"

    def _open(self, st: MeasureState, o: Obs, level: str, direction: str, metric, trigger: str, ev, as_of: datetime) -> None:
        s = st.cfg
        item = {"item_id": f"{s.key}_{minute_stamp(o.value_time)}", "measure": s.key, "direction": direction, "size_at_open": level, "size_peak": level,
                "opened_at": iso(o.value_time), "peak_at": iso(o.value_time), "closed_at": None, "peak_value": self._peak_value(o), "trigger": trigger, "status": "open",
                "item_class": self._item_class(s, direction, trigger, o.status), "handed_off_at": None, "close_reason": None, "peak_metric": metric if metric is not None else 0.0, "context": None}
        st.item = item
        item["context"], handoff = self._handoff_context(st, o, item, ev, as_of)
        if item["item_class"] == "adverse":                                    # a favourable item is recorded and closed like any other but is not handed off
            item["handed_off_at"] = iso(o.value_time)
            if handoff["handoff_id"] not in self._handed:                      # R11: exactly one hand-off per handed-off item, never twice
                self._handed.add(handoff["handoff_id"])
                self.handoffs.append(handoff)
        self.items_changed.append(item)

    def _close(self, st: MeasureState, at: datetime, reason: str) -> None:
        item = st.item
        item["status"], item["closed_at"], item["close_reason"] = "closed", iso(at), reason
        self.items_changed.append(item)
        st.item = None

    def _handoff_context(self, st: MeasureState, o: Obs, item: dict, ev, as_of: datetime):
        s = st.cfg
        ctx_last_meal = self.inputs.last_meal(o.value_time, self.cfg.last_meal_window_minutes)
        med = next((x for x in self.states.values() if x.cfg.kind == "count"), None)
        sleep = next((x for x in self.states.values() if x.cfg.role == "sleep"), None)
        context = {
            "last_meal": {"label": ctx_last_meal["label"], "time": iso(ctx_last_meal["time"]), "minutes_ago": ctx_last_meal["minutes_ago"]} if ctx_last_meal else None,
            "medication": ({"taken": med.value.value["taken"], "expected": med.value.value["expected"], "missed": [self.medicine(m) for m in med.value.value["missed"]]}
                           if med and med.value and med.value.value_time.date() == o.value_time.date() else None),
            "sleep_last_night": ({"value": sleep.value.value, "position": self._label_of(sleep)} if sleep and sleep.value else None),
            "other_open_items": [x.cfg.key for x in self.states.values() if x.item and x is not st],
            "diary_today_count": len(self.inputs.diary_today(o.value_time))}
        z = None
        if isinstance(ev, dict) and isinstance(ev.get("position"), dict):
            z = ev["position"].get("z")
        handoff = {"handoff_id": f"handoff_{item['item_id']}", "item_id": item["item_id"], "written_at": iso(o.value_time), "measure": s.key, "direction": item["direction"],
                   "size": item["size_at_open"], "trigger": item["trigger"], "value": self._peak_value(o), "clinical_status": o.status,
                   "usual_basis": ev["usual"]["basis"] if isinstance(ev, dict) and ev.get("usual") else None, "position_z": z, "opened_at": item["opened_at"],
                   "context": context, "snapshot_as_of": iso(as_of)}
        return context, handoff

    def _label_of(self, st: MeasureState):
        """The position label of a measure's last good value against today's usual (a string such as "clearly below", or "no_baseline_yet")."""
        D, D_idx, early = self._ctx
        pos = self.evaluate(st.cfg, st.value, D, D_idx, early, [], st.cfg.key)["position"]
        return pos["label"] if isinstance(pos, dict) else pos

    # ---- replay -------------------------------------------------------------------------------------------------------------------------------
    def ticks(self, start: _date | datetime | None = None, end: _date | None = None):
        """Ticks every `tick_minutes` from `start` (a date = its midnight, or an exact tick) to the end of `end` (default: the record's first / last day)."""
        start = start or self.inputs.first_date
        end = end or self.inputs.last_date
        t = start if isinstance(start, datetime) else datetime.combine(start, datetime.min.time(), tzinfo=self.cfg.tz)
        stop = datetime.combine(end, datetime.min.time(), tzinfo=self.cfg.tz) + timedelta(days=1)
        step = timedelta(minutes=self.cfg.tick_minutes)
        while t < stop:
            yield t
            t += step
