"""Event evidence for one packet (spec 8, E1 to E6; 9.2; 9.3). The record holds no statistics: each factor points to its relationship record, plus the event's own exposure state
and, for event-level checks, the event-specific statistic. A record is never changed after it is written; a label that needs later data is filled by a completion."""

from collections import Counter
from datetime import date, datetime, time, timedelta

import numpy as np

from v0_code.evidence_engine import event_checks as ec
from v0_code.evidence_engine.config import EvidenceConfig
from v0_code.evidence_engine.data import EvidenceData
from v0_code.evidence_engine.library import KEY, Library
from v0_code.evidence_engine.refresh import DailyRefresh
from v0_code.evidence_engine.storage import EvidenceStore
from v0_code.evidence_engine.units import Unit

COUNT_KEYS = ("supported", "suggestive", "not_supported", "insufficient", "not_applicable", "not_yet_available")


class EventEngine:
    def __init__(self, data: EvidenceData, lib: Library, cfg: EvidenceConfig, store: EvidenceStore, refresh: DailyRefresh):
        self.data, self.lib, self.cfg, self.store, self.refresh = data, lib, cfg, store, refresh
        self._rels: dict[date, dict] = {}

    # ---- helpers ------------------------------------------------------------------------------------------------------------------------------------
    def _outcome_date(self, rule_id: str | None, T: datetime) -> date:
        """spec 3.1 rule 1: the local date of opened_at, or the day before for an end-of-day outcome."""
        for p in self.lib.runnable():
            if p["rule"] == rule_id:
                if self.lib.outcomes[p["outcome"]].get("outcome_date") == "opened_date_minus_1":
                    return T.date() - timedelta(days=1)
                break
        return T.date()

    def relationships(self, D: date) -> dict:
        """E2: the relationship evidence of the outcome date, made now if it does not exist yet."""
        if D not in self._rels:
            if not self.store.has_date(D.isoformat(), self.cfg.method_version):
                self.refresh.refresh(D)
            self._rels[D] = {r["evidence_id"]: r for r in self.store.relationships_on(D.isoformat())}
        return self._rels[D]

    def _meal(self, handoff: dict) -> dict | None:
        lm = (handoff.get("context") or {}).get("last_meal")
        if not lm:
            return None
        t = datetime.fromisoformat(lm["time"]).astimezone(self.data.tz)
        return {"label": lm["label"], "time": t, "kind": self.data.kind_of(lm["label"])}

    def _not_tested(self, packet: dict) -> list[dict]:
        out = [{"candidate": n["candidate"], "reason": "not_selected_budget" if n["reason"] == "budget" else n["reason"]} for n in packet.get("not_selected", [])]
        out += [{"candidate": s["candidate"], "reason": "skipped_by_packet", "packet_reason": s["reason"], "packet_detail": s["detail"]} for s in packet.get("skipped", [])]
        rank = {p["candidate"]: p["rank"] for p in self.lib.pairs if p["rule"] == (packet.get("matched_rule") or {}).get("rule_id")}
        return sorted(out, key=lambda x: rank.get(x["candidate"], 10 ** 6))                      # in rank order where the library knows the candidate; packet order otherwise

    # ---- the event exposure state (7.4) ---------------------------------------------------------------------------------------------------------------------
    def exposure_state(self, pair: dict, scope, D: date, T: datetime, meal: dict | None) -> dict:
        exposure, outcome = self.lib.exposures[pair["exposure"]], self.lib.outcomes[pair["outcome"]]
        tag = KEY.match(pair["key"]).group(2)
        unit_kind = outcome["unit"]
        if unit_kind == "meal":
            start, udate = (meal["time"] if meal else T), (meal["time"].date() if meal else D)
            anchor = "meal_start"
        elif unit_kind == "hour":
            start, udate, anchor = T.replace(minute=0, second=0, microsecond=0), T.date(), "hour_start"
        elif unit_kind == "reading":
            start, udate, anchor = T, T.date(), "opened_at"
        else:
            start, udate, anchor = T, D, "outcome_date"
        unit = Unit(start, start, udate, float("nan"), scope)
        v, why, pending = self.refresh.ev.event_value(exposure, tag, outcome, unit, pair["ordering"] == "excludes_outcome_day", T)
        out = {"anchor": anchor}
        if v is None:
            return {"state": "not_yet_available", "available_at": pending, **out} if pending else {"state": "no_data", **out}
        series = self.refresh.series(pair, scope)
        if exposure["form"] == "binary":
            if exposure.get("binarize"):
                th = series.at(D, self.data.tz).threshold
                exposed = th is not None and v >= th
            else:
                exposed = v == 1.0
            state = "exposed" if exposed else ("not_yet_available" if pending else "not_exposed")
            return {"state": state, **({"available_at": pending} if state == "not_yet_available" else {}), **out}
        ref = series.reference(D, self.data.tz)
        pct = round(100 * float(np.mean(ref <= v)), 1) if len(ref) else None
        q = self.cfg.event_exposure["tail_quantile"] * 100
        worse = pct is not None and (pct <= q if exposure["risk_side"] == "low" else pct >= 100 - q)
        return {"state": "exposed" if worse else "not_exposed", "tail_percentile": pct, **out}

    # ---- overlap (7.2) ------------------------------------------------------------------------------------------------------------------------------------
    def _overlap(self, items: list[tuple[str, dict, object, dict]], D: date) -> list[dict]:
        tail = self.cfg.overlap["tail_quantile"]
        sets = {}
        for key, pair, scope, _ in items:
            ser = self.refresh.series(pair, scope)
            sets[key] = (*ser.exposed_dates(D, self.data.tz, tail), "binary" if ser.binary else "worst_quartile")
        out = []
        for i in range(len(items)):
            for j in range(i + 1, len(items)):
                ka, kb = items[i][0], items[j][0]
                cands = []
                for a, b in ((ka, kb), (kb, ka)):
                    ua, ea, va = sets[a]
                    ub, eb, vb = sets[b]
                    uni = ua & ub
                    A, B = ea & uni, eb & uni
                    sg = len(A & B) / len(A) if A else 0.0
                    so = len(B) / len(uni) if uni else 0.0
                    cands.append((sg, a, b, va, vb, so))
                sg, a, b, va, vb, so = max(cands, key=lambda c: c[0])
                ratio = sg / so if so > 0 else None
                ov = self.cfg.overlap
                out.append({"a": a.split("->")[0], "b": b.split("->")[0], "a_view": va, "b_view": vb, "share_given_a": round(sg, 2), "share_overall": round(so, 2),
                            "ratio": round(ratio, 2) if ratio is not None else None, "flag": bool(sg >= ov["min_share_given_a"] and ratio is not None and ratio >= ov["min_ratio"])})
        return out

    # ---- the record (E1 to E6) ------------------------------------------------------------------------------------------------------------------------------
    def record(self, packet: dict, handoff: dict) -> dict:
        cfg = self.cfg
        T = datetime.fromisoformat(handoff["opened_at"]).astimezone(self.data.tz)
        rule = (packet.get("matched_rule") or {}).get("rule_id")
        D = self._outcome_date(rule, T)
        rec = {"evidence_id": f"ev_{packet['handoff_id']}", "packet_id": packet["packet_id"], "handoff_id": packet["handoff_id"], "rule_id": rule, "event_time": handoff["opened_at"],
               "as_of_date": D.isoformat(), "method_version": cfg.method_version, "config_version": cfg.config_version, "factors": [], "overlap": [], "not_tested": self._not_tested(packet)}
        if packet.get("status") in ("deferred", "unmatched"):                                   # E1
            rec["counts"] = self._counts([], rec["not_tested"])
            return rec
        meal = self._meal(handoff)
        rels = self.relationships(D)
        strong = []
        for sel in sorted(packet["selected"], key=lambda s: s["rank"]):
            pair = self.lib.pair(rule, sel["rank"])
            f = {"rank": sel["rank"], "weight_tier": sel["weight_tier"], "candidate": sel["candidate"], "check_type": sel["check_type"], "relationship_evidence_id": None,
                 "support": "insufficient", "flags": [], "event_exposure": None, "event_specific": None}
            if pair is None or pair["candidate"] != sel["candidate"]:
                f.update(reason="not_in_library")
            elif pair["status"] == "no_definition":
                f.update(reason="no_definition")
            elif pair["status"] == "rule_deferred":
                f.update(support="not_applicable", reason="rule_deferred")
            elif pair["status"] == "event_level":
                chk = self.lib.event_checks[pair["event_check"]]
                r = ec.CHECKS[chk.get("measure")](ec.EventCtx(self.data, cfg, T, D, meal, chk))
                f.update(support=r["support"], event_exposure=r["event_exposure"], event_specific=r["event_specific"])
                if "reason" in r:
                    f["reason"] = r["reason"]
            else:                                                                               # runnable
                outcome = self.lib.outcomes[pair["outcome"]]
                scope = None
                if outcome.get("scope") == "event_kind":
                    scope = meal["kind"] if meal else None
                    if scope is None:
                        f.update(reason="no_meal_kind")
                        rec["factors"].append(f)
                        continue
                key = pair["key"].replace("{meal_kind}", scope) if scope else pair["key"]
                eid = f"rel|{key}|{D.isoformat()}|{cfg.method_version}"
                r = rels.get(eid)
                if r is None:
                    f.update(reason="no_relationship")
                else:
                    f.update(relationship_evidence_id=eid, support=r["support"], flags=list(r["flags"]))
                    if r["support"] == "insufficient":
                        f["reason"] = r["insufficient_reason"]
                    if r["support"] in ("supported", "suggestive"):
                        strong.append((key, pair, scope, f))
                f["event_exposure"] = self.exposure_state(pair, scope, D, T, meal)
            rec["factors"].append(f)
        rec["overlap"] = self._overlap(strong, D) if len(strong) > 1 else []
        rec["counts"] = self._counts(rec["factors"], rec["not_tested"])
        return rec

    @staticmethod
    def _counts(factors: list[dict], not_tested: list[dict]) -> dict:
        c = Counter(f["support"] for f in factors)
        return {"factors": len(factors), **{k: c.get(k, 0) for k in COUNT_KEYS}, "not_tested": len(not_tested)}

    def process(self, packet: dict, handoff: dict) -> tuple[dict, str]:
        """E6: write the record once. Writing the same packet again gives the same record (`same`); a record that would differ leaves the stored one in place (`differs`)."""
        rec = self.record(packet, handoff)
        how = self.store.put_event(rec)
        return (self.store.get_event(rec["evidence_id"]) if how == "differs" else rec), how

    # ---- completions (7.3, 9.3) -----------------------------------------------------------------------------------------------------------------------------
    def complete(self, evidence_id: str, data_until: datetime | None = None) -> list[dict]:
        """Fill the labels that were written as `not_yet_available` once the readings they need exist. Never changes the event record. In a replay the driver calls this right
        after the record is written; `data_until` limits the data to what exists so far."""
        rec = self.store.get_event(evidence_id)
        if rec is None:
            return []
        T = datetime.fromisoformat(rec["event_time"]).astimezone(self.data.tz)
        done = []
        have = {c["candidate"] for c in self.store.completions() if c["evidence_id"] == evidence_id}
        for f in rec["factors"]:
            if f["support"] != "not_yet_available" or f["candidate"] in have:
                continue
            pair = self.lib.pair(rec["rule_id"], f["rank"])
            chk = self.lib.event_checks[pair["event_check"]]
            end = datetime.fromisoformat(f["event_specific"]["earliest_evaluation_time"])
            last = max((r.ts for r in self.data.records(chk["source"]) if r.ts is not None), default=None)
            if (data_until is not None and data_until < end) or last is None or last < end:
                continue
            feats = ec.isolated_reading_features(self.data, self.cfg, chk, T, data_until)
            support = ec.shape_support(feats)
            span = {"start": (T - timedelta(minutes=int(chk["window_minutes"]))).isoformat(), "end": end.isoformat()}
            if self.store.put_completion(evidence_id, f["candidate"], support, feats, span):
                done.append({"evidence_id": evidence_id, "candidate": f["candidate"], "support": support, "result": feats, "evaluated_from": span})
        return done
