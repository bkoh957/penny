# Rubric: Continuity Drift — Tier-1 Isolated Inspector

**Layer:** `/config/review-rubrics/` · consumed by `inspector-continuity` (design §6).
**Posture:** judgment against the loaded ledger slice — does this chapter contradict
what is already canon, or have a character act on what they cannot yet know.

**Inputs (fixed contract, §6):** `{ text, this rubric, ledger_slice }`. The slice is
`canon-core.md` + brief-derived entries + one-hop links (§4.2). No drafting history,
no other verdicts.

**Output (fixed contract, §6):**
`{ score 1-5, violations[], blocking_issues[], evidence[], reviewed_by }`, written via
`penny_verdict.write_verdict` with `producer: inspector-continuity`, `kind: inspector`.

## What you are judging

1. **Fact contradictions.** A concrete fact established in the slice (a date, a
   relationship, an object's location, a physical detail) is contradicted by this
   chapter. Cite the slice line and the chapter line.
2. **Knowledge-state violations.** A character knows or uses information their
   knowledge-state in the slice says they do not yet have. This is the cozy-mystery
   killer — the sleuth "knowing" the solution early. Cite both.
3. **Timeline coherence.** Events ordered impossibly relative to the slice's current
   timeline position.

Score 1-5 on continuity overall. Mark a specific contradiction or knowledge-state
violation **blocking** — these are correctness faults, not taste.

## Thresholds (seeds, tunable during Book 1)

- **Score 5:** no contradictions; knowledge-states all respected.
- **Score 3:** a minor detail drift, non-load-bearing.
- **Score 1:** a load-bearing contradiction or a knowledge-state break.
- **Blocking:** any fact contradiction or knowledge-state violation that the slice
  actually establishes. A fact NOT in the slice is out of scope — do not invent canon.

## Boundary with other tiers (do not duplicate)

- **Fair-play of the mystery PLAN** (clue scheduled before reveal, culprit floor) is
  `fairplay_check.py` (Tier-3, on the ledger). Whether the scheduled clue is on the
  PAGE is `inspector-fairplay`. You judge continuity, not fairness.
- **Prose tics / taste** belong to `voice_drift.py` and `inspector-ai-prose`.
