Let me confirm back what I understood before writing any code, since a couple of your framings shift roles slightly from what we had earlier — worth syncing explicitly rather than silently coding my old assumptions.

## What I understood

**Scope for this first pass:** a single straight chain, no GI Aggregator, no Pattern Discovery Engine branching, no personalization-loop-back complexity yet. Just: does data correctly flow start to finish, one path, for one event.

**The chain, in order:**
```
Short-Range Event Linker + Working Memory Buffer
        ↓
Personal Data Store
        ↓
Baseline Engine
        ↓
State Engine
        ↓
Rulebook Lookup (static)
        ↓
Evidence Engine
        ↓
Findings Engine
        ↓
Personalized Rulebook (memory store)
        ↓
3 outputs (baseline / what happened / why)
```

**Role clarifications you're making, which are genuine refinements to what we had:**

1. **Baseline Engine = short + mid-term memory.** This is a slight reframe from before — we'd treated Baseline purely as "her averaged normal," but you're now explicitly calling it a *memory tier*, not just a stats output. I'll treat it as: holds recent-window averages (short-term) and a slightly longer rolling view (mid-term), not just one static number.

2. **Rulebook Lookup + Short-Range Linker = static rule-based, no learning in this pass.** Confirmed — no GI Aggregator feeding back into Rulebook Lookup yet; it's a fixed lookup table for now.

3. **Evidence Engine = takes what Rulebook Lookup handed it, and makes sense of the data.** Same as before — statistical testing.

4. **Findings Engine is actually the component that reads memory and diary, not just Evidence Engine's output.** This is the real shift — previously Findings Engine only read Evidence Engine's output. You're now saying Findings Engine *also* directly reads: the diary/long-term context, and the **Personalized Rulebook** (which you're defining as a memory store — short+mid+episodic+long — not an active "refinement" process like we designed earlier). So Findings Engine becomes the component that synthesizes statistical evidence *with* stored personal/episodic memory to produce "what happened and why" — a slightly bigger job than before.

5. **Personalized Rulebook = pure memory, not a re-ranking engine.** This is a genuine redefinition from our earlier design — previously "Personalized Rulebook Refinement" actively reordered Rulebook Lookup's candidate list. Now you're describing it as a **passive memory store** (short/mid/episodic/long-term facts about her) that Findings Engine *reads from*, not something that writes back into Rulebook Lookup in this first pass.

## Is this right?

If I've got this correctly: **for this first coding pass, Personalized Rulebook is just storage (memory), and Findings Engine is the "smart" component that pulls together Evidence Engine's stats + the Personalized Rulebook's stored memory + diary context to produce the final why/what-happened output** — with the loop-back (Personalized Rulebook actively reshaping future Rulebook Lookup checks) deliberately deferred to a later pass, not built now.

Confirm this is the right read, and I'll move straight to scaffolding the actual code structure (likely as a Claude Code task doc, given the scale) for this single chain.