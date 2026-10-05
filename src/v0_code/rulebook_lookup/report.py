"""The run report: counts by rule and status, selected / skipped / not selected per candidate per rule, and the candidates never selected. Presentation only."""

from collections import Counter, defaultdict

from v0_code.rulebook_lookup.rulebook import Rulebook


def summarise(packets: list[dict], book: Rulebook) -> dict:
    by_rule = defaultdict(list)
    for p in packets:
        by_rule[p["matched_rule"]["rule_id"] if p["matched_rule"] else None].append(p)
    per_candidate = {}
    for r in book.rules:
        ps = by_rule.get(r.rule_id, [])
        rows = []
        for c in book.candidates.get(r.rule_id, ()):
            sel = sum(any(x["candidate"] == c.candidate for x in p["selected"]) for p in ps)
            skip = Counter(x["reason"] for p in ps for x in p["skipped"] if x["candidate"] == c.candidate)
            cut = Counter(x["reason"] for p in ps for x in p["not_selected"] if x["candidate"] == c.candidate)
            rows.append({"rank": c.rank, "tier": c.tier, "candidate": c.candidate, "selected": sel, "skipped": dict(skip), "not_selected": dict(cut), "never": bool(ps) and sel == 0})
        per_candidate[r.rule_id] = rows
    return {"by_rule": by_rule, "per_candidate": per_candidate}


def render(packets: list[dict], book: Rulebook) -> str:
    s = summarise(packets, book)
    status = Counter(p.get("status", "ok") for p in packets)
    out = ["# Rulebook Lookup run report", "", f"rulebook_version `{book.version}` ({book.review_status}); {len(packets)} packets. Status counts: " + ", ".join(f"{k} {v}" for k, v in sorted(status.items())), "",
           "## By rule", "", "| rule | status | hand-offs | selected per packet | skipped (sum) | not selected (sum) | bar hint |", "|---|---|---|---|---|---|---|"]
    for r in book.rules:
        ps = s["by_rule"].get(r.rule_id, [])
        sel = sorted({p["counts"]["selected"] for p in ps})
        hints = Counter(p["evidence_bar_hint"] for p in ps)
        out.append(f"| `{r.rule_id}` | {r.status} | {len(ps)} | {', '.join(map(str, sel)) or '-'} | {sum(p['counts']['skipped'] for p in ps)} | {sum(p['counts']['not_selected'] for p in ps)} | "
                   + ", ".join(f"{k} {v}" for k, v in sorted(hints.items())) + " |")
    if s["by_rule"].get(None):
        out.append(f"| (unmatched) | - | {len(s['by_rule'][None])} | - | - | - | - |")
    out += ["", "## Per candidate (packets in which it was selected / skipped / not selected)", ""]
    never = []
    for r in book.rules:
        ps = s["by_rule"].get(r.rule_id, [])
        out += [f"### `{r.rule_id}` ({len(ps)} packets)", "", "| # | tier | candidate | selected | skipped | not selected |", "|---|---|---|---|---|---|"]
        for row in s["per_candidate"][r.rule_id]:
            fmt = lambda d: ", ".join(f"{k} {v}" for k, v in d.items()) or "-"
            out.append(f"| {row['rank']} | {row['tier']} | {row['candidate']} | {row['selected']} | {fmt(row['skipped'])} | {fmt(row['not_selected'])} |")
            if row["never"] or (not ps and r.status == "deferred"):
                never.append((r.rule_id, row["candidate"]))
        out.append("")
    n_cands = sum(len(v) for v in book.candidates.values())
    out += [f"## Candidates never selected ({len(never)} of {n_cands})", ""] + [f"- `{rid}`: {name}" for rid, name in never]
    return "\n".join(out) + "\n"
