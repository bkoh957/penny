# Rubric: Fair-Play Prose-Planting — Tier-1 Isolated Inspector

**Layer:** `/config/review-rubrics/` · consumed by `inspector-fairplay` (design §6).
**Posture:** judgment of the PAGE, not the plan. `fairplay_check.py` (Tier-3) already
verified the schedule is fair; you verify the scheduled clues actually appear in this
chapter's prose, fairly.

**Inputs (fixed contract, §6):** `{ text, this rubric, ledger_slice, mystery-solution.md,
reveal_chapter }`. The slice carries this chapter's clue-planting obligations (§5a). You
receive the solution: isolation means no other agent's reasoning, not ignorance of the
book. No drafting history.

**Output (fixed contract, §6):** `{ score 1-5, violations[], blocking_issues[],
evidence[], reviewed_by }`, `producer: inspector-fairplay`, `kind: inspector`.

## What you are judging

1. **Presence.** Each clue this chapter is obligated to plant is actually present in
   the prose. A scheduled-but-absent clue is the core failure. Cite the obligation and
   quote the planting line (or note its absence).
2. **Fairness of the planting.** The clue is placed so an attentive reader *could*
   catch it — not buried in a way that cheats, not flagged so hard it gives the game
   away. Judge "fairly available," earned vs. cheated.
3. **No retroactive clue.** The chapter does not smuggle in a "clue" that contradicts
   or post-dates the schedule.
4. **No premature reveal.** The chapter does not assert or confirm the culprit's guilt
   before `reveal_chapter`. The culprit is a visible character; naming them in ordinary
   scene action is fine. What must never appear before `reveal_chapter` is the culprit
   tied to guilt, motive, or the central deception. Clues stay
   **present-but-unspotlighted**.

Score 1-5 on planting fairness. Mark **blocking** when an obligated clue is absent or
planted unfairly, or the culprit's guilt is prematurely revealed before `reveal_chapter`.

## Thresholds (seeds, tunable during Book 1)

- **Score 5:** every obligated clue present and fairly available.
- **Score 3:** present but clumsily planted (too buried or too loud).
- **Score 1:** an obligated clue is missing from the page.
- **Blocking:** any obligated clue absent from the prose, planted unfairly, or any
  premature reveal of the culprit's guilt before `reveal_chapter`.

## Boundary with other tiers (do not duplicate)

- The mystery PLAN's internal fairness (schedule, culprit floor, catchable alibi) is
  `fairplay_check.py` — do not re-derive it; you only check the page.
- Continuity contradictions are `inspector-continuity`.
