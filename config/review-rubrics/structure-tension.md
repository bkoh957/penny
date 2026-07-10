# Rubric: Structure & Tension — Tier-1 Isolated Inspector

**Layer:** `/config/review-rubrics/` · consumed by `inspector-structure` (design §6, §8).
**Posture:** judgment of dramatic shape + a deterministic-ish thread-liveness check
against a supplied roster.

**Inputs (fixed contract, §6) + roster:** `{ text, this rubric, ledger_slice }` plus a
**thread roster** `[{ thread_id, last_advanced_chapter }]` (from `threads/*.md` +
`arc-ledger.md`). No drafting history.

**Output (fixed contract, §6):** `{ score 1-5, violations[], blocking_issues[],
evidence[], reviewed_by }`, `producer: inspector-structure`, `kind: inspector`.

## What you are judging

1. **Tension curve / sagging middle.** Does the chapter advance or deflate tension?
   Flag a chapter that resolves its stakes with no cost or marks time without
   complication (design §8: sagging middle, conflict resolved too easily).
2. **Hook-out.** Cozy chapters end on a hook (genre rule). Flag a flat ending.
3. **Thread liveness.** For each roster thread, if `last_advanced_chapter` is known
   and this chapter is more than `thread_dormant_after_chapters` beyond it AND this
   chapter does not advance it, flag the thread dormant.
   **EMPTY-STATE:** if `last_advanced_chapter` is `unknown` (pre-Phase-4, before the
   ledger-updater maintains it), emit **NO** liveness flag for that thread — do not
   compute liveness from a missing value.

Score 1-5 on structure. Mark **blocking** for a genuinely deflated/no-stakes chapter
or a confirmed dormant load-bearing thread.

## Thresholds (seeds, tunable during Book 1)

- **Score 5:** rising tension, costed complications, strong hook.
- **Score 3:** functional but slack in the middle.
- **Score 1:** no stakes movement; flat ending; a load-bearing thread gone dormant.
- **Blocking:** a no-stakes/deflated chapter, or a confirmed (non-`unknown`) dormant
  thread past the threshold.
- `thread_dormant_after_chapters` default 3 (run-config.md).

## Boundary with other tiers (do not duplicate)

- Cross-BOOK thread fatigue is the Phase-8 cross-book reviewer, not you (single book).
- Recording what advanced is the ledger-updater's job (Phase 4); you only flag.
