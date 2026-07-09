# Rubric: Developmental Craft — Per-Chapter Context-Rich Read

**Layer:** `/config/review-rubrics/` · consumed by `developmental-editor` (design §6).
**Posture:** the top of the edit stack (developmental → line → copy). A context-rich
craft diagnosis on the **draft**, before polish is spent. **Advisory:** it scores and
writes margin notes but emits **no ^BLOCKING lines** and never blocks the gate. It is a
hard precondition for `/finalize-chapter` only via the showrunner's out-of-band clearance.

**Inputs (context-rich, NOT blind):** `{ draft text, this rubric, setting-pack,
character-bible slice, chapter brief/intent }`. **Denied** the whodunit solution — craft
review does not need it, so fair-play is never exposed.

**Output:** a verdict via `scripts/penny_verdict.py` into
`ch-MM.reviews/developmental-edit.md`, `producer: developmental-editor`,
`kind: developmental`, an overall `score` 1-5, `reviewed_draft_sha256` (the sha256 of the
draft as read — load-bearing for clearance binding), and margin notes in the body. Each
margin note **quotes the passage**, names the missing craft, and suggests a concrete move.
Write a margin note ONLY for a dimension that scores low — high-scoring dimensions get a
score but no note (full-coverage scoring, no bloat).

## What you are judging — eight obligation-aware dimensions

Judge each against *what THIS chapter must do* per its brief (a mid-book chapter is not
dinged for not re-establishing place):

1. **Setting grounding.** Is the reader anchored in place/time/sensory texture? Draws on
   the active series' setting pack under `config/setting-pack/`. Flag white-room scenes
   and inert travelogue alike.
2. **Motivation & stakes.** Is the "why" of each beat on the page, or buried in the
   author's head? Flag actions the reader can't motivate.
3. **Scene economy.** Inert detail, throat-clearing, scenes that don't turn. Flag passages
   that cost words without advancing character, plot, or tone.
4. **Scene texture / subtext.** Do scenes carry a second layer (what's unsaid), or is every
   line on-the-nose? Flag dialogue and action that state rather than imply.
5. **Interiority / emotional access.** Do we have access to the POV character's inner life
   at the moments that matter? Flag emotionally opaque beats.
6. **Show-don't-tell.** Are conclusions asserted ("she was nervous") where rendering would
   land harder? Flag told emotion/character where showing is available.
7. **Genre delivery (cozy).** Warmth, charm, comfort-tone, community texture — the cozy
   promise. Flag scenes that read cold, clinical, or generic-thriller.
8. **Hook & promise of the premise.** Especially openers: does the chapter open a question
   and end on a hook? Flag flat openings/endings that release tension.

## Thresholds (seeds, tunable during Book 1)

- **Score 5:** the dimension is fully delivered for this chapter's obligations.
- **Score 3:** functional but flat — serviceable prose a developmental editor would still
  push on.
- **Score 1:** the dimension is essentially absent (e.g. a white-room scene with no
  grounding; a beat with no discernible motivation).
- There is **no blocking threshold.** Low scores never produce a `^BLOCKING:` line; the
  read is advisory. Clearance to finalize is a deliberate showrunner act, not a score gate.

## Boundary with other tiers (do not duplicate)

- **Grammar, punctuation, consistency** belong to the copy editor — not here.
- **Sentence rhythm / word-choice polish** belong to the line editor — you diagnose craft,
  you do not rewrite prose. Revision flows back to the `drafter`.
- **Continuity, fair-play, voice-drift, structural blocking** belong to the five blind
  inspectors and the deterministic checkers — you may observe but you never block.
- **Whole-book experience** belongs to the post-assembly beta read — you are per-chapter.
