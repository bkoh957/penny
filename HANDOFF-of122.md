# Handoff — Penny (fiction-series engine) / of122
Saved: 2026-08-25 13:38 | Type: build (a bug fix, shipped)

> **Stream note.** A single-bug stream, opened for a defect the writing agent found
> while drafting book 01 in `~/myBooks/pelicanscrook-series`. The engine-side work is
> **done, committed and pushed**. What remains is entirely in the SERIES repo, and is
> the showrunner's call, not the engine's. Sits beside `HANDOFF-story.md` (story-layer
> build, 2026-08-06) and `HANDOFF-direction.md` (strategy proposals, 2026-08-11) —
> neither touched this session.

## What we built

`scripts/story_cut.py`'s per-chapter emit loop interpolated `reveal_chapter` into two
lines with no comparison against the chapter being emitted, so **every chapter past the
reveal was handed both, and both were false**. Book 01 (reveal 30, 35 chapters) gave
chapters 30–35 "the solution, until chapter 30" and "do not resolve the mystery before
chapter 30" — in a stretch where the culprit is named and has already confessed. These
are the drafter's instructions: a chapter whose job is epiphany-to-verification was
being told to hedge. Bug report (from the writing agent, tracked as OF-122 in the
series' `output/book-01/reports/outline-feedback.yaml`):
`/private/tmp/claude-501/-Users-beeko-myBooks-pelicanscrook-series/abcd6607-725b-435b-b3b9-1a3061685e7c/scratchpad/penny-bug-of122.md`

Both lines are now chapter-relative:

| chapter | Character Knowledge | Guardrails |
|---|---|---|
| before reveal | `Not yet known: — The solution, until chapter NN.` | `Do not resolve the mystery before chapter NN.` |
| the reveal chapter | `Revealed here: — The solution is revealed in this chapter.` | unchanged |
| after reveal | `Known from here on: — The solution, known since chapter NN.` | `The mystery resolved in chapter NN; do not write it as still open.` |

## Git state

- Branch: `main`, clean, pushed (`36bc2a1..12ab467`).
- Last commit: `12ab467 story_cut: the reveal-relative lines now know which side they are on`
- Tests: **1087 passed** (`python3 -m pytest`). Five new regressions in
  `tests/test_story_cut_emit.py`.

## Next actions

All of these are in `~/myBooks/pelicanscrook-series`, not this repo. **None is started.**

1. **Re-cut book 01** so the fix reaches the derived outline —
   `python3 ~/myTools/penny/scripts/story_cut.py 01` from the series root. `outline.md`
   is derived, so the book keeps the false lines until this runs; hand-editing it is
   pointless, the next cut overwrites it.
2. **The re-cut rewrites `plant_chapter:` in `series/whodunit/book-01.yaml`**, so the
   existing mystery lock must be deleted first (`.penny/locks/book-01.mystery.lock`) and
   re-minted after with `preflight lock-mystery 01`. Carry forward whatever `--waive`
   flags the current certificate records — read it before deleting it.
3. **Mark OF-122 `solved`** in the series'
   `output/book-01/reports/outline-feedback.yaml` (hand-edited; the ledger is
   append-only and the showrunner owns each `state:`).
4. Any chapter already drafted from a post-reveal packet (ch 30–35) is worth re-reading
   for hedged prose — the bad instruction was in the packet, so a literal-minded drafter
   may have obeyed it.

## Decisions made this session

- **The reveal chapter keeps the guardrail but loses "not yet known".** The bug report
  flagged this as a deliberate choice and it was taken deliberately: the solution *is*
  known in the reveal chapter — that is what the reveal is — so `Not yet known` is
  plainly false there, while "do not resolve **before** ch NN" is still true *in* ch NN,
  where it reads as "the reveal belongs here, not earlier". Different boundaries: `<` for
  Character Knowledge, `<=` for the guardrail. This also keeps
  `test_series_guardrail_and_reveal_line_still_follow_the_authored_ones` green, which
  pinned the guardrail line in a fixture whose reveal chapter *is* chapter 2.
- **Emit the true counterpart, not silence.** The report's minimum was "stop asserting
  the false thing". Deleting alone leaves the endgame drafter inferring the knowledge
  state from beats, and the failure mode being fixed *is* hedged pre-reveal prose in the
  endgame — so the inverted lines name it directly. Both are derived and deterministic;
  no LLM judgment enters `scripts/`.
- **No chapter-specific knowledge modelling.** The report's ideal ("ch 31 knows Marion is
  Tara, ch 32 has heard the confession privately") was NOT built: the engine has strands,
  not a per-character knowledge state, and inventing one is a design change, not a fix.
- **Verified read-only.** The book-01 check imported `emit_outline` and diffed in memory
  rather than running the cut in the series repo — running it would have rewritten
  `outline.md` and the ledger's `plant_chapter:` values and invalidated the lock, which
  is the showrunner's decision (see Next actions). Result: 29 pre-reveal lines, 30
  guardrails, 1 "revealed here", 5 of each post-reveal line, across 35 chapters.
- **Specs left alone, `CLAUDE.md` updated.** `2026-08-04-chapter-direction-and-guardrails-design.md`
  §106 still says the line is emitted "unchanged" — dated design records aren't rewritten
  in this repo; the live doc is.

## User preferences expressed this session

- Fix first, commit only when asked — the commit and push came as a separate instruction.
- Don't touch the series repo without being asked; engine changes and series data are
  separate decisions.

## Key files right now

- `scripts/story_cut.py` — the two guarded emissions, ~line 499 (Character Knowledge)
  and ~line 520 (Guardrails), each with the reasoning in a comment above it.
- `tests/test_story_cut_emit.py` — new section at the tail, `LATE_REVEAL_STORY` /
  `LATE_REVEAL_PLAN`, four chapters revealing at ch 3.
- `CLAUDE.md:177` — the paragraph recording that the derived lines are chapter-relative.

## Watch out for

- **Why this survived 475 commits: every pre-existing fixture reveals in its LAST
  chapter**, so there was no "after" to get wrong. Any new test about reveal-relative
  behaviour needs `LATE_REVEAL_*` (reveal at 3 of 4) or it proves nothing.
- **This was never a blind-read leak.** `plot_stage.readers_copy_text` is allowlist-based
  (Character Knowledge and Guardrails are not admitted) *and* truncates at
  `reveal_chapter − 1`, so post-reveal chapters never reach the fan at all. Confirmed,
  and `test_character_knowledge_section_never_reaches_the_reader` stays green. Don't
  re-investigate it as fan-read contamination.
- `CLAUDE.md` says the suite is 350 tests; it is 1087. Stale doc, not a regression.
- No script parses *inside* `### Character Knowledge` — `packet_assemble` slices the
  section whole — which is why its internal shape was free to change. Check that again
  before changing the shape a second time.
