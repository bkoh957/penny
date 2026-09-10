# Rubric: Structure & Tension — Tier-1 Isolated Inspector

**Layer:** `/config/review-rubrics/` · consumed by `inspector-structure` (design §6, §8).
**Posture:** judgment of dramatic shape — the chapter's tension curve and how it ends.

**Inputs (fixed contract, §6):** `{ text, this rubric }`. No ledger slice, no drafting
history: both of the things judged here are properties of the page.

**Output (fixed contract, §6):** `{ score 1-5, violations[], blocking_issues[],
evidence[], reviewed_by }`, `producer: inspector-structure`, `kind: inspector`.

## What you are judging

1. **Tension curve / sagging middle.** Does the chapter advance or deflate tension?
   Flag a chapter that resolves its stakes with no cost or marks time without
   complication (design §8: sagging middle, conflict resolved too easily).
2. **Hook-out.** Cozy chapters end on a hook (genre rule). Flag a flat ending.

**Per-thread dormancy is not checked here.** A named thread going quiet is caught at
book scale by `tension_check.py`'s `starved-thread`, which reads each chapter's
`### Track Movement` rows against the genre beat sheet's `tracks.max_dark_gap` — a
property of the whole outline that no per-chapter read can see.

Score 1-5 on structure. Mark **blocking** for a genuinely deflated/no-stakes chapter.

## Thresholds (seeds, tunable during Book 1)

- **Score 5:** rising tension, costed complications, strong hook.
- **Score 3:** functional but slack in the middle.
- **Score 1:** no stakes movement; flat ending.
- **Blocking:** a no-stakes/deflated chapter.

## Boundary with other tiers (do not duplicate)

- Book-scale track starvation is `tension_check.py`'s `starved-thread`, not you.
- Cross-BOOK thread fatigue is the Phase-8 cross-book reviewer, not you (single book).
- Recording what advanced is the ledger-updater's job (Phase 4); you only flag.
