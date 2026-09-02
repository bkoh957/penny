# Handoff — Penny (fiction-series engine) / readiness-briefs
Saved: 2026-08-25 | Type: build (shipped)

> **Stream note.** A single-check stream: `readiness_check` demanded a directory the
> packet/map redesign had retired, so a correctly-configured series reported
> **NOT-READY** for a reason that no longer existed. Diagnosed in a prior session,
> executed and pushed in this one (`main` → `2be1a40`). Nothing remains — the series
> repo needs no change either, which is what distinguishes it from its siblings.
> Sits beside `HANDOFF.md` (chapter types + length-profile schema, 2026-08-25),
> `HANDOFF-of122.md` (reveal-relative emissions, 2026-08-25),
> `HANDOFF-story.md` (story-layer build, 2026-08-06) and `HANDOFF-direction.md`
> (strategy proposals, unapproved, 2026-08-11).

## What we built

Deleted the `chapter-briefs` block from `scripts/readiness_check.py`'s `book_inputs`
tier — eleven lines, and the only place in the engine that still named
`series/briefs/book-NN`.

That directory was the drafter's input before the 2026-07-18 packet/map redesign retired
`/build-briefs`. Since then nothing has written it and nothing has read it, so every
series has been failing one of twenty checks forever. `~/myBooks/pelicanscrook-series`
with book 01 locked and chapter 1 mapped now reports `ready: 19, missing: 0,
verdict: READY` — the truthful answer for a book in that state.

The point is not the eleven lines. **A NOT-READY verdict everyone has learned to ignore
is worse than no verdict**, because the next genuine failure in that tier renders
identically to this one. Same family as the two fixes in `HANDOFF.md` (`dccd9aa`,
`467415f`): a mechanism that outlived its process, where the only signal was something
nobody read closely.

## Git state

- Branch: `main`, clean except the untracked `HANDOFF*.md` files (never committed here).
- Last commit: `2be1a40 readiness_check: drop the retired chapter-briefs check` —
  **pushed** (`467415f..2be1a40`).
- Tests: **1101 passed**, full suite, after the change.

## Next actions

**None for this stream.** It is closed. If you picked this file up expecting work, the
work is already on `main`.

## Decisions made this session

- **Deleted rather than repointed at packets/maps.** The obvious instinct is to swap in
  `input/book-NN/packets/` and `input/book-NN/maps/`. Two reasons not to, and they are
  the reason this stream is closed rather than half-done:
  - `book_status.py` already tracks both properly — per-chapter counts with separate RUN
    and PASS columns. `readiness_check`'s third tier (`pipeline_progress`) already
    mirrors it for the summary view.
  - `book_inputs` is for what exists **once, per book, before drafting** — the ledger,
    the fairplay result, the entity list, the lock. Packets and maps are neither once nor
    before; they are per-chapter artefacts produced *during* the pipeline. Putting them
    here would make a book report NOT-READY until all 35 chapters were mapped, inverting
    what the tier is for.
- **Kept `readiness_check` itself.** Its `engine_and_config` tier covers fifteen things
  nothing else in the engine checks: run-config, review-panel routing, voice-pack,
  ai-tics config and detection, lexicon, setting-pack, genre-pack, length-profile,
  line-edit, copy-edit, review-rubrics, beta-personas, beta-protocol, canon-core. "Is
  this series wired up to run at all" is a different question from `book_status`'s "how
  far through is this book", and it is the one that bites when a new series is
  scaffolded.
- **Replaced the deleted test rather than just dropping it.** `test_briefs_dir_present_ready`
  created `series/briefs/book-01/ch-01-brief.md` purely to make the check pass — the
  staleness in fixture form, the only thing in the repo that had written a brief file
  since the redesign. Its replacement, `test_book_ready_without_briefs_dir`, asserts the
  converse: ledger + entities + lock present, no `series/briefs/` on disk anywhere, every
  `book_inputs` row ready, `verdict: READY`. A deletion with no test leaves nothing
  pinning the new behaviour.

## User preferences expressed this session

- Commit when the work is done; push only when asked (push came as a separate
  instruction, as it did in `HANDOFF-of122.md`).

## Key files right now

- `scripts/readiness_check.py` — the `book_inputs` builder; the `chapter-briefs` block
  used to sit between the fairplay/entities branch and `mystery-lock`.
- `tests/test_readiness_check.py` — `test_book_ready_without_briefs_dir` at the tail of
  the per-book-inputs section.

## Watch out for

- **Two files still match "briefs" and both should stay.**
  `tests/test_map_chapter_command.py:2` is a docstring citing the old test's git path;
  `tests/test_preflight.py:541` is a comment noting that `cmd_draft` polices the
  packet/map chain instead of briefs. Both accurate. So is `commands/map-chapter.md`'s
  "replaces /build-briefs" description, and `commands/finalize-chapter.md:148`, which is
  an unrelated scratch path under `.penny/tmp/`.
- **Don't re-add a per-chapter artefact check to `book_inputs`** without re-reading the
  tier rule above — the deletion is only correct because `book_status.py` already covers
  that ground.
- `CLAUDE.md` says the suite is 350 tests; it is 1101. Stale doc, not a regression —
  same note as `HANDOFF-of122.md` carried at 1087.
