"""Reads the three upstream databases, read-only: hand-offs (State Engine), packet statuses (Rulebook Lookup), event evidence and completions (Evidence Engine)."""

from v0_code.evidence_engine.storage import EvidenceStore
from v0_code.findings_engine.config import FindingsConfig
from v0_code.rulebook_lookup.storage import PacketStore
from v0_code.state_engine.storage import StateStore


def load_inputs(cfg: FindingsConfig) -> dict:
    state = StateStore(cfg.paths["state_db"], readonly=True)
    handoffs = state.handoffs()
    state.close()
    packets = PacketStore(cfg.paths["rulebook_db"], readonly=True)
    status = {p["handoff_id"]: p.get("status", "ok") for p in packets.packets()}
    packets.close()
    ev = EvidenceStore(cfg.paths["evidence_db"], readonly=True)
    evidence = {r["handoff_id"]: r for r in ev.events()}
    completions = ev.completions()
    ev.close()
    return {"handoffs": handoffs, "packet_status": status, "evidence": evidence, "completions": completions}
